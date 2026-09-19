import asyncio
import calendar
import logging
import re
import time
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from telethon import events
import MetaTrader5 as mt5
from telethon.errors import MessageNotModifiedError

from telegram_client import client

from telegram_sender import (
    copy_message_to_destination,
    edit_destination_message,
    edit_destination_message_with_signal,
    send_trailing_sl_hit_message,
    send_breakeven_sl_hit_message,
    send_initial_sl_hit_message,
    send_be_applied_message,
    send_pips_progress_message,
    send_take_profit_reached_message,
    send_daily_report_message,
    send_weekly_report_message,
    send_monthly_report_message,
    send_good_morning_message,
    send_forced_daily_close_message,
)

from signal_parser import parse_signal

from mt5_executor import (
    connect_mt5,
    open_market_order,
    close_position,
    modify_position_sl,
    modify_position_sl_tp,
    move_position_to_breakeven,
    move_position_to_profit_protection,
    get_closed_position_info,
)

from database import (
    init_database,
    insert_message,
    get_message,
    get_latest_open_trade,
    get_open_trade_for_signal,
    get_open_trades,
    get_open_trade_by_ticket_any_source,
    get_recovery_candidates,
    associate_position_ticket,
    adopt_orphan_position,
    update_copy,
    update_trade_sl,
    update_trade_params,
    update_status,
    has_trailing_sl_update,
    has_breakeven_applied,
    mark_automatic_breakeven,
    get_last_pips_notified,
    set_last_pips_notified,
    mark_tp3_reached,
    has_tp3_reached,
    record_daily_trade_result,
    get_daily_trade_results,
    get_weekly_trade_results,
    get_monthly_trade_results,
    has_daily_report,
    mark_daily_report_sent,
    has_weekly_report,
    mark_weekly_report_sent,
    has_monthly_report,
    mark_monthly_report_sent,
)

from config import (
    SOURCE_CHAT,
    DESTINATION_CHAT,
    MAX_SIGNAL_AGE_SECONDS,
    MAX_SIMULTANEOUS_SIGNALS,
    TRADING_ENABLED,
    LOG_DIR,
    MAGIC_NUMBER,
)


# ============================================================
# CONFIGURAZIONE
# ============================================================

ITALY_TZ = ZoneInfo("Europe/Rome")

BOT_START_TIME = datetime.now(timezone.utc)

# Task di apertura trade attualmente in corso
active_trade_tasks = {}

# Posizioni recuperate da MT5 all'avvio. Il valore e' il source_chat_id
# del record DB associato al ticket, se esistente.
recovered_trade_rows = []
recovered_trade_sources = {}

# Lock per evitare che due eventi contemporanei
# prenotino lo stesso slot simultaneo.
simultaneous_signal_lock = asyncio.Lock()

# Contatore dei segnali per timestamp Telegram al secondo.
#
# Esempio:
#
# 13:31:03 -> 3 segnali massimo
# 13:31:04 -> altri 3 segnali massimo
# 13:31:05 -> altri 3 segnali massimo
#
# Il contatore NON viene decrementato quando un trade termina.
# In questo modo il limite è realmente "massimo 3 segnali
# ricevuti nello stesso secondo Telegram".
simultaneous_signal_counts = {}


# ============================================================
# LOGGING
# ============================================================

def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_file = Path(LOG_DIR) / "bot.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Evita duplicazione degli handler se il modulo viene
    # eventualmente ricaricato.
    if logger.handlers:
        return logger

    class ItalyMillisecondsFormatter(logging.Formatter):
        """Logger formatter con orario italiano e millisecondi reali."""

        def formatTime(self, record, datefmt=None):
            dt = datetime.fromtimestamp(record.created, tz=timezone.utc).astimezone(ITALY_TZ)
            if datefmt:
                return dt.strftime(datefmt).replace("%f", f"{dt.microsecond:06d}")
            return dt.strftime("%d/%m/%Y %H:%M:%S") + f".{dt.microsecond // 1000:03d}"

    formatter = ItalyMillisecondsFormatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S.%f",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()


# ============================================================
# STATO MT5
# ============================================================

MT5_READY = False


# ============================================================
# LOCK PER MESSAGGI
# ============================================================

# Serve a evitare che NewMessage e MessageEdited
# elaborino contemporaneamente lo stesso message_id.
message_locks = {}


def get_message_lock(source_message_id):
    lock = message_locks.get(source_message_id)

    if lock is None:
        lock = asyncio.Lock()
        message_locks[source_message_id] = lock

    return lock


# ============================================================
# UTILITY
# ============================================================

def timestamp():
    """
    Orario locale del server con precisione al millisecondo.
    """
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def print_separator():
    logger.info("=" * 72)


def telegram_timestamp_key(telegram_datetime):
    """
    Restituisce il timestamp Telegram arrotondato al secondo.

    Esempio:
    13:31:06.000 -> 13:31:06
    13:31:06.850 -> 13:31:06

    Il limite dei 3 segnali viene quindi applicato
    allo stesso secondo Telegram.
    """
    if telegram_datetime.tzinfo is None:
        telegram_datetime = telegram_datetime.replace(
            tzinfo=timezone.utc
        )

    telegram_datetime = telegram_datetime.astimezone(
        timezone.utc
    )

    return telegram_datetime.replace(
        microsecond=0
    )


def calculate_signal_age_seconds(telegram_datetime):
    """
    Calcola l'età del segnale usando esclusivamente
    il timestamp originale Telegram.

    NON usa il momento in cui il bot ha ricevuto il messaggio.
    """

    if telegram_datetime is None:
        return float("inf")

    if telegram_datetime.tzinfo is None:
        telegram_datetime = telegram_datetime.replace(
            tzinfo=timezone.utc
        )

    telegram_utc = telegram_datetime.astimezone(
        timezone.utc
    )

    now_utc = datetime.now(timezone.utc)

    age = (
        now_utc - telegram_utc
    ).total_seconds()

    # In caso di piccolo disallineamento dell'orologio,
    # non consideriamo il messaggio "negativo".
    return max(0.0, age)


async def reserve_simultaneous_signal_slot(
    telegram_datetime,
    source_message_id,
):
    """
    Prenota uno dei massimo MAX_SIMULTANEOUS_SIGNALS
    slot disponibili per lo stesso secondo Telegram.

    Ritorna:

        True  -> il segnale può essere tradato
        False -> limite raggiunto
    """

    key = telegram_timestamp_key(
        telegram_datetime
    )

    async with simultaneous_signal_lock:

        current_count = simultaneous_signal_counts.get(
            key,
            0,
        )

        if current_count >= MAX_SIMULTANEOUS_SIGNALS:

            logger.warning(
                "🚫 LIMITE SEGNALI SIMULTANEI | "
                "Messaggio #%s | "
                "Telegram=%s | "
                "Già autorizzati=%s/%s",
                source_message_id,
                key.strftime("%H:%M:%S"),
                current_count,
                MAX_SIMULTANEOUS_SIGNALS,
            )

            return False

        simultaneous_signal_counts[key] = (
            current_count + 1
        )

        logger.info(
            "🟢 SLOT TRADE AUTORIZZATO | "
            "Messaggio #%s | "
            "Telegram=%s | "
            "Slot=%s/%s",
            source_message_id,
            key.strftime("%H:%M:%S"),
            current_count + 1,
            MAX_SIMULTANEOUS_SIGNALS,
        )

        return True


def cleanup_old_timestamp_counters():
    """
    Pulisce i timestamp molto vecchi dal dizionario.
    Manteniamo comunque quelli recenti per evitare crescita
    infinita della memoria.
    """

    now = datetime.now(timezone.utc)

    old_keys = []

    for key in simultaneous_signal_counts:
        age = (
            now - key
        ).total_seconds()

        if age > 3600:
            old_keys.append(key)

    for key in old_keys:
        simultaneous_signal_counts.pop(
            key,
            None,
        )


# ============================================================
# PREZZO LIVE XAUUSD
# ============================================================

def get_live_xau_price(direction=None):
    """
    Restituisce il prezzo live di XAUUSD.
    BUY -> ASK, SELL -> BID.
    Senza direzione usa il mid-price.
    """
    if direction is None:
        # Se esiste una posizione del bot, usiamo il prezzo corrente
        # della posizione (quello coerente con il suo lato).
        positions = mt5.positions_get(symbol="XAUUSD-P") or []
        bot_positions = [
            p for p in positions
            if getattr(p, "magic", None) == int(MAGIC_NUMBER)
        ]
        if bot_positions:
            return float(getattr(bot_positions[-1], "price_current", 0.0) or 0.0)

    tick = mt5.symbol_info_tick("XAUUSD-P")
    if tick is None:
        return None

    if direction == "BUY":
        return float(tick.ask)
    if direction == "SELL":
        return float(tick.bid)

    bid = float(getattr(tick, "bid", 0.0) or 0.0)
    ask = float(getattr(tick, "ask", 0.0) or 0.0)
    if bid and ask:
        return (bid + ask) / 2.0
    return bid or ask or None


# ============================================================
# NUOVO MESSAGGIO DAL SOURCE
# ============================================================

@client.on(
    events.NewMessage(
        chats=SOURCE_CHAT
    )
)
async def new_message_handler(event):

    message = event.message
    source_message_id = message.id

    message_lock = get_message_lock(source_message_id)

    async with message_lock:

        received_datetime = datetime.now(timezone.utc)
        received_monotonic = time.monotonic()
        telegram_datetime = message.date

        # --------------------------------------------------------
        # RIEPILOGO DI CÉDRIC:
        # non deve nemmeno essere passato al parser operativo.
        # Il nostro riepilogo viene generato autonomamente alle 23:00 IT.
        # --------------------------------------------------------
        raw_text = message.text or ""
        if re.search(r"riepilogo\s+giornaliero", raw_text, re.IGNORECASE):
            logger.info(
                "⏭️ RIEPILOGO CÉDRIC IGNORATO ALL'ORIGINE | #%s",
                source_message_id,
            )
            return

        # --------------------------------------------------------
        # PARSER PRIMA DELLA COPIA:
        # copiamo SOLO i messaggi operativi riconosciuti.
        # Tutto il resto viene ignorato completamente.
        # --------------------------------------------------------
        signal = parse_signal(message.text)

        if signal is None:
            logger.info(
                "⏭️ MESSAGGIO #%s IGNORATO | Nessun formato operativo riconosciuto.",
                source_message_id,
            )
            return

        signal["message_id"] = source_message_id

        print_separator()
        logger.info("📩 NUOVO MESSAGGIO OPERATIVO #%s", source_message_id)
        logger.info("Testo: %s", message.text or "[VUOTO]")

        telegram_local = (
            telegram_datetime
            if telegram_datetime.tzinfo is not None
            else telegram_datetime.replace(tzinfo=timezone.utc)
        ).astimezone(ITALY_TZ)

        received_local = received_datetime.astimezone(ITALY_TZ)

        logger.info(
            "Source time : %s IT",
            telegram_local.strftime("%d/%m/%Y %H:%M:%S.%f")[:-3],
        )
        logger.info(
            "Bot time    : %s IT",
            received_local.strftime("%d/%m/%Y %H:%M:%S.%f")[:-3],
        )

        # --------------------------------------------------------
        # CONTROLLO DUPLICATO
        # --------------------------------------------------------
        try:
            existing_row = get_message(
                SOURCE_CHAT,
                source_message_id,
            )
        except Exception as e:
            logger.exception(
                "❌ ERRORE LETTURA DATABASE #%s: %s",
                source_message_id,
                e,
            )
            return

        if existing_row is not None:
            logger.info(
                "↩️ MESSAGGIO #%s GIÀ PRESENTE NEL DATABASE. Ignoro.",
                source_message_id,
            )
            return

        # --------------------------------------------------------
        # DATABASE - PRENOTAZIONE
        # --------------------------------------------------------
        try:
            inserted = insert_message(
                source_chat_id=SOURCE_CHAT,
                source_message_id=source_message_id,
                symbol=signal.get("symbol"),
                direction=signal.get("direction"),
                entry=signal.get("entry"),
                sl=signal.get("sl"),
                # Il DB storico usa il campo tp1; per ÉLITE memorizziamo
                # lì il TP operativo, cioè TP3.
                tp1=signal.get("tp3", signal.get("tp1")),
                status="COPYING",
                source_datetime=telegram_datetime.isoformat(),
                received_datetime=received_datetime.isoformat(),
            )
        except Exception as e:
            logger.exception(
                "❌ ERRORE INSERIMENTO DATABASE #%s: %s",
                source_message_id,
                e,
            )
            return

        if not inserted:
            logger.info(
                "↩️ MESSAGGIO #%s GIÀ INSERITO. Ignoro.",
                source_message_id,
            )
            return

        action = signal["action"]

        if action == "INFO_ONLY":
            logger.info("⏭️ MESSAGGIO INFORMATIVO IGNORATO | #%s", source_message_id)
            cleanup_old_timestamp_counters()
            return

        # --------------------------------------------------------
        # AGGIORNAMENTO PIPS (+50, +100 ecc mandati dal provider) -> IGNORATO
        # --------------------------------------------------------
        # Non viene copiato nel canale destinazione: il trailing/protezione
        # e' calcolato esclusivamente dal monitor MT5, questi messaggi sono
        # solo rumore informativo del provider.
        if action == "PIPS_UPDATE":
            update_status(
                SOURCE_CHAT,
                source_message_id,
                "PIPS_INFO_IGNORED",
                trade_datetime=datetime.now(timezone.utc).isoformat(),
            )
            logger.info(
                "⏭️ PIPS INFORMATIVO IGNORATO #%s | +%.2f",
                source_message_id,
                float(signal["pips"]),
            )
            cleanup_old_timestamp_counters()
            return

        # --------------------------------------------------------
        # CÉDRIC SCRIVE "STOP LOSS" NEL SUO CANALE -> IGNORATO
        # --------------------------------------------------------
        # Solo informativo lato Cédric: NON viene copiato nel canale
        # destinazione, per non duplicare il messaggio di chiusura reale
        # che il monitor manda (in risposta al segnale) quando MT5 conferma
        # la chiusura effettiva della posizione.
        if action == "SL_HIT":
            await process_sl_hit(signal, source_message_id)
            cleanup_old_timestamp_counters()
            return

        # --------------------------------------------------------
        # Per gli aggiornamenti informativi leggiamo il prezzo live
        # di MT5 prima di pubblicarli.
        # --------------------------------------------------------
        if action == "MODIFY_SL":
            signal["current_price"] = get_live_xau_price(
                signal.get("direction")
            )

        # --------------------------------------------------------
        # RIEPILOGO CÉDRIC: IGNORATO COMPLETAMENTE.
        # Il nostro report viene generato autonomamente alle 23:00 IT
        # usando le chiusure reali registrate da MT5.
        # --------------------------------------------------------
        if action == "DAILY_RECAP":
            logger.info(
                "⏭️ RIEPILOGO CÉDRIC IGNORATO | #%s | Report YARDFX alle 23:00 IT.",
                source_message_id,
            )
            cleanup_old_timestamp_counters()
            return

        # --------------------------------------------------------
        # MESSAGGIO DI CORREZIONE (SL/TP1 senza TP3) -> UPDATE_PARAMS
        # --------------------------------------------------------
        # NON viene copiato come messaggio nuovo nella destination: deve
        # solo modificare la copia del segnale originale già inviata (stessa
        # regola già usata per gli edit, vedi process_update_params). Per
        # questo il controllo sta PRIMA della copia qui sotto, come
        # INFO_ONLY/DAILY_RECAP.
        if action == "UPDATE_PARAMS":
            await process_update_params(signal, source_message_id)
            cleanup_old_timestamp_counters()
            return

        # --------------------------------------------------------
        # ANNUNCIO "SEGNALE IN ARRIVO" -> IGNORATO COMPLETAMENTE
        # --------------------------------------------------------
        # NON viene copiato nel canale destinazione e NON apre alcuna
        # posizione. Solo il segnale completo (SL + TP3), gestito sotto
        # come azione OPEN, viene copiato nel canale e apre su MT5.
        if action == "OPEN_SIGNAL":
            update_status(
                SOURCE_CHAT,
                source_message_id,
                "SIGNAL_ANNOUNCED",
            )
            logger.info(
                "⏭️ SEGNALE IN ARRIVO IGNORATO | #%s | %s %s | Entry indicativa=%.2f",
                source_message_id,
                signal["symbol"],
                signal["direction"],
                signal["entry"],
            )
            cleanup_old_timestamp_counters()
            return

        # --------------------------------------------------------
        # SEGNALE COMPLETO -> APERTURA IMMEDIATA
        # --------------------------------------------------------
        # La copia nel canale destinazione avviene SOLO dentro process_trade,
        # DOPO l'apertura reale su MT5, mostrando come ENTRY il prezzo di
        # esecuzione REALE (non quello dichiarato dal segnale). Se il trade
        # non apre per qualunque motivo, nel canale non compare nulla, e non
        # viene mai fatta alcuna modifica successiva al messaggio.
        if action == "OPEN":
            logger.info(
                "🎯 SEGNALE ÉLITE | %s %s | Entry %.2f | SL=%.2f | "
                "TP1 info=%.2f | TP2 info=%.2f | TAKE PROFIT=%.2f",
                signal["symbol"],
                signal["direction"],
                signal["entry"],
                signal["sl"],
                float(signal.get("tp1") or 0.0),
                float(signal.get("tp2") or 0.0),
                signal["tp3"],
            )

            if not TRADING_ENABLED:
                logger.warning("🚫 TRADE DISABILITATO DA CONFIG | #%s", source_message_id)
                update_status(SOURCE_CHAT, source_message_id, "TRADE_DISABLED")
                cleanup_old_timestamp_counters()
                return

            if not MT5_READY:
                logger.warning("🚫 MT5 NON PRONTO | #%s", source_message_id)
                update_status(SOURCE_CHAT, source_message_id, "MT5_NOT_READY")
                cleanup_old_timestamp_counters()
                return

            # --------------------------------------------------------
            # BLOCCO SEGNALI IN DIREZIONE OPPOSTA A UN TRADE GIA' APERTO
            # --------------------------------------------------------
            # Se c'e' gia' una posizione del bot aperta in direzione
            # OPPOSTA, il segnale non va ne' copiato nel canale ne' aperto
            # su MT5, finche' quella posizione non si chiude (in profitto o
            # in perdita). Segnali nella STESSA direzione restano ammessi e
            # possono aprirsi/essere copiati insieme.
            try:
                existing_positions = await asyncio.to_thread(
                    mt5.positions_get, symbol="XAUUSD-P"
                ) or []
            except Exception:
                existing_positions = []

            opposite_direction_open = any(
                (
                    "BUY" if int(getattr(p, "type", -1)) == mt5.POSITION_TYPE_BUY
                    else "SELL"
                ) != signal["direction"]
                for p in existing_positions
                if int(getattr(p, "magic", -1)) == int(MAGIC_NUMBER)
            )

            if opposite_direction_open:
                logger.warning(
                    "🚫 SEGNALE %s BLOCCATO | #%s | Trade opposto già aperto: "
                    "ignorato, non copiato nel canale, non aperto su MT5.",
                    signal["direction"],
                    source_message_id,
                )
                update_status(SOURCE_CHAT, source_message_id, "BLOCKED_OPPOSITE_DIRECTION")
                cleanup_old_timestamp_counters()
                return

            signal_age = calculate_signal_age_seconds(telegram_datetime)
            logger.info(
                "⏱ SIGNAL AGE #%s: %.3fs | Limite=%ss",
                source_message_id,
                signal_age,
                MAX_SIGNAL_AGE_SECONDS,
            )

            if signal_age > MAX_SIGNAL_AGE_SECONDS:
                logger.warning(
                    "🚫 SEGNALE TROPPO VECCHIO | #%s | Età %.3fs > %.3fs",
                    source_message_id,
                    signal_age,
                    MAX_SIGNAL_AGE_SECONDS,
                )
                update_status(SOURCE_CHAT, source_message_id, "SIGNAL_TOO_OLD")
                cleanup_old_timestamp_counters()
                return

            slot_available = await reserve_simultaneous_signal_slot(
                telegram_datetime,
                source_message_id,
            )

            if not slot_available:
                update_status(SOURCE_CHAT, source_message_id, "SIMULTANEOUS_LIMIT")
                cleanup_old_timestamp_counters()
                return

            update_status(SOURCE_CHAT, source_message_id, "OPENING_IMMEDIATE")

            task = asyncio.create_task(
                process_trade(
                    signal=signal,
                    message=message,
                    received_datetime=received_datetime,
                    received_monotonic=received_monotonic,
                    telegram_datetime=telegram_datetime,
                )
            )

            active_trade_tasks[source_message_id] = task

            logger.info(
                "🚀 Trade task #%s avviato | task attivi=%s",
                source_message_id,
                len(active_trade_tasks),
            )

            cleanup_old_timestamp_counters()
            return

        # --------------------------------------------------------
        # COPIA FORMATTA NELLA DESTINATION
        # --------------------------------------------------------
        destination_start = time.monotonic()

        try:
            destination_message = await copy_message_to_destination(
                message,
                signal=signal,
            )
        except Exception as e:
            logger.exception(
                "❌ ERRORE COPIA DESTINATION #%s: %s",
                source_message_id,
                e,
            )
            try:
                update_status(
                    SOURCE_CHAT,
                    source_message_id,
                    "COPY_ERROR",
                    error=str(e),
                )
            except Exception:
                logger.exception("❌ Impossibile aggiornare stato DB.")
            return

        destination_end = time.monotonic()
        destination_delay = destination_end - destination_start
        destination_datetime = datetime.now(timezone.utc)

        logger.info(
            "📤 Copiato in destination #%s | %.3fs",
            destination_message.id,
            destination_delay,
        )

        try:
            update_copy(
                SOURCE_CHAT,
                source_message_id,
                destination_message.id,
                destination_datetime.isoformat(),
            )
        except Exception as e:
            logger.exception(
                "❌ ERRORE SALVATAGGIO MAPPATURA #%s: %s",
                source_message_id,
                e,
            )
            return

        # --------------------------------------------------------
        # EVENTI INFORMATIVI
        # --------------------------------------------------------
        if action == "MODIFY_SL":
            await process_modify_sl(signal, source_message_id)
            cleanup_old_timestamp_counters()
            return

# ============================================================
# PROCESSAMENTO APERTURA TRADE
# ============================================================

async def process_trade(
    signal,
    message,
    received_datetime,
    received_monotonic,
    telegram_datetime,
):

    source_message_id = signal["message_id"]
    trade_start_monotonic = time.monotonic()

    try:
        print_separator()
        logger.info("📈 TRADE ENGINE #%s", source_message_id)
        print_separator()

        logger.info(
            "Apertura IMMEDIATA | Entry indicativa=%.2f | SL=%.2f | TAKE PROFIT=%.2f",
            signal["entry"],
            signal["sl"],
            signal["tp3"],
        )

        current_age = calculate_signal_age_seconds(telegram_datetime)

        if current_age > MAX_SIGNAL_AGE_SECONDS:
            logger.warning(
                "🚫 SEGNALE SCADUTO PRIMA DEL TRADE | #%s | Età %.3fs",
                source_message_id,
                current_age,
            )
            update_status(SOURCE_CHAT, source_message_id, "SIGNAL_TOO_OLD")
            return

        result = await asyncio.to_thread(
            open_market_order,
            signal,
            received_monotonic,
            telegram_datetime.timestamp(),
        )

        trade_end_datetime = datetime.now(timezone.utc)
        trade_end_monotonic = time.monotonic()

        if result is None:
            logger.warning("❌ TRADE NON APERTO #%s", source_message_id)
            update_status(
                SOURCE_CHAT,
                source_message_id,
                "EXPIRED_OR_ERROR",
            )
            return

        trade_processing_time = trade_end_monotonic - trade_start_monotonic

        # --------------------------------------------------------
        # COPIA NELLA DESTINATION *DOPO* L'APERTURA REALE SU MT5
        # --------------------------------------------------------
        # L'ENTRY mostrata è il prezzo di esecuzione REALE di MT5, non
        # quello dichiarato dal segnale Cédric. Scritta una sola volta, in
        # automatico: nessuna modifica successiva al messaggio.
        destination_signal = dict(signal)
        destination_signal["entry"] = result.price
        try:
            destination_message = await copy_message_to_destination(
                message,
                signal=destination_signal,
            )
            update_copy(
                SOURCE_CHAT,
                source_message_id,
                destination_message.id,
                datetime.now(timezone.utc).isoformat(),
            )
            logger.info(
                "📤 Copiato in destination #%s | Entry reale MT5=%.2f",
                destination_message.id,
                result.price,
            )
        except Exception:
            logger.exception(
                "❌ ERRORE COPIA DESTINATION (post-apertura) #%s",
                source_message_id,
            )

        telegram_aware = (
            telegram_datetime
            if telegram_datetime.tzinfo is not None
            else telegram_datetime.replace(tzinfo=timezone.utc)
        ).astimezone(timezone.utc)

        received_aware = (
            received_datetime
            if received_datetime.tzinfo is not None
            else received_datetime.replace(tzinfo=timezone.utc)
        )

        trade_end_aware = trade_end_datetime

        source_to_trade = (trade_end_aware - telegram_aware).total_seconds()
        bot_to_trade = (trade_end_aware - received_aware).total_seconds()

        print_separator()
        logger.info("📊 EXECUTION REPORT #%s", source_message_id)
        print_separator()

        logger.info(
            "Source message : %s IT",
            telegram_aware.astimezone(ITALY_TZ).strftime("%H:%M:%S.%f")[:-3],
        )
        logger.info(
            "Bot received   : %s IT",
            received_aware.astimezone(ITALY_TZ).strftime("%H:%M:%S.%f")[:-3],
        )
        logger.info(
            "Trade opened   : %s IT",
            trade_end_aware.astimezone(ITALY_TZ).strftime("%H:%M:%S.%f")[:-3],
        )

        logger.info("---------------- DELAY ----------------")
        logger.info(
            "Source → Bot       : %.3fs",
            (received_aware - telegram_aware).total_seconds(),
        )
        logger.info("Bot → Trade        : %.3fs", bot_to_trade)
        logger.info("Source → Trade     : %.3fs", source_to_trade)
        logger.info("Trade Engine       : %.3fs", trade_processing_time)
        logger.info("----------------------------------------")

        logger.info("---------------- TRADE ----------------")
        logger.info("Order Ticket: %s", result.order)
        logger.info("Position    : %s", result.position_ticket)
        logger.info("Deal        : %s", result.deal)
        logger.info("Volume      : %s", result.volume)
        logger.info("Open Price  : %.2f", result.price)
        logger.info("Signal Entry (dichiarata da Cédric): %.2f", signal["entry"])

        price_difference = result.price - signal["entry"]
        price_difference_percent = (
            price_difference / signal["entry"] * 100
        )

        logger.info("Price Diff  : %+.2f USD", price_difference)
        logger.info("Price Diff %%: %+.4f%%", price_difference_percent)
        logger.info("SL          : %.2f", signal["sl"])
        logger.info("TP1 INFO    : %.2f", float(signal.get("tp1") or 0.0))
        logger.info("TP2 INFO    : %.2f", float(signal.get("tp2") or 0.0))
        logger.info("TP3         : %.2f | OPERATIVO", signal["tp3"])
        logger.info("BE          : ATTIVATO A +100 PIPS")
        logger.info("LIVE TRAIL  : GESTITO DA PREZZO MT5")
        logger.info("----------------------------------------")
        print_separator()

        try:
            saved = update_status(
                SOURCE_CHAT,
                source_message_id,
                "OPENED",
                mt5_ticket=result.position_ticket,
                mt5_deal=result.deal,
                mt5_volume=result.volume,
                mt5_price=result.price,
                trade_datetime=trade_end_datetime.isoformat(),
            )
            if saved:
                logger.info("💾 DB TICKET SALVATO")
                logger.info("    📨 Source Message : #%s", source_message_id)
                logger.info("    🎫 Position Ticket: %s", result.position_ticket)
                logger.info("    📍 Entry MT5       : %.2f", result.price)
                logger.info("    📊 Status          : OPENED")
            else:
                logger.error("🚨 DB TICKET NON SALVATO | #%s | Ticket=%s", source_message_id, result.position_ticket)
        except Exception:
            logger.exception(
                "❌ Errore aggiornamento DB OPENED #%s",
                source_message_id,
            )

    except Exception as e:
        logger.exception(
            "❌ ERRORE TRADE ENGINE #%s: %s",
            source_message_id,
            e,
        )
        try:
            update_status(
                SOURCE_CHAT,
                source_message_id,
                "ERROR",
                error=str(e),
            )
        except Exception:
            logger.exception(
                "❌ Errore salvataggio ERROR #%s",
                source_message_id,
            )

    finally:
        active_trade_tasks.pop(source_message_id, None)


# ============================================================
# AGGIORNAMENTO PARAMETRI DOPO APERTURA
# ============================================================

async def process_update_params(signal, source_message_id):
    """
    Il secondo messaggio contiene SL/TP1.
    NON apre un nuovo trade: aggiorna esclusivamente l'ultima
    posizione XAUUSD aperta dal bot nella stessa direzione.
    """
    new_sl = float(signal["sl"])
    new_tp1 = float(signal["tp1"])
    direction = signal["direction"]

    logger.info(
        "🛠️ PARAMETRI RICEVUTI #%s | %s | SL=%.2f | TP1=%.2f | TP2 IGNORATO",
        source_message_id,
        direction,
        new_sl,
        new_tp1,
    )

    if not TRADING_ENABLED:
        update_status(SOURCE_CHAT, source_message_id, "TRADE_DISABLED")
        return

    if not MT5_READY:
        update_status(SOURCE_CHAT, source_message_id, "MT5_NOT_READY")
        return

    try:
        # Il secondo messaggio può arrivare pochi millisecondi dopo il primo.
        # In quel caso il trade MT5 può essere già aperto ma la riga OPENED
        # non essere ancora stata scritta nel DB. Attendere brevemente qui
        # serve solo ad associare i parametri alla posizione appena aperta;
        # NON è un retry sull'entry e NON ritarda l'apertura del trade.
        row = None
        entry = float(signal["entry"])
        for attempt in range(10):
            row = get_open_trade_for_signal(
                source_chat_id=SOURCE_CHAT,
                symbol="XAUUSD",
                direction=direction,
                entry=entry,
            )
            if row is not None:
                break
            if attempt < 9:
                await asyncio.sleep(0.10)

        if row is None:
            logger.warning(
                "⚠️ NESSUNA POSIZIONE %s ASSOCIATA A ENTRY %.2f | messaggio #%s",
                direction,
                entry,
                source_message_id,
            )
            update_status(
                SOURCE_CHAT,
                source_message_id,
                "NO_OPEN_TRADE",
            )
            return

        position_ticket = row[0]
        original_message_id = row[1]

        logger.info(
            "🎯 AGGIORNO POSIZIONE ESISTENTE | Position=%s | Segnale originale=#%s",
            position_ticket,
            original_message_id,
        )

        # --------------------------------------------------------
        # AGGIORNA IL MESSAGGIO GIÀ COPIATO NELLA DESTINATION
        # --------------------------------------------------------
        # Il secondo messaggio della source (UPDATE_PARAMS) non viene
        # copiato come nuovo messaggio. Deve modificare la copia del
        # primo messaggio, usando il destination_message_id del trade
        # originale.
        # get_open_trade_for_signal() restituisce destination_message_id
        # come ultimo campo per non rompere gli indici storici usati dal bot.
        destination_message_id = row[11]
        real_entry_price = row[10]

        if destination_message_id is not None:
            try:
                message_edit_start = time.monotonic()
                signal_for_edit = dict(signal)
                if real_entry_price:
                    signal_for_edit["entry"] = float(real_entry_price)
                edited = await edit_destination_message_with_signal(
                    destination_message_id,
                    signal_for_edit,
                )
                message_edit_delay = time.monotonic() - message_edit_start

                if edited:
                    logger.info(
                        "✏️ DESTINATION AGGIORNATA | #%s -> #%s | %.3fs",
                        original_message_id,
                        destination_message_id,
                        message_edit_delay,
                    )
                else:
                    logger.info(
                        "ℹ️ DESTINATION #%s già aggiornata.",
                        destination_message_id,
                    )
            except Exception as e:
                # Un errore Telegram NON deve impedire l'aggiornamento MT5.
                logger.exception(
                    "❌ ERRORE MODIFICA DESTINATION #%s: %s",
                    destination_message_id,
                    e,
                )
        else:
            logger.warning(
                "⚠️ NESSUN DESTINATION MESSAGE ID per il trade originale #%s",
                original_message_id,
            )

        result = await asyncio.to_thread(
            modify_position_sl_tp,
            position_ticket,
            new_sl,
            new_tp1,
        )

        # Salva nel DB solo i parametri effettivamente accettati/applicati.
        if result["sl_applied"] and result["tp_applied"]:
            update_trade_params(
                SOURCE_CHAT,
                original_message_id,
                result["sl"],
                result["tp"],
            )
            applied_status = "TP_SET"
        elif result["sl_applied"]:
            update_trade_sl(
                SOURCE_CHAT,
                original_message_id,
                result["sl"],
                status="OPENED",
            )
            applied_status = "SL_SET_TP_INVALID"
        elif result["tp_applied"]:
            # Manteniamo lo SL già presente nel DB quando il nuovo SL è invalido.
            row_after = get_open_trade_for_signal(
                SOURCE_CHAT, "XAUUSD", direction, entry
            )
            existing_db_sl = row_after[5] if row_after else None
            if existing_db_sl is not None:
                update_trade_params(
                    SOURCE_CHAT,
                    original_message_id,
                    existing_db_sl,
                    result["tp"],
                )
            applied_status = "TP_SET_SL_INVALID"
        else:
            raise RuntimeError("Nessun parametro applicato.")

        update_status(
            SOURCE_CHAT,
            source_message_id,
            "PARAMS_APPLIED",
            trade_datetime=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            "✅ PARAMETRI APPLICATI | Position=%s | SL=%s | TP1=%s | SL_OK=%s | TP_OK=%s | Nessuna nuova posizione",
            result["position_ticket"],
            f'{result["sl"]:.2f}',
            f'{result["tp"]:.2f}',
            result["sl_applied"],
            result["tp_applied"],
        )

        if result["sl_error"]:
            logger.warning("⚠️ SL RICHIESTO NON APPLICATO: %s", result["sl_error"])
        if result["tp_error"]:
            logger.warning("⚠️ TP1 RICHIESTO NON APPLICATO: %s", result["tp_error"])

    except Exception as e:
        logger.exception(
            "❌ ERRORE AGGIORNAMENTO PARAMETRI #%s: %s",
            source_message_id,
            e,
        )
        update_status(
            SOURCE_CHAT,
            source_message_id,
            "PARAMS_ERROR",
            error=str(e),
        )


# ============================================================
# MODIFICA STOP LOSS
# ============================================================

async def process_modify_sl(signal, source_message_id):
    new_sl = float(signal["sl"])

    logger.info(
        "🔄 RICHIESTA MODIFICA SL #%s | Nuovo SL=%.2f",
        source_message_id,
        new_sl,
    )

    if not TRADING_ENABLED:
        update_status(SOURCE_CHAT, source_message_id, "TRADE_DISABLED")
        return

    if not MT5_READY:
        update_status(SOURCE_CHAT, source_message_id, "MT5_NOT_READY")
        return

    try:
        row = get_latest_open_trade(
            source_chat_id=SOURCE_CHAT,
            symbol="XAUUSD",
        )

        if row is None:
            logger.warning("⚠️ Nessuna operazione aperta da modificare.")
            update_status(SOURCE_CHAT, source_message_id, "NO_OPEN_TRADE")
            return

        position_ticket = row[0]
        original_message_id = row[1]

        await asyncio.to_thread(
            modify_position_sl,
            position_ticket,
            new_sl,
        )

        update_trade_sl(
            SOURCE_CHAT,
            original_message_id,
            new_sl,
            status="OPENED",
        )
        update_status(
            SOURCE_CHAT,
            source_message_id,
            "SL_MODIFIED",
            trade_datetime=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            "✅ SL MODIFICATO | Position=%s | Nuovo SL=%.2f | Segnale originale=#%s",
            position_ticket,
            new_sl,
            original_message_id,
        )

    except Exception as e:
        logger.exception("❌ ERRORE MODIFICA SL #%s: %s", source_message_id, e)
        update_status(
            SOURCE_CHAT,
            source_message_id,
            "SL_MODIFY_ERROR",
            error=str(e),
        )


# ============================================================
# STOP LOSS PRESO
# ============================================================

async def process_sl_hit(signal, source_message_id):
    """
    Registra il messaggio STOP LOSS senza marcare prematuramente il trade
    originale come chiuso. La chiusura reale viene confermata dal monitor
    leggendo lo storico MT5.
    """
    logger.info("🛑 STOP LOSS SEGNALATO DA TELEGRAM #%s", source_message_id)

    try:
        update_status(
            SOURCE_CHAT,
            source_message_id,
            "SL_HIT_SIGNAL",
            trade_datetime=datetime.now(timezone.utc).isoformat(),
        )
        logger.info(
            "🛑 Messaggio STOP LOSS registrato #%s | La chiusura viene confermata da MT5.",
            source_message_id,
        )
    except Exception as e:
        logger.exception("❌ ERRORE REGISTRAZIONE SL #%s: %s", source_message_id, e)
        update_status(
            SOURCE_CHAT,
            source_message_id,
            "SL_HIT_ERROR",
            error=str(e),
        )


# ============================================================
# RIEPILOGO GIORNALIERO YARDFX
# ============================================================

def _calculate_position_profit_pips(position):
    """Calcola il profitto live in PIPS di una posizione XAUUSD."""
    info = mt5.symbol_info("XAUUSD-P")
    if info is None:
        return 0.0

    pip_size = float(info.point) * 10.0
    if pip_size <= 0:
        return 0.0

    open_price = float(getattr(position, "price_open", 0.0) or 0.0)
    current_price = float(getattr(position, "price_current", 0.0) or 0.0)
    position_type = int(getattr(position, "type", -1))

    if open_price <= 0 or current_price <= 0:
        return 0.0

    if position_type == mt5.POSITION_TYPE_BUY:
        return (current_price - open_price) / pip_size

    if position_type == mt5.POSITION_TYPE_SELL:
        return (open_price - current_price) / pip_size

    return 0.0


# Tabella di protezione SL live (vedi banner di avvio "GESTIONE SL LIVE").
# Ogni voce e' (trigger_pips, protected_pips): al raggiungimento di
# trigger_pips di profitto, lo SL viene spostato a protected_pips.
LIVE_PROTECTION_LEVELS = (
    (100.0, 20.0),
    (125.0, 50.0),
    (150.0, 80.0),
    (175.0, 110.0),
    (200.0, 128.0),
    (225.0, 157.0),
    (250.0, 186.0),
    (275.0, 215.0),
    (300.0, 244.0),
    (325.0, 273.0),
    (350.0, 302.0),
    (375.0, 331.0),
    (400.0, 360.0),
)

# Oltre i 400 pips di profitto il trade resta aperto e passa a un
# trailing dinamico: lo SL protegge sempre il 15% sotto il profitto corrente,
# cioe' l'85% del profitto viene bloccato.
LIVE_TRAILING_ABOVE_PIPS = 400.0
LIVE_TRAILING_LOCK_PCT = 0.85


def _live_protection_step(profit_pips):
    """
    Determina il livello di protezione SL da applicare in base al profitto
    live (in PIPS) della posizione, seguendo la tabella:
        +100  -> SL +20 (BE)
        +125  -> SL +50
        +150  -> SL +80
        +175  -> SL +110
        +200  -> SL +128
        +225  -> SL +157
        +250  -> SL +186
        +275  -> SL +215
        +300  -> SL +244
        +325  -> SL +273
        +350  -> SL +302
        +375  -> SL +331
        +400  -> SL +360 (trade resta aperto)
        >400  -> trailing dinamico: protezione = 85% del profitto corrente

    Ritorna una tupla (trigger_pips, protected_pips, protection_mode),
    oppure None se il profitto non ha ancora raggiunto la prima soglia
    (+50 pips). Lo SL non arretra mai: e' compito del chiamante non
    peggiorare mai la protezione gia' applicata.
    """
    if profit_pips is None:
        return None

    try:
        profit_pips = float(profit_pips)
    except (TypeError, ValueError):
        return None

    if profit_pips > LIVE_TRAILING_ABOVE_PIPS:
        protected_pips = profit_pips * LIVE_TRAILING_LOCK_PCT
        return profit_pips, protected_pips, "TRAILING_15PCT"

    selected = None
    for trigger_pips, protected_pips in LIVE_PROTECTION_LEVELS:
        if profit_pips >= trigger_pips:
            selected = (trigger_pips, protected_pips, "FIXED")

    return selected


def _calculate_closed_trade_pips(open_price, close_price, direction):
    """Calcola i PIPS reali XAUUSD usando lo stesso pip_size del monitor MT5."""
    info = mt5.symbol_info("XAUUSD-P")
    if info is None:
        return 0.0

    pip_size = float(info.point) * 10.0
    if pip_size <= 0:
        return 0.0

    open_price = float(open_price)
    close_price = float(close_price)

    if str(direction).upper() == "BUY":
        return (close_price - open_price) / pip_size

    return (open_price - close_price) / pip_size


def _format_report_pips(value):
    value = float(value)
    if abs(value) < 0.005:
        value = 0.0
    if value.is_integer():
        return f"{int(value):+d} PIPS"
    return f"{value:+.2f} PIPS"


_ITALIAN_MONTH_ABBR = {
    1: "GEN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAG", 6: "GIU",
    7: "LUG", 8: "AGO", 9: "SET", 10: "OTT", 11: "NOV", 12: "DIC",
}


def _format_date_range_it(start_date, end_date):
    """Es. '14 SET - 18 SET' oppure '1 SET - 30 SET'."""
    def fmt(d):
        return f"{d.day} {_ITALIAN_MONTH_ABBR[d.month]}"
    return f"{fmt(start_date)} - {fmt(end_date)}"


def _build_daily_report(report_date):
    rows = get_daily_trade_results(report_date, SOURCE_CHAT)

    operations = len(rows)
    wins = sum(1 for row in rows if float(row[6]) > 1.0)
    losses = sum(1 for row in rows if float(row[6]) < -1.0)
    breakeven = operations - wins - losses

    result_pips = sum(float(row[6]) for row in rows)
    win_rate = (wins / operations * 100.0) if operations else 0.0

    be_activated = sum(1 for row in rows if bool(row[9]))
    profit_sl = sum(1 for row in rows if bool(row[10]))
    tp3_reached = sum(1 for row in rows if bool(row[11]))

    return {
        "operations": operations,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "win_rate": win_rate,
        "result_pips": _format_report_pips(result_pips),
        "be_activated": be_activated,
        "profit_sl": profit_sl,
        "tp3_reached": tp3_reached,
    }


def _build_weekly_report(week_start, week_end):
    rows = get_weekly_trade_results(week_start, week_end, SOURCE_CHAT)

    operations = len(rows)
    wins = sum(1 for row in rows if float(row[6]) > 1.0)
    losses = sum(1 for row in rows if float(row[6]) < -1.0)
    breakeven = operations - wins - losses
    result_pips = sum(float(row[6]) for row in rows)
    win_rate = (wins / operations * 100.0) if operations else 0.0

    return {
        "operations": operations,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "win_rate": win_rate,
        "result_pips": _format_report_pips(result_pips).replace(" PIPS", " PIPS"),
    }


def _build_monthly_report(month_start, month_end_exclusive):
    """month_end_exclusive e' il primo giorno del mese successivo (limite escluso)."""
    rows = get_monthly_trade_results(month_start, month_end_exclusive, SOURCE_CHAT)

    operations = len(rows)
    wins = sum(1 for row in rows if float(row[6]) > 1.0)
    losses = sum(1 for row in rows if float(row[6]) < -1.0)
    result_pips = sum(float(row[6]) for row in rows)
    win_rate = (wins / operations * 100.0) if operations else 0.0

    return {
        "operations": operations,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "pips": result_pips,
    }


async def weekly_report_scheduler(stop_event):
    """Invia il report settimanale ogni sabato alle 10:00 Europe/Rome."""
    while not stop_event.is_set():
        try:
            now_local = datetime.now(ITALY_TZ)
            target = now_local.replace(hour=10, minute=0, second=0, microsecond=0)
            if target <= now_local:
                days_until_saturday = (5 - now_local.weekday()) % 7 or 7
                target = (now_local + timedelta(days=days_until_saturday)).replace(
                    hour=10, minute=0, second=0, microsecond=0
                )
            elif target.weekday() != 5:
                days_until_saturday = (5 - target.weekday()) % 7
                target += timedelta(days=days_until_saturday)

            wait_seconds = max(0.0, (target - now_local).total_seconds())
            logger.info(
                "📊 WEEKLY REPORT SCHEDULER | Prossimo report: %s IT",
                target.strftime("%d/%m/%Y %H:%M:%S"),
            )

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
                continue
            except asyncio.TimeoutError:
                pass

            # Guardia anti doppio invio: su attese molto lunghe asyncio puo'
            # risvegliarsi qualche centinaio di ms prima del timeout, con
            # l'evento target ancora "nel futuro" - se procedessimo subito
            # verrebbe reimpostato un nuovo timeout brevissimo, causando un
            # secondo invio mezzo secondo dopo. Aspettiamo l'eventuale
            # residuo prima di considerare l'orario davvero raggiunto.
            residual = (target - datetime.now(ITALY_TZ)).total_seconds()
            if residual > 0:
                await asyncio.sleep(residual)

            saturday = datetime.now(ITALY_TZ).date()
            week_end = saturday
            week_start = saturday - timedelta(days=5)  # lunedi della settimana corrente
            report_week = week_start.isoformat()

            if await asyncio.to_thread(has_weekly_report, report_week):
                logger.info("📊 WEEKLY REPORT %s già inviato. Nessun duplicato.", report_week)
                continue

            stats = await asyncio.to_thread(_build_weekly_report, week_start, week_end)
            # week_end e' il limite ESCLUSO (sabato); il range mostrato va
            # da lunedi a venerdi, l'ultimo giorno incluso nei dati.
            date_range = _format_date_range_it(week_start, week_end - timedelta(days=1))
            try:
                sent = await send_weekly_report_message(date_range=date_range, **stats)
                await asyncio.to_thread(mark_weekly_report_sent, report_week)
                logger.info(
                    "📊 YARDFX WEEKLY REPORT INVIATO | Week=%s | Destination=%s | Message=%s | Operazioni=%s | PIPS=%s",
                    report_week, DESTINATION_CHAT, sent.id, stats["operations"], stats["result_pips"]
                )
            except Exception:
                logger.exception("❌ ERRORE INVIO YARDFX WEEKLY REPORT | Week=%s", report_week)

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE WEEKLY REPORT SCHEDULER")
            await asyncio.sleep(5)


async def morning_message_scheduler(stop_event):
    """Invia il messaggio di buongiorno lunedi-venerdi alle 06:00 Europe/Rome."""
    while not stop_event.is_set():
        try:
            now_local = datetime.now(ITALY_TZ)
            target = now_local.replace(hour=6, minute=0, second=0, microsecond=0)
            if target <= now_local:
                target += timedelta(days=1)
            while target.weekday() >= 5:
                target += timedelta(days=1)

            wait_seconds = max(0.0, (target - now_local).total_seconds())
            logger.info("☀️ MORNING MESSAGE SCHEDULER | Prossimo: %s IT", target.strftime("%d/%m/%Y %H:%M:%S"))
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
                continue
            except asyncio.TimeoutError:
                pass

            # Guardia anti doppio invio (vedi weekly_report_scheduler).
            residual = (target - datetime.now(ITALY_TZ)).total_seconds()
            if residual > 0:
                await asyncio.sleep(residual)

            try:
                sent = await send_good_morning_message()
                logger.info("☀️ BUONGIORNO INVIATO | Destination #%s", sent.id)
            except Exception:
                logger.exception("❌ ERRORE INVIO BUONGIORNO")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE MORNING MESSAGE SCHEDULER")
            await asyncio.sleep(5)


async def daily_close_scheduler(stop_event):
    """
    Chiude a mercato tutte le posizioni del bot alle 22:59 Europe/Rome.

    NOTA ORARI: il mercato reale (conto live) chiude alle 23:00; chiudiamo
    un minuto prima (22:59) per essere sicuri di trovarlo ancora aperto,
    invece di rischiare un rifiuto "Market closed" a ridosso della
    chiusura. Il conto demo attuale a volte ha una pausa a orari leggermente
    diversi: da qui il retry qui sotto. Il report giornaliero (vedi
    daily_report_scheduler) parte separatamente alle 23:00, quando il
    mercato reale e' gia' chiuso.
    """
    while not stop_event.is_set():
        try:
            now_local = datetime.now(ITALY_TZ)
            target = now_local.replace(hour=22, minute=59, second=0, microsecond=0)
            if target <= now_local:
                target += timedelta(days=1)

            wait_seconds = max(0.0, (target - now_local).total_seconds())
            logger.info("🌙 DAILY CLOSE SCHEDULER | Prossima chiusura: %s IT", target.strftime("%d/%m/%Y %H:%M:%S"))
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
                continue
            except asyncio.TimeoutError:
                pass

            # Guardia anti doppio invio (vedi weekly_report_scheduler).
            residual = (target - datetime.now(ITALY_TZ)).total_seconds()
            if residual > 0:
                await asyncio.sleep(residual)

            if MT5_READY and TRADING_ENABLED:
                positions = await asyncio.to_thread(mt5.positions_get, symbol="XAUUSD-P") or []
                bot_positions = [
                    position for position in positions
                    if int(getattr(position, "magic", -1)) == int(MAGIC_NUMBER)
                ]

                if not bot_positions:
                    logger.info("🌙 22:59 | Nessun trade XAUUSD del bot aperto. Nessun messaggio di chiusura inviato.")
                else:
                    closed_prices = []
                    for position in bot_positions:
                        ticket = int(position.ticket)
                        # Alcuni broker (spesso i demo) hanno una breve pausa di
                        # mercato proprio intorno a quest'orario per il rollover
                        # giornaliero (retcode 10018 "Market closed"): è
                        # transitorio, quindi ritentiamo alcune volte prima di
                        # rinunciare, invece di lasciare la posizione aperta
                        # tutta la notte per un rifiuto che dura pochi minuti.
                        max_attempts = 6
                        retry_delay_seconds = 20
                        for attempt in range(1, max_attempts + 1):
                            try:
                                result = await asyncio.to_thread(close_position, ticket)
                                closed_prices.append(float(result.price))
                                logger.info(
                                    "🌙 CHIUSURA GIORNALIERA | Position=%s | Prezzo=%.2f | 22:59 IT",
                                    ticket, float(result.price),
                                )
                                break
                            except Exception as e:
                                market_closed = "10018" in str(e)
                                if market_closed and attempt < max_attempts:
                                    logger.warning(
                                        "⚠️ MERCATO CHIUSO (10018) | Position=%s | Tentativo %s/%s | "
                                        "Riprovo tra %ss",
                                        ticket, attempt, max_attempts, retry_delay_seconds,
                                    )
                                    await asyncio.sleep(retry_delay_seconds)
                                    continue
                                logger.exception("❌ ERRORE CHIUSURA 22:59 | Position=%s", ticket)
                                break

                    # Un solo avviso giornaliero, solo se esistevano posizioni da chiudere.
                    if closed_prices:
                        try:
                            await send_forced_daily_close_message()
                        except Exception:
                            logger.exception("❌ ERRORE MESSAGGIO CHIUSURA GIORNALIERA")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE DAILY CLOSE SCHEDULER")
            await asyncio.sleep(5)


async def daily_report_scheduler(stop_event):
    """
    Invia il report giornaliero YARDFX alle 23:00 Europe/Rome, lun-ven.

    Orario separato da daily_close_scheduler (22:59) apposta: sul conto
    reale il mercato chiude alle 23:00, quindi il report parte un minuto
    DOPO la chiusura forzata, quando il mercato è già chiuso e la
    posizione (se c'era) risulta già chiusa.
    """
    while not stop_event.is_set():
        try:
            now_local = datetime.now(ITALY_TZ)
            target = now_local.replace(hour=23, minute=0, second=0, microsecond=0)
            if target <= now_local:
                target += timedelta(days=1)
            while target.weekday() >= 5:
                target += timedelta(days=1)

            wait_seconds = max(0.0, (target - now_local).total_seconds())
            logger.info("📊 DAILY REPORT SCHEDULER | Prossimo report: %s IT", target.strftime("%d/%m/%Y %H:%M:%S"))
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
                continue
            except asyncio.TimeoutError:
                pass

            # Guardia anti doppio invio (vedi weekly_report_scheduler).
            residual = (target - datetime.now(ITALY_TZ)).total_seconds()
            if residual > 0:
                await asyncio.sleep(residual)

            await send_daily_report_now()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE DAILY REPORT SCHEDULER")
            await asyncio.sleep(5)


async def monthly_report_scheduler(stop_event):
    """
    Invia il report mensile YARDFX alle 23:59 Europe/Rome, l'ultimo
    giorno del mese (qualunque giorno della settimana sia).
    """
    while not stop_event.is_set():
        try:
            now_local = datetime.now(ITALY_TZ)
            last_day = calendar.monthrange(now_local.year, now_local.month)[1]
            target = now_local.replace(day=last_day, hour=23, minute=59, second=0, microsecond=0)
            if target <= now_local:
                next_year = now_local.year + 1 if now_local.month == 12 else now_local.year
                next_month = 1 if now_local.month == 12 else now_local.month + 1
                next_last_day = calendar.monthrange(next_year, next_month)[1]
                target = now_local.replace(
                    year=next_year, month=next_month, day=next_last_day,
                    hour=23, minute=59, second=0, microsecond=0,
                )

            wait_seconds = max(0.0, (target - now_local).total_seconds())
            logger.info(
                "📊 MONTHLY REPORT SCHEDULER | Prossimo report: %s IT",
                target.strftime("%d/%m/%Y %H:%M:%S"),
            )
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=wait_seconds)
                continue
            except asyncio.TimeoutError:
                pass

            # Guardia anti doppio invio (vedi weekly_report_scheduler).
            residual = (target - datetime.now(ITALY_TZ)).total_seconds()
            if residual > 0:
                await asyncio.sleep(residual)

            month_start = date(target.year, target.month, 1)
            if target.month == 12:
                month_end_exclusive = date(target.year + 1, 1, 1)
            else:
                month_end_exclusive = date(target.year, target.month + 1, 1)
            report_month = month_start.isoformat()

            if await asyncio.to_thread(has_monthly_report, report_month):
                logger.info("📊 MONTHLY REPORT %s già inviato. Nessun duplicato.", report_month)
                continue

            stats = await asyncio.to_thread(_build_monthly_report, month_start, month_end_exclusive)
            date_range = _format_date_range_it(month_start, month_end_exclusive - timedelta(days=1))
            try:
                sent = await send_monthly_report_message(date_range=date_range, **stats)
                await asyncio.to_thread(mark_monthly_report_sent, report_month)
                logger.info(
                    "📊 YARDFX MONTHLY REPORT INVIATO | Month=%s | Destination=%s | Message=%s | Operazioni=%s | PIPS=%s",
                    report_month, DESTINATION_CHAT, sent.id, stats["operations"], stats["pips"],
                )
            except Exception:
                logger.exception("❌ ERRORE INVIO YARDFX MONTHLY REPORT | Month=%s", report_month)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE MONTHLY REPORT SCHEDULER")
            await asyncio.sleep(5)


async def send_daily_report_now():
    """
    Costruisce e invia il report giornaliero YARDFX, se non gia' inviato
    oggi. Chiamata da daily_report_scheduler alle 23:00. Salta il weekend,
    il report considera esclusivamente le chiusure reali registrate da
    MT5: il report di Cédric viene sempre ignorato.
    """
    now_local = datetime.now(ITALY_TZ)
    if now_local.weekday() >= 5:
        return

    report_date = now_local.date()

    if await asyncio.to_thread(has_daily_report, report_date):
        logger.info(
            "📊 DAILY REPORT %s già inviato. Nessun duplicato.",
            report_date,
        )
        return

    stats = await asyncio.to_thread(
        _build_daily_report,
        report_date,
    )

    try:
        sent = await send_daily_report_message(
            report_date=report_date.strftime("%d/%m/%Y"),
            **stats,
        )

        await asyncio.to_thread(
            mark_daily_report_sent,
            report_date,
        )

        logger.info(
            "📊 YARDFX ELITE REPORT INVIATO | Date=%s | "
            "Destination=%s | Message=%s | Operazioni=%s | PIPS=%s",
            report_date,
            DESTINATION_CHAT,
            sent.id,
            stats["operations"],
            stats["result_pips"],
        )
    except Exception:
        logger.exception(
            "❌ ERRORE INVIO YARDFX ELITE REPORT | Date=%s",
            report_date,
        )


# ============================================================
# MONITOR CHIUSURE BROKER-SIDE DEL TRAILING SL
# ============================================================

async def recover_open_positions_after_startup():
    """Recovery sicuro e verificabile delle posizioni XAUUSD del BOT.

    MT5 e' la fonte primaria. Il recovery NON apre, chiude o modifica ordini.
    Una posizione viene associata al DB solo tramite ticket esatto oppure,
    in assenza del ticket, quando esiste una sola candidata compatibile.
    """
    global recovered_trade_rows, recovered_trade_sources

    recovered_trade_rows = []
    recovered_trade_sources = {}

    if not MT5_READY or not TRADING_ENABLED:
        logger.info("🔄 RECOVERY AVVIO | Saltato: MT5 non pronto o trading disabilitato.")
        return

    try:
        positions = await asyncio.to_thread(mt5.positions_get, symbol="XAUUSD-P")
    except Exception as e:
        logger.exception("❌ RECOVERY AVVIO | Errore lettura posizioni MT5: %s", e)
        return

    positions = positions or []
    bot_positions = [
        p for p in positions
        if int(getattr(p, "magic", -1) or -1) == int(MAGIC_NUMBER)
    ]

    logger.info("=" * 72)
    logger.info("🔄 RECOVERY AVVIO")
    logger.info("    📊 Posizioni XAUUSD MT5   : %s", len(positions))
    logger.info("    🤖 Posizioni BOT (Magic)  : %s", len(bot_positions))
    logger.info("    🔢 Magic                  : %s", MAGIC_NUMBER)
    logger.info("=" * 72)

    if not bot_positions:
        logger.info("🔄 RECOVERY COMPLETATO")
        logger.info("    📊 Posizioni BOT trovate : 0")
        logger.info("    🔗 Recuperate             : 0")
        logger.info("    🔧 Associate ora         : 0")
        logger.info("    ⚠️ Non associate          : 0")
        logger.info("    🛡️ Modifiche SL/TP        : 0")
        logger.info("    📌 Ordini eseguiti        : 0")
        logger.info("=" * 72)
        return

    matched = 0
    associated_now = 0
    orphaned = 0

    for position in bot_positions:
        ticket = int(getattr(position, "ticket", 0) or 0)
        if ticket <= 0:
            continue

        direction = (
            "BUY" if int(getattr(position, "type", -1)) == mt5.POSITION_TYPE_BUY
            else "SELL"
        )
        entry = float(getattr(position, "price_open", 0.0) or 0.0)
        current = float(getattr(position, "price_current", 0.0) or 0.0)
        sl = float(getattr(position, "sl", 0.0) or 0.0)
        pips = _calculate_position_profit_pips(position)

        row = await asyncio.to_thread(
            get_open_trade_by_ticket_any_source,
            ticket,
            "XAUUSD",
        )

        if row is None:
            # Fallback sicuro: cerca una sola riga DB senza ticket nella stessa
            # direzione. Non viene mai associata se le candidate sono multiple.
            candidates = await asyncio.to_thread(
                get_recovery_candidates,
                direction,
                "XAUUSD",
                20,
            )

            if len(candidates) == 1:
                candidate = candidates[0]
                candidate_source = int(candidate[0])
                candidate_message = int(candidate[1])
                ok = await asyncio.to_thread(
                    associate_position_ticket,
                    candidate_source,
                    candidate_message,
                    ticket,
                    mt5_volume=getattr(position, "volume", None),
                    mt5_price=entry,
                    trade_datetime=datetime.now(timezone.utc).isoformat(),
                )
                if ok:
                    row = await asyncio.to_thread(
                        get_open_trade_by_ticket_any_source,
                        ticket,
                        "XAUUSD",
                    )
                    if row is not None:
                        associated_now += 1
                        logger.info("🔗 RECOVERY ASSOCIAZIONE RIUSCITA")
                        logger.info("    🎫 Ticket       : %s", ticket)
                        logger.info("    📡 DB Source    : %s", candidate_source)
                        logger.info("    📨 Messaggio    : #%s", candidate_message)
                        logger.info("    🔧 Metodo       : CANDIDATA UNICA")
            elif len(candidates) > 1:
                logger.warning("⚠️ RECOVERY AMBIGUA")
                logger.warning("    🎫 Ticket       : %s", ticket)
                logger.warning("    💱 Symbol       : XAUUSD")
                logger.warning("    📊 Direzione    : %s", direction)
                logger.warning("    🔢 Candidate DB : %s", len(candidates))
                logger.warning("    🛑 Azione       : NESSUNA MODIFICA")
            else:
                # ZERO candidate: nessuna riga DB esiste affatto per questa
                # posizione (es. crash tra apertura ordine MT5 e scrittura
                # del ticket nel DB). A differenza del caso ambiguo, qui non
                # c'è alcun rischio di associare al trade sbagliato: creiamo
                # una riga sintetica così il monitor SL live può gestire da
                # subito la posizione. Lo SL salvato è quello ATTUALMENTE
                # impostato su MT5, quindi un eventuale trailing/SL già
                # applicato manualmente viene preservato, non peggiorato.
                adopted_message_id = await asyncio.to_thread(
                    adopt_orphan_position,
                    SOURCE_CHAT,
                    "XAUUSD",
                    direction,
                    entry,
                    sl,
                    ticket,
                    mt5_volume=getattr(position, "volume", None),
                    mt5_price=entry,
                    trade_datetime=datetime.now(timezone.utc).isoformat(),
                )
                if adopted_message_id is not None:
                    row = await asyncio.to_thread(
                        get_open_trade_by_ticket_any_source,
                        ticket,
                        "XAUUSD",
                    )
                    if row is not None:
                        associated_now += 1
                        logger.warning("🩹 RECOVERY RIGA RICOSTRUITA (nessuna riga DB trovata)")
                        logger.warning("    🎫 Ticket             : %s", ticket)
                        logger.warning("    📊 Direzione          : %s", direction)
                        logger.warning("    📍 Entry MT5          : %.2f", entry)
                        logger.warning("    🛑 SL preso da MT5    : %.2f (trailing/SL manuale preservato)", sl)
                        logger.warning("    📨 Messaggio sintetico: #%s", adopted_message_id)

        if row is None:
            orphaned += 1
            logger.warning("⚠️ RECOVERY MT5 NON ASSOCIATO")
            logger.warning("    🎫 Ticket       : %s", ticket)
            logger.warning("    💱 Symbol       : XAUUSD")
            logger.warning("    📊 Direzione    : %s", direction)
            logger.warning("    📍 Entry MT5    : %.2f", entry)
            logger.warning("    💰 Prezzo LIVE  : %.2f", current)
            logger.warning("    📈 PIPS         : %+.2f", pips)
            logger.warning("    🔢 Magic        : %s", MAGIC_NUMBER)
            logger.warning("    🛑 Azione       : NESSUNA MODIFICA")
            continue

        source_chat_id = int(row[-1])
        clean_row = tuple(row[:12])
        recovered_trade_rows.append(clean_row)
        recovered_trade_sources[ticket] = source_chat_id
        matched += 1

        logger.info("🔄 POSIZIONE RECUPERATA")
        logger.info("    🎫 Ticket       : %s", ticket)
        logger.info("    💱 Symbol       : XAUUSD")
        logger.info("    📊 Direzione    : %s", direction)
        logger.info("    📍 Entry MT5    : %.2f", entry)
        logger.info("    💰 Prezzo LIVE  : %.2f", current)
        logger.info("    📈 PIPS         : %+.2f", pips)
        logger.info("    🛑 Stop Loss    : %.2f", sl)
        logger.info("    📡 DB Source    : %s", source_chat_id)
        logger.info("    🛡️ Trailing     : LIVE ATTIVO")

    logger.info("=" * 72)
    logger.info("🔄 RECOVERY COMPLETATO")
    logger.info("    📊 Posizioni BOT trovate : %s", len(bot_positions))
    logger.info("    🔗 Recuperate             : %s", matched)
    logger.info("    🔧 Associate ora          : %s", associated_now)
    logger.info("    ⚠️ Non associate          : %s", orphaned)
    logger.info("    🛡️ Modifiche SL/TP        : 0")
    logger.info("    📌 Ordini eseguiti        : 0")
    logger.info("=" * 72)


async def monitor_trailing_sl_closures(stop_event):
    """
    Gestione autonoma dello SL basata sul prezzo LIVE di MT5.

    Il prezzo live di MT5 governa tutta la gestione dello SL.
    A +50 PIPS scatta la prima protezione (+10 PIPS).
    Quando il livello TAKE PROFIT (TP3 del segnale) viene raggiunto,
    l'operazione NON viene chiusa: viene notificato il raggiungimento e
    si attiva il trailing dinamico al 15% di ritracciamento.
    """
    logger.info("🛡️ MONITOR LIVE SL ATTIVO | Controllo ogni 0.5s")

    while not stop_event.is_set():
        try:
            if MT5_READY and TRADING_ENABLED:
                rows = await asyncio.to_thread(
                    get_open_trades,
                    SOURCE_CHAT,
                    "XAUUSD",
                )

                # Aggiunge eventuali posizioni recuperate da MT5 associate
                # a un record DB con source_chat_id differente.
                seen_tickets = {int(row[0]) for row in rows if row[0] is not None}
                for recovered_row in recovered_trade_rows:
                    if int(recovered_row[0]) not in seen_tickets:
                        rows.append(recovered_row)
                        seen_tickets.add(int(recovered_row[0]))

                for row in rows:
                    (
                        position_ticket,
                        original_message_id,
                        destination_message_id,
                        symbol,
                        direction,
                        entry,
                        last_sl,
                        tp1_db,
                        status,
                        mt5_deal,
                        mt5_volume,
                        mt5_price,
                    ) = row

                    trade_source_chat = recovered_trade_sources.get(
                        int(position_ticket), SOURCE_CHAT
                    )

                    positions = await asyncio.to_thread(
                        mt5.positions_get,
                        ticket=int(position_ticket),
                    )

                    if positions:
                        position = positions[0]

                        # La protezione parte direttamente dal prezzo LIVE di MT5.
                        # A +50 PIPS il primo step porta lo SL a +10 PIPS
                        # rispetto all'entry; non aspettiamo più alcun messaggio Telegram.
                        current_price = float(
                            getattr(position, "price_current", 0.0) or 0.0
                        )
                        profit_pips = _calculate_position_profit_pips(position)

                        # --------------------------------------------------
                        # AGGIORNAMENTO NEL CANALE OGNI 100 PIPS DI PROFITTO
                        # --------------------------------------------------
                        # Indipendente dagli step fini di protezione SL qui
                        # sotto (che continuano a muovere lo SL su MT5 come
                        # sempre, silenziosamente): qui contiamo solo i
                        # multipli di 100 pips di profitto e mandiamo un
                        # messaggio in risposta al segnale originale, una
                        # volta sola per multiplo. A +100 e' il messaggio di
                        # BE, dai +200 in poi il semplice aggiornamento pips.
                        # Continua anche dopo il TP raggiunto, fino alla
                        # chiusura del trade.
                        if profit_pips >= 100.0:
                            pips_bucket = int(profit_pips // 100) * 100
                            last_notified = await asyncio.to_thread(
                                get_last_pips_notified, position_ticket
                            )
                            if pips_bucket > last_notified:
                                await asyncio.to_thread(
                                    set_last_pips_notified,
                                    position_ticket,
                                    trade_source_chat,
                                    original_message_id,
                                    pips_bucket,
                                )
                                try:
                                    if pips_bucket == 100:
                                        sent = await send_be_applied_message(
                                            pips=pips_bucket,
                                            reply_to=destination_message_id,
                                        )
                                    else:
                                        sent = await send_pips_progress_message(
                                            pips=pips_bucket,
                                            reply_to=destination_message_id,
                                        )
                                    logger.info(
                                        "📈 AGGIORNAMENTO PIPS | Position=%s | +%s PIPS | Destination #%s",
                                        position_ticket, pips_bucket, sent.id,
                                    )
                                except Exception:
                                    logger.exception(
                                        "❌ ERRORE MESSAGGIO AGGIORNAMENTO PIPS | Position=%s",
                                        position_ticket,
                                    )

                        # Il TP3 del segnale e' il nostro TAKE PROFIT logico.
                        # Non viene impostato come TP broker-side: quando il prezzo
                        # lo raggiunge, il bot avvisa il gruppo e lascia correre il trade
                        # con trailing dinamico del 15%.
                        take_profit_price = float(tp1_db or 0.0)
                        tp_reached_now = (
                            take_profit_price > 0
                            and (
                                (str(direction).upper() == "BUY" and current_price >= take_profit_price)
                                or (str(direction).upper() == "SELL" and current_price <= take_profit_price)
                            )
                        )

                        if tp_reached_now and not await asyncio.to_thread(has_tp3_reached, position_ticket):
                            # Prima applichiamo/rafforziamo subito la protezione dinamica.
                            # Non peggioriamo mai uno SL gia' migliore.
                            dynamic_protected_pips = max(0.0, profit_pips * 0.85)
                            existing_sl_price = float(getattr(position, "sl", 0.0) or 0.0)
                            pip_size = float(mt5.symbol_info("XAUUSD-P").point) * 10.0
                            existing_protected_pips = 0.0
                            if pip_size > 0 and existing_sl_price > 0:
                                if str(direction).upper() == "BUY":
                                    existing_protected_pips = (existing_sl_price - float(position.price_open)) / pip_size
                                else:
                                    existing_protected_pips = (float(position.price_open) - existing_sl_price) / pip_size
                            protected_pips_at_tp = max(dynamic_protected_pips, existing_protected_pips)
                            if protected_pips_at_tp > 0 and pip_size > 0 and protected_pips_at_tp > existing_protected_pips + 0.01:
                                percentage_at_tp = protected_pips_at_tp / max(profit_pips, 0.01)
                                try:
                                    tp_result = await asyncio.to_thread(
                                        move_position_to_profit_protection,
                                        position_ticket,
                                        max(profit_pips, 0.01),
                                        percentage_at_tp,
                                    )
                                except Exception as e:
                                    logger.warning(
                                        "⚠️ TRAILING TP NON APPLICATO | Position=%s | Errore=%s",
                                        position_ticket, e,
                                    )
                                    tp_result = None
                            else:
                                tp_result = {"changed": False, "sl": existing_sl_price}

                            tp_sl = float((tp_result or {}).get("sl") or existing_sl_price or 0.0)
                            await asyncio.to_thread(
                                mark_tp3_reached, position_ticket, trade_source_chat, original_message_id
                            )
                            if tp_sl > 0 and (tp_result or {}).get("changed"):
                                update_trade_sl(trade_source_chat, original_message_id, tp_sl, status="OPENED")
                            try:
                                sent = await send_take_profit_reached_message(
                                    pips=profit_pips,
                                    reply_to=destination_message_id,
                                )
                                logger.info(
                                    "🎯 TAKE PROFIT RAGGIUNTO | Position=%s | Prezzo=%.2f | PIPS=%.2f | SL=%.3f | Destination #%s",
                                    position_ticket, current_price, profit_pips, tp_sl, sent.id,
                                )
                            except Exception:
                                logger.exception(
                                    "❌ ERRORE MESSAGGIO TAKE PROFIT | Position=%s",
                                    position_ticket,
                                )

                        step = _live_protection_step(profit_pips)

                        if step is None:
                            continue

                        trigger_pips, protected_pips, protection_mode = step

                        # A +400 il trade NON viene chiuso: viene protetto a +350.
                        # Oltre +400 il livello protetto è l'85% del profitto corrente.
                        # Aggiorniamo solo se miglioriamo lo SL di almeno 5 PIPS,
                        # evitando modifiche continue per ogni tick.
                        existing_sl_price = float(getattr(position, "sl", 0.0) or 0.0)
                        pip_size = float(mt5.symbol_info("XAUUSD-P").point) * 10.0
                        existing_protected_pips = 0.0
                        if pip_size > 0 and existing_sl_price > 0:
                            if str(direction).upper() == "BUY":
                                existing_protected_pips = (existing_sl_price - float(position.price_open)) / pip_size
                            else:
                                existing_protected_pips = (float(position.price_open) - existing_sl_price) / pip_size

                        if existing_protected_pips > 0 and protected_pips < existing_protected_pips + 5.0:
                            continue

                        percentage = protected_pips / trigger_pips

                        try:
                            result = await asyncio.to_thread(
                                move_position_to_profit_protection,
                                position_ticket,
                                trigger_pips,
                                percentage,
                            )
                        except Exception as e:
                            logger.warning(
                                "⚠️ LIVE SL NON APPLICATO | Position=%s | Prezzo=%.2f | "
                                "Profitto=%.2f pips | Protezione=+%.2f | Errore=%s",
                                position_ticket, current_price, profit_pips, protected_pips, e,
                            )
                            continue

                        if not result["changed"]:
                            continue

                        new_sl = float(result["sl"])

                        if trigger_pips == 100.0:
                            await asyncio.to_thread(
                                mark_automatic_breakeven,
                                position_ticket,
                                trade_source_chat,
                                original_message_id,
                                new_sl,
                            )

                        update_trade_sl(
                            trade_source_chat,
                            original_message_id,
                            new_sl,
                            status="OPENED",
                        )

                        logger.info(
                            "🛡️ LIVE SL STEP | Position=%s | Prezzo=%.2f | "
                            "Profitto=%.2f PIPS | Trigger=+%.2f | Protezione=+%.2f | Mode=%s | SL=%.2f",
                            position_ticket,
                            current_price,
                            profit_pips,
                            trigger_pips,
                            protected_pips,
                            protection_mode,
                            new_sl,
                        )
                        # Nessun messaggio da qui: l'aggiornamento nel canale
                        # (BE a +100, poi ogni 100 pips) e' gestito sopra,
                        # indipendentemente da questo step fine di protezione.

                        continue

                    # ----------------------------------------------------
                    # POSIZIONE CHIUSA: leggiamo lo storico MT5
                    # ----------------------------------------------------
                    close_info = await asyncio.to_thread(
                        get_closed_position_info,
                        position_ticket,
                    )

                    if not close_info:
                        continue

                    current_row = get_message(
                        SOURCE_CHAT,
                        original_message_id,
                    )
                    if current_row is None:
                        continue

                    if current_row[8] not in ("OPENED", "TP_SET"):
                        continue

                    actual_close_price = float(
                        close_info.get("price") or 0.0
                    )
                    close_datetime = datetime.now(timezone.utc)

                    if close_info.get("is_tp"):
                        open_price_for_report = float(row[11] or row[5] or 0.0)
                        breakeven_applied_for_report = await asyncio.to_thread(
                            has_breakeven_applied,
                            SOURCE_CHAT,
                            original_message_id,
                        )
                        trailing_applied_for_report = (
                            (
                                (
                                    str(direction).upper() == "BUY"
                                    and float(last_sl or 0.0) > open_price_for_report
                                )
                                or (
                                    str(direction).upper() == "SELL"
                                    and float(last_sl or 0.0) < open_price_for_report
                                )
                            )
                        )
                        record_daily_trade_result(
                            position_ticket=position_ticket,
                            source_chat_id=SOURCE_CHAT,
                            source_message_id=original_message_id,
                            symbol="XAUUSD",
                            direction=direction,
                            open_price=open_price_for_report,
                            close_price=actual_close_price,
                            profit_pips=_calculate_closed_trade_pips(
                                open_price_for_report,
                                actual_close_price,
                                direction,
                            ),
                            close_status="TAKE_PROFIT_HIT",
                            close_datetime=close_datetime.isoformat(),
                            breakeven_applied=breakeven_applied_for_report,
                            trailing_applied=trailing_applied_for_report,
                            tp3_hit=True,
                        )
                        update_status(
                            SOURCE_CHAT,
                            original_message_id,
                            "TAKE_PROFIT_HIT",
                            trade_datetime=close_datetime.isoformat(),
                        )
                        logger.info(
                            "🎯 TP3 PRESO | Position=%s | Close Price=%.2f",
                            position_ticket,
                            actual_close_price,
                        )
                        continue

                    if close_info.get("is_sl"):
                        last_sl_price = float(last_sl or 0.0)
                        open_price_for_report = float(row[11] or row[5] or 0.0)
                        breakeven_applied = await asyncio.to_thread(
                            has_breakeven_applied,
                            SOURCE_CHAT,
                            original_message_id,
                        )
                        pip_size_for_report = 0.0
                        symbol_info_for_report = mt5.symbol_info("XAUUSD-P")
                        if symbol_info_for_report is not None:
                            pip_size_for_report = float(symbol_info_for_report.point) * 10.0

                        trailing_applied = (
                            pip_size_for_report > 0
                            and (
                                (
                                    str(direction).upper() == "BUY"
                                    and last_sl_price >= open_price_for_report + pip_size_for_report
                                )
                                or (
                                    str(direction).upper() == "SELL"
                                    and last_sl_price <= open_price_for_report - pip_size_for_report
                                )
                            )
                        )

                        if trailing_applied:
                            close_status = "SL_TRAILING_HIT"
                        elif breakeven_applied:
                            close_status = "SL_BREAKEVEN_HIT"
                        else:
                            close_status = "SL_INITIAL_HIT"

                        open_price_for_report = float(row[11] or row[5] or 0.0)
                        close_pips_for_report = _calculate_closed_trade_pips(
                            open_price_for_report,
                            actual_close_price,
                            direction,
                        )
                        record_daily_trade_result(
                            position_ticket=position_ticket,
                            source_chat_id=SOURCE_CHAT,
                            source_message_id=original_message_id,
                            symbol="XAUUSD",
                            direction=direction,
                            open_price=open_price_for_report,
                            close_price=actual_close_price,
                            profit_pips=close_pips_for_report,
                            close_status=close_status,
                            close_datetime=close_datetime.isoformat(),
                            breakeven_applied=breakeven_applied,
                            trailing_applied=trailing_applied,
                            tp3_hit=await asyncio.to_thread(has_tp3_reached, position_ticket),
                        )

                        update_status(
                            SOURCE_CHAT,
                            original_message_id,
                            close_status,
                            trade_datetime=close_datetime.isoformat(),
                        )

                        logger.info(
                            "🛑 %s | Position=%s | Close Price=%.2f | Ultimo SL=%.2f",
                            close_status,
                            position_ticket,
                            actual_close_price,
                            last_sl_price,
                        )

                        try:
                            if trailing_applied:
                                sent = await send_trailing_sl_hit_message(
                                    sl=last_sl_price,
                                    price=actual_close_price,
                                    pips=close_pips_for_report,
                                    reply_to=destination_message_id,
                                )
                            elif breakeven_applied:
                                sent = await send_breakeven_sl_hit_message(
                                    actual_close_price,
                                    reply_to=destination_message_id,
                                )
                            else:
                                sent = await send_initial_sl_hit_message(
                                    close_pips_for_report,
                                    reply_to=destination_message_id,
                                )

                            logger.info(
                                "📤 MESSAGGIO CHIUSURA SL INVIATO | Destination #%s",
                                sent.id,
                            )
                        except Exception:
                            logger.exception(
                                "❌ ERRORE INVIO MESSAGGIO SL | Position=%s",
                                position_ticket,
                            )
                        continue

                    # Chiusura esterna/non riconducibile a TP3 o SL.
                    # Può essere una chiusura forzata delle 22:59.
                    open_price_for_report = float(row[11] or row[5] or 0.0)
                    close_pips_for_report = _calculate_closed_trade_pips(
                        open_price_for_report,
                        actual_close_price,
                        direction,
                    )
                    record_daily_trade_result(
                        position_ticket=position_ticket,
                        source_chat_id=SOURCE_CHAT,
                        source_message_id=original_message_id,
                        symbol="XAUUSD",
                        direction=direction,
                        open_price=open_price_for_report,
                        close_price=actual_close_price,
                        profit_pips=close_pips_for_report,
                        close_status="CLOSED_EXTERNAL",
                        close_datetime=close_datetime.isoformat(),
                        breakeven_applied=await asyncio.to_thread(
                            has_breakeven_applied, SOURCE_CHAT, original_message_id
                        ),
                        trailing_applied=False,
                        tp3_hit=await asyncio.to_thread(has_tp3_reached, position_ticket),
                    )
                    update_status(
                        SOURCE_CHAT,
                        original_message_id,
                        "CLOSED_EXTERNAL",
                        trade_datetime=close_datetime.isoformat(),
                    )
                    logger.info(
                        "ℹ️ Position=%s chiusa su MT5 | reason=%s.",
                        position_ticket,
                        close_info.get("reason"),
                    )

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("❌ ERRORE MONITOR LIVE SL")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=0.5)
        except asyncio.TimeoutError:
            pass


# ============================================================
# MESSAGGIO MODIFICATO NEL SOURCE
# ============================================================

@client.on(
    events.MessageEdited(
        chats=SOURCE_CHAT
    )
)
async def edited_message_handler(event):

    message = event.message

    source_message_id = message.id

    message_lock = get_message_lock(
        source_message_id
    )

    async with message_lock:

        edited_datetime = datetime.now(timezone.utc)

        print_separator()

        logger.info(
            "✏️ MESSAGGIO MODIFICATO #%s",
            source_message_id,
        )

        print_separator()

        logger.info(
            "SOURCE EDIT: %s",
            edited_datetime.strftime(
                "%H:%M:%S.%f"
            )[:-3],
        )

        logger.info(
            "Nuovo testo:"
        )

        logger.info(
            "%s",
            message.text
            if message.text
            else "[VUOTO]",
        )

        # ====================================================
        # CERCA MAPPATURA DATABASE
        # ====================================================

        row = None

        # Telegram può notificare l'edit praticamente
        # nello stesso momento del NewMessage.
        #
        # Facciamo alcuni tentativi brevi per dare tempo
        # al salvataggio della mappatura.
        for attempt in range(5):

            try:

                row = get_message(
                    SOURCE_CHAT,
                    source_message_id,
                )

            except Exception as e:

                logger.warning(
                    "⚠️ Errore lettura DB edit #%s "
                    "tentativo %s/5: %s",
                    source_message_id,
                    attempt + 1,
                    e,
                )

                row = None

            if row is not None:
                break

            await asyncio.sleep(
                0.20
            )

        # ====================================================
        # MESSAGGIO NON PRESENTE
        # ====================================================

        if row is None:

            logger.warning(
                "⚠️ Messaggio #%s non presente "
                "nel database.",
                source_message_id,
            )

            return

        # ====================================================
        # DESTINATION MESSAGE ID
        # ====================================================

        try:

            destination_message_id = row[2]

        except Exception:

            logger.exception(
                "❌ Impossibile leggere "
                "destination_message_id #%s",
                source_message_id,
            )

            return

        if destination_message_id is None:

            logger.warning(
                "⚠️ Destination ID mancante #%s",
                source_message_id,
            )

            return

        # ====================================================
        # AGGIORNA DESTINATION
        # ====================================================
        # Se Cedric modifica il messaggio originale (es. per correggere un
        # refuso), NON dobbiamo mai far ricomparire la SUA entry al posto
        # di quella reale MT5 gia' mostrata all'apertura: la recuperiamo dal
        # DB (mt5_price) e la usiamo al posto di quella riparsata dal testo.
        try:
            edited_signal = parse_signal(message.text or "")
        except Exception as e:
            logger.exception(
                "❌ Errore parsing EDIT #%s: %s",
                source_message_id,
                e,
            )
            edited_signal = None

        signal_for_destination_edit = edited_signal
        if edited_signal and edited_signal.get("action") == "OPEN":
            real_entry_price = row[12]
            if real_entry_price:
                signal_for_destination_edit = dict(edited_signal)
                signal_for_destination_edit["entry"] = float(real_entry_price)

        edit_start = time.monotonic()

        try:

            await edit_destination_message(
                destination_message_id,
                message,
                signal=signal_for_destination_edit,
            )

        except MessageNotModifiedError:

            logger.info(
                "ℹ️ Destination #%s già aggiornato.",
                destination_message_id,
            )

        except Exception as e:

            logger.exception(
                "❌ ERRORE MODIFICA DESTINATION #%s: %s",
                destination_message_id,
                e,
            )
            # Anche se la sincronizzazione Telegram fallisce, continuiamo
            # con l'elaborazione MT5 dell'edit.

        edit_end = time.monotonic()

        edit_delay = (
            edit_end
            - edit_start
        )

        logger.info(
            "✏️ Destination #%s aggiornato.",
            destination_message_id,
        )

        logger.info(
            "Edit Delay: %.3fs",
            edit_delay,
        )

        # ====================================================
        # EDIT -> sincronizzazione + eventuale aggiornamento MT5
        # ====================================================
        # Un edit del messaggio completo (SL + TP1) NON apre mai
        # una nuova posizione. Viene invece trattato come UPDATE_PARAMS
        # sulla posizione già associata al messaggio originale.
        #
        # Questo permette anche di correggere un segnale errato:
        # se il primo invio conteneva un TP invalido e poi il messaggio
        # viene modificato con un TP corretto, MT5 viene aggiornato
        # automaticamente.
        # ====================================================

        if edited_signal and edited_signal.get("action") == "UPDATE_PARAMS":
            logger.info(
                "🔄 EDIT CON PARAMETRI -> aggiorno automaticamente MT5 | #%s",
                source_message_id,
            )
            await process_update_params(
                edited_signal,
                source_message_id,
            )
        else:
            logger.info(
                "🔒 EDIT sincronizzato senza riaprire trade #%s.",
                source_message_id,
            )

        print_separator()


# ============================================================
# MAIN
# ============================================================

async def main():

    global MT5_READY

    print_separator()

    logger.info(
        "🚀 CÉDRIC FX → MT5 COPIER"
    )

    print_separator()

    # ========================================================
    # RIEPILOGO SETTAGGI BOT
    # ========================================================
    # Solo logging: non modifica alcun parametro o comportamento.
    logger.info("📡 TELEGRAM")
    logger.info("SOURCE CEDRIC FX ELITE        : %s", SOURCE_CHAT)
    logger.info("DESTINATION YARDFX ELITE      : %s", DESTINATION_CHAT)
    logger.info("SESSION             : gestita dal client Telegram")
    logger.info("")
    logger.info("💱 TRADING")
    logger.info("SYMBOL              : XAUUSD")
    logger.info("TRADING ENABLED     : %s", TRADING_ENABLED)
    logger.info("MAX SIGNAL AGE      : %ss", MAX_SIGNAL_AGE_SECONDS)
    logger.info("MAX SAME-SECOND     : %s segnali", MAX_SIMULTANEOUS_SIGNALS)
    logger.info("ENTRY               : IMMEDIATA A MERCATO")
    logger.info("SL                  : DAL SEGNALE")
    logger.info("TP OPERATIVO        : NESSUNO | TRADE GESTITO DA SL")
    logger.info("TP1 / TP2           : SOLO INFORMATIVI | TAKE PROFIT = TP3 LOGICO")
    logger.info("TRAILING TELEGRAM   : DISABILITATO")
    logger.info("")
    logger.info("🛡️ GESTIONE SL LIVE")
    logger.info("+100 PIPS           : SL +20 (BE) DA MT5")
    logger.info("+125 PIPS           : SL +50")
    logger.info("+150 PIPS           : SL +80")
    logger.info("+175 PIPS           : SL +110")
    logger.info("+200 PIPS           : SL +128")
    logger.info("+225 PIPS           : SL +157")
    logger.info("+250 PIPS           : SL +186")
    logger.info("+275 PIPS           : SL +215")
    logger.info("+300 PIPS           : SL +244")
    logger.info("+325 PIPS           : SL +273")
    logger.info("+350 PIPS           : SL +302")
    logger.info("+375 PIPS           : SL +331")
    logger.info("+400 PIPS           : SL +360 | TRADE RESTA APERTO")
    logger.info(">+400 PIPS          : TRAILING DINAMICO 15%%")
    logger.info("SL                  : NON ARRETRA MAI")
    logger.info("")
    logger.info("📋 EVENTI")
    logger.info("SEGNALE COMPLETO    : APERTURA IMMEDIATA")
    logger.info("TP1 +50             : INFORMATIVO | PROTEZIONE DA MT5")
    logger.info("TP2 / TP3 PIPS      : INFORMATIVI")
    logger.info("CHIUSURA GIORN.     : TUTTE LE POSIZIONI ENTRO LE 22:59 IT")
    logger.info("BUONGIORNO          : LUN-VEN | ORE 06:00 IT")
    logger.info("RIEPILOGO GIORN.    : LUN-VEN | ORE 23:00 IT")
    logger.info("RIEPILOGO SETT.     : SABATO | ORE 10:00 IT")
    logger.info("SL HIT              : RILEVATO DA MT5")
    logger.info("TAKE PROFIT         : TP3 LOGICO | NON CHIUDE | ATTIVA TRAILING 15%")
    logger.info("")
    logger.info("🛡️ MONITOR")
    logger.info("PREZZO MT5          : ogni 0.5s")
    logger.info("BE / TRAILING / HIT : MESSAGGI NELLA DESTINATION")
    logger.info("")
    logger.info("🔌 META TRADER 5")
    logger.info("CONNESSIONE         : %s", "PRONTA ALLO START" if MT5_READY is False else "PRONTA")
    logger.info("MAGIC/LOT/DEVIATION : gestiti da mt5_executor.py")
    logger.info("")

    bot_start_local = BOT_START_TIME.astimezone(ITALY_TZ)

    logger.info(
        "Bot Start: %s IT",
        bot_start_local.strftime(
            "%d/%m/%Y %H:%M:%S"
        ),
    )

    logger.info(
        "MAX SIGNAL AGE       : %ss",
        MAX_SIGNAL_AGE_SECONDS,
    )

    logger.info(
        "MAX SAME-SECOND      : %s segnali",
        MAX_SIMULTANEOUS_SIGNALS,
    )

    logger.info(
        "TRADING ENABLED      : %s",
        TRADING_ENABLED,
    )

    # ========================================================
    # DATABASE
    # ========================================================

    try:

        init_database()

        logger.info(
            "🗄️ Database pronto."
        )

    except Exception as e:

        logger.exception(
            "❌ ERRORE INIZIALIZZAZIONE DATABASE: %s",
            e,
        )

        raise

    # ========================================================
    # TELEGRAM
    # ========================================================

    logger.info(
        "📡 Connessione Telegram..."
    )

    await client.start()

    logger.info(
        "✅ Telegram collegato."
    )

    logger.info(
        "SOURCE      : %s",
        SOURCE_CHAT,
    )

    logger.info(
        "DESTINATION : %s",
        DESTINATION_CHAT,
    )

    # ========================================================
    # MT5
    # ========================================================

    try:

        MT5_READY = await asyncio.to_thread(
            connect_mt5
        )

    except Exception as e:

        logger.exception(
            "❌ Errore connessione MT5: %s",
            e,
        )

        MT5_READY = False

    if MT5_READY:

        logger.info(
            "✅ MT5 PRONTO: trading abilitato=%s",
            TRADING_ENABLED,
        )

    else:

        logger.warning(
            "⚠️ MT5 NON COLLEGATO."
        )

        logger.warning(
            "Telegram continuerà a funzionare,"
        )

        logger.warning(
            "ma nessun trade verrà aperto."
        )

    # ========================================================
    # RECOVERY POSIZIONI GIA' APERTE
    # ========================================================

    await recover_open_positions_after_startup()

    # ========================================================
    # BOT OPERATIVO
    # ========================================================

    print_separator()

    logger.info(
        "🟢 BOT OPERATIVO"
    )

    print_separator()

    logger.info(
        "Ascolto nuovi messaggi + modifiche."
    )

    logger.info(
        "Più segnali possono essere eseguiti contemporaneamente."
    )

    logger.info(
        "Massimo %s segnali per lo stesso secondo Telegram.",
        MAX_SIMULTANEOUS_SIGNALS,
    )

    logger.info(
        "Segnali più vecchi di %ss: copiati ma NON tradati.",
        MAX_SIGNAL_AGE_SECONDS,
    )

    print_separator()

    # ========================================================
    # MONITOR TRAILING SL
    # ========================================================

    monitor_stop_event = asyncio.Event()
    monitor_task = asyncio.create_task(
        monitor_trailing_sl_closures(monitor_stop_event)
    )

    logger.info("🛡️ Monitor trailing SL avviato.")

    # ========================================================
    # DAILY REPORT YARDFX
    # ========================================================

    daily_report_stop_event = asyncio.Event()
    daily_report_task = asyncio.create_task(
        daily_report_scheduler(daily_report_stop_event)
    )

    monthly_report_stop_event = asyncio.Event()
    monthly_report_task = asyncio.create_task(
        monthly_report_scheduler(monthly_report_stop_event)
    )

    weekly_report_stop_event = asyncio.Event()
    weekly_report_task = asyncio.create_task(
        weekly_report_scheduler(weekly_report_stop_event)
    )

    morning_stop_event = asyncio.Event()
    morning_task = asyncio.create_task(
        morning_message_scheduler(morning_stop_event)
    )

    daily_close_stop_event = asyncio.Event()
    daily_close_task = asyncio.create_task(
        daily_close_scheduler(daily_close_stop_event)
    )

    logger.info("📊 YARDFX Daily Report avviato | Lun-Ven 23:00 Europe/Rome.")
    logger.info("📊 YARDFX Monthly Report avviato | Ultimo giorno del mese 23:59 Europe/Rome.")
    logger.info("📊 YARDFX Weekly Report avviato | Sabato 10:00 Europe/Rome.")
    logger.info("☀️ YARDFX Buongiorno avviato | Lun-Ven 06:00 Europe/Rome.")
    logger.info("🌙 YARDFX Daily Close avviato | Tutte le posizioni chiuse alle 22:59 Europe/Rome.")

    # ========================================================
    # TELEGRAM LOOP
    # ========================================================

    try:
        await client.run_until_disconnected()
    finally:
        monitor_stop_event.set()
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

        daily_report_stop_event.set()
        daily_report_task.cancel()
        try:
            await daily_report_task
        except asyncio.CancelledError:
            pass

        monthly_report_stop_event.set()
        monthly_report_task.cancel()
        try:
            await monthly_report_task
        except asyncio.CancelledError:
            pass

        weekly_report_stop_event.set()
        weekly_report_task.cancel()
        try:
            await weekly_report_task
        except asyncio.CancelledError:
            pass

        morning_stop_event.set()
        morning_task.cancel()
        try:
            await morning_task
        except asyncio.CancelledError:
            pass

        daily_close_stop_event.set()
        daily_close_task.cancel()
        try:
            await daily_close_task
        except asyncio.CancelledError:
            pass


# ============================================================
# AVVIO
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()

        logger.info(
            "🛑 Bot arrestato manualmente."
        )

    except Exception as e:

        logger.exception(
            "❌ ERRORE FATALE: %s",
            e,
        )