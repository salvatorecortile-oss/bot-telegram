import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from telethon import events

from telegram_client import client
from telegram_sender import copy_message_to_destination, edit_destination_message
from signal_parser import parse_signal

import mt5_executor
import dual_executor

from database import (
    init_database,
    insert_message,
    get_message,
    get_latest_open_trade,
    get_latest_trade_awaiting_sltp,
    get_open_trades,
    update_copy,
    update_status,
    update_trade_sltp,
    mark_breakeven_applied,
    mark_closed,
)

from config import (
    SOURCE_CHAT,
    DESTINATION_CHAT,
    MAX_SIGNAL_AGE_SECONDS,
    TRADING_ENABLED,
    LOG_DIR,
    MONITOR_INTERVAL_SECONDS,
)

ITALY_TZ = ZoneInfo("Europe/Rome")

MT5_READY = False

# Serializza NewMessage/edit sullo stesso message_id.
message_locks = {}


def get_message_lock(message_id):
    lock = message_locks.get(message_id)
    if lock is None:
        lock = asyncio.Lock()
        message_locks[message_id] = lock
    return lock


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = Path(LOG_DIR) / "bot.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    class ItalyFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            dt = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone(ITALY_TZ)
            return dt.strftime("%d/%m/%Y %H:%M:%S") + f".{dt.microsecond // 1000:03d}"

    formatter = ItalyFormatter("%(asctime)s | %(levelname)s | %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


logger = setup_logging()


def calculate_signal_age_seconds(telegram_datetime):
    if telegram_datetime is None:
        return float("inf")
    if telegram_datetime.tzinfo is None:
        telegram_datetime = telegram_datetime.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - telegram_datetime.astimezone(timezone.utc)).total_seconds()
    return max(0.0, age)


def _row_to_state(row, *, closed=False, close_reason=None, close_price=None):
    (
        source_message_id, destination_message_id, direction, entry,
        sl, tp1, tp2, tp3, tp4, tp_open_runner,
        mt5_ticket, mt5_price, mt5_ticket_2, mt5_price_2,
        sltp_applied, breakeven_applied,
    ) = row

    return {
        "source_message_id": source_message_id,
        "destination_message_id": destination_message_id,
        "direction": direction,
        "entry": mt5_price if mt5_price is not None else entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "tp4": tp4,
        "tp_open_runner": bool(tp_open_runner),
        "primary_ticket": mt5_ticket,
        "secondary_ticket": mt5_ticket_2,
        "sltp_applied": bool(sltp_applied),
        "breakeven_applied": bool(breakeven_applied),
        "closed": closed,
        "close_reason": close_reason,
        "close_price": close_price,
    }


# ============================================================
# NUOVO MESSAGGIO DAL CANALE SORGENTE
# ============================================================

@client.on(events.NewMessage(chats=SOURCE_CHAT))
async def new_message_handler(event):
    message = event.message
    source_message_id = message.id

    async with get_message_lock(source_message_id):
        received_datetime = datetime.now(timezone.utc)
        telegram_datetime = message.date

        signal = parse_signal(message.text)
        if signal is None:
            logger.info("⏭️ MESSAGGIO #%s IGNORATO | Nessun formato riconosciuto.", source_message_id)
            return

        try:
            existing = get_message(SOURCE_CHAT, source_message_id)
        except Exception:
            logger.exception("❌ ERRORE LETTURA DATABASE #%s", source_message_id)
            return

        if existing is not None:
            logger.info("↩️ MESSAGGIO #%s GIA' PRESENTE. Ignoro.", source_message_id)
            return

        action = signal["action"]

        try:
            inserted = insert_message(
                source_chat_id=SOURCE_CHAT,
                source_message_id=source_message_id,
                symbol=signal.get("symbol"),
                direction=signal.get("direction"),
                entry=signal.get("entry"),
                entry_zone_low=signal.get("entry_zone_low"),
                entry_zone_high=signal.get("entry_zone_high"),
                status="RECEIVED",
                source_datetime=telegram_datetime.isoformat(),
                received_datetime=received_datetime.isoformat(),
            )
        except Exception:
            logger.exception("❌ ERRORE INSERIMENTO DATABASE #%s", source_message_id)
            return

        if not inserted:
            logger.info("↩️ MESSAGGIO #%s GIA' INSERITO. Ignoro.", source_message_id)
            return

        if action == "OPEN":
            await process_open(signal, source_message_id, telegram_datetime)
        elif action == "SET_SLTP":
            await process_sltp(signal, source_message_id)


# ============================================================
# APERTURA IMMEDIATA A MERCATO
# ============================================================

async def process_open(signal, source_message_id, telegram_datetime):
    direction = signal["direction"]

    logger.info(
        "🎯 SEGNALE GOLD MO | %s | Zona indicativa=%s-%s",
        direction, signal.get("entry_zone_low"), signal.get("entry_zone_high"),
    )

    if not TRADING_ENABLED:
        logger.warning("🚫 TRADING DISABILITATO | #%s", source_message_id)
        update_status(SOURCE_CHAT, source_message_id, "TRADE_DISABLED")
        return

    if not MT5_READY:
        logger.warning("🚫 MT5 NON PRONTO | #%s", source_message_id)
        update_status(SOURCE_CHAT, source_message_id, "MT5_NOT_READY")
        return

    signal_age = calculate_signal_age_seconds(telegram_datetime)
    if signal_age > MAX_SIGNAL_AGE_SECONDS:
        logger.warning("🚫 SEGNALE TROPPO VECCHIO | #%s | Eta'=%.2fs", source_message_id, signal_age)
        update_status(SOURCE_CHAT, source_message_id, "SIGNAL_TOO_OLD")
        return

    try:
        primary, secondary = await dual_executor.open_market_order_dual(direction, sl=0.0)
    except Exception as e:
        logger.exception("❌ ERRORE APERTURA TRADE #%s", source_message_id)
        update_status(SOURCE_CHAT, source_message_id, "ERROR", error=str(e))
        return

    logger.info(
        "✅ TRADE APERTO | Conto1 ticket=%s prezzo=%.2f%s",
        primary.position_ticket, primary.price,
        f" | Conto2 ticket={secondary.position_ticket} prezzo={secondary.price:.2f}" if secondary else " | Conto2: n/d",
    )

    state = {
        "direction": direction,
        "entry": primary.price,
        "sl": None,
        "tp1": None, "tp2": None, "tp3": None, "tp4": None,
        "tp_open_runner": False,
        "breakeven_applied": False,
        "closed": False,
    }

    try:
        destination_message = await copy_message_to_destination(state)
        update_copy(SOURCE_CHAT, source_message_id, destination_message.id, datetime.now(timezone.utc).isoformat())
    except Exception:
        logger.exception("❌ ERRORE COPIA DESTINATION #%s", source_message_id)

    update_status(
        SOURCE_CHAT, source_message_id, "OPENED",
        mt5_ticket=primary.position_ticket, mt5_deal=primary.deal,
        mt5_volume=primary.volume, mt5_price=primary.price,
        mt5_ticket_2=secondary.position_ticket if secondary else None,
        mt5_deal_2=secondary.deal if secondary else None,
        mt5_volume_2=secondary.volume if secondary else None,
        mt5_price_2=secondary.price if secondary else None,
        trade_datetime=datetime.now(timezone.utc).isoformat(),
    )


# ============================================================
# APPLICAZIONE SL / TP (secondo messaggio)
# ============================================================

async def process_sltp(signal, source_message_id):
    sl = float(signal["sl"])
    tp3 = signal.get("tp3")

    logger.info(
        "🛠️ SL/TP RICEVUTI #%s | SL=%.2f | TP1=%s TP2=%s TP3(operativo)=%s TP4=%s open=%s",
        source_message_id, sl, signal.get("tp1"), signal.get("tp2"), tp3,
        signal.get("tp4"), signal.get("tp_open_runner"),
    )

    if not TRADING_ENABLED:
        update_status(SOURCE_CHAT, source_message_id, "TRADE_DISABLED")
        return
    if not MT5_READY:
        update_status(SOURCE_CHAT, source_message_id, "MT5_NOT_READY")
        return

    # Prima cerchiamo un trade ancora "in attesa" di SL/TP (caso normale:
    # un solo trade alla volta senza parametri). Se non c'e' (es. arriva
    # una correzione dopo che i parametri erano gia' stati applicati),
    # ripieghiamo sul trade aperto piu' recente in assoluto.
    row = get_latest_trade_awaiting_sltp(SOURCE_CHAT)
    if row is None:
        row = get_latest_open_trade(SOURCE_CHAT)
    if row is None:
        logger.warning("⚠️ NESSUN TRADE APERTO A CUI ASSOCIARE SL/TP | #%s", source_message_id)
        update_status(SOURCE_CHAT, source_message_id, "NO_OPEN_TRADE")
        return

    state = _row_to_state(row)
    primary_ticket = state["primary_ticket"]
    secondary_ticket = state["secondary_ticket"]
    original_message_id = state["source_message_id"]

    try:
        await dual_executor.apply_sltp_dual(primary_ticket, secondary_ticket, sl, tp3 or 0.0)
    except Exception as e:
        logger.exception("❌ ERRORE APPLICAZIONE SL/TP #%s", source_message_id)
        update_status(SOURCE_CHAT, source_message_id, "SLTP_ERROR", error=str(e))
        return

    update_trade_sltp(
        SOURCE_CHAT, original_message_id, sl,
        signal.get("tp1"), signal.get("tp2"), tp3, signal.get("tp4"),
        bool(signal.get("tp_open_runner")),
    )
    update_status(SOURCE_CHAT, source_message_id, "PARAMS_APPLIED", trade_datetime=datetime.now(timezone.utc).isoformat())

    state.update({
        "sl": sl, "tp1": signal.get("tp1"), "tp2": signal.get("tp2"),
        "tp3": tp3, "tp4": signal.get("tp4"),
        "tp_open_runner": bool(signal.get("tp_open_runner")),
    })

    if state["destination_message_id"] is not None:
        try:
            await edit_destination_message(state["destination_message_id"], state)
        except Exception:
            logger.exception("❌ ERRORE MODIFICA DESTINATION #%s", state["destination_message_id"])

    logger.info("✅ SL/TP APPLICATI | Position=%s | SL=%.2f | TP operativo(TP3)=%s", primary_ticket, sl, tp3)


# ============================================================
# MONITOR: TP1 -> BREAK EVEN, RILEVAMENTO CHIUSURE
# ============================================================

async def monitor_loop(stop_event):
    while not stop_event.is_set():
        try:
            rows = await asyncio.to_thread(get_open_trades, SOURCE_CHAT)
            for row in rows:
                await _monitor_single_trade(row)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE MONITOR LOOP")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=MONITOR_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass


async def _monitor_single_trade(row):
    state = _row_to_state(row)
    source_message_id = state["source_message_id"]
    primary_ticket = state["primary_ticket"]
    secondary_ticket = state["secondary_ticket"]
    direction = state["direction"]

    # --------------------------------------------------------
    # CHIUSURA (TP3 o SL): controlliamo prima, se e' gia' chiusa
    # non ha senso proseguire con BE.
    # --------------------------------------------------------
    is_open = await asyncio.to_thread(dual_executor.primary_position_is_open, primary_ticket)
    if not is_open:
        info = await asyncio.to_thread(dual_executor.primary_closed_position_info, primary_ticket)
        if info is None:
            # Storico non ancora disponibile: riprovare al prossimo giro.
            return

        close_reason = "TP" if info["is_tp"] else ("SL" if info["is_sl"] else None)
        mark_closed(SOURCE_CHAT, source_message_id)

        state.update({"closed": True, "close_reason": close_reason, "close_price": info["price"]})
        if state["destination_message_id"] is not None:
            try:
                await edit_destination_message(state["destination_message_id"], state)
            except Exception:
                logger.exception("❌ ERRORE MODIFICA DESTINATION (chiusura) #%s", state["destination_message_id"])

        logger.info(
            "🏁 TRADE CHIUSO | Position=%s | Motivo=%s | Prezzo=%.2f",
            primary_ticket, close_reason or "N/D", info["price"],
        )
        return

    # --------------------------------------------------------
    # TP1 -> BREAK EVEN
    # --------------------------------------------------------
    if not state["sltp_applied"] or state["breakeven_applied"] or state["tp1"] is None:
        return

    price = await asyncio.to_thread(mt5_executor.current_price, direction)
    if price is None:
        return

    tp1 = float(state["tp1"])
    reached = (direction == "BUY" and price >= tp1) or (direction == "SELL" and price <= tp1)
    if not reached:
        return

    try:
        new_sl, _ = await dual_executor.move_to_breakeven_dual(primary_ticket, secondary_ticket)
    except Exception:
        logger.exception("❌ ERRORE BREAK EVEN | Position=%s", primary_ticket)
        return

    mark_breakeven_applied(SOURCE_CHAT, source_message_id, new_sl)
    state.update({"sl": new_sl, "breakeven_applied": True})

    if state["destination_message_id"] is not None:
        try:
            await edit_destination_message(state["destination_message_id"], state)
        except Exception:
            logger.exception("❌ ERRORE MODIFICA DESTINATION (BE) #%s", state["destination_message_id"])

    logger.info("🟢 BREAK EVEN APPLICATO | Position=%s | Nuovo SL=%.2f | TP1 raggiunto=%.2f", primary_ticket, new_sl, tp1)


# ============================================================
# AVVIO
# ============================================================

async def main():
    global MT5_READY

    init_database()

    MT5_READY = mt5_executor.connect_mt5()
    if not MT5_READY:
        logger.error("❌ Connessione MT5 conto principale fallita. Il bot copia i messaggi ma NON tradera'.")

    if dual_executor.secondary_enabled():
        dual_executor.start_secondary_worker()

    stop_event = asyncio.Event()
    monitor_task = asyncio.create_task(monitor_loop(stop_event))

    logger.info("=" * 72)
    logger.info("🤖 GOLD MO BOT AVVIATO | Source=%s | Destination=%s", SOURCE_CHAT, DESTINATION_CHAT)
    logger.info("=" * 72)

    await client.start()
    try:
        await client.run_until_disconnected()
    finally:
        stop_event.set()
        await monitor_task
        dual_executor.stop_secondary_worker()


if __name__ == "__main__":
    asyncio.run(main())
