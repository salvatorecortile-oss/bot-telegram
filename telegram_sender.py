from html import escape
import re

from telethon.errors import MessageNotModifiedError
from telegram_client import client
from config import DESTINATION_CHAT


# ============================================================
# MESSAGGI PERSONALIZZABILI - MODIFICA QUI I TESTI
# ============================================================

GOOD_MORNING_MESSAGE_TEMPLATE = (
    "☀️ <b>BUONGIORNO RAGAZZI</b> ☀️\n\n"
    "Una nuova giornata di trading sta per iniziare.\n\n"
    "📩 <b>Hai bisogno di assistenza?</b>\n"
    "Scrivimi in privato @yard_fx\n\n"
    "Restate pronti e soprattutto disciplinati. 📊\n"
    "Ci sentiamo tra poco con le operazioni della giornata.\n"
    "<b>- YardFX</b>"
)

FORCED_DAILY_CLOSE_MESSAGE_TEMPLATE = (
    "🌙 <b>CHIUSURA GIORNALIERA</b>\n"
    "🕙 Tutte le operazioni vengono chiuse entro le 21:59."
)

OPEN_TRADE_MESSAGE_TEMPLATE = (
    "👑 <b>XAUUSD — {direction}</b>\n\n"
    "🟢 <b>ENTRY:</b> {entry:.2f}\n"
    "🛑 <b>STOP LOSS:</b> {sl:.2f}\n"
    "🎯 <b>TAKE PROFIT:</b> {tp3:.2f}"
)

BE_APPLIED_MESSAGE_TEMPLATE = (
    "🟢 <b>BE ATTIVATO</b>\n"
    "📈 <b>+{pips} PIPS</b>\n"
)

PIPS_PROGRESS_MESSAGE_TEMPLATE = (
    "📈 <b>+{pips} PIPS</b>\n"
    "💰 Parzializzate o chiudete l'operazione.\n"
    "Se volete potete lasciare aperto e puntare al TP!"
)

# Copia informativa quando Cédric scrive "STOP LOSS" in chat (nessuna
# posizione chiusa per davvero a quel momento): resta com'era, con il
# prezzo live. Da non confondere con SL_HIT_MESSAGE_TEMPLATE, usato per
# la chiusura reale rilevata da MT5.
SL_HIT_INFO_MESSAGE_TEMPLATE = (
    "🛑 <b>STOP LOSS PRESO</b>\n"
    "📍 Prezzo attuale/chiusura: <b>{price:.2f}</b>"
)

SL_HIT_MESSAGE_TEMPLATE = (
    "🛑 <b>STOP LOSS PRESO</b>\n"
    "📈 <b>{pips:+.0f} PIPS</b>"
)

BREAKEVEN_SL_HIT_MESSAGE_TEMPLATE = (
    "🟢 <b>STOP LOSS A BE PRESO</b>\n"
    "📍 Prezzo di chiusura: <b>{price:.2f}</b>\n"
    "✅ <b>OPERAZIONE CHIUSA</b>"
)

TRAILING_SL_HIT_MESSAGE_TEMPLATE = (
    "🛑 <b>STOP LOSS IN PROFITTO PRESO</b> ✅\n"
    "📍 Prezzo di chiusura: <b>{price:.2f}</b>\n"
    "📈 <b>PIPS TOTALI: {pips:+.0f}</b>\n"
    "💰 <b>OPERAZIONE CHIUSA IN PROFITTO</b>"
)

TAKE_PROFIT_REACHED_MESSAGE_TEMPLATE = (
    "🟢 <b>TAKE PROFIT RAGGIUNTO!</b>\n"
    "✅ Chiudere l'operazione o se si vuole lasciare aperta seguite i prossimi messaggi.\n\n"
    "📈 <b>PIPS TOTALI: +{pips}</b>"
)

WEEKLY_REPORT_MESSAGE_TEMPLATE = (
    "📊 YARDFX ELITE REPORT\n"
    "📅 REPORT SETTIMANALE\n\n"
    "📅 {date_range}\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "Operazioni: {operations}\n"
    "✅ {wins} Win\n"
    "❌ {losses} Loss\n"
    "🟢 {breakeven} BE\n\n"
    "📈 Win Rate: {win_rate:.1f}%\n"
    "📊 TOT {result_pips}\n\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "Grazie per averci seguito e supportato in questi giorni.\n"
    "Ci sentiamo lunedì con nuove operazioni.\n\n"
    "Buon weekend!\n"
    "- YardFX"
)

MONTHLY_REPORT_TEMPLATE = (
    "📊 <b>YARDFX ELITE REPORT</b>\n"
    "📅 <b>RISULTATO MENSILE</b>\n\n"
    "📅 {date_range}\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "Operazioni: {operations}\n"
    "✅ {wins} Win\n"
    "❌ {losses} Loss\n"
    "📈 Win Rate: {win_rate:.1f}%\n"
    "📊 TOT {pips:+.0f} PIPS\n\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "Grazie per averci seguito e supportato in questo mese.\n"
    "<b>- YardFX</b>"
)

DAILY_REPORT_MESSAGE_TEMPLATE = (
    "📊 YARDFX ELITE REPORT\n"
    "💰 RISULTATO GIORNALIERO\n\n"
    "📅 {date}\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "Operazioni: {operations}\n"
    "✅ Vincenti: {wins}\n"
    "❌ Perse: {losses}\n"
    "🟢 BE: {breakeven}\n\n"
    "📈 Win Rate: {win_rate:.0f}%\n"
    "📊 Risultato: {result_pips}\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "Grazie per averci seguito!\n"
    "Ci sentiamo domani con altre operazioni.\n"
    "- YardFX"
)

# Compatibilità con eventuali riferimenti storici.
DAILY_RECAP_MESSAGE_TEMPLATE = DAILY_REPORT_MESSAGE_TEMPLATE

# Compatibilità con vecchi riferimenti del bot.
PROFIT_MESSAGE = BE_APPLIED_MESSAGE_TEMPLATE



def _format_pips_value(pips):
    value = float(pips)
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_open_trade_message(signal):
    return OPEN_TRADE_MESSAGE_TEMPLATE.format(
        direction=escape(str(signal["direction"])),
        entry=float(signal["entry"]),
        sl=float(signal["sl"]),
        tp3=float(signal["tp3"]),
    )


def format_signal_for_destination(source_message, signal=None):
    """Crea il messaggio brandizzato da pubblicare nella destination."""
    if signal is None:
        return None

    action = signal.get("action")

    if action == "OPEN":
        return format_open_trade_message(signal)

    if action in {"PIPS_UPDATE", "PIPS_INFO"}:
        # I messaggi pips non vengono più copiati nella destination.
        return None

    if action == "DAILY_RECAP":
        # Il riepilogo di Cédric NON viene più pubblicato.
        return None

    if action == "SL_HIT":
        price = signal.get("current_price")
        if price is None:
            return "🛑 <b>STOP LOSS PRESO</b>"
        return SL_HIT_INFO_MESSAGE_TEMPLATE.format(price=float(price))

    if action == "MODIFY_SL":
        sl = float(signal["sl"])
        current_price = signal.get("current_price")
        if current_price is None:
            return f"🛡️ <b>STOP LOSS MODIFICATO:</b> {sl:.2f}"
        return (
            "🛡️ <b>STOP LOSS MODIFICATO</b>\n"
            f"📍 Prezzo attuale: <b>{float(current_price):.2f}</b>\n"
            f"🛑 Nuovo SL: <b>{sl:.2f}</b>"
        )


    return None


async def send_be_applied_message(pips, reply_to=None):
    return await client.send_message(
        DESTINATION_CHAT,
        BE_APPLIED_MESSAGE_TEMPLATE.format(pips=_format_pips_value(pips)),
        parse_mode="html",
        silent=True,
        reply_to=reply_to,
    )


async def send_pips_progress_message(pips, reply_to=None):
    return await client.send_message(
        DESTINATION_CHAT,
        PIPS_PROGRESS_MESSAGE_TEMPLATE.format(pips=_format_pips_value(pips)),
        parse_mode="html",
        silent=True,
        reply_to=reply_to,
    )


def format_trailing_sl_hit_message(sl, price, pips):
    return TRAILING_SL_HIT_MESSAGE_TEMPLATE.format(
        price=float(price),
        sl=float(sl),
        pips=float(pips),
    )

async def send_trailing_sl_hit_message(sl, price, pips, reply_to=None):
    return await client.send_message(
        DESTINATION_CHAT,
        format_trailing_sl_hit_message(sl, price, pips),
        parse_mode="html",
        silent=True,
        reply_to=reply_to,
    )


def format_breakeven_sl_hit_message(price):
    return BREAKEVEN_SL_HIT_MESSAGE_TEMPLATE.format(price=float(price))


async def send_initial_sl_hit_message(pips, reply_to=None):
    return await client.send_message(
        DESTINATION_CHAT,
        SL_HIT_MESSAGE_TEMPLATE.format(pips=float(pips)),
        parse_mode="html",
        silent=True,
        reply_to=reply_to,
    )


async def send_breakeven_sl_hit_message(price, reply_to=None):
    return await client.send_message(
        DESTINATION_CHAT,
        format_breakeven_sl_hit_message(price),
        parse_mode="html",
        silent=True,
        reply_to=reply_to,
    )


def format_take_profit_reached_message(pips):
    return TAKE_PROFIT_REACHED_MESSAGE_TEMPLATE.format(
        pips=_format_pips_value(pips),
    )


async def send_take_profit_reached_message(pips, reply_to=None):
    return await client.send_message(
        DESTINATION_CHAT,
        format_take_profit_reached_message(pips),
        parse_mode="html",
        silent=True,
        reply_to=reply_to,
    )


def format_daily_report_message(
    report_date,
    operations,
    wins,
    losses,
    breakeven,
    win_rate,
    result_pips,
    be_activated,
    profit_sl,
    tp3_reached,
):
    return DAILY_REPORT_MESSAGE_TEMPLATE.format(
        date=str(report_date),
        operations=int(operations),
        wins=int(wins),
        losses=int(losses),
        breakeven=int(breakeven),
        win_rate=float(win_rate),
        result_pips=str(result_pips),
        be_activated=int(be_activated),
        profit_sl=int(profit_sl),
        tp3_reached=int(tp3_reached),
    )


async def send_daily_report_message(
    report_date,
    operations,
    wins,
    losses,
    breakeven,
    win_rate,
    result_pips,
    be_activated,
    profit_sl,
    tp3_reached,
):
    text = format_daily_report_message(
        report_date=report_date,
        operations=operations,
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        win_rate=win_rate,
        result_pips=result_pips,
        be_activated=be_activated,
        profit_sl=profit_sl,
        tp3_reached=tp3_reached,
    )
    return await client.send_message(
        DESTINATION_CHAT,
        text,
        parse_mode="html",
        silent=True,
    )


def format_weekly_report_message(date_range, operations, wins, losses, breakeven, win_rate, result_pips):
    return WEEKLY_REPORT_MESSAGE_TEMPLATE.format(
        date_range=str(date_range),
        operations=int(operations),
        wins=int(wins),
        losses=int(losses),
        breakeven=int(breakeven),
        win_rate=float(win_rate),
        result_pips=str(result_pips),
    )


async def send_weekly_report_message(date_range, operations, wins, losses, breakeven, win_rate, result_pips):
    return await client.send_message(
        DESTINATION_CHAT,
        format_weekly_report_message(
            date_range=date_range,
            operations=operations,
            wins=wins,
            losses=losses,
            breakeven=breakeven,
            win_rate=win_rate,
            result_pips=result_pips,
        ),
        parse_mode="html",
        silent=True,
    )


def format_monthly_report_message(date_range, operations, wins, losses, win_rate, pips):
    return MONTHLY_REPORT_TEMPLATE.format(
        date_range=str(date_range),
        operations=int(operations),
        wins=int(wins),
        losses=int(losses),
        win_rate=float(win_rate),
        pips=float(pips),
    )


async def send_monthly_report_message(date_range, operations, wins, losses, win_rate, pips):
    return await client.send_message(
        DESTINATION_CHAT,
        format_monthly_report_message(
            date_range=date_range,
            operations=operations,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            pips=pips,
        ),
        parse_mode="html",
        silent=True,
    )


async def send_good_morning_message():
    return await client.send_message(
        DESTINATION_CHAT,
        GOOD_MORNING_MESSAGE_TEMPLATE,
        parse_mode="html",
        silent=True,
    )


async def send_forced_daily_close_message():
    return await client.send_message(
        DESTINATION_CHAT,
        FORCED_DAILY_CLOSE_MESSAGE_TEMPLATE,
        parse_mode="html",
        silent=True,
    )


async def copy_message_to_destination(source_message, signal=None):
    formatted_text = format_signal_for_destination(source_message, signal)
    if not formatted_text:
        raise ValueError("Tentativo di copiare un messaggio non operativo.")
    return await client.send_message(
        DESTINATION_CHAT,
        formatted_text,
        parse_mode="html",
        silent=True,
    )


async def edit_destination_message(destination_message_id, source_message, signal=None):
    from signal_parser import parse_signal

    if signal is None:
        signal = parse_signal(source_message.message)

    if signal is None:
        return False

    formatted_text = format_signal_for_destination(source_message, signal)
    if not formatted_text:
        return False

    try:
        await client.edit_message(
            DESTINATION_CHAT,
            destination_message_id,
            text=formatted_text,
            parse_mode="html",
        )
    except MessageNotModifiedError:
        return False

    return True


async def edit_destination_message_with_signal(destination_message_id, signal):
    formatted_text = format_signal_for_destination(None, signal)
    if not formatted_text:
        return False

    try:
        await client.edit_message(
            DESTINATION_CHAT,
            destination_message_id,
            text=formatted_text,
            parse_mode="html",
        )
    except MessageNotModifiedError:
        return False

    return True


async def delete_destination_message(destination_message_id):
    await client.delete_messages(DESTINATION_CHAT, [destination_message_id])


# ============================================================
# COMANDI BOT2 (Messaggi Salvati) - risposte inviate con event.reply()
# ============================================================

BOT2_PLAY_MESSAGE_TEMPLATE = (
    "✅ <b>BOT2 (CÉDRIC) ATTIVO AL 100%</b>\n"
    "Ascolto segnali e apro nuovi trade normalmente."
)

BOT2_RESTART_MESSAGE_TEMPLATE = (
    "🔄 <b>BOT2 (CÉDRIC) RIAVVIATO</b>\n"
    "Posizioni chiuse: {closed}\n"
    "{errors_line}"
    "Di nuovo operativo al 100%: ascolto segnali e apro nuovi trade normalmente."
)

BOT2_PAUSED_MESSAGE_TEMPLATE = (
    "⏸️ <b>BOT2 (CÉDRIC) IN PAUSA</b>\n"
    "Nessun nuovo trade verrà aperto.\n"
    "Le posizioni già aperte continuano a essere gestite."
)

BOT2_STOPPED_MESSAGE_TEMPLATE = (
    "🛑 <b>BOT2 (CÉDRIC) FERMATO</b>\n"
    "Posizioni chiuse: {closed}\n"
    "{errors_line}"
    "Non ascolto più messaggi e non invio altro nel canale finché non ricevo bot2_play."
)

BOT2_STATUS_MESSAGE_TEMPLATE = (
    "<b>STATO BOT:</b> {state_label}\n\n"
    "<b>Posizioni aperte ({positions_count}):</b>\n{positions}"
)

BOT2_COMMANDS_LIST_TEXT = (
    "bot2_play, bot2_pausa, bot2_stop, bot2_riavvio, bot2_status, "
    "bot2_report, bot2_reportw, bot2_reportm, bot2_comandi"
)

BOT2_UNKNOWN_COMMAND_MESSAGE = (
    "❓ <b>Comando non riconosciuto.</b>\n"
    "Comandi disponibili: " + BOT2_COMMANDS_LIST_TEXT
)

BOT2_HELP_MESSAGE_TEMPLATE = (
    "📋 <b>COMANDI DISPONIBILI BOT2 (CÉDRIC)</b>\n\n"
    "bot2_play — attivo al 100%\n"
    "bot2_pausa — nessun nuovo trade, gestisce quelli aperti\n"
    "bot2_stop — chiude tutto e non ascolta più nulla\n"
    "bot2_riavvio — chiude tutto e riparte al 100%\n"
    "bot2_status — stato attuale e posizioni aperte\n"
    "bot2_report — report giornaliero ora\n"
    "bot2_reportw — report settimanale ora\n"
    "bot2_reportm — report mensile ora\n"
    "bot2_comandi — questo elenco"
)


def format_bot2_stopped_message(closed, errors):
    errors_line = f"⚠️ Errori chiusura: {errors}\n" if errors else ""
    return BOT2_STOPPED_MESSAGE_TEMPLATE.format(closed=closed, errors_line=errors_line)


def format_bot2_restart_message(closed, errors):
    errors_line = f"⚠️ Errori chiusura: {errors}\n" if errors else ""
    return BOT2_RESTART_MESSAGE_TEMPLATE.format(closed=closed, errors_line=errors_line)


def format_bot2_status_message(state_label, positions_count, positions_text):
    return BOT2_STATUS_MESSAGE_TEMPLATE.format(
        state_label=state_label,
        positions_count=positions_count,
        positions=positions_text,
    )
