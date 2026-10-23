"""
BOT GOLD EMPIRE -> canale Telegram + MetaTrader 5

1. Legge i messaggi del canale "Gold empire signals room".
2. VENDI/COMPRA XAUUSD   -> apre subito a mercato su MT5 (SL = Stop,
                            TP = Obiettivo / Obiettivo 1) e pubblica il
                            segnale riformattato nel tuo canale con l'entry reale.
3. OBIETTIVO RAGGIUNTO   -> chiude (se MT5 non l'ha gia' chiusa al TP).
4. STOP A PAREGGIO       -> sposta lo SL al prezzo d'ingresso reale (BE).
5. STOP                  -> chiude (se MT5 non l'ha gia' chiusa allo SL).
6. CHIUSA                -> chiude subito a mercato.

Gli aggiornamenti sono collegati al segnale tramite la reply Telegram
(riserva: ultimo "SIGNAL N" ancora aperto). BUY e SELL possono essere
aperti contemporaneamente: ogni segnale e' una posizione a se'.

Avvio:  python main.py
"""
import asyncio
import logging
import sys
import time
from datetime import datetime, timezone

from telethon import events

import database as db
from config import (
    COMMAND_PREFIX,
    DESTINATION_CHAT,
    LOG_FILE,
    LOT_SIZE,
    MAGIC_NUMBER,
    MAX_ENTRY_DISTANCE,
    MAX_SIGNAL_AGE_SECONDS,
    MONITOR_INTERVAL_SECONDS,
    FREE_CLOSE_COOLDOWN_MINUTES,
    PENDING_EXPIRY_MINUTES,
    REVERSAL_SIGNALS,
    MT5_SYMBOL,
    PIP_SIZE,
    SOURCE_CHAT,
    TRADING_ENABLED,
)
from messages import (
    calculate_pips,
    classify_stop_close,
    help_message,
    paused_message,
    play_message,
    restart_message,
    stopped_message,
)
from signal_parser import parse_signal


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
    )
    for handler in (logging.StreamHandler(), logging.FileHandler(LOG_FILE, encoding="utf-8")):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logging.getLogger("telethon").setLevel(logging.WARNING)
    return logger


logger = setup_logging()

# Import dopo il logging: telegram_client si ferma subito se manca la config.
from telegram_client import client  # noqa: E402
from telegram_sender import (  # noqa: E402
    send_be_applied_message,
    send_close_message,
    send_open_message,
    send_sl_updated_message,
    send_text,
    send_tp_updated_message,
)
import reports  # noqa: E402
from messages import GOOD_MORNING_MESSAGE_TEMPLATE  # noqa: E402
import mt5_executor as mt5x  # noqa: E402


# ============================================================
# STATO
# ============================================================
# RUNNING -> normale | PAUSED -> nessun nuovo trade, gestisce gli aperti
# STOPPED -> posizioni chiuse, non ascolta piu' il canale
BOT_STATE = "RUNNING"
MT5_READY = False

_locks = {}


def get_lock(source_message_id):
    lock = _locks.get(source_message_id)
    if lock is None:
        lock = asyncio.Lock()
        _locks[source_message_id] = lock
    return lock


def current_pip_size():
    return mt5x.pip_size() if TRADING_ENABLED and MT5_READY else PIP_SIZE


# ============================================================
# APERTURA
# ============================================================

async def handle_open(message, signal):
    source_id = message.id

    # SIGNAL 5 / 6 (stop and reverse): prima si chiudono le operazioni dello
    # stesso SIGNAL nella direzione opposta, anche se il segnale e' in ritardo.
    if signal.get("signal_no") in REVERSAL_SIGNALS:
        await close_opposite_for_reversal(signal, source_id)

    age = (datetime.now(timezone.utc) - message.date).total_seconds()
    if age > MAX_SIGNAL_AGE_SECONDS:
        logger.warning("⏭️ SEGNALE #%s TROPPO VECCHIO (%.0fs): ignorato.", source_id, age)
        return

    async with get_lock(source_id):
        if not db.insert_signal(source_id, signal):
            return  # gia' gestito

        logger.info(
            "🎯 SIGNAL %s | %s XAUUSD | Ingresso %.2f | SL %.2f | TP %s%s | #%s",
            signal["signal_no"], signal["direction"], signal["entry"], signal["sl"],
            f"{signal['tp']:.2f}" if signal["tp"] else "nessuno (chiusura a segnale)",
            f" (obiettivo 1 di {signal['targets_total']})" if signal["targets_total"] > 1 else "",
            source_id,
        )

        if BOT_STATE == "PAUSED":
            logger.warning("⏸️ BOT IN PAUSA: trade non aperto | #%s", source_id)
            db.set_status(source_id, "PAUSED_NO_NEW_TRADE")
            return

        if TRADING_ENABLED:
            if not MT5_READY:
                logger.error("❌ MT5 NON PRONTO: trade non aperto | #%s", source_id)
                db.set_status(source_id, "MT5_NOT_READY")
                return
            try:
                if signal.get("order_type", "MARKET") == "MARKET":
                    result = await asyncio.to_thread(mt5x.open_market_order, signal)
                else:
                    result = await asyncio.to_thread(mt5x.place_pending_order, signal)
            except ValueError as exc:
                logger.warning("⏭️ TRADE NON APERTO | #%s | %s", source_id, exc)
                db.set_status(source_id, "SKIPPED", error=str(exc))
                return
            except Exception as exc:
                logger.exception("❌ ERRORE APERTURA | #%s", source_id)
                db.set_status(source_id, "ERROR", error=str(exc))
                return
            if isinstance(result, mt5x.PendingResult):
                db.mark_pending(source_id, result.order_ticket)
                logger.info(
                    "🕓 %s %s PIAZZATO | Order %s @ %.2f | pubblicato nel canale quando viene eseguito",
                    signal["direction"], signal["order_type"], result.order_ticket, result.price,
                )
                return
            position_ticket, open_price = result.position_ticket, result.price
            volume, sl, tp = result.volume, result.sl, result.tp
            logger.info(
                "✅ APERTO SU MT5 | Position %s | %s %.2f lotti @ %.2f",
                position_ticket, signal["direction"], volume, open_price,
            )
        else:
            # Modalita' TEST: nessun ordine, si usa l'ingresso del segnale.
            position_ticket, open_price = None, signal["entry"]
            volume, sl, tp = 0.0, signal["sl"], signal["tp"]
            logger.info(
                "🧪 TEST (nessun ordine MT5) | apertura simulata @ %.2f%s", open_price,
                f" (ordine {signal['order_type']} considerato eseguito)"
                if signal.get("order_type", "MARKET") != "MARKET" else "",
            )

        db.mark_opened(source_id, position_ticket, open_price, volume, sl, tp)
        await publish_open(source_id, signal["direction"], open_price, sl, tp)


async def close_opposite_for_reversal(signal, source_id):
    """
    Nuovo SIGNAL N BUY -> chiude tutti i SELL del SIGNAL N (e viceversa),
    pubblicando la chiusura di ciascuno. Gli altri SIGNAL non vengono toccati.
    """
    opposite = "SELL" if signal["direction"] == "BUY" else "BUY"
    rows = db.get_active_by_signal_no(signal["signal_no"], opposite)
    if not rows:
        return
    if db.get_signal(source_id) is not None:
        return  # messaggio gia' gestito

    logger.info(
        "🔄 INVERSIONE SIGNAL %s -> %s | chiudo %d operazioni %s",
        signal["signal_no"], signal["direction"], len(rows), opposite,
    )
    for row in rows:
        row_id = row["source_message_id"]
        async with get_lock(row_id):
            current = db.get_signal(row_id)
            live = TRADING_ENABLED and (current["position_ticket"] or current["order_ticket"])
            if live and not MT5_READY:
                logger.error("❌ MT5 NON PRONTO: inversione non eseguita per #%s", row_id)
                continue
            try:
                if current["status"] == db.PENDING_STATUS:
                    if live:
                        await asyncio.to_thread(mt5x.cancel_pending_order, current["order_ticket"])
                    db.finish_pending(row_id, "CANCELED")
                    logger.info("🚫 INVERSIONE: ordine pendente #%s annullato", row_id)
                    continue
                if current["status"] != db.OPEN_STATUS:
                    continue
                if live:
                    if await asyncio.to_thread(mt5x.is_position_open, current["position_ticket"]):
                        price = await asyncio.to_thread(mt5x.close_position, current["position_ticket"])
                        await finalize_close(current, "CLOSED_MANUAL", price)
                    else:
                        await finalize_if_closed_on_mt5(current)
                else:
                    # Modalita' TEST: chiusura simulata all'ingresso del nuovo segnale.
                    await finalize_close(current, "CLOSED_MANUAL", signal["entry"])
            except Exception:
                logger.exception("❌ ERRORE CHIUSURA PER INVERSIONE | #%s", row_id)


async def publish_open(source_id, direction, open_price, sl, tp):
    try:
        sent = await send_open_message(direction, open_price, sl, tp)
        db.set_destination_message(source_id, sent.id)
        logger.info("📤 SEGNALE PUBBLICATO | Destination #%s", sent.id)
    except Exception:
        logger.exception("❌ ERRORE INVIO SEGNALE NEL CANALE | #%s", source_id)


# ============================================================
# ORDINI PENDENTI (LIMIT / STOP)
# ============================================================

async def refresh_pending(row):
    """
    Controlla un ordine pendente: se eseguito lo registra e lo pubblica nel
    canale con l'entry reale; se annullato dal broker o scaduto lo chiude.
    Da chiamare con il lock del segnale.
    """
    source_id = row["source_message_id"]
    fill = await asyncio.to_thread(mt5x.check_pending_order, row["order_ticket"])

    if fill is None:
        if PENDING_EXPIRY_MINUTES > 0 and row["pending_since"]:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(row["pending_since"])
            if age.total_seconds() > PENDING_EXPIRY_MINUTES * 60:
                if await asyncio.to_thread(mt5x.cancel_pending_order, row["order_ticket"]):
                    db.finish_pending(source_id, "EXPIRED")
                    logger.info("⌛ ORDINE PENDENTE SCADUTO E ANNULLATO | Order %s | #%s",
                                row["order_ticket"], source_id)
        return

    if not fill["filled"]:
        db.finish_pending(source_id, "CANCELED")
        logger.info("🚫 ORDINE PENDENTE ANNULLATO SU MT5 | Order %s | #%s", row["order_ticket"], source_id)
        return

    db.mark_opened(source_id, fill["position_ticket"], fill["price"], fill["volume"], row["sl"], row["tp"])
    logger.info(
        "✅ ORDINE %s ESEGUITO | Position %s | %s @ %.2f",
        row["order_type"], fill["position_ticket"], row["direction"], fill["price"],
    )
    await publish_open(source_id, row["direction"], fill["price"], row["sl"], row["tp"])


# ============================================================
# AGGIORNAMENTI (TP / BE / STOP / CHIUSA)
# ============================================================

def find_signal_row(message, signal):
    reply_to = getattr(message, "reply_to_msg_id", None)
    if reply_to:
        row = db.get_signal(reply_to)
        if row is not None:
            return row
    # Riserva: messaggio non in reply (o reply a un messaggio sconosciuto).
    return db.get_latest_open_by_signal_no(signal.get("signal_no"))


async def finalize_close(row, close_status, close_price):
    """Registra la chiusura (una sola volta) e la comunica nel canale."""
    pips = calculate_pips(row["open_price"], close_price, row["direction"], current_pip_size())
    if close_status == "CLOSED_SL":
        close_status = classify_stop_close(pips, bool(row["be_applied"]))

    if not db.claim_close(row["source_message_id"], close_status, close_price, pips):
        return

    logger.info(
        "🏁 %s | SIGNAL %s %s | Position %s | Chiusura %.2f | %+.1f pips",
        close_status, row["signal_no"], row["direction"], row["position_ticket"],
        close_price, pips,
    )
    try:
        await send_close_message(
            close_status, pips, close_price, reply_to=row["destination_message_id"],
        )
    except Exception:
        logger.exception("❌ ERRORE INVIO MESSAGGIO DI CHIUSURA | #%s", row["source_message_id"])


async def finalize_if_closed_on_mt5(row):
    """La posizione non c'e' piu' su MT5: legge lo storico e chiude il record."""
    info = await asyncio.to_thread(mt5x.get_closed_position_info, row["position_ticket"])
    if info is None:
        return False
    if info["is_tp"]:
        status = "CLOSED_TP"
    elif info["is_sl"]:
        status = "CLOSED_SL"
    else:
        status = "CLOSED_EXTERNAL"
    await finalize_close(row, status, info["price"])
    return True


async def handle_update(message, signal, row=None):
    action = signal["action"]
    if row is None:
        row = find_signal_row(message, signal)
    if row is None or row["status"] not in (db.OPEN_STATUS, db.PENDING_STATUS):
        logger.info(
            "⏭️ %s SIGNAL %s ignorato | #%s | nessuna operazione aperta collegata.",
            action, signal.get("signal_no"), message.id,
        )
        return

    source_id = row["source_message_id"]
    async with get_lock(source_id):
        row = db.get_signal(source_id)
        if row["status"] not in (db.OPEN_STATUS, db.PENDING_STATUS):
            return

        logger.info("📩 %s | SIGNAL %s | collegato al segnale #%s", action, signal.get("signal_no"), source_id)

        if row["status"] == db.PENDING_STATUS:
            # Ordine non ancora eseguito: annullato, chiuso o stop -> lo si toglie.
            if not MT5_READY:
                logger.error("❌ MT5 NON PRONTO: %s non eseguito | #%s", action, source_id)
                return
            if action == "BREAKEVEN":
                logger.info("⏭️ BE ignorato: ordine #%s ancora pendente.", source_id)
                return
            try:
                cancelled = await asyncio.to_thread(mt5x.cancel_pending_order, row["order_ticket"])
            except Exception:
                logger.exception("❌ ERRORE ANNULLAMENTO ORDINE PENDENTE | #%s", source_id)
                return
            if cancelled:
                db.finish_pending(source_id, "CANCELED")
                logger.info("🚫 ORDINE PENDENTE ANNULLATO (%s) | Order %s | #%s",
                            action, row["order_ticket"], source_id)
                return
            # Non c'e' piu' tra i pendenti: probabilmente appena eseguito.
            await refresh_pending(row)
            row = db.get_signal(source_id)
            if row["status"] != db.OPEN_STATUS:
                return

        live = TRADING_ENABLED and row["position_ticket"] is not None
        if live:
            if not MT5_READY:
                logger.error("❌ MT5 NON PRONTO: %s non eseguito | #%s", action, source_id)
                return
            still_open = await asyncio.to_thread(mt5x.is_position_open, row["position_ticket"])
            if not still_open:
                # Gia' chiusa da MT5 (TP/SL broker): comunica la chiusura reale.
                await finalize_if_closed_on_mt5(row)
                return

        if action == "BREAKEVEN":
            # BE = prezzo d'ingresso REALE della nostra posizione.
            new_sl = float(row["open_price"])
            if live:
                try:
                    new_sl = await asyncio.to_thread(mt5x.move_stop_loss, row["position_ticket"], new_sl)
                except ValueError as exc:
                    logger.warning("⚠️ BE NON APPLICABILE | #%s | %s", source_id, exc)
                    return
                except Exception:
                    logger.exception("❌ ERRORE BE | #%s", source_id)
                    return
            db.mark_breakeven(source_id, new_sl)
            logger.info("🛡️ BE ATTIVATO | SIGNAL %s | Nuovo SL %.2f", row["signal_no"], new_sl)
            try:
                await send_be_applied_message(new_sl, reply_to=row["destination_message_id"])
            except Exception:
                logger.exception("❌ ERRORE INVIO MESSAGGIO BE | #%s", source_id)
            return

        status = {
            "TP_HIT": "CLOSED_TP", "SL_HIT": "CLOSED_SL",
            "CLOSE": "CLOSED_MANUAL", "CANCEL": "CLOSED_MANUAL",
        }[action]
        if live:
            try:
                close_price = await asyncio.to_thread(mt5x.close_position, row["position_ticket"])
            except Exception:
                logger.exception("❌ ERRORE CHIUSURA | #%s", source_id)
                # Forse si e' chiusa nel frattempo: il monitor la registrera'.
                return
        else:
            close_price = signal.get("exit_price") or row["open_price"]

        await finalize_close(row, status, close_price)


# ============================================================
# HANDLER CANALE SORGENTE
# ============================================================

# ============================================================
# CHIUSURE SCRITTE A PAROLE ("Chiudiamo...", senza SIGNAL N)
# ============================================================

_last_free_close = {"at": 0.0}


async def handle_free_close(message):
    """
    - in reply a un segnale -> chiude quell'operazione
    - senza reply -> chiude l'operazione aperta piu' recente
    I SIGNAL di inversione (5 e 6) non vengono mai chiusi cosi'.
    """
    key = f"freeclose:{message.id}"
    if db.was_sent(key):
        return  # stesso messaggio gia' gestito (es. poi modificato)
    db.mark_sent(key)

    row = None
    reply_to = getattr(message, "reply_to_msg_id", None)
    if reply_to:
        row = db.get_signal(reply_to)
    if row is not None:
        if row["signal_no"] in REVERSAL_SIGNALS:
            logger.info("⏭️ CHIUSURA A PAROLE #%s ignorata: SIGNAL %s si chiude solo con i suoi messaggi.",
                        message.id, row["signal_no"])
            return
    else:
        elapsed = time.monotonic() - _last_free_close["at"]
        if _last_free_close["at"] and elapsed < FREE_CLOSE_COOLDOWN_MINUTES * 60:
            logger.info("⏭️ CHIUSURA A PAROLE #%s ignorata: chiusura gia' fatta %.0f secondi fa.",
                        message.id, elapsed)
            return
        candidates = [r for r in db.get_open_signals() if r["signal_no"] not in REVERSAL_SIGNALS]
        if not candidates:
            logger.info("⏭️ CHIUSURA A PAROLE #%s: nessuna operazione aperta da chiudere.", message.id)
            return
        row = max(candidates, key=lambda r: (r["opened_at"] or "", r["source_message_id"]))

    logger.info("✂️ CHIUSURA A PAROLE #%s -> SIGNAL %s %s (#%s)",
                message.id, row["signal_no"], row["direction"], row["source_message_id"])
    _last_free_close["at"] = time.monotonic()
    await handle_update(
        message,
        {"action": "CLOSE", "symbol": "XAUUSD", "signal_no": row["signal_no"],
         "exit_price": None, "pips": None},
        row=row,
    )


async def source_edited_handler(event):
    """Messaggi modificati: si considerano solo le chiusure scritte a parole."""
    if BOT_STATE == "STOPPED":
        return
    signal = parse_signal(event.message.raw_text or "")
    if signal is not None and signal["action"] == "FREE_CLOSE":
        try:
            await handle_free_close(event.message)
        except Exception:
            logger.exception("❌ ERRORE GESTIONE MESSAGGIO MODIFICATO #%s", event.message.id)


async def source_message_handler(event):
    if BOT_STATE == "STOPPED":
        return
    message = event.message
    signal = parse_signal(message.raw_text or "")
    if signal is None:
        logger.info("ℹ️ Messaggio #%s non operativo: ignorato.", message.id)
        return
    try:
        if signal["action"] == "FREE_CLOSE":
            await handle_free_close(message)
        elif signal["action"] == "OPEN":
            await handle_open(message, signal)
        else:
            await handle_update(message, signal)
    except Exception:
        logger.exception("❌ ERRORE GESTIONE MESSAGGIO #%s", message.id)


# ============================================================
# MONITOR: chiusure fatte da MT5 (TP/SL raggiunti, chiusure manuali)
# ============================================================

async def monitor_closures():
    while True:
        try:
            if TRADING_ENABLED and MT5_READY and BOT_STATE != "STOPPED":
                for row in db.get_pending_signals():
                    async with get_lock(row["source_message_id"]):
                        current = db.get_signal(row["source_message_id"])
                        if current["status"] == db.PENDING_STATUS:
                            await refresh_pending(current)
                for row in db.get_open_signals():
                    if row["position_ticket"] is None:
                        continue
                    async with get_lock(row["source_message_id"]):
                        current = db.get_signal(row["source_message_id"])
                        if current["status"] != db.OPEN_STATUS:
                            continue
                        levels = await asyncio.to_thread(mt5x.get_position_levels, current["position_ticket"])
                        if levels is None:
                            await finalize_if_closed_on_mt5(current)
                        else:
                            mt5_sl, mt5_tp = levels
                            await check_sl_change(current, mt5_sl)
                            await check_tp_change(current, mt5_tp)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE MONITOR")
        await asyncio.sleep(MONITOR_INTERVAL_SECONDS)


async def check_tp_change(row, mt5_tp):
    """TP cambiato a mano su MT5: lo registra e lo comunica in reply al segnale."""
    known_tp = float(row["tp"] or 0.0)
    if abs(mt5_tp - known_tp) < 0.005:
        return
    db.update_tp(row["source_message_id"], mt5_tp)
    logger.info(
        "🎯 TP MODIFICATO SU MT5 | SIGNAL %s %s | Position %s | %s -> %s",
        row["signal_no"], row["direction"], row["position_ticket"],
        f"{known_tp:.2f}" if known_tp else "nessuno", f"{mt5_tp:.2f}" if mt5_tp else "nessuno",
    )
    try:
        await send_tp_updated_message(mt5_tp, reply_to=row["destination_message_id"])
    except Exception:
        logger.exception("❌ ERRORE INVIO MESSAGGIO TP | #%s", row["source_message_id"])


async def check_sl_change(row, mt5_sl):
    """
    SL cambiato a mano su MT5:
    - portato all'ingresso o in profitto la prima volta -> "BE ATTIVATO"
    - spostato ma ancora in perdita -> "STOP LOSS IMPOSTATO A ..."
    - spostato di nuovo quando era gia' in profitto -> "STOP LOSS IN PROFITTO A ..."
    """
    known_sl = float(row["sl"] or 0.0)
    if abs(mt5_sl - known_sl) < 0.005:
        return
    source_id = row["source_message_id"]
    open_price = float(row["open_price"])
    if row["direction"] == "BUY":
        in_profit = bool(mt5_sl) and mt5_sl >= open_price - 0.005
    else:
        in_profit = bool(mt5_sl) and mt5_sl <= open_price + 0.005

    logger.info(
        "🛡️ SL MODIFICATO SU MT5 | SIGNAL %s %s | Position %s | %s -> %s%s",
        row["signal_no"], row["direction"], row["position_ticket"],
        f"{known_sl:.2f}" if known_sl else "nessuno", f"{mt5_sl:.2f}" if mt5_sl else "nessuno",
        " (in profitto)" if in_profit else "",
    )
    try:
        if in_profit and not row["be_applied"]:
            db.mark_breakeven(source_id, mt5_sl)
            await send_be_applied_message(mt5_sl, reply_to=row["destination_message_id"])
        else:
            db.update_sl(source_id, mt5_sl)
            await send_sl_updated_message(mt5_sl, in_profit, reply_to=row["destination_message_id"])
    except Exception:
        logger.exception("❌ ERRORE INVIO MESSAGGIO SL | #%s", source_id)


async def mt5_connection_keeper():
    """Connette MT5 all'avvio e riprova ogni 30s se non e' disponibile."""
    global MT5_READY
    while True:
        if not MT5_READY:
            MT5_READY = await asyncio.to_thread(mt5x.connect_mt5)
            if not MT5_READY:
                logger.error("❌ MT5 non disponibile: nuovo tentativo tra 30 secondi.")
        await asyncio.sleep(30)


# ============================================================
# REPORT E BUONGIORNO PROGRAMMATI
# ============================================================

def scheduled_text(kind, day):
    if kind == "morning":
        return GOOD_MORNING_MESSAGE_TEMPLATE
    if kind == "daily":
        return reports.daily_report_text(day)
    if kind == "weekly":
        return reports.weekly_report_text(day)
    return reports.monthly_report_text(day)


async def scheduler():
    """Buongiorno lun-ven 06:00, giornaliero lun-ven 23:00, settimanale sabato
    10:00, mensile ultimo giorno del mese 23:00 (ora italiana)."""
    while True:
        try:
            if BOT_STATE != "STOPPED":
                for key, kind, day in reports.due_messages(reports.now_italy()):
                    if db.was_sent(key):
                        continue
                    # Segnato prima dell'invio: mai due volte, anche se Telegram e' lento.
                    db.mark_sent(key)
                    try:
                        sent = await send_text(scheduled_text(kind, day))
                        logger.info("📨 %s INVIATO | Destination #%s", kind.upper(), sent.id)
                    except Exception:
                        logger.exception("❌ ERRORE INVIO %s", kind.upper())
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE SCHEDULER REPORT")
        await asyncio.sleep(20)


# ============================================================
# COMANDI DA "MESSAGGI SALVATI"
# ============================================================

async def close_all_open_trades():
    closed, errors = 0, 0
    for row in db.get_pending_signals():
        async with get_lock(row["source_message_id"]):
            try:
                if TRADING_ENABLED and MT5_READY:
                    await asyncio.to_thread(mt5x.cancel_pending_order, row["order_ticket"])
                db.finish_pending(row["source_message_id"], "CANCELED")
            except Exception:
                errors += 1
                logger.exception("❌ ERRORE ANNULLAMENTO PENDENTE | #%s", row["source_message_id"])
    for row in db.get_open_signals():
        async with get_lock(row["source_message_id"]):
            current = db.get_signal(row["source_message_id"])
            if current["status"] != db.OPEN_STATUS:
                continue
            try:
                if TRADING_ENABLED and current["position_ticket"] is not None:
                    if await asyncio.to_thread(mt5x.is_position_open, current["position_ticket"]):
                        price = await asyncio.to_thread(mt5x.close_position, current["position_ticket"])
                        await finalize_close(current, "CLOSED_MANUAL", price)
                    else:
                        await finalize_if_closed_on_mt5(current)
                else:
                    db.claim_close(current["source_message_id"], "CLOSED_MANUAL", None, None)
                closed += 1
            except Exception:
                errors += 1
                logger.exception("❌ ERRORE CHIUSURA DA COMANDO | #%s", row["source_message_id"])
    return closed, errors


STATE_LABELS = {"RUNNING": "▶️ ATTIVO", "PAUSED": "⏸️ IN PAUSA", "STOPPED": "🛑 FERMATO"}


def status_text():
    rows = db.get_open_signals()
    lines = [
        f"<b>STATO BOT:</b> {STATE_LABELS.get(BOT_STATE, BOT_STATE)}",
        f"<b>MT5:</b> {'collegato' if MT5_READY else ('modalita TEST' if not TRADING_ENABLED else 'NON collegato')}",
        f"<b>Operazioni aperte ({len(rows)}):</b>",
    ]
    profit_by_ticket = {}
    if TRADING_ENABLED and MT5_READY:
        try:
            profit_by_ticket = {int(p.ticket): float(p.profit) for p in mt5x.get_bot_positions()}
        except Exception:
            logger.exception("❌ ERRORE LETTURA POSIZIONI")
    for row in rows:
        profit = profit_by_ticket.get(int(row["position_ticket"] or 0))
        profit_txt = f" | {profit:+.2f} $" if profit is not None else ""
        tp_txt = f"{row['tp']:.2f}" if row["tp"] else "a segnale"
        lines.append(
            f"• SIGNAL {row['signal_no']} {row['direction']} @ {row['open_price']:.2f} "
            f"| SL {row['sl'] or 0:.2f} | TP {tp_txt}{' | BE' if row['be_applied'] else ''}{profit_txt}"
        )
    if not rows:
        lines.append("Nessuna")
    pending = db.get_pending_signals()
    if pending:
        lines.append(f"\n<b>Ordini pendenti ({len(pending)}):</b>")
        for row in pending:
            tp_txt = f"{row['tp']:.2f}" if row["tp"] else "a segnale"
            lines.append(
                f"• SIGNAL {row['signal_no']} {row['direction']} {row['order_type']} @ {row['entry_signal']:.2f} "
                f"| SL {row['sl'] or 0:.2f} | TP {tp_txt}"
            )
    return "\n".join(lines)


async def saved_messages_handler(event):
    global BOT_STATE
    text = (event.raw_text or "").strip().lower()
    if not text.startswith(COMMAND_PREFIX):
        return
    command = text[len(COMMAND_PREFIX):].strip()
    try:
        if command == "play":
            BOT_STATE = "RUNNING"
            await event.reply(play_message(COMMAND_PREFIX), parse_mode="html")
        elif command == "pausa":
            BOT_STATE = "PAUSED"
            await event.reply(paused_message(COMMAND_PREFIX), parse_mode="html")
        elif command == "stop":
            closed, errors = await close_all_open_trades()
            BOT_STATE = "STOPPED"
            await event.reply(stopped_message(COMMAND_PREFIX, closed, errors), parse_mode="html")
        elif command == "riavvio":
            closed, errors = await close_all_open_trades()
            BOT_STATE = "RUNNING"
            await event.reply(restart_message(COMMAND_PREFIX, closed, errors), parse_mode="html")
        elif command in {"report", "reportw", "reportm"}:
            kind = {"report": "daily", "reportw": "weekly", "reportm": "monthly"}[command]
            await send_text(scheduled_text(kind, reports.now_italy().date()))
            await event.reply(f"✅ Report {kind} inviato nel canale.")
        elif command == "status":
            await event.reply(status_text(), parse_mode="html")
        else:
            await event.reply(help_message(COMMAND_PREFIX), parse_mode="html")
    except Exception:
        logger.exception("❌ ERRORE COMANDO %s", command)


# ============================================================
# AVVIO
# ============================================================

async def main():
    if not SOURCE_CHAT or not DESTINATION_CHAT:
        logger.error(
            "❌ Imposta TELEGRAM_SOURCE_CHAT e TELEGRAM_DESTINATION_CHAT nel file .env "
            "(usa get_chats.py per trovare gli ID)."
        )
        sys.exit(1)

    db.init_database()

    logger.info("=" * 60)
    logger.info("🚀 BOT GOLD EMPIRE -> MT5")
    logger.info("SOURCE      : %s", SOURCE_CHAT)
    logger.info("DESTINATION : %s", DESTINATION_CHAT)
    logger.info("TRADING     : %s", "ATTIVO" if TRADING_ENABLED else "DISATTIVATO (modalita TEST)")
    logger.info("SIMBOLO     : %s | Lotto %.2f | Magic %s", MT5_SYMBOL, LOT_SIZE, MAGIC_NUMBER)
    logger.info("INVERSIONE  : SIGNAL %s (il segnale opposto chiude quelli dello stesso numero)",
                ", ".join(str(n) for n in sorted(REVERSAL_SIGNALS)) or "nessuno")
    logger.info("ETA' MAX    : %.0fs | Distanza max ingresso: %s",
                MAX_SIGNAL_AGE_SECONDS, f"{MAX_ENTRY_DISTANCE:.2f} $" if MAX_ENTRY_DISTANCE else "nessun limite")
    logger.info("COMANDI     : %scomandi (in Messaggi salvati)", COMMAND_PREFIX)
    logger.info("PROGRAMMATI : buongiorno lun-ven 06:00 | report giornaliero lun-ven 23:00 | "
                "settimanale sabato 10:00 | mensile ultimo giorno 23:00")
    logger.info("=" * 60)

    await client.start()
    me = await client.get_me()
    logger.info("👤 Telegram collegato come %s (ID %s)", me.first_name, me.id)

    # Carica i dialoghi cosi' Telethon conosce gli ID dei canali.
    await client.get_dialogs()
    for label, chat_id in (("SOURCE", SOURCE_CHAT), ("DESTINATION", DESTINATION_CHAT)):
        try:
            entity = await client.get_entity(chat_id)
            logger.info("✅ %s: %s", label, getattr(entity, "title", chat_id))
        except Exception:
            logger.error("❌ %s %s non raggiungibile: l'account e' iscritto al canale?", label, chat_id)
            sys.exit(1)

    client.add_event_handler(source_message_handler, events.NewMessage(chats=SOURCE_CHAT))
    client.add_event_handler(source_edited_handler, events.MessageEdited(chats=SOURCE_CHAT))
    client.add_event_handler(saved_messages_handler, events.NewMessage(chats="me"))

    tasks = [asyncio.create_task(monitor_closures()), asyncio.create_task(scheduler())]
    if TRADING_ENABLED:
        tasks.append(asyncio.create_task(mt5_connection_keeper()))

    logger.info("👂 In ascolto del canale Gold Empire...")
    try:
        await client.run_until_disconnected()
    finally:
        for task in tasks:
            task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot fermato.")
