"""
SALA SEGNALI KAIROS: MetaTrader 5 -> canale Telegram

Legge le operazioni aperte su MT5 dal bot Kairos (magic 61800 e 54001)
e le pubblica nel canale:
- apertura (entry, stop loss, take profit)
- TP / SL cambiati, break-even
- chiusura con i pips, in reply al messaggio di apertura
- buongiorno e report giornaliero / settimanale / mensile

Non apre, non modifica e non chiude niente su MT5.

Avvio:  python main.py
"""
import asyncio
import logging
import sys

from telethon import events

import database as db
from config import (
    COMMAND_PREFIX,
    DESTINATION_CHAT,
    LOG_FILE,
    MAGIC_NUMBERS,
    MT5_SYMBOL,
    POLL_INTERVAL_SECONDS,
)
from messages import (
    GOOD_MORNING_MESSAGE_TEMPLATE,
    PAUSED_MESSAGE_TEMPLATE,
    PLAY_MESSAGE_TEMPLATE,
    help_message,
)


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
import mt5_reader  # noqa: E402
import reports  # noqa: E402
from tracker import Tracker  # noqa: E402

MT5_READY = False


async def send(text, reply_to=None):
    message = await client.send_message(
        DESTINATION_CHAT, text, parse_mode="html", reply_to=reply_to, silent=reply_to is not None,
    )
    return message.id


tracker = Tracker(mt5_reader, send)


# ============================================================
# LETTURA MT5
# ============================================================

async def monitor():
    global MT5_READY
    while True:
        try:
            if not MT5_READY:
                MT5_READY = await asyncio.to_thread(mt5_reader.connect)
                if not MT5_READY:
                    logger.error("❌ MT5 non disponibile: nuovo tentativo tra 30 secondi.")
                    await asyncio.sleep(30)
                    continue
            await tracker.sync()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE LETTURA MT5")
            MT5_READY = await asyncio.to_thread(mt5_reader.is_connected)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


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
            for key, kind, day in reports.due_messages(reports.now_italy()):
                if db.was_sent(key):
                    continue
                # Segnato prima dell'invio: mai due volte, anche se Telegram e' lento.
                db.mark_sent(key)
                try:
                    message_id = await send(scheduled_text(kind, day))
                    logger.info("📨 %s INVIATO | messaggio #%s", kind.upper(), message_id)
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

def status_text():
    rows = db.get_open_trades()
    lines = [
        f"<b>SALA SEGNALI:</b> {'▶️ ATTIVA' if tracker.publishing else '⏸️ IN PAUSA'}",
        f"<b>MT5:</b> {'collegato' if MT5_READY else 'NON collegato'}",
        f"<b>Operazioni aperte ({len(rows)}):</b>",
    ]
    profit_by_ticket = {}
    if MT5_READY:
        try:
            profit_by_ticket = {p["ticket"]: p["profit"] for p in mt5_reader.get_positions() or []}
        except Exception:
            logger.exception("❌ ERRORE LETTURA POSIZIONI")
    for row in rows:
        profit = profit_by_ticket.get(row["ticket"])
        profit_txt = f" | {profit:+.2f} $" if profit is not None else ""
        tp_txt = f"{row['tp']:.2f}" if row["tp"] else "a segnale"
        lines.append(
            f"• {row['direction']} @ {row['open_price']:.2f} | SL {row['sl'] or 0:.2f} | TP {tp_txt}"
            f" | magic {row['magic']}{'' if row['published'] else ' | non pubblicata'}{profit_txt}"
        )
    if not rows:
        lines.append("Nessuna")
    return "\n".join(lines)


async def saved_messages_handler(event):
    text = (event.raw_text or "").strip().lower()
    if not text.startswith(COMMAND_PREFIX):
        return
    command = text[len(COMMAND_PREFIX):].strip()
    try:
        if command == "play":
            tracker.publishing = True
            await event.reply(PLAY_MESSAGE_TEMPLATE, parse_mode="html")
        elif command == "pausa":
            tracker.publishing = False
            await event.reply(PAUSED_MESSAGE_TEMPLATE, parse_mode="html")
        elif command in {"report", "reportw", "reportm"}:
            kind = {"report": "daily", "reportw": "weekly", "reportm": "monthly"}[command]
            await send(scheduled_text(kind, reports.now_italy().date()))
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
    if not DESTINATION_CHAT:
        logger.error("❌ Imposta TELEGRAM_DESTINATION_CHAT nel file .env (usa get_chats.py per trovare l'ID).")
        sys.exit(1)

    db.init_database()

    logger.info("=" * 60)
    logger.info("🚀 SALA SEGNALI KAIROS: MT5 -> TELEGRAM")
    logger.info("CANALE      : %s", DESTINATION_CHAT)
    logger.info("MAGIC       : %s", ", ".join(str(m) for m in sorted(MAGIC_NUMBERS)) or "tutti (ogni operazione del conto)")
    logger.info("SIMBOLO     : %s", MT5_SYMBOL or "tutti")
    logger.info("COMANDI     : %scomandi (in Messaggi salvati)", COMMAND_PREFIX)
    logger.info("PROGRAMMATI : buongiorno lun-ven 06:00 | report giornaliero lun-ven 23:00 | "
                "settimanale sabato 10:00 | mensile ultimo giorno 23:00")
    logger.info("=" * 60)

    await client.start()
    me = await client.get_me()
    logger.info("👤 Telegram collegato come %s (ID %s)", me.first_name, me.id)

    # Carica i dialoghi cosi' Telethon conosce l'ID del canale.
    await client.get_dialogs()
    try:
        entity = await client.get_entity(DESTINATION_CHAT)
        logger.info("✅ CANALE: %s", getattr(entity, "title", DESTINATION_CHAT))
    except Exception:
        logger.error("❌ Canale %s non raggiungibile: l'account e' amministratore del canale?", DESTINATION_CHAT)
        sys.exit(1)

    client.add_event_handler(saved_messages_handler, events.NewMessage(chats="me"))

    tasks = [asyncio.create_task(monitor()), asyncio.create_task(scheduler())]
    logger.info("👀 Leggo le operazioni da MT5...")
    try:
        await client.run_until_disconnected()
    finally:
        for task in tasks:
            task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Sala segnali fermata.")
