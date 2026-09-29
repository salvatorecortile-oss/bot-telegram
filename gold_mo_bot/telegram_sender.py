from telethon.errors import MessageNotModifiedError
from telegram_client import client
from config import BRAND_NAME, DESTINATION_CHAT

# ============================================================
# MESSAGGI - MODIFICA QUI I TESTI
# ============================================================

HEADER_TEMPLATE = "🟡 <b>XAUUSD — {direction}</b>\n\n"

ENTRY_LINE_TEMPLATE = "🟢 <b>ENTRY:</b> {entry:.2f}\n"
SL_LINE_TEMPLATE = "🛑 <b>STOP LOSS:</b> {sl:.2f}\n"
SL_PENDING_LINE = "🛑 <b>STOP LOSS:</b> in attesa...\n"

TP_LINE_TEMPLATE = "🎯 <b>TP:</b> {value:.2f}\n"
TP_PENDING_LINE = "🎯 <b>TP:</b> in attesa...\n"

CLOSED_TP_MESSAGE_TEMPLATE = "✅ <b>TAKE PROFIT RAGGIUNTO</b>\n📈 <b>{pips:+.0f} PIPS</b>"
CLOSED_SL_MESSAGE_TEMPLATE = "🛑 <b>STOP LOSS PRESO</b>\n📉 <b>{pips:+.0f} PIPS</b>"
CLOSED_GENERIC_MESSAGE_TEMPLATE = "⚪ <b>OPERAZIONE CHIUSA</b>\n📊 <b>{pips:+.0f} PIPS</b>"

SL_MOVED_MESSAGE_TEMPLATE = "🔄 <b>STOP LOSS SPOSTATO</b>\n🛑 Nuovo SL: <b>{sl:.2f}</b>"


def format_trade_card(state):
    """
    Messaggio principale pubblicato quando arrivano SL/TP: entry, SL e
    un unico TP (quello operativo su MT5, cioe' TP3). TP1/TP2/TP4/"open"
    restano interni al bot, non vengono mostrati. La chiusura (unico
    aggiornamento previsto) NON modifica questo messaggio: viene
    inviata come messaggio separato (vedi send_closure_message), in
    risposta a questo.
    state = {direction, entry, sl, tp3, ...}
    """
    text = HEADER_TEMPLATE.format(direction=state["direction"])
    text += ENTRY_LINE_TEMPLATE.format(entry=float(state["entry"]))

    if state.get("sl") is not None:
        text += SL_LINE_TEMPLATE.format(sl=float(state["sl"]))
    else:
        text += SL_PENDING_LINE

    if state.get("tp3") is not None:
        text += TP_LINE_TEMPLATE.format(value=float(state["tp3"]))
    else:
        text += TP_PENDING_LINE

    return text


async def copy_message_to_destination(state):
    text = format_trade_card(state)
    return await client.send_message(
        DESTINATION_CHAT,
        text,
        parse_mode="html",
        silent=True,
    )


async def edit_destination_message(destination_message_id, state):
    """Usata solo per correggere il messaggio principale (SL/TP rilanciati
    dal provider prima di qualunque BE/chiusura), non per gli aggiornamenti
    di stato del trade."""
    text = format_trade_card(state)
    try:
        await client.edit_message(
            DESTINATION_CHAT,
            destination_message_id,
            text=text,
            parse_mode="html",
        )
    except MessageNotModifiedError:
        return False
    return True


async def send_sl_moved_message(destination_message_id, new_sl):
    return await client.send_message(
        DESTINATION_CHAT,
        SL_MOVED_MESSAGE_TEMPLATE.format(sl=float(new_sl)),
        parse_mode="html",
        silent=True,
        reply_to=destination_message_id,
    )


async def send_closure_message(destination_message_id, reason, pips):
    pips = float(pips)
    if reason == "TP":
        text = CLOSED_TP_MESSAGE_TEMPLATE.format(pips=pips)
    elif reason == "SL":
        text = CLOSED_SL_MESSAGE_TEMPLATE.format(pips=pips)
    else:
        text = CLOSED_GENERIC_MESSAGE_TEMPLATE.format(pips=pips)
    return await client.send_message(
        DESTINATION_CHAT,
        text,
        parse_mode="html",
        silent=True,
        reply_to=destination_message_id,
    )


# ============================================================
# REPORT AUTOMATICI
# ============================================================

GOOD_MORNING_MESSAGE_TEMPLATE = (
    "☀️ <b>BUONGIORNO RAGAZZI</b> ☀️\n\n"
    "Una nuova giornata di trading sta per iniziare.\n\n"
    "Restate pronti e soprattutto disciplinati. 📊\n"
    "Ci sentiamo tra poco con le operazioni della giornata.\n"
    f"<b>- {BRAND_NAME}</b>"
)

DAILY_REPORT_TEMPLATE = (
    f"📊 <b>{BRAND_NAME} REPORT</b>\n"
    "💰 <b>RISULTATO GIORNALIERO</b>\n\n"
    "📅 {date}\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "Operazioni chiuse: {operations}\n"
    "✅ Vincenti: {wins}\n"
    "❌ Perse: {losses}\n"
    "📈 Win Rate: {win_rate:.1f}%\n"
    "📊 TOT {pips:+.0f} PIPS\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "Grazie per averci seguito!\n"
    "Ci sentiamo domani con altre operazioni.\n"
    f"<b>- {BRAND_NAME}</b>"
)

WEEKLY_REPORT_TEMPLATE = (
    f"📊 <b>{BRAND_NAME} REPORT</b>\n"
    "📅 <b>RISULTATO SETTIMANALE</b>\n\n"
    "📅 {date_range}\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "Operazioni chiuse: {operations}\n"
    "✅ Vincenti: {wins}\n"
    "❌ Perse: {losses}\n"
    "📈 Win Rate: {win_rate:.1f}%\n"
    "📊 TOT {pips:+.0f} PIPS\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "Grazie per averci seguito e supportato in questi giorni.\n"
    "Ci sentiamo lunedì con nuove operazioni.\n"
    "Buon weekend!\n"
    f"<b>- {BRAND_NAME}</b>"
)

MONTHLY_REPORT_TEMPLATE = (
    f"📊 <b>{BRAND_NAME} REPORT</b>\n"
    "📅 <b>RISULTATO MENSILE</b>\n\n"
    "📅 {date_range}\n"
    "━━━━━━━━━━━━━━━━━━\n\n"
    "Operazioni chiuse: {operations}\n"
    "✅ Vincenti: {wins}\n"
    "❌ Perse: {losses}\n"
    "📈 Win Rate: {win_rate:.1f}%\n"
    "📊 TOT {pips:+.0f} PIPS\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "Grazie per averci seguito e supportato in questo mese.\n"
    f"<b>- {BRAND_NAME}</b>"
)


async def send_good_morning_message():
    return await client.send_message(
        DESTINATION_CHAT, GOOD_MORNING_MESSAGE_TEMPLATE, parse_mode="html", silent=True,
    )


async def send_daily_report_message(**kwargs):
    return await client.send_message(
        DESTINATION_CHAT, DAILY_REPORT_TEMPLATE.format(**kwargs), parse_mode="html", silent=True,
    )


async def send_weekly_report_message(**kwargs):
    return await client.send_message(
        DESTINATION_CHAT, WEEKLY_REPORT_TEMPLATE.format(**kwargs), parse_mode="html", silent=True,
    )


async def send_monthly_report_message(**kwargs):
    return await client.send_message(
        DESTINATION_CHAT, MONTHLY_REPORT_TEMPLATE.format(**kwargs), parse_mode="html", silent=True,
    )
