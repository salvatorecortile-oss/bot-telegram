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
    MT5_SYMBOL,
    PIP_SIZE,
    SOURCE_CHAT,
    TRADING_ENABLED,
)
from messages import calculate_pips, classify_stop_close, help_message
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
)
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

    age = (datetime.now(timezone.utc) - message.date).total_seconds()
    if age > MAX_SIGNAL_AGE_SECONDS:
        logger.warning("⏭️ SEGNALE #%s TROPPO VECCHIO (%.0fs): ignorato.", source_id, age)
        return

    async with get_lock(source_id):
        if not db.insert_signal(source_id, signal):
            return  # gia' gestito

        logger.info(
            "🎯 SIGNAL %s | %s XAUUSD | Ingresso %.2f | SL %.2f | TP %.2f%s | #%s",
            signal["signal_no"], signal["direction"], signal["entry"], signal["sl"],
            signal["tp"],
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
                result = await asyncio.to_thread(mt5x.open_market_order, signal)
            except ValueError as exc:
                logger.warning("⏭️ TRADE NON APERTO | #%s | %s", source_id, exc)
                db.set_status(source_id, "SKIPPED", error=str(exc))
                return
            except Exception as exc:
                logger.exception("❌ ERRORE APERTURA | #%s", source_id)
                db.set_status(source_id, "ERROR", error=str(exc))
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
            logger.info("🧪 TEST (nessun ordine MT5) | apertura simulata @ %.2f", open_price)

        db.mark_opened(source_id, position_ticket, open_price, volume, sl, tp)

        try:
            sent = await send_open_message(signal["direction"], open_price, sl, tp)
            db.set_destination_message(source_id, sent.id)
            logger.info("📤 SEGNALE PUBBLICATO | Destination #%s", sent.id)
        except Exception:
            logger.exception("❌ ERRORE INVIO SEGNALE NEL CANALE | #%s", source_id)


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


async def handle_update(message, signal):
    action = signal["action"]
    row = find_signal_row(message, signal)
    if row is None or row["status"] != db.OPEN_STATUS:
        logger.info(
            "⏭️ %s SIGNAL %s ignorato | #%s | nessuna operazione aperta collegata.",
            action, signal.get("signal_no"), message.id,
        )
        return

    source_id = row["source_message_id"]
    async with get_lock(source_id):
        row = db.get_signal(source_id)
        if row["status"] != db.OPEN_STATUS:
            return

        logger.info("📩 %s | SIGNAL %s | collegato al segnale #%s", action, signal.get("signal_no"), source_id)

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

        status = {"TP_HIT": "CLOSED_TP", "SL_HIT": "CLOSED_SL", "CLOSE": "CLOSED_MANUAL"}[action]
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

async def source_message_handler(event):
    if BOT_STATE == "STOPPED":
        return
    message = event.message
    signal = parse_signal(message.raw_text or "")
    if signal is None:
        logger.info("ℹ️ Messaggio #%s non operativo: ignorato.", message.id)
        return
    try:
        if signal["action"] == "OPEN":
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
                for row in db.get_open_signals():
                    if row["position_ticket"] is None:
                        continue
                    async with get_lock(row["source_message_id"]):
                        current = db.get_signal(row["source_message_id"])
                        if current["status"] != db.OPEN_STATUS:
                            continue
                        if await asyncio.to_thread(mt5x.is_position_open, current["position_ticket"]):
                            continue
                        await finalize_if_closed_on_mt5(current)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE MONITOR")
        await asyncio.sleep(MONITOR_INTERVAL_SECONDS)


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
# COMANDI DA "MESSAGGI SALVATI"
# ============================================================

async def close_all_open_trades():
    closed, errors = 0, 0
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


def status_text():
    rows = db.get_open_signals()
    lines = [
        f"<b>STATO BOT GOLD EMPIRE:</b> {BOT_STATE}",
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
        lines.append(
            f"• SIGNAL {row['signal_no']} {row['direction']} @ {row['open_price']:.2f} "
            f"| SL {row['sl']:.2f} | TP {row['tp']:.2f}{' | BE' if row['be_applied'] else ''}{profit_txt}"
        )
    if not rows:
        lines.append("Nessuna")
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
            await event.reply("✅ <b>BOT GOLD EMPIRE ATTIVO</b>", parse_mode="html")
        elif command == "pausa":
            BOT_STATE = "PAUSED"
            await event.reply(
                "⏸️ <b>BOT GOLD EMPIRE IN PAUSA</b>\nNessun nuovo trade, gli aperti restano gestiti.",
                parse_mode="html",
            )
        elif command == "stop":
            closed, errors = await close_all_open_trades()
            BOT_STATE = "STOPPED"
            await event.reply(
                f"🛑 <b>BOT GOLD EMPIRE FERMATO</b>\nPosizioni chiuse: {closed}"
                + (f"\n⚠️ Errori: {errors}" if errors else "")
                + f"\nScrivi {COMMAND_PREFIX}play per ripartire.",
                parse_mode="html",
            )
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
    logger.info("ETA' MAX    : %.0fs | Distanza max ingresso: %s",
                MAX_SIGNAL_AGE_SECONDS, f"{MAX_ENTRY_DISTANCE:.2f} $" if MAX_ENTRY_DISTANCE else "nessun limite")
    logger.info("COMANDI     : %scomandi (in Messaggi salvati)", COMMAND_PREFIX)
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
    client.add_event_handler(saved_messages_handler, events.NewMessage(chats="me"))

    tasks = [asyncio.create_task(monitor_closures())]
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
