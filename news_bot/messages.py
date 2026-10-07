"""
Testi dei messaggi pubblicati nel canale.
Per cambiare lo stile dei messaggi basta modificare questo file.
"""
from html import escape as _html_escape

from feeds import CATEGORY_LABELS

GIORNI = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]

FRASI_BUONGIORNO = [
    "Disciplina e pazienza: le due armi migliori del trader. 💪",
    "Ogni giorno è una nuova opportunità. Restiamo concentrati! 🎯",
    "Prima si studia il mercato, poi si agisce. Buona giornata! 📊",
    "Il mercato premia chi sa aspettare. ⏳",
    "Gestione del rischio prima di tutto. Buona giornata a tutti! 🛡️",
    "Un passo alla volta, con costanza. 🚀",
    "Mente lucida e piano chiaro: si parte! ☕",
]


def escape(text, quote=False):
    # Gli apostrofi restano leggibili; le virgolette vanno escapate solo nei link.
    return _html_escape(text, quote=quote)


def format_date(now):
    return f"{GIORNI[now.weekday()]} {now.day} {MESI[now.month - 1]} {now.year}"


def _link(title, url):
    if url:
        return f'<a href="{escape(url, quote=True)}">{escape(title)}</a>'
    return escape(title)


def format_alert(level, category, title_it, summary_it, source, num_sources, link):
    """Notizia importante inviata subito."""
    if level == "critical":
        header = "🚨 <b>ULTIM'ORA</b>"
    else:
        header = "⚡️ <b>NOTIZIA IMPORTANTE</b>"
    label = CATEGORY_LABELS.get(category, "📰 Notizie")

    lines = [f"{header} · {label}", "", f"<b>{escape(title_it)}</b>"]
    if summary_it:
        lines += ["", escape(summary_it)]
    fonte = f"📰 Fonte: {escape(source)}"
    if num_sources > 1:
        fonte += f" (confermata da {num_sources} fonti)"
    lines += ["", fonte]
    if link:
        lines.append(f'🔗 <a href="{escape(link, quote=True)}">Leggi la notizia</a>')
    return "\n".join(lines)


def format_morning(now, recap):
    """
    Messaggio del buongiorno + riepilogo.
    recap = lista di dict con: category, title_it, source, link
    """
    frase = FRASI_BUONGIORNO[now.timetuple().tm_yday % len(FRASI_BUONGIORNO)]
    lines = [
        "☀️ <b>Buongiorno Community!</b>",
        f"📅 {format_date(now)}",
        "",
        frase,
        "",
    ]
    if not recap:
        lines.append("📰 Nessuna notizia di rilievo nelle ultime 24 ore: notte tranquilla sui mercati.")
    else:
        lines.append("📰 <b>Le notizie più importanti delle ultime 24 ore</b>")
        for category in ("oro", "macro", "geopolitica", "mondo"):
            group = [r for r in recap if r["category"] == category]
            if not group:
                continue
            lines += ["", f"<b>{CATEGORY_LABELS[category]}</b>"]
            for r in group:
                lines.append(f"• {_link(r['title_it'], r['link'])} <i>({escape(r['source'])})</i>")
    lines += ["", "Buona giornata a tutti! 🚀"]
    return "\n".join(lines)


def split_message(text, limit=4000):
    """Telegram accetta al massimo 4096 caratteri: divide sulle righe."""
    parts, current = [], ""
    for line in text.split("\n"):
        if current and len(current) + len(line) + 1 > limit:
            parts.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        parts.append(current)
    return parts
