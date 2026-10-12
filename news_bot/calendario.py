"""
Calendario economico della settimana (solo USD), pubblicato ogni lunedì.

I dati arrivano dal calendario gratuito di ForexFactory:
    https://nfs.faireconomy.media/ff_calendar_thisweek.json
Per ogni evento: titolo, valuta, data/ora, impatto (High/Medium/Low/Holiday),
previsione e dato precedente.

Per cambiare testi ed emoji del messaggio: modifica NOMI_ITALIANI,
SPIEGAZIONI e la funzione format_calendar() qui sotto.
"""
import logging
import re
from datetime import datetime
from html import escape as _html_escape
from zoneinfo import ZoneInfo

import requests

import config
from messages import GIORNI, MESI

log = logging.getLogger("news_bot")

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
TZ = ZoneInfo(config.TIMEZONE)


def escape(text):
    return _html_escape(text, quote=False)


# ---------- Nomi in italiano dei dati più comuni ----------
NOMI_ITALIANI = {
    "CPI m/m": "CPI (inflazione USA) mensile",
    "CPI y/y": "CPI (inflazione USA) annuale",
    "Core CPI m/m": "CPI core (inflazione di fondo) mensile",
    "Core CPI y/y": "CPI core (inflazione di fondo) annuale",
    "PPI m/m": "PPI (prezzi alla produzione) mensile",
    "Core PPI m/m": "PPI core (prezzi alla produzione) mensile",
    "Core PCE Price Index m/m": "PCE core (inflazione preferita dalla Fed) mensile",
    "PCE Price Index m/m": "PCE (inflazione) mensile",
    "Non-Farm Employment Change": "NFP – Nuovi posti di lavoro (Non-Farm Payrolls)",
    "ADP Non-Farm Employment Change": "ADP – Nuovi posti di lavoro nel settore privato",
    "Unemployment Rate": "Tasso di disoccupazione",
    "Unemployment Claims": "Richieste settimanali di sussidi di disoccupazione",
    "Average Hourly Earnings m/m": "Salari orari medi mensili",
    "JOLTS Job Openings": "JOLTS – Posti di lavoro disponibili",
    "Employment Cost Index q/q": "Indice del costo del lavoro trimestrale",
    "Federal Funds Rate": "Decisione della Fed sui tassi di interesse",
    "FOMC Statement": "Comunicato della Fed (FOMC)",
    "FOMC Press Conference": "Conferenza stampa della Fed (Powell)",
    "FOMC Meeting Minutes": "Verbali della riunione Fed (FOMC Minutes)",
    "FOMC Economic Projections": "Proiezioni economiche della Fed",
    "Fed Chair Powell Speaks": "Discorso di Powell (presidente Fed)",
    "Advance GDP q/q": "PIL USA trimestrale (prima stima)",
    "Prelim GDP q/q": "PIL USA trimestrale (stima preliminare)",
    "Final GDP q/q": "PIL USA trimestrale (stima finale)",
    "Advance GDP Price Index q/q": "Deflatore del PIL (prima stima)",
    "Retail Sales m/m": "Vendite al dettaglio mensili",
    "Core Retail Sales m/m": "Vendite al dettaglio core mensili",
    "ISM Manufacturing PMI": "ISM manifatturiero",
    "ISM Services PMI": "ISM servizi",
    "ISM Manufacturing Prices": "ISM manifatturiero – prezzi",
    "Flash Manufacturing PMI": "PMI manifatturiero (stima flash)",
    "Flash Services PMI": "PMI servizi (stima flash)",
    "Final Manufacturing PMI": "PMI manifatturiero (finale)",
    "Final Services PMI": "PMI servizi (finale)",
    "Empire State Manufacturing Index": "Indice manifatturiero di New York (Empire State)",
    "Philly Fed Manufacturing Index": "Indice manifatturiero di Philadelphia",
    "Durable Goods Orders m/m": "Ordini di beni durevoli mensili",
    "Core Durable Goods Orders m/m": "Ordini di beni durevoli core mensili",
    "CB Consumer Confidence": "Fiducia dei consumatori (Conference Board)",
    "Prelim UoM Consumer Sentiment": "Fiducia dei consumatori Univ. Michigan (preliminare)",
    "Revised UoM Consumer Sentiment": "Fiducia dei consumatori Univ. Michigan (finale)",
    "Prelim UoM Inflation Expectations": "Aspettative di inflazione Univ. Michigan (preliminare)",
    "Revised UoM Inflation Expectations": "Aspettative di inflazione Univ. Michigan (finale)",
    "Industrial Production m/m": "Produzione industriale mensile",
    "Building Permits": "Permessi di costruzione",
    "Housing Starts": "Nuovi cantieri edilizi",
    "Existing Home Sales": "Vendite di case esistenti",
    "New Home Sales": "Vendite di nuove case",
    "Pending Home Sales m/m": "Vendite di case in corso mensili",
    "Trade Balance": "Bilancia commerciale",
    "Personal Spending m/m": "Spesa personale mensile",
    "Personal Income m/m": "Reddito personale mensile",
    "Crude Oil Inventories": "Scorte di petrolio (EIA)",
    "Natural Gas Storage": "Scorte di gas naturale",
    "Federal Budget Balance": "Saldo del bilancio federale",
    "10-y Bond Auction": "Asta dei titoli di Stato a 10 anni",
    "30-y Bond Auction": "Asta dei titoli di Stato a 30 anni",
    "Bank Holiday": "Festività: banche USA chiuse",
}

# ---------- Cosa succede di solito a dollaro e oro ----------
_SOPRA_DOLLARO_SU = ("Sopra le attese: dollaro più forte, oro sotto pressione.\n"
                     "     Sotto le attese: dollaro più debole, spinta per l'oro.")
_SOPRA_DOLLARO_GIU = ("Sopra le attese: dollaro più debole, spinta per l'oro.\n"
                      "     Sotto le attese: dollaro più forte, oro sotto pressione.")
_TONI = ("Più restrittivo delle attese: dollaro più forte, oro sotto pressione.\n"
         "     Più accomodante delle attese: dollaro più debole, spinta per l'oro.")
_TASSI = ("Tassi sopra le attese: dollaro più forte, oro sotto pressione.\n"
          "     Tassi sotto le attese: dollaro più debole, spinta per l'oro.")

SPIEGAZIONI = [
    # (parole nel titolo originale, spiegazione) — vince la prima che corrisponde
    (r"unemployment rate|unemployment claims", _SOPRA_DOLLARO_GIU),
    (r"federal funds rate|fomc statement|economic projections", _TASSI),
    (r"press conference|minutes|speaks|testifies", _TONI),
    (r"cpi|ppi|pce|price index|inflation expectations|earnings|cost index", _SOPRA_DOLLARO_SU),
    (r"employment|payroll|jolts|gdp|retail sales|pmi|ism|manufacturing|durable|"
     r"confidence|sentiment|production|spending|income|housing|home sales|permits",
     _SOPRA_DOLLARO_SU),
    (r"crude oil inventories",
     "Scorte più alte delle attese: petrolio giù. Più basse: petrolio su."),
]

IMPATTO_ALTO = "High"
IMPATTO_MEDIO = "Medium"
FESTIVITA = "Holiday"


def italian_name(title):
    if title in NOMI_ITALIANI:
        return NOMI_ITALIANI[title]
    m = re.match(r"FOMC Member (.+) Speaks", title)
    if m:
        return f"Discorso di {m.group(1)} (membro Fed)"
    return title


def explanation(title):
    lower = title.lower()
    for pattern, text in SPIEGAZIONI:
        if re.search(pattern, lower):
            return text
    return ""


def _number(value):
    """'0.3%' -> '0,3%' (formato italiano)."""
    return re.sub(r"(\d)\.(\d)", r"\1,\2", value or "")


def fetch_calendar(url=CALENDAR_URL, timeout=20):
    response = requests.get(url, timeout=timeout,
                            headers={"User-Agent": "Mozilla/5.0 news-bot"})
    response.raise_for_status()
    return response.json()


def usd_events(raw_events):
    """Solo USD con impatto alto/medio (più le festività), in orario italiano."""
    events = []
    for ev in raw_events:
        if ev.get("country") != "USD":
            continue
        impact = ev.get("impact")
        if impact not in (IMPATTO_ALTO, IMPATTO_MEDIO, FESTIVITA):
            continue
        try:
            when = datetime.fromisoformat(ev["date"]).astimezone(TZ)
        except (KeyError, ValueError):
            continue
        events.append({
            "title": ev.get("title", ""),
            "impact": impact,
            "when": when,
            "forecast": (ev.get("forecast") or "").strip(),
            "previous": (ev.get("previous") or "").strip(),
        })
    events.sort(key=lambda e: e["when"])
    return events


def _day(when):
    return f"{GIORNI[when.weekday()]} {when.day}"


def _week_range(events, now):
    if events:
        first, last = events[0]["when"], events[-1]["when"]
    else:
        first = last = now
    if first.month == last.month:
        return f"{first.day} – {last.day} {MESI[last.month - 1]} {last.year}"
    return f"{first.day} {MESI[first.month - 1]} – {last.day} {MESI[last.month - 1]} {last.year}"


def format_calendar(events, now):
    """Messaggio del lunedì (HTML per Telegram)."""
    high = [e for e in events if e["impact"] == IMPATTO_ALTO]
    other = [e for e in events if e["impact"] != IMPATTO_ALTO]

    lines = [
        "📅 <b>CALENDARIO ECONOMICO DELLA SETTIMANA</b> 🇺🇸",
        f"<i>{_week_range(events, now)} · orari italiani</i>",
    ]

    if not events:
        lines += ["", "Nessun dato importante sul dollaro in programma questa settimana."]
        return "\n".join(lines)

    lines += ["", "🔴 <b>GLI APPUNTAMENTI PIÙ IMPORTANTI</b>"]
    if not high:
        lines += ["", "Nessun dato ad alto impatto questa settimana."]
    previous_key = None
    for e in high:
        lines += ["", f"• <b>{_day(e['when'])} ore {e['when']:%H:%M}</b> · {escape(italian_name(e['title']))}"]
        numbers = []
        if e["forecast"]:
            numbers.append(f"Previsione {escape(_number(e['forecast']))}")
        if e["previous"]:
            numbers.append(f"Precedente {escape(_number(e['previous']))}")
        if numbers:
            lines.append("  " + " · ".join(numbers))
        text = explanation(e["title"])
        # Dati usciti alla stessa ora con la stessa spiegazione (es. CPI e CPI core):
        # la spiegazione si scrive una volta sola.
        key = (e["when"], text)
        if text and key != previous_key:
            lines.append(f"  ➜ {escape(text)}")
        previous_key = key

    if other:
        lines += ["", "🟠 <b>GLI ALTRI DATI DELLA SETTIMANA</b>"]
        current_day = None
        for e in other:
            day = _day(e["when"])
            if day != current_day:
                lines += ["", f"<b>{day}</b>"]
                current_day = day
            if e["impact"] == FESTIVITA:
                lines.append(f"  🏦 {escape(italian_name(e['title']))}")
            else:
                lines.append(f"  {e['when']:%H:%M} · {escape(italian_name(e['title']))}")

    lines += ["", "Buona settimana di trading a tutti! 📈"]
    return "\n".join(lines)


def build_weekly_message(now=None):
    now = now or datetime.now(TZ)
    return format_calendar(usd_events(fetch_calendar()), now)
