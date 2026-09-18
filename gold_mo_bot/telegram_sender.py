from telethon.errors import MessageNotModifiedError
from telegram_client import client
from config import DESTINATION_CHAT

# ============================================================
# MESSAGGI - MODIFICA QUI I TESTI
# ============================================================

HEADER_TEMPLATE = "🟡 <b>XAUUSD — {direction}</b>\n\n"

ENTRY_LINE_TEMPLATE = "🟢 <b>ENTRY:</b> {entry:.2f}\n"
SL_LINE_TEMPLATE = "🛑 <b>STOP LOSS:</b> {sl:.2f}\n"
SL_PENDING_LINE = "🛑 <b>STOP LOSS:</b> in attesa...\n"

TP_LINE_TEMPLATE = "🎯 <b>TP{n}:</b> {value:.2f}{op_tag}\n"
TP_OPERATIVE_TAG = " ⬅️ operativo su MT5"

BE_LINE = "\n🟢 <b>BREAK EVEN ATTIVATO</b> (SL spostato all'entry)\n"

CLOSED_TP_LINE_TEMPLATE = "\n✅ <b>TAKE PROFIT RAGGIUNTO</b>\n📍 Chiusura: <b>{price:.2f}</b>\n"
CLOSED_SL_LINE_TEMPLATE = "\n🛑 <b>STOP LOSS PRESO</b>\n📍 Chiusura: <b>{price:.2f}</b>\n"
CLOSED_GENERIC_LINE_TEMPLATE = "\n⚪ <b>OPERAZIONE CHIUSA</b>\n📍 Chiusura: <b>{price:.2f}</b>\n"


def _format_tp_lines(state):
    lines = []
    for n, key in ((1, "tp1"), (2, "tp2"), (3, "tp3"), (4, "tp4")):
        value = state.get(key)
        if value is None:
            continue
        op_tag = TP_OPERATIVE_TAG if n == 3 else ""
        lines.append(TP_LINE_TEMPLATE.format(n=n, value=float(value), op_tag=op_tag))
    if state.get("tp_open_runner"):
        lines.append("🎯 <b>TP oltre TP3:</b> open (informativo)\n")
    return "".join(lines)


def format_trade_card(state):
    """
    Ricostruisce l'intero messaggio dallo stato corrente del trade.
    state = {
        direction, entry, sl, tp1, tp2, tp3, tp4, tp_open_runner,
        sltp_applied, breakeven_applied, closed, close_reason, close_price,
    }
    """
    text = HEADER_TEMPLATE.format(direction=state["direction"])
    text += ENTRY_LINE_TEMPLATE.format(entry=float(state["entry"]))

    if state.get("sl") is not None:
        text += SL_LINE_TEMPLATE.format(sl=float(state["sl"]))
    else:
        text += SL_PENDING_LINE

    text += _format_tp_lines(state)

    if state.get("breakeven_applied") and not state.get("closed"):
        text += BE_LINE

    if state.get("closed"):
        price = float(state.get("close_price") or 0.0)
        reason = state.get("close_reason")
        if reason == "TP":
            text += CLOSED_TP_LINE_TEMPLATE.format(price=price)
        elif reason == "SL":
            text += CLOSED_SL_LINE_TEMPLATE.format(price=price)
        else:
            text += CLOSED_GENERIC_LINE_TEMPLATE.format(price=price)

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
