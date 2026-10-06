"""
Fonti delle notizie.

Sono le stesse fonti RSS che usa World Monitor (worldmonitor.app), prese dal
suo codice open source (src/config/feeds.ts). Il bot le legge direttamente,
senza passare dal sito.

Ogni fonte ha:
- name: nome mostrato nel messaggio
- url: indirizzo del feed RSS
- tier: affidabilità come in World Monitor
        1 = agenzie e fonti ufficiali (Reuters, AP, Fed...)
        2 = grandi testate (BBC, CNN, CNBC...)
        3 = fonti specializzate
        4 = aggregatori
- category: "oro", "macro", "geopolitica" oppure "mondo"

Per aggiungere o togliere una fonte basta modificare la lista FEEDS.
"""
from urllib.parse import quote_plus


def google_news(query):
    """Feed di Google News per una ricerca (come fa World Monitor)."""
    return (
        "https://news.google.com/rss/search?q="
        + quote_plus(query)
        + "&hl=en-US&gl=US&ceid=US:en"
    )


FEEDS = [
    # ---------- ORO E METALLI ----------
    {"name": "Gold & Metals", "tier": 2, "category": "oro",
     "url": google_news('(gold price OR "spot gold" OR "gold futures" OR XAUUSD OR bullion) when:1d')},
    {"name": "Kitco News", "tier": 2, "category": "oro",
     "url": google_news("site:kitco.com (gold OR silver OR metals) when:1d")},
    {"name": "Reuters Gold", "tier": 1, "category": "oro",
     "url": google_news("site:reuters.com gold when:1d")},

    # ---------- MACRO / BANCHE CENTRALI ----------
    {"name": "Federal Reserve", "tier": 1, "category": "macro",
     "url": "https://www.federalreserve.gov/feeds/press_all.xml"},
    {"name": "Central Bank Rates", "tier": 2, "category": "macro",
     "url": google_news('("central bank" OR "interest rate" OR "rate decision" OR "monetary policy") when:1d')},
    {"name": "ECB Watch", "tier": 2, "category": "macro",
     "url": google_news('("European Central Bank" OR ECB OR Lagarde) monetary policy when:1d')},
    {"name": "Economic Data", "tier": 2, "category": "macro",
     "url": google_news('(CPI OR inflation OR GDP OR "jobs report" OR "nonfarm payrolls" OR PMI) when:1d')},
    {"name": "Trade & Tariffs", "tier": 2, "category": "macro",
     "url": google_news('(tariff OR "trade war" OR sanctions) when:1d')},
    {"name": "Dollar Watch", "tier": 2, "category": "macro",
     "url": google_news('("dollar index" OR DXY OR "US dollar") when:1d')},
    {"name": "Treasury Watch", "tier": 2, "category": "macro",
     "url": google_news('("Treasury yields" OR "10-year yield" OR "bond market") when:1d')},
    {"name": "Reuters Business", "tier": 1, "category": "macro",
     "url": google_news("site:reuters.com business markets when:1d")},
    {"name": "CNBC", "tier": 2, "category": "macro",
     "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
    {"name": "Financial Times", "tier": 2, "category": "macro",
     "url": "https://www.ft.com/rss/home"},
    {"name": "Oil & Gas", "tier": 2, "category": "macro",
     "url": google_news('(oil price OR OPEC OR "crude oil" OR Brent OR WTI) when:1d')},

    # ---------- GEOPOLITICA ----------
    {"name": "Reuters World", "tier": 1, "category": "geopolitica",
     "url": google_news("site:reuters.com world when:1d")},
    {"name": "AP News", "tier": 1, "category": "geopolitica",
     "url": google_news("site:apnews.com when:1d")},
    {"name": "BBC Middle East", "tier": 2, "category": "geopolitica",
     "url": "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"},
    {"name": "Al Jazeera", "tier": 2, "category": "geopolitica",
     "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "Guardian World", "tier": 2, "category": "geopolitica",
     "url": "https://www.theguardian.com/world/rss"},
    {"name": "CrisisWatch", "tier": 3, "category": "geopolitica",
     "url": "https://www.crisisgroup.org/rss"},
    {"name": "IAEA", "tier": 1, "category": "geopolitica",
     "url": "https://www.iaea.org/feeds/topnews"},

    # ---------- MONDO ----------
    {"name": "BBC World", "tier": 2, "category": "mondo",
     "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "CNN World", "tier": 2, "category": "mondo",
     "url": google_news("site:cnn.com world news when:1d")},
    {"name": "WHO", "tier": 1, "category": "mondo",
     "url": "https://www.who.int/rss-feeds/news-english.xml"},
]

CATEGORY_LABELS = {
    "oro": "🥇 Oro",
    "macro": "🏦 Macro",
    "geopolitica": "🌍 Geopolitica",
    "mondo": "📰 Mondo",
}
