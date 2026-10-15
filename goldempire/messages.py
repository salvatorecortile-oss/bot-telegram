"""
Testi dei messaggi pubblicati nel canale di destinazione.
Stesso stile dei messaggi degli altri bot: modifica qui i testi.
"""
from html import escape


OPEN_TRADE_MESSAGE_TEMPLATE = (
    "👑 <b>XAUUSD — {direction}</b>\n\n"
    "🟢 <b>ENTRY:</b> {entry:.2f}\n"
    "🛑 <b>STOP LOSS:</b> {sl:.2f}\n"
    "🎯 <b>TAKE PROFIT:</b> {tp:.2f}"
)

TAKE_PROFIT_MESSAGE_TEMPLATE = (
    "🟢 <b>TAKE PROFIT RAGGIUNTO!</b>\n"
    "✅ <b>OPERAZIONE CHIUSA</b>\n\n"
    "📈 <b>PIPS TOTALI: {pips}</b>"
)

BE_APPLIED_MESSAGE_TEMPLATE = (
    "🟢 <b>BE ATTIVATO</b>\n"
    "🛡️ Stop Loss spostato a <b>{sl:.2f}</b>"
)

BREAKEVEN_SL_HIT_MESSAGE_TEMPLATE = (
    "🟢 <b>BE PRESO</b>\n"
    "📍 Prezzo di chiusura: <b>{price:.2f}</b>\n"
    "✅ <b>OPERAZIONE CHIUSA</b>"
)

SL_HIT_MESSAGE_TEMPLATE = (
    "🛑 <b>STOP LOSS PRESO</b>\n"
    "📉 <b>{pips} PIPS</b>"
)

CLOSED_PROFIT_MESSAGE_TEMPLATE = (
    "✅ <b>OPERAZIONE CHIUSA IN PROFITTO</b>\n"
    "📈 <b>{pips} PIPS</b>"
)

CLOSED_LOSS_MESSAGE_TEMPLATE = (
    "❌ <b>OPERAZIONE CHIUSA IN PERDITA</b>\n"
    "📉 <b>{pips} PIPS</b>"
)

# Sotto questa soglia (in pips, in valore assoluto) una chiusura per stop
# dopo il BE viene comunicata come "BE PRESO".
BREAKEVEN_TOLERANCE_PIPS = 20.0


def format_signed_pips(value):
    value = round(float(value))
    if value == 0:
        return "0"
    return f"{value:+d}"


def format_open_message(direction, entry, sl, tp):
    return OPEN_TRADE_MESSAGE_TEMPLATE.format(
        direction=escape(str(direction).upper()),
        entry=float(entry),
        sl=float(sl),
        tp=float(tp),
    )


def format_be_applied_message(sl):
    return BE_APPLIED_MESSAGE_TEMPLATE.format(sl=float(sl))


def format_close_message(close_status, pips, close_price):
    """
    close_status: CLOSED_TP, CLOSED_SL, CLOSED_BE, CLOSED_MANUAL, CLOSED_EXTERNAL.
    """
    if close_status == "CLOSED_TP":
        return TAKE_PROFIT_MESSAGE_TEMPLATE.format(pips=format_signed_pips(pips))
    if close_status == "CLOSED_BE":
        return BREAKEVEN_SL_HIT_MESSAGE_TEMPLATE.format(price=float(close_price))
    if close_status == "CLOSED_SL":
        return SL_HIT_MESSAGE_TEMPLATE.format(pips=format_signed_pips(pips))
    if float(pips) >= 0:
        return CLOSED_PROFIT_MESSAGE_TEMPLATE.format(pips=format_signed_pips(pips))
    return CLOSED_LOSS_MESSAGE_TEMPLATE.format(pips=format_signed_pips(pips))


def classify_stop_close(pips, be_applied):
    """Chiusura per stop: BE PRESO se il BE era attivo e il risultato e' ~0."""
    if be_applied and abs(float(pips)) <= BREAKEVEN_TOLERANCE_PIPS:
        return "CLOSED_BE"
    return "CLOSED_SL"


def calculate_pips(open_price, close_price, direction, pip_size):
    if not pip_size or pip_size <= 0:
        return 0.0
    diff = float(close_price) - float(open_price)
    if str(direction).upper() == "SELL":
        diff = -diff
    return diff / float(pip_size)


# ============================================================
# COMANDI (Messaggi salvati)
# ============================================================

def help_message(prefix):
    return (
        "📋 <b>COMANDI BOT GOLD EMPIRE</b>\n\n"
        f"▶️ <b>{prefix}play</b> — Il bot riparte al 100%\n"
        f"⏸️ <b>{prefix}pausa</b> — Non apre nuovi trade, gestisce quelli aperti\n"
        f"🛑 <b>{prefix}stop</b> — Chiude tutte le posizioni del bot e si ferma\n"
        f"📊 <b>{prefix}status</b> — Stato del bot e posizioni aperte\n"
        f"❓ <b>{prefix}comandi</b> — Mostra questo elenco"
    )
