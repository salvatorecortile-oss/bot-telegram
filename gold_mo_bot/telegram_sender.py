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

BE_LINE = "\n🟢 <b>BREAK EVEN ATTIVATO</b> (SL spostato all'entry)\n"

CLOSED_TP_LINE_TEMPLATE = "\n✅ <b>TAKE PROFIT RAGGIUNTO</b>\n📈 <b>{pips:+.0f} PIPS</b>\n"
CLOSED_SL_LINE_TEMPLATE = "\n🛑 <b>STOP LOSS</b>\n📉 <b>{pips:+.0f} PIPS</b>\n"
CLOSED_GENERIC_LINE_TEMPLATE = "\n⚪ <b>OPERAZIONE CHIUSA</b>\n📊 <b>{pips:+.0f} PIPS</b>\n"


def format_trade_card(state):
    """
    Ricostruisce l'intero messaggio dallo stato corrente del trade.
    Nel canale compaiono SOLO entry, SL e un unico TP (quello operativo
    su MT5, cioe' TP3): TP1/TP2/TP4/"open" restano interni al bot, non
    vengono mostrati. Alla chiusura si mostrano i PIPS, non il prezzo.
    state = {
        direction, entry, sl, tp1, tp2, tp3, tp4, tp_open_runner,
        sltp_applied, breakeven_applied, closed, close_reason, close_pips,
    }
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

    if state.get("breakeven_applied") and not state.get("closed"):
        text += BE_LINE

    if state.get("closed"):
        pips = float(state.get("close_pips") or 0.0)
        reason = state.get("close_reason")
        if reason == "TP":
            text += CLOSED_TP_LINE_TEMPLATE.format(pips=pips)
        elif reason == "SL":
            text += CLOSED_SL_LINE_TEMPLATE.format(pips=pips)
        else:
            text += CLOSED_GENERIC_LINE_TEMPLATE.format(pips=pips)

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
    "🟢 BE: {breakeven}\n\n"
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
    "🟢 BE: {breakeven}\n\n"
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
    "🟢 BE: {breakeven}\n\n"
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
