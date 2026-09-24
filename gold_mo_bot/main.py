import asyncio
import calendar
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from telethon import events

from telegram_client import client
from telegram_sender import (
    copy_message_to_destination,
    edit_destination_message,
    send_good_morning_message,
    send_daily_report_message,
    send_weekly_report_message,
    send_monthly_report_message,
)
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
    get_trade_by_primary_ticket,
    adopt_orphan_position,
    update_copy,
    update_status,
    update_trade_sltp,
    mark_breakeven_applied,
    mark_closed,
    report_was_sent,
    mark_report_sent,
)

from config import (
    SOURCE_CHAT,
    DESTINATION_CHAT,
    MAX_SIGNAL_AGE_SECONDS,
    TRADING_ENABLED,
    LOG_DIR,
    MONITOR_INTERVAL_SECONDS,
    COMMAND_PREFIX,
    DAILY_CLOSE_HOUR,
    DAILY_CLOSE_MINUTE,
    DAILY_REPORT_HOUR,
    DAILY_REPORT_MINUTE,
    GOOD_MORNING_HOUR,
    GOOD_MORNING_MINUTE,
    WEEKLY_REPORT_HOUR,
    WEEKLY_REPORT_MINUTE,
)

ITALY_TZ = ZoneInfo("Europe/Rome")

MT5_READY = False

# RUNNING -> tutto normale
# PAUSED  -> non copia ne' apre nuovi trade; i trade gia' aperti restano
#            gestiti normalmente (SL/TP/BE/chiusura continuano)
# STOPPED -> non ascolta/copia piu' nulla e non invia piu' messaggi nel
#            canale (report automatici compresi)
BOT_STATE = "RUNNING"

# ID del nostro stesso account Telegram: riconosce la chat "Messaggi
# Salvati" dove arrivano i comandi.
MY_USER_ID = None

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


def print_separator():
    logger.info("=" * 72)


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
        if BOT_STATE == "STOPPED":
            logger.info("🛑 BOT FERMATO | Messaggio #%s ignorato.", source_message_id)
            return

        if BOT_STATE == "PAUSED":
            logger.info("⏸️ BOT IN PAUSA | Messaggio #%s ignorato (non copiato).", source_message_id)
            return

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

        if action == "OPEN_WITH_PARAMS":
            await process_open_with_params(signal, source_message_id, telegram_datetime)
        elif action == "OPEN":
            await process_open(signal, source_message_id, telegram_datetime)
        elif action == "SET_SLTP":
            await process_sltp(signal, source_message_id)


# ============================================================
# APERTURA + SL/TP NELLO STESSO MESSAGGIO (caso normale Gold MO)
# ============================================================

async def process_open_with_params(signal, source_message_id, telegram_datetime):
    direction = signal["direction"]
    sl = float(signal["sl"])
    tp3 = signal.get("tp3")

    logger.info(
        "🎯 SEGNALE GOLD MO | %s | Zona indicativa=%s-%s | SL=%.2f | TP1=%s TP2=%s TP3(operativo)=%s TP4=%s open=%s",
        direction, signal.get("entry_zone_low"), signal.get("entry_zone_high"), sl,
        signal.get("tp1"), signal.get("tp2"), tp3, signal.get("tp4"), signal.get("tp_open_runner"),
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

    # Apertura con SL + TP3 gia' impostati nello stesso ordine: la
    # posizione non resta mai scoperta, nemmeno per un istante.
    try:
        primary, secondary = await dual_executor.open_market_order_dual(direction, sl=sl, tp=tp3 or 0.0)
    except Exception as e:
        logger.exception("❌ ERRORE APERTURA TRADE #%s", source_message_id)
        update_status(SOURCE_CHAT, source_message_id, "ERROR", error=str(e))
        return

    logger.info(
        "✅ TRADE APERTO | Conto1 ticket=%s prezzo=%.2f | SL=%.2f | TP=%s%s",
        primary.position_ticket, primary.price, sl, tp3,
        f" | Conto2 ticket={secondary.position_ticket} prezzo={secondary.price:.2f}" if secondary else " | Conto2: n/d",
    )

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
    update_trade_sltp(
        SOURCE_CHAT, source_message_id, sl,
        signal.get("tp1"), signal.get("tp2"), tp3, signal.get("tp4"),
        bool(signal.get("tp_open_runner")),
    )

    # Un solo messaggio pubblicato, gia' completo: entry reale, SL, e
    # l'unico TP mostrato (quello operativo, TP3).
    state = {
        "direction": direction,
        "entry": primary.price,
        "sl": sl,
        "tp1": signal.get("tp1"), "tp2": signal.get("tp2"), "tp3": tp3, "tp4": signal.get("tp4"),
        "tp_open_runner": bool(signal.get("tp_open_runner")),
        "breakeven_applied": False,
        "closed": False,
    }
    try:
        destination_message = await copy_message_to_destination(state)
        update_copy(SOURCE_CHAT, source_message_id, destination_message.id, datetime.now(timezone.utc).isoformat())
    except Exception:
        logger.exception("❌ ERRORE PUBBLICAZIONE DESTINATION #%s", source_message_id)


# ============================================================
# APERTURA IMMEDIATA A MERCATO (fallback: solo "Gold buy/sell now ...",
# senza SL/TP nello stesso messaggio)
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

    # Apertura silenziosa: NON pubblichiamo ancora nulla nel canale.
    # Il messaggio parte solo quando arrivano SL/TP (vedi process_sltp),
    # gia' completo di tutti i dati reali.
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
# APPLICAZIONE SL / TP (fallback: messaggio separato senza "Gold buy/sell
# now" nello stesso testo, applicato al trade aperto in attesa)
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

    # Il messaggio nel canale parte SOLO ora, completo di entry reale +
    # SL + TP: prima dell'arrivo di questo messaggio non era stato
    # pubblicato nulla (vedi process_open).
    if state["destination_message_id"] is None:
        try:
            destination_message = await copy_message_to_destination(state)
            update_copy(SOURCE_CHAT, original_message_id, destination_message.id, datetime.now(timezone.utc).isoformat())
        except Exception:
            logger.exception("❌ ERRORE PUBBLICAZIONE DESTINATION #%s", original_message_id)
    else:
        # Messaggio di correzione arrivato dopo che il segnale era gia'
        # stato pubblicato: aggiorna quello esistente.
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
# RECOVERY ALL'AVVIO
# ============================================================

async def recover_orphan_positions():
    """
    Non salta mai una posizione aperta sul conto principale: se una
    posizione con il nostro MAGIC risulta aperta su MT5 ma non ha
    nessuna riga nel DB (es. crash tra l'apertura e la scrittura),
    la "adotta" creando una riga sintetica e pubblicando un messaggio
    nel canale, cosi' il monitor riprende a gestirla (BE/chiusura).
    """
    try:
        positions = await asyncio.to_thread(mt5_executor.list_open_positions)
    except Exception:
        logger.exception("❌ Errore lettura posizioni aperte per il recovery all'avvio.")
        return

    if not positions:
        logger.info("ℹ️ Nessuna posizione aperta da recuperare all'avvio.")
        return

    adopted = 0
    for position in positions:
        ticket = position["ticket"]

        try:
            row = await asyncio.to_thread(get_trade_by_primary_ticket, ticket)
        except Exception:
            logger.exception("❌ Errore lettura DB per il ticket %s.", ticket)
            continue

        if row is not None:
            continue  # gia' tracciata, il monitor la gestisce normalmente

        synthetic_id = -abs(int(ticket))
        direction = position["direction"]
        sl = position["sl"] or None
        tp3 = position["tp"] or None
        status = "SLTP_APPLIED" if tp3 else "OPENED"

        try:
            adopt_orphan_position(
                SOURCE_CHAT, synthetic_id,
                direction=direction, entry=position["price_open"], sl=sl, tp3=tp3,
                mt5_ticket=ticket, mt5_volume=position["volume"], mt5_price=position["price_open"],
                status=status,
            )
        except Exception:
            logger.exception("❌ Errore adozione posizione orfana ticket %s.", ticket)
            continue

        # Se SL/TP non erano ancora stati applicati prima del crash, NON
        # pubblichiamo nulla ora: sara' il prossimo messaggio SL/TP in
        # arrivo dal canale sorgente a farlo (process_sltp trova questa
        # riga tramite get_latest_trade_awaiting_sltp), stessa regola
        # usata per l'apertura normale.
        if tp3:
            state = {
                "direction": direction, "entry": position["price_open"], "sl": sl,
                "tp1": None, "tp2": None, "tp3": tp3, "tp4": None, "tp_open_runner": False,
                "breakeven_applied": False, "closed": False,
            }
            try:
                destination_message = await copy_message_to_destination(state)
                update_copy(SOURCE_CHAT, synthetic_id, destination_message.id, datetime.now(timezone.utc).isoformat())
            except Exception:
                logger.exception("❌ Errore pubblicazione messaggio di recovery ticket %s.", ticket)

        adopted += 1
        logger.warning("♻️ POSIZIONE ORFANA ADOTTATA | Ticket=%s | %s", ticket, direction)

    if adopted:
        logger.warning("♻️ RECOVERY COMPLETATO | %s posizioni adottate.", adopted)


# ============================================================
# COMANDI DA "MESSAGGI SALVATI"
# ============================================================
#
# bot5_play    -> il bot riparte al 100%
# bot5_stop    -> chiude tutte le posizioni (entrambi i conti) e ferma
#                 completamente il bot (niente ascolto ne' messaggi)
# bot5_riavvio -> come bot5_stop e subito dopo come bot5_play
# bot5_pausa   -> non copia ne' apre nuovi trade, ma i trade gia'
#                 aperti restano gestiti normalmente (BE/chiusura)
# bot5_status  -> stato attuale + posizioni aperte con il profitto
#                 flottante di ciascuna (conto principale + secondo)
# bot5_report  -> invia subito il report giornaliero
# bot5_reportw -> invia subito il report settimanale
# bot5_reportm -> invia subito il report mensile
# bot5_comandi -> mostra l'elenco comandi
# ============================================================

COMMANDS_HELP_TEXT = (
    "📋 COMANDI DISPONIBILI\n\n"
    f"▶️ {COMMAND_PREFIX}play — il bot riparte al 100%\n"
    f"🛑 {COMMAND_PREFIX}stop — chiude tutte le posizioni (entrambi i conti) e ferma il bot\n"
    f"🔄 {COMMAND_PREFIX}riavvio — come stop e subito dopo come play\n"
    f"⏸️ {COMMAND_PREFIX}pausa — non copia ne' apre nuovi trade, lascia gestiti quelli aperti\n"
    f"📊 {COMMAND_PREFIX}status — stato del bot + posizioni aperte\n"
    f"📈 {COMMAND_PREFIX}report — invia subito il report giornaliero\n"
    f"📅 {COMMAND_PREFIX}reportw — invia subito il report settimanale\n"
    f"🗓️ {COMMAND_PREFIX}reportm — invia subito il report mensile\n"
    f"❓ {COMMAND_PREFIX}comandi — mostra questo elenco"
)


def _format_status_message():
    state_labels = {
        "RUNNING": "🟢 ATTIVO AL 100%",
        "PAUSED": "⏸️ IN PAUSA",
        "STOPPED": "🛑 FERMO",
    }
    lines = [f"<b>STATO BOT:</b> {state_labels.get(BOT_STATE, BOT_STATE)}", ""]

    if not MT5_READY:
        lines.append("⚠️ Impossibile leggere le posizioni: MT5 conto principale non connesso.")
        return "\n".join(lines)

    positions = mt5_executor.list_open_positions()
    if not positions:
        lines.append("Nessuna posizione aperta (conto principale).")
    else:
        lines.append(f"<b>Conto principale ({len(positions)}):</b>")
        for position in positions:
            lines.append(f"XAUUSD {position['direction']} — {position['profit']:+.2f}$")

    return "\n".join(lines)


@client.on(events.NewMessage())
async def command_handler(event):
    global BOT_STATE

    if MY_USER_ID is None or not event.is_private:
        return
    if event.chat_id != MY_USER_ID:
        return

    text = (event.message.text or "").strip().lower()
    if text.startswith("/"):
        text = text[1:]
    if not text.startswith(COMMAND_PREFIX):
        return

    print_separator()
    logger.info("🎮 COMANDO RICEVUTO: %s", text)
    print_separator()

    command = text[len(COMMAND_PREFIX):]

    if command == "play":
        BOT_STATE = "RUNNING"
        logger.info("🟢 BOT_STATE -> RUNNING")
        await event.reply("✅ Comando eseguito.\n🟢 Il bot è di nuovo ATTIVO al 100%.")

    elif command in ("stop", "riavvio"):
        try:
            p_closed, p_errors, s_closed, s_errors = await dual_executor.close_all_dual()
        except Exception as e:
            logger.exception("❌ Errore chiusura posizioni durante %s: %s", command, e)
            await event.reply(f"❌ Errore durante la chiusura delle posizioni ({e}). Comando NON eseguito.")
            print_separator()
            return

        BOT_STATE = "STOPPED" if command == "stop" else "RUNNING"
        logger.info(
            "%s BOT_STATE -> %s | Conto1 chiuse=%s errori=%s | Conto2 chiuse=%s errori=%s",
            "🛑" if command == "stop" else "🔄", BOT_STATE, len(p_closed), len(p_errors), len(s_closed), len(s_errors),
        )

        summary = (
            f"🛑 Posizioni chiuse — Conto1: {len(p_closed)} (errori {len(p_errors)}) | "
            f"Conto2: {len(s_closed)} (errori {len(s_errors)})."
        )
        if command == "stop":
            await event.reply(f"✅ Comando eseguito.\n{summary}\n🛑 Bot FERMATO finché non ricevo {COMMAND_PREFIX}play.")
        else:
            await event.reply(f"✅ Comando eseguito.\n{summary}\n🟢 Bot subito dopo riattivato al 100%.")

    elif command == "pausa":
        BOT_STATE = "PAUSED"
        logger.info("⏸️ BOT_STATE -> PAUSED")
        await event.reply(
            "✅ Comando eseguito.\n⏸️ Il bot è IN PAUSA: non aprirà nuovi trade, "
            "ma le posizioni già aperte restano gestite normalmente."
        )

    elif command == "status":
        try:
            status_message = await asyncio.to_thread(_format_status_message)
        except Exception as e:
            logger.exception("❌ Errore lettura stato: %s", e)
            await event.reply(f"❌ Errore durante la lettura dello stato ({e}).")
            print_separator()
            return
        await event.reply(status_message)

    elif command == "report":
        try:
            await generate_daily_report(datetime.now(ITALY_TZ).date())
        except Exception as e:
            logger.exception("❌ Errore invio report giornaliero manuale: %s", e)
            await event.reply(f"❌ Errore durante l'invio ({e}).")
            print_separator()
            return
        await event.reply("✅ Report giornaliero inviato nel canale.")

    elif command == "reportw":
        today = datetime.now(ITALY_TZ).date()
        monday = today - timedelta(days=today.weekday())
        try:
            await generate_weekly_report(monday)
        except Exception as e:
            logger.exception("❌ Errore invio report settimanale manuale: %s", e)
            await event.reply(f"❌ Errore durante l'invio ({e}).")
            print_separator()
            return
        await event.reply("✅ Report settimanale inviato nel canale.")

    elif command == "reportm":
        today = datetime.now(ITALY_TZ).date()
        try:
            await generate_monthly_report(today.replace(day=1))
        except Exception as e:
            logger.exception("❌ Errore invio report mensile manuale: %s", e)
            await event.reply(f"❌ Errore durante l'invio ({e}).")
            print_separator()
            return
        await event.reply("✅ Report mensile inviato nel canale.")

    elif command == "comandi":
        await event.reply(COMMANDS_HELP_TEXT)

    else:
        await event.reply(f"❓ Comando non riconosciuto.\n\n{COMMANDS_HELP_TEXT}")

    print_separator()


# ============================================================
# REPORT: LETTURA DIRETTA DALLO STORICO MT5 (conto principale)
# ============================================================

_ITALIAN_MONTH_ABBR = {
    1: "GEN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAG", 6: "GIU",
    7: "LUG", 8: "AGO", 9: "SET", 10: "OTT", 11: "NOV", 12: "DIC",
}


def _format_date_range_it(start_date, end_date):
    return f"{start_date.day} {_ITALIAN_MONTH_ABBR[start_date.month]} - {end_date.day} {_ITALIAN_MONTH_ABBR[end_date.month]}"


def _build_report_stats(trades):
    operations = len(trades)
    wins = sum(1 for t in trades if t["result"] == "WIN")
    losses = sum(1 for t in trades if t["result"] == "LOSS")
    breakeven_result = sum(1 for t in trades if t["result"] == "BE")

    # BE "gestito dal bot" (SL spostato a breakeven per TP1) e' diverso dal
    # risultato "BE" per pips quasi nulli: lo leggiamo dal nostro DB.
    breakeven_managed = 0
    for trade in trades:
        row = get_trade_by_primary_ticket(trade["position_id"])
        if row is not None and bool(row[3]):
            breakeven_managed += 1

    pips = sum(float(t["pips"]) for t in trades)
    win_rate = (wins / operations * 100.0) if operations else 0.0

    return {
        "operations": operations,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven_managed or breakeven_result,
        "pips": pips,
        "win_rate": win_rate,
    }


async def generate_daily_report(report_date):
    start_local = datetime(report_date.year, report_date.month, report_date.day, tzinfo=ITALY_TZ)
    end_local = start_local + timedelta(days=1)

    trades = await asyncio.to_thread(
        mt5_executor.get_closed_trades_for_period,
        start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc),
    )
    stats = _build_report_stats(trades)
    await send_daily_report_message(date=report_date.strftime("%d/%m/%Y"), **stats)


async def generate_weekly_report(week_monday):
    start_local = datetime(week_monday.year, week_monday.month, week_monday.day, tzinfo=ITALY_TZ)
    end_local = start_local + timedelta(days=5)

    trades = await asyncio.to_thread(
        mt5_executor.get_closed_trades_for_period,
        start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc),
    )
    stats = _build_report_stats(trades)
    friday = week_monday + timedelta(days=4)
    await send_weekly_report_message(date_range=_format_date_range_it(week_monday, friday), **stats)


async def generate_monthly_report(report_month):
    start_local = datetime(report_month.year, report_month.month, 1, tzinfo=ITALY_TZ)
    if report_month.month == 12:
        next_month_local = datetime(report_month.year + 1, 1, 1, tzinfo=ITALY_TZ)
    else:
        next_month_local = datetime(report_month.year, report_month.month + 1, 1, tzinfo=ITALY_TZ)
    last_day = (next_month_local - timedelta(days=1)).date()

    trades = await asyncio.to_thread(
        mt5_executor.get_closed_trades_for_period,
        start_local.astimezone(timezone.utc), next_month_local.astimezone(timezone.utc),
    )
    stats = _build_report_stats(trades)
    await send_monthly_report_message(date_range=_format_date_range_it(start_local.date(), last_day), **stats)


# ============================================================
# SCHEDULER: BUONGIORNO, CHIUSURA FINE GIORNATA, REPORT
# ============================================================

def _next_scheduled_event(now_local):
    candidates = []

    for offset in range(8):
        day = (now_local + timedelta(days=offset)).date()
        if day.weekday() < 5:
            candidate = datetime(day.year, day.month, day.day, GOOD_MORNING_HOUR, GOOD_MORNING_MINUTE, tzinfo=ITALY_TZ)
            if candidate > now_local:
                candidates.append((candidate, "morning"))

    for offset in range(8):
        day = (now_local + timedelta(days=offset)).date()
        if day.weekday() < 5:
            candidate = datetime(day.year, day.month, day.day, DAILY_CLOSE_HOUR, DAILY_CLOSE_MINUTE, tzinfo=ITALY_TZ)
            if candidate > now_local:
                candidates.append((candidate, "close_positions"))

    for offset in range(8):
        day = (now_local + timedelta(days=offset)).date()
        if day.weekday() < 5:
            candidate = datetime(day.year, day.month, day.day, DAILY_REPORT_HOUR, DAILY_REPORT_MINUTE, tzinfo=ITALY_TZ)
            if candidate > now_local:
                candidates.append((candidate, "daily"))

    for offset in range(8):
        day = (now_local + timedelta(days=offset)).date()
        if day.weekday() == 5:
            candidate = datetime(day.year, day.month, day.day, WEEKLY_REPORT_HOUR, WEEKLY_REPORT_MINUTE, tzinfo=ITALY_TZ)
            if candidate > now_local:
                candidates.append((candidate, "weekly"))

    for offset in range(32):
        day = (now_local + timedelta(days=offset)).date()
        last_day_of_month = calendar.monthrange(day.year, day.month)[1]
        if day.day == last_day_of_month:
            candidate = datetime(day.year, day.month, day.day, 23, 59, tzinfo=ITALY_TZ)
            if candidate > now_local:
                candidates.append((candidate, "monthly"))

    return min(candidates, key=lambda item: item[0])


async def automatic_scheduler(stop_event):
    """Scheduler locale Europe/Rome. Evita duplicati dopo un riavvio usando sent_reports."""
    while not stop_event.is_set():
        now_local = datetime.now(ITALY_TZ)
        next_event, event_type = _next_scheduled_event(now_local)
        delay = max(0.5, (next_event - now_local).total_seconds())

        logger.info("⏰ Prossimo evento automatico: %s alle %s IT", event_type, next_event.strftime("%d/%m/%Y %H:%M"))

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
            continue
        except asyncio.TimeoutError:
            pass

        # asyncio.sleep puo' risvegliarsi qualche centinaio di ms prima:
        # attendiamo l'eventuale residuo per evitare doppi invii.
        residual = (next_event - datetime.now(ITALY_TZ)).total_seconds()
        if residual > 0:
            await asyncio.sleep(residual)

        if BOT_STATE == "STOPPED":
            logger.info("🛑 BOT FERMATO | Evento automatico '%s' saltato.", event_type)
            continue

        event_date = next_event.date()

        try:
            if event_type == "morning":
                await send_good_morning_message()
                logger.info("☀️ BUONGIORNO INVIATO")

            elif event_type == "close_positions":
                close_key = event_date.isoformat()
                if report_was_sent("close_positions", close_key):
                    continue
                p_closed, p_errors, s_closed, s_errors = await dual_executor.close_all_dual()
                mark_report_sent("close_positions", close_key)
                logger.info(
                    "🔒 CHIUSURA FINE GIORNATA | Conto1 chiuse=%s errori=%s | Conto2 chiuse=%s errori=%s",
                    len(p_closed), len(p_errors), len(s_closed), len(s_errors),
                )

            elif event_type == "daily":
                report_key = event_date.isoformat()
                if report_was_sent("daily", report_key):
                    continue
                await generate_daily_report(event_date)
                mark_report_sent("daily", report_key)
                logger.info("📊 REPORT GIORNALIERO INVIATO | %s", report_key)

            elif event_type == "weekly":
                monday = event_date - timedelta(days=event_date.weekday())
                report_key = monday.isoformat()
                if report_was_sent("weekly", report_key):
                    continue
                await generate_weekly_report(monday)
                mark_report_sent("weekly", report_key)
                logger.info("📊 REPORT SETTIMANALE INVIATO | %s", report_key)

            elif event_type == "monthly":
                report_key = event_date.strftime("%Y-%m")
                if report_was_sent("monthly", report_key):
                    continue
                await generate_monthly_report(event_date.replace(day=1))
                mark_report_sent("monthly", report_key)
                logger.info("📊 REPORT MENSILE INVIATO | %s", report_key)

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE EVENTO AUTOMATICO '%s'", event_type)


# ============================================================
# AVVIO
# ============================================================

async def main():
    global MT5_READY, MY_USER_ID

    init_database()

    await client.start()
    me = await client.get_me()
    MY_USER_ID = me.id
    logger.info("👤 Comandi %s* attivi su Messaggi Salvati di: %s (ID %s)", COMMAND_PREFIX, me.first_name, MY_USER_ID)

    MT5_READY = mt5_executor.connect_mt5()
    if not MT5_READY:
        logger.error("❌ Connessione MT5 conto principale fallita. Il bot copia i messaggi ma NON tradera'.")
    else:
        await recover_orphan_positions()

    if dual_executor.secondary_enabled():
        dual_executor.start_secondary_worker()

    stop_event = asyncio.Event()
    monitor_task = asyncio.create_task(monitor_loop(stop_event))
    scheduler_task = asyncio.create_task(automatic_scheduler(stop_event))

    logger.info("=" * 72)
    logger.info("🤖 GOLD MO BOT AVVIATO | Source=%s | Destination=%s", SOURCE_CHAT, DESTINATION_CHAT)
    logger.info(
        "📅 Scheduler: ☀️ %02d:%02d | 🔒 chiusura %02d:%02d | 📊 giornaliero %02d:%02d | "
        "📅 settimanale sab %02d:%02d | 🗓️ mensile ultimo giorno 23:59",
        GOOD_MORNING_HOUR, GOOD_MORNING_MINUTE, DAILY_CLOSE_HOUR, DAILY_CLOSE_MINUTE,
        DAILY_REPORT_HOUR, DAILY_REPORT_MINUTE, WEEKLY_REPORT_HOUR, WEEKLY_REPORT_MINUTE,
    )
    logger.info("=" * 72)

    try:
        await client.run_until_disconnected()
    finally:
        stop_event.set()
        await monitor_task
        await scheduler_task
        dual_executor.stop_secondary_worker()


if __name__ == "__main__":
    asyncio.run(main())
