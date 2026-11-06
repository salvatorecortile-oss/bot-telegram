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
import re
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
    PUBLISH_TO_CHANNEL,
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
import signal_parser as sp
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
import sync  # noqa: E402


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
    if is_reversal_signal(signal):
        await close_opposite_for_reversal(signal, source_id)

    # "Se dovesse arrivare un altro segnale N di oggi non lo apriamo"
    if signal.get("signal_no") is not None and db.was_sent(block_key(signal["signal_no"])):
        logger.warning("🚫 SIGNAL %s BLOCCATO PER OGGI dal canale: #%s non aperto.",
                       signal["signal_no"], source_id)
        if db.insert_signal(source_id, signal):
            db.set_status(source_id, "BLOCKED_BY_CHANNEL")
        return

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


def is_reversal_signal(signal):
    """
    Inversione automatica solo per le strategie senza TP del SIGNAL 5
    (5.1 ... 5.8, o "SIGNAL 5" del vecchio formato), sempre sul numero esatto:
    un 5.3 chiude solo un 5.3. I segnali con TP (es. SIGNAL 4 e 6) non si
    chiudono mai con un segnale nuovo: solo con TP/SL o "CHIUDI ORA".
    """
    signal_no = signal.get("signal_no")
    if signal_no is None or signal.get("tp"):
        return False
    return int(signal_no) in REVERSAL_SIGNALS


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
        if sent is None:
            return  # PUBLISH_TO_CHANNEL=false: nessun messaggio nel canale
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
        if close_status == "CLOSED_SL" and pips > 0:
            # Stop spostato in profitto e poi colpito: e' una chiusura in
            # profitto, non uno "STOP LOSS PRESO".
            close_status = "CLOSED_STOP_PROFIT"

    if not db.claim_close(row["source_message_id"], close_status, close_price, pips):
        return
    sync.publish(row["source_message_id"], "CLOSE")

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
            if action in ("BREAKEVEN", "MOVE_SL"):
                logger.info("⏭️ %s ignorato: ordine #%s ancora pendente.", action, source_id)
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
            mt5x.register_ticket(row["position_ticket"])
            if not MT5_READY:
                logger.error("❌ MT5 NON PRONTO: %s non eseguito | #%s", action, source_id)
                return
            still_open = await asyncio.to_thread(mt5x.is_position_open, row["position_ticket"])
            if not still_open:
                # Gia' chiusa da MT5 (TP/SL broker): comunica la chiusura reale.
                await finalize_if_closed_on_mt5(row)
                return

        if action == "MOVE_SL":
            # "🟡 SPOSTA LO STOP": lo SL va al nuovo prezzo, l'operazione resta aperta.
            new_sl = signal.get("new_sl")
            open_price = float(row["open_price"])
            if not new_sl or abs(float(new_sl) - open_price) > open_price * 0.2:
                logger.warning("⚠️ SPOSTA LO STOP ignorato | #%s | prezzo non valido: %s", source_id, new_sl)
                return
            if live:
                try:
                    new_sl = await asyncio.to_thread(mt5x.move_stop_loss, row["position_ticket"], new_sl)
                except ValueError as exc:
                    logger.warning("⚠️ SPOSTA LO STOP NON APPLICABILE | #%s | %s", source_id, exc)
                    return
                except Exception:
                    logger.exception("❌ ERRORE SPOSTA LO STOP | #%s", source_id)
                    return
            logger.info("🟡 STOP SPOSTATO | SIGNAL %s | Nuovo SL %.2f", row["signal_no"], float(new_sl))
            # Registra il nuovo SL e manda il messaggio (BE ATTIVATO se in profitto).
            await check_sl_change(row, float(new_sl))
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
            sync.publish(source_id, "BE")
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


async def handle_free_close(message, reply_only=False, signal_no=None):
    """
    Vale per tutti i SIGNAL (anche 5 e 6):
    - in reply a un segnale -> chiude quell'operazione
    - senza reply -> chiude l'operazione aperta piu' recente
    - "Non apriamo" (reply_only) -> solo in reply: chiude quel segnale
    """
    key = f"freeclose:{message.id}"
    if db.was_sent(key):
        return  # stesso messaggio gia' gestito (es. poi modificato)
    db.mark_sent(key)

    row = None
    reply_to = getattr(message, "reply_to_msg_id", None)
    if reply_to:
        row = db.get_signal(reply_to)
    if row is None:
        if reply_only:
            logger.info("⏭️ 'NON APRIAMO' #%s ignorato: non e' in risposta a un segnale.", message.id)
            return
        elapsed = time.monotonic() - _last_free_close["at"]
        if _last_free_close["at"] and elapsed < FREE_CLOSE_COOLDOWN_MINUTES * 60:
            logger.info("⏭️ CHIUSURA A PAROLE #%s ignorata: chiusura gia' fatta %.0f secondi fa.",
                        message.id, elapsed)
            return
        candidates = db.get_open_signals()
        if signal_no is not None:
            # "Chiudiamo il segnale 6": solo le operazioni di quel SIGNAL.
            candidates = [r for r in candidates if r["signal_no"] == signal_no]
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


def block_key(signal_no):
    return f"block:{signal_no}:{reports.now_italy().date().isoformat()}"


def handle_block(message, signal):
    """Blocca le nuove aperture di quel SIGNAL fino a mezzanotte (ora italiana)."""
    db.mark_sent(block_key(signal["signal_no"]))
    logger.warning("🚫 SIGNAL %s: il canale ha detto di non aprirlo piu' oggi (#%s). Bloccato fino a mezzanotte.",
                   signal["signal_no"], message.id)


async def source_edited_handler(event):
    """
    Messaggi modificati: chiusure scritte a parole, blocchi e aperture. Un
    segnale corretto subito dopo l'invio viene aperto se la prima versione non
    era leggibile (mai due volte: ogni messaggio apre al massimo un'operazione).
    """
    if BOT_STATE == "STOPPED":
        return
    signal = parse_signal(event.message.raw_text or "")
    if signal is not None and signal["action"] == "OPEN":
        try:
            await handle_open(event.message, signal)
        except Exception:
            logger.exception("❌ ERRORE APERTURA DA MESSAGGIO MODIFICATO #%s", event.message.id)
    elif signal is not None and signal["action"] == "BLOCK_SIGNAL":
        handle_block(event.message, signal)
    elif signal is not None and signal["action"] == "FREE_CLOSE":
        try:
            await handle_free_close(event.message, signal.get("reply_only", False), signal.get("signal_no"))
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
        if signal["action"] == "BLOCK_SIGNAL":
            handle_block(message, signal)
        elif signal["action"] == "FREE_CLOSE":
            await handle_free_close(message, signal.get("reply_only", False), signal.get("signal_no"))
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
                    mt5x.register_ticket(row["position_ticket"])
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
    sync.publish(row["source_message_id"], "TP", mt5_tp)
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

    # Allineamento: SL all'ingresso (±0,30 $) = BE, l'altro conto lo mette al SUO ingresso.
    if mt5_sl and abs(mt5_sl - open_price) <= 0.30:
        sync.publish(source_id, "BE")
    else:
        sync.publish(source_id, "SL", mt5_sl)
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


# ============================================================
# ADOZIONE OPERAZIONI APERTE A MANO
# ============================================================
# Se un segnale e' stato aperto a mano su MT5 (es. il bot l'aveva perso), il
# bot lo riconosce confrontando la posizione con i segnali di apertura degli
# ultimi giorni del canale (stessa direzione + stesso SL, o stesso TP, e
# ingresso vicino) e da quel momento lo gestisce come se l'avesse aperto lui:
# CHIUDI ORA, SPOSTA LO STOP, inversione, TP/SL, report.

ADOPT_LOOKBACK_HOURS = 72
ADOPT_PRICE_TOLERANCE = 1.0     # $ di differenza ammessa su SL/TP
ADOPT_ENTRY_TOLERANCE = 15.0    # $ di differenza ammessa sull'ingresso


async def recent_open_signals():
    """Segnali di apertura del canale delle ultime ADOPT_LOOKBACK_HOURS ore."""
    since = datetime.now(timezone.utc).timestamp() - ADOPT_LOOKBACK_HOURS * 3600
    found = []
    async for message in client.iter_messages(SOURCE_CHAT, limit=400):
        if message.date.timestamp() < since:
            break
        signal = parse_signal(message.raw_text or "")
        if signal is not None and signal["action"] == "OPEN":
            found.append((message, signal))
    return found


def _match_score(position, signal):
    """None se la posizione non corrisponde al segnale, altrimenti la distanza dall'ingresso."""
    is_buy = int(position.type) == 0  # POSITION_TYPE_BUY
    if signal["direction"] != ("BUY" if is_buy else "SELL"):
        return None
    entry_gap = abs(float(position.price_open) - float(signal["entry"]))
    pos_sl, pos_tp = float(position.sl or 0.0), float(position.tp or 0.0)
    sl_match = pos_sl and abs(pos_sl - float(signal["sl"])) <= ADOPT_PRICE_TOLERANCE
    tp_match = pos_tp and signal.get("tp") and abs(pos_tp - float(signal["tp"])) <= ADOPT_PRICE_TOLERANCE
    # Ingresso lontano (aperta a mano piu' tardi): va bene solo se SL o TP coincidono.
    if entry_gap > ADOPT_ENTRY_TOLERANCE and not (sl_match or tp_match):
        return None
    # Senza SL/TP impostati: solo se l'ingresso e' praticamente lo stesso.
    if not (sl_match or tp_match or (not pos_sl and not pos_tp and entry_gap <= 3.0)):
        return None
    return entry_gap


_unmatched_logged = set()


async def adopt_manual_positions():
    open_rows = db.get_open_signals()
    known = {int(r["position_ticket"]) for r in open_rows if r["position_ticket"]}
    for ticket in known:
        mt5x.register_ticket(ticket)

    now = await asyncio.to_thread(mt5x.server_time)
    candidates = [
        p for p in await asyncio.to_thread(mt5x.get_symbol_positions)
        # Le posizioni aperte da meno di 2 minuti le sta ancora gestendo l'apertura normale.
        if not now or int(p.time) < now - 120
    ]
    candidates = [
        p for p in candidates
        # Aperte a mano, oppure aperte dal bot ma rimaste senza ticket nel database
        # (es. "ticket della posizione non trovato" subito dopo l'esecuzione).
        if int(p.ticket) not in known
    ]
    if not candidates:
        # Operazioni manuali gia' collegate in un avvio precedente: cerca comunque
        # il post di apertura scritto a mano nel canale.
        await link_recent_destination_posts()
        return

    signals = await recent_open_signals()
    used = set()
    for position in candidates:
        best = None
        for message, signal in signals:
            if message.id in used:
                continue
            row = db.get_signal(message.id)
            if row is not None and row["status"] not in ("RECEIVED", "SKIPPED", "ERROR", "MT5_NOT_READY",
                                                          "PAUSED_NO_NEW_TRADE", "BLOCKED_BY_CHANNEL"):
                continue  # segnale gia' gestito (aperto o chiuso) dal bot
            score = _match_score(position, signal)
            if score is not None and (best is None or score < best[0]):
                best = (score, message, signal)
        if best is None:
            if int(position.ticket) not in _unmatched_logged:
                _unmatched_logged.add(int(position.ticket))
                logger.info(
                    "ℹ️ Posizione %s %s @ %.2f (SL %.2f, TP %.2f) non collegata: nessun segnale con "
                    "stessa direzione e stesso SL/TP nelle ultime %s ore.",
                    position.ticket, "BUY" if int(position.type) == 0 else "SELL",
                    float(position.price_open), float(position.sl or 0.0), float(position.tp or 0.0),
                    ADOPT_LOOKBACK_HOURS,
                )
            continue
        _, message, signal = best
        used.add(message.id)
        db.insert_signal(message.id, signal)
        tp = float(position.tp or 0.0) or None
        db.mark_opened(message.id, int(position.ticket), float(position.price_open),
                       float(position.volume), float(position.sl or 0.0), tp)
        mt5x.register_ticket(position.ticket)
        logger.info(
            "🤝 OPERAZIONE APERTA A MANO COLLEGATA | Position %s %s @ %.2f -> SIGNAL %s (#%s)",
            position.ticket, signal["direction"], float(position.price_open), signal["signal_no"], message.id,
        )
        # L'apertura nel canale la pubblica l'utente a mano: il bot la riconosce
        # (link_destination_post) e risponde a quel messaggio con TP/SL/chiusure.
        db.mark_sent(f"adopted:{message.id}")

    await link_recent_destination_posts()


# ---- Messaggio di apertura pubblicato A MANO nel canale di destinazione ----

def _adopted_without_post(direction=None):
    """
    Operazioni aperte che non hanno ancora un messaggio nel canale: aperte a
    mano (anche collegate da una versione precedente del bot) o con l'invio
    fallito. Quelle appena aperte dal bot (meno di 2 minuti) si escludono:
    il loro messaggio lo sta pubblicando il bot stesso.
    """
    limit = datetime.now(timezone.utc).timestamp() - 120
    rows = []
    for r in db.get_open_signals():
        if r["destination_message_id"] is not None:
            continue
        if direction is not None and r["direction"] != direction:
            continue
        adopted = db.was_sent(f"adopted:{r['source_message_id']}")
        opened = datetime.fromisoformat(r["opened_at"]).timestamp() if r["opened_at"] else 0
        if adopted or opened < limit:
            rows.append(r)
    return rows


def _read_destination_post(text):
    """Direzione, ingresso e SL di un messaggio di apertura scritto a mano nel canale."""
    clean = sp._clean(text)
    direction = re.search(r"\b(BUY|SELL|COMPRA|VENDI)\b", clean.upper())
    if not direction:
        return None
    entry = sp._number_after(r"\b(?:ENTRY|INGRESSO|ENTRATA|PREZZO)\b", clean)
    sl = sp._labeled_sl(clean) or sp._number_after(r"\b(?:STOP\s*LOSS|STOP|SL)\b", clean)
    if entry is None and sl is None:
        return None
    return {"direction": "SELL" if direction.group(1) in ("SELL", "VENDI") else "BUY", "entry": entry, "sl": sl}


def link_destination_post(message):
    """Collega il post scritto a mano all'operazione aperta a mano corrispondente."""
    post = _read_destination_post(message.raw_text or "")
    if post is None or db.is_destination_used(message.id):
        return False  # non e' un'apertura, o e' il messaggio di un'altra operazione
    best = None
    for row in _adopted_without_post(post["direction"]):
        # Stesso SL (±1 $); se uno dei due non ha lo SL, ingresso quasi uguale (±3 $).
        # Un post con SL diverso e' di un'altra operazione, anche se l'ingresso e' vicino.
        if post["sl"] is not None and row["sl"]:
            gap = abs(float(row["sl"]) - post["sl"])
            if gap > ADOPT_PRICE_TOLERANCE:
                continue
        elif post["entry"] is not None:
            gap = abs(float(row["open_price"]) - post["entry"])
            if gap > 3.0:
                continue
        else:
            continue
        if best is None or gap < best[0]:
            best = (gap, row)
    if best is None:
        return False
    row = best[1]
    db.set_destination_message(row["source_message_id"], message.id)
    logger.info("🔗 POST MANUALE NEL CANALE COLLEGATO | Destination #%s -> SIGNAL %s %s",
                message.id, row["signal_no"], row["direction"])
    return True


async def link_recent_destination_posts():
    """Cerca tra gli ultimi messaggi del canale il post scritto a mano (anche se gia' inviato)."""
    if not PUBLISH_TO_CHANNEL or not _adopted_without_post():
        return
    async for message in client.iter_messages(DESTINATION_CHAT, limit=100):
        if not _adopted_without_post():
            break
        link_destination_post(message)

    # Nessun post nel canale per un'operazione aperta a mano: lo pubblica il bot,
    # come un segnale normale, con entry/SL/TP reali della posizione su MT5.
    for row in _adopted_without_post():
        levels = None
        if TRADING_ENABLED and MT5_READY and row["position_ticket"]:
            levels = await asyncio.to_thread(mt5x.get_position_levels, row["position_ticket"])
        if levels is None and TRADING_ENABLED:
            continue  # posizione gia' chiusa: ci pensa il monitor
        sl, tp = levels if levels else (float(row["sl"] or 0.0), float(row["tp"] or 0.0))
        logger.info(
            "📤 OPERAZIONE APERTA A MANO SENZA POST NEL CANALE: pubblico il segnale | SIGNAL %s %s @ %.2f",
            row["signal_no"], row["direction"], float(row["open_price"]),
        )
        await publish_open(row["source_message_id"], row["direction"], float(row["open_price"]), sl, tp or None)


async def destination_message_handler(event):
    if PUBLISH_TO_CHANNEL and _adopted_without_post():
        try:
            link_destination_post(event.message)
        except Exception:
            logger.exception("❌ ERRORE COLLEGAMENTO POST MANUALE #%s", event.message.id)


async def adopt_loop():
    """All'avvio (appena MT5 e' pronto) e poi ogni 10 minuti."""
    while True:
        try:
            if TRADING_ENABLED and MT5_READY and BOT_STATE != "STOPPED":
                await adopt_manual_positions()
                await asyncio.sleep(600)
                continue
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE COLLEGAMENTO OPERAZIONI APERTE A MANO")
        await asyncio.sleep(15)


# ============================================================
# ALLINEAMENTO CON IL CONTO PRINCIPALE (bot follower)
# ============================================================

async def apply_sync_event(event):
    """Fa sulla nostra operazione quello che il conto principale ha fatto sulla sua."""
    row = db.get_signal(event["source_message_id"])
    if row is None or row["status"] not in (db.OPEN_STATUS, db.PENDING_STATUS):
        return  # su questo conto quell'operazione non c'e' (o e' gia' chiusa)
    source_id = row["source_message_id"]
    kind = event["kind"]
    async with get_lock(source_id):
        row = db.get_signal(source_id)
        if row["status"] == db.PENDING_STATUS:
            if kind == "CLOSE":
                await asyncio.to_thread(mt5x.cancel_pending_order, row["order_ticket"])
                db.finish_pending(source_id, "CANCELED")
                logger.info("🔁 ALLINEATO: ordine pendente #%s annullato come sul conto principale", source_id)
            return
        if row["status"] != db.OPEN_STATUS or not row["position_ticket"]:
            return
        ticket = row["position_ticket"]
        mt5x.register_ticket(ticket)
        if not await asyncio.to_thread(mt5x.is_position_open, ticket):
            await finalize_if_closed_on_mt5(row)
            return
        if kind == "CLOSE":
            price = await asyncio.to_thread(mt5x.close_position, ticket)
            logger.info("🔁 ALLINEATO: SIGNAL %s %s chiusa come sul conto principale",
                        row["signal_no"], row["direction"])
            await finalize_close(row, "CLOSED_MANUAL", price)
        elif kind in ("SL", "BE"):
            new_sl = float(row["open_price"]) if kind == "BE" else float(event["value"] or 0.0)
            new_sl, _ = await asyncio.to_thread(mt5x.set_levels, ticket, new_sl, None)
            logger.info("🔁 ALLINEATO: SIGNAL %s %s -> %s a %.2f",
                        row["signal_no"], row["direction"], "BE" if kind == "BE" else "SL", new_sl)
            await check_sl_change(row, new_sl)
        elif kind == "TP":
            new_tp = float(event["value"] or 0.0)
            _, new_tp = await asyncio.to_thread(mt5x.set_levels, ticket, None, new_tp)
            logger.info("🔁 ALLINEATO: SIGNAL %s %s -> TP %s",
                        row["signal_no"], row["direction"], f"{new_tp:.2f}" if new_tp else "tolto")
            await check_tp_change(row, new_tp)


async def sync_follower_loop():
    """Ogni 2 secondi applica le novita' del conto principale (file SYNC_FILE)."""
    while True:
        try:
            if TRADING_ENABLED and MT5_READY and BOT_STATE != "STOPPED":
                last_id = int(db.get_setting("sync_last_id", "0"))
                for event in await asyncio.to_thread(sync.read_after, last_id):
                    try:
                        await apply_sync_event(event)
                    except Exception:
                        logger.exception("❌ ERRORE ALLINEAMENTO (%s su #%s)",
                                         event["kind"], event["source_message_id"])
                    db.set_setting("sync_last_id", event["id"])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE LETTURA FILE DI ALLINEAMENTO")
        await asyncio.sleep(2)


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
            if BOT_STATE != "STOPPED" and PUBLISH_TO_CHANNEL:
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
            text = scheduled_text(kind, reports.now_italy().date())
            if PUBLISH_TO_CHANNEL:
                await send_text(text)
                await event.reply(f"✅ Report {kind} inviato nel canale.")
            else:
                # Bot che non pubblica: il report arriva solo qui nei Messaggi salvati.
                await event.reply(text, parse_mode="html")
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
    if not SOURCE_CHAT or (PUBLISH_TO_CHANNEL and not DESTINATION_CHAT):
        logger.error(
            "❌ Imposta TELEGRAM_SOURCE_CHAT e TELEGRAM_DESTINATION_CHAT nel file .env "
            "(usa get_chats.py per trovare gli ID)."
        )
        sys.exit(1)

    db.init_database()

    logger.info("=" * 60)
    logger.info("🚀 BOT GOLD EMPIRE -> MT5")
    logger.info("SOURCE      : %s", SOURCE_CHAT)
    logger.info("DESTINATION : %s", DESTINATION_CHAT if PUBLISH_TO_CHANNEL
                else "NESSUNA (PUBLISH_TO_CHANNEL=false: non scrive nel canale)")
    logger.info("TRADING     : %s", "ATTIVO" if TRADING_ENABLED else "DISATTIVATO (modalita TEST)")
    logger.info("SIMBOLO     : %s | Lotto %.2f | Magic %s", MT5_SYMBOL, LOT_SIZE, MAGIC_NUMBER)
    logger.info("INVERSIONE  : SIGNAL %s (il segnale opposto chiude quelli dello stesso numero)",
                ", ".join(str(n) for n in sorted(REVERSAL_SIGNALS)) or "nessuno")
    logger.info("ETA' MAX    : %.0fs | Distanza max ingresso: %s",
                MAX_SIGNAL_AGE_SECONDS, f"{MAX_ENTRY_DISTANCE:.2f} $" if MAX_ENTRY_DISTANCE else "nessun limite")
    logger.info("COMANDI     : %scomandi (in Messaggi salvati)", COMMAND_PREFIX)
    if sync.IS_MASTER:
        logger.info("ALLINEAMENTO: CONTO PRINCIPALE (scrive in %s)", sync.SYNC_FILE)
    elif sync.IS_FOLLOWER:
        logger.info("ALLINEAMENTO: COPIA del conto principale (legge %s)", sync.SYNC_FILE)
    logger.info("PROGRAMMATI : buongiorno lun-ven 06:00 | report giornaliero lun-ven 23:00 | "
                "settimanale sabato 10:00 | mensile ultimo giorno 23:00")
    logger.info("=" * 60)

    await client.start()
    me = await client.get_me()
    logger.info("👤 Telegram collegato come %s (ID %s)", me.first_name, me.id)

    # Carica i dialoghi cosi' Telethon conosce gli ID dei canali.
    await client.get_dialogs()
    chats = [("SOURCE", SOURCE_CHAT)]
    if PUBLISH_TO_CHANNEL:
        chats.append(("DESTINATION", DESTINATION_CHAT))
    for label, chat_id in chats:
        try:
            entity = await client.get_entity(chat_id)
            logger.info("✅ %s: %s", label, getattr(entity, "title", chat_id))
        except Exception:
            logger.error("❌ %s %s non raggiungibile: l'account e' iscritto al canale?", label, chat_id)
            sys.exit(1)

    client.add_event_handler(source_message_handler, events.NewMessage(chats=SOURCE_CHAT))
    client.add_event_handler(source_edited_handler, events.MessageEdited(chats=SOURCE_CHAT))
    if PUBLISH_TO_CHANNEL:
        client.add_event_handler(destination_message_handler, events.NewMessage(chats=DESTINATION_CHAT))
    client.add_event_handler(saved_messages_handler, events.NewMessage(chats="me"))

    tasks = [asyncio.create_task(monitor_closures()), asyncio.create_task(scheduler())]
    if TRADING_ENABLED:
        tasks.append(asyncio.create_task(mt5_connection_keeper()))
        tasks.append(asyncio.create_task(adopt_loop()))
        if sync.IS_FOLLOWER:
            tasks.append(asyncio.create_task(sync_follower_loop()))

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
