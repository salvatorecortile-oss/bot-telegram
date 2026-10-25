"""
Testi dei messaggi pubblicati nella sala segnali: modifica qui i testi.
"""
from html import escape


# ============================================================
# TP / SL CAMBIATI SU MT5
# Il bot li rileva da solo e risponde al messaggio del segnale nel canale.
# {tp} e {sl} sono il nuovo prezzo: lasciali tra le graffe.
# ============================================================

# TP spostato
TP_UPDATED_MESSAGE_TEMPLATE = (
    "🎯 <b>TP IMPOSTATO A {tp:.2f}</b>"
)

# TP tolto
TP_REMOVED_MESSAGE_TEMPLATE = (
    "🎯 <b>TP RIMOSSO</b>\n"
    "Chiusura a segnale."
)

# SL spostato ma ancora in perdita (es. avvicinato al prezzo)
SL_UPDATED_MESSAGE_TEMPLATE = (
    "🛡️ <b>STOP LOSS IMPOSTATO A {sl:.2f}</b>"
)

# SL spostato di nuovo quando e' gia' in profitto (dopo il BE)
SL_PROFIT_UPDATED_MESSAGE_TEMPLATE = (
    "🛡️ <b>STOP LOSS IN PROFITTO A {sl:.2f}</b>"
)

# SL tolto
SL_REMOVED_MESSAGE_TEMPLATE = (
    "⚠️ <b>STOP LOSS RIMOSSO</b>"
)

# La prima volta che lo SL viene portato all'ingresso o in profitto si usa
# BE_APPLIED_MESSAGE_TEMPLATE (vedi sotto, "BE ATTIVATO").


OPEN_TRADE_MESSAGE_TEMPLATE = (
    "👑 <b>{symbol} — {direction}</b>\n\n"
    "🟢 <b>ENTRY:</b> {entry:.2f}\n"
    "🛑 <b>STOP LOSS:</b> {sl:.2f}\n"
    "🎯 <b>TAKE PROFIT:</b> {tp:.2f}"
)

# Operazioni senza TP su MT5: le chiude il bot quando e' il momento.
OPEN_TRADE_NO_TP_MESSAGE_TEMPLATE = (
    "👑 <b>{symbol} — {direction}</b>\n\n"
    "🟢 <b>ENTRY:</b> {entry:.2f}\n"
    "🛑 <b>STOP LOSS:</b> {sl:.2f}\n"
    "🎯 <b>TAKE PROFIT:</b> chiusura a segnale"
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


def format_open_message(symbol, direction, entry, sl, tp):
    if not tp:
        return OPEN_TRADE_NO_TP_MESSAGE_TEMPLATE.format(
            symbol=escape(str(symbol)),
            direction=escape(str(direction).upper()),
            entry=float(entry),
            sl=float(sl),
        )
    return OPEN_TRADE_MESSAGE_TEMPLATE.format(
        symbol=escape(str(symbol)),
        direction=escape(str(direction).upper()),
        entry=float(entry),
        sl=float(sl),
        tp=float(tp),
    )


def format_tp_updated_message(tp):
    if not tp:
        return TP_REMOVED_MESSAGE_TEMPLATE
    return TP_UPDATED_MESSAGE_TEMPLATE.format(tp=float(tp))


def format_sl_updated_message(sl, in_profit):
    if not sl:
        return SL_REMOVED_MESSAGE_TEMPLATE
    if in_profit:
        return SL_PROFIT_UPDATED_MESSAGE_TEMPLATE.format(sl=float(sl))
    return SL_UPDATED_MESSAGE_TEMPLATE.format(sl=float(sl))


def format_be_applied_message(sl):
    return BE_APPLIED_MESSAGE_TEMPLATE.format(sl=float(sl))


def format_close_message(close_status, pips, close_price):
    """
    close_status: CLOSED_TP, CLOSED_SL, CLOSED_BE, CLOSED_EXTERNAL.
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
# REPORT E BUONGIORNO
# ============================================================

DAILY_REPORT_TEMPLATE = (
    "📊 <b>KAIROS TRADING BOT REPORT</b>\n"
    "💰 <b>RISULTATO GIORNALIERO</b>\n\n"

    "📅 {date}\n"
    "━━━━━━━━━━━━━━━━━━\n\n"

    "Operazioni chiuse: {operations}\n"
    "✅ Vincenti: {wins}\n"
    "❌ Perse: {losses}\n\n"

    "📈 Win Rate: {win_rate:.1f}%\n"
    "📊 TOT {pips:+.0f} PIPS\n\n"

    "━━━━━━━━━━━━━━━━━━\n"
    "Grazie per averci seguito!\n"
    "Ci sentiamo domani con altre operazioni.\n"
    "<b>- Kairos Trading Bot</b>"
)

WEEKLY_REPORT_TEMPLATE = (
    "📊 <b>KAIROS TRADING BOT REPORT</b>\n"
    "📅 <b>RISULTATO SETTIMANALE</b>\n\n"

    "📅 {date_range}\n"
    "━━━━━━━━━━━━━━━━━━\n\n"

    "Operazioni chiuse: {operations}\n"
    "✅ Vincenti: {wins}\n"
    "❌ Perse: {losses}\n\n"

    "📈 Win Rate: {win_rate:.1f}%\n"
    "📊 TOT {pips:+.0f} PIPS\n\n"

    "━━━━━━━━━━━━━━━━━━\n"
    "Grazie per averci seguito e supportato in questi giorni.\n"
    "Ci sentiamo lunedì con nuove operazioni.\n"
    "Buon weekend!\n"
    "<b>- Kairos Trading Bot</b>"
)

MONTHLY_REPORT_TEMPLATE = (
    "📊 <b>KAIROS TRADING BOT REPORT</b>\n"
    "📅 <b>RISULTATO MENSILE</b>\n\n"

    "📅 {date_range}\n"
    "━━━━━━━━━━━━━━━━━━\n\n"

    "Operazioni chiuse: {operations}\n"
    "✅ Vincenti: {wins}\n"
    "❌ Perse: {losses}\n\n"

    "📈 Win Rate: {win_rate:.1f}%\n"
    "📊 TOT {pips:+.0f} PIPS\n\n"

    "━━━━━━━━━━━━━━━━━━\n"
    "Grazie per averci seguito e supportato in questo mese.\n"
    "<b>- Kairos Trading Bot</b>"
)

GOOD_MORNING_MESSAGE_TEMPLATE = (
    "☀️ <b>BUONGIORNO RAGAZZI</b> ☀️\n\n"

    "Una nuova giornata di trading sta per iniziare.\n\n"

    "📩 <b>Hai bisogno di assistenza?</b>\n"
    "Scrivimi in privato @yard_fx\n\n"

    "Restate pronti e soprattutto disciplinati. 📊\n"
    "Ci sentiamo tra poco con le operazioni della giornata.\n"
    "<b>- Kairos Trading Bot</b>"
)


# ============================================================
# COMANDI (Messaggi salvati)
# ============================================================

HELP_MESSAGE_TEMPLATE = (
    "📋 <b>COMANDI SALA SEGNALI</b>\n\n"
    "▶️ <b>{p}play</b> — Pubblica di nuovo le operazioni nel canale\n"
    "⏸️ <b>{p}pausa</b> — Smette di pubblicare: le operazioni aperte nel frattempo "
    "non vengono pubblicate (MT5 continua a lavorare normalmente)\n"
    "📊 <b>{p}status</b> — Stato della sala + posizioni aperte con il profitto/perdita di ciascuna\n"
    "📈 <b>{p}report</b> — Invia subito nel canale il report giornaliero\n"
    "📅 <b>{p}reportw</b> — Invia subito nel canale il report settimanale\n"
    "🗓️ <b>{p}reportm</b> — Invia subito nel canale il report mensile\n"
    "❓ <b>{p}comandi</b> — Mostra questo elenco"
)

PLAY_MESSAGE_TEMPLATE = (
    "✅ <b>SALA SEGNALI ATTIVA</b>\n"
    "Le nuove operazioni di MT5 vengono pubblicate nel canale."
)

PAUSED_MESSAGE_TEMPLATE = (
    "⏸️ <b>SALA SEGNALI IN PAUSA</b>\n"
    "Le nuove operazioni non vengono pubblicate.\n"
    "Quelle già pubblicate continuano a ricevere gli aggiornamenti."
)


def help_message(prefix):
    return HELP_MESSAGE_TEMPLATE.format(p=prefix)
