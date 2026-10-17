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
# REPORT E BUONGIORNO
# ============================================================

DAILY_REPORT_TEMPLATE = (
    "📊 <b>YARDFX GOLD MORNING REPORT</b>\n"
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
    "<b>- YardFX</b>"
)

WEEKLY_REPORT_TEMPLATE = (
    "📊 <b>YARDFX GOLD MORNING REPORT</b>\n"
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
    "<b>- YardFX</b>"
)

MONTHLY_REPORT_TEMPLATE = (
    "📊 <b>YARDFX GOLD MORNING REPORT</b>\n"
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
    "<b>- YardFX</b>"
)

GOOD_MORNING_MESSAGE_TEMPLATE = (
    "☀️ <b>BUONGIORNO RAGAZZI</b> ☀️\n\n"

    "Una nuova giornata di trading sta per iniziare.\n\n"

    "📩 <b>Hai bisogno di assistenza?</b>\n"
    "Scrivimi in privato @yard_fx\n\n"

    "Restate pronti e soprattutto disciplinati. 📊\n"
    "Ci sentiamo tra poco con le operazioni della giornata.\n"
    "<b>- YardFX</b>"
)


# ============================================================
# COMANDI (Messaggi salvati)
# ============================================================

HELP_MESSAGE_TEMPLATE = (
    "📋 <b>COMANDI DISPONIBILI {name}</b>\n\n"
    "▶️ <b>{p}play</b> — Il bot riparte al 100%\n"
    "🛑 <b>{p}stop</b> — Chiude tutte le posizioni a mercato e ferma "
    "completamente il bot (niente più ascolto né messaggi nel canale)\n"
    "🔄 <b>{p}riavvio</b> — Come {p}stop e subito dopo come {p}play\n"
    "⏸️ <b>{p}pausa</b> — Non copia né apre nuovi trade, ma lascia gestite "
    "da MT5 le posizioni già aperte\n"
    "📊 <b>{p}status</b> — Stato attuale del bot + posizioni aperte con "
    "il profitto/perdita di ciascuna\n"
    "📈 <b>{p}report</b> — Invia subito nel canale il report giornaliero\n"
    "📅 <b>{p}reportw</b> — Invia subito nel canale il report settimanale\n"
    "🗓️ <b>{p}reportm</b> — Invia subito nel canale il report mensile\n"
    "❓ <b>{p}comandi</b> — Mostra questo elenco"
)

PLAY_MESSAGE_TEMPLATE = (
    "✅ <b>{name} ATTIVO AL 100%</b>\n"
    "Ascolto segnali e apro nuovi trade normalmente."
)

PAUSED_MESSAGE_TEMPLATE = (
    "⏸️ <b>{name} IN PAUSA</b>\n"
    "Nessun nuovo trade verrà aperto.\n"
    "Le posizioni già aperte continuano a essere gestite."
)

STOPPED_MESSAGE_TEMPLATE = (
    "🛑 <b>{name} FERMATO</b>\n"
    "Posizioni chiuse: {closed}\n"
    "{errors_line}"
    "Non ascolto più messaggi e non invio altro nel canale finché non ricevo {p}play."
)

RESTART_MESSAGE_TEMPLATE = (
    "🔄 <b>{name} RIAVVIATO</b>\n"
    "Posizioni chiuse: {closed}\n"
    "{errors_line}"
    "Di nuovo operativo al 100%: ascolto segnali e apro nuovi trade normalmente."
)


def bot_name(prefix):
    """Nome mostrato nei messaggi dei comandi: dal prefisso (bot3_ -> BOT3)."""
    return prefix.strip("_ ").upper() or "BOT"


def help_message(prefix):
    return HELP_MESSAGE_TEMPLATE.format(p=prefix, name=bot_name(prefix))


def play_message(prefix):
    return PLAY_MESSAGE_TEMPLATE.format(name=bot_name(prefix))


def paused_message(prefix):
    return PAUSED_MESSAGE_TEMPLATE.format(name=bot_name(prefix))


def _errors_line(errors):
    return f"⚠️ Errori chiusura: {errors}\n" if errors else ""


def stopped_message(prefix, closed, errors):
    return STOPPED_MESSAGE_TEMPLATE.format(
        name=bot_name(prefix), p=prefix, closed=closed, errors_line=_errors_line(errors),
    )


def restart_message(prefix, closed, errors):
    return RESTART_MESSAGE_TEMPLATE.format(
        name=bot_name(prefix), closed=closed, errors_line=_errors_line(errors),
    )
