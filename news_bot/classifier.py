"""
Filtro di importanza delle notizie.

È la versione Python del classificatore a parole chiave di World Monitor
(shared/threat-keyword-classifier.ts): ogni titolo riceve un livello
critical / high / medium / low / info.

In più ci sono parole chiave per oro e macro (Fed, CPI, payrolls...),
perché sono le notizie che interessano la community.

Il punteggio finale (score) somma:
- il livello della notizia
- l'affidabilità della fonte (tier)
- quante fonti diverse riportano la stessa notizia (conferme)
- un bonus se parla di oro
"""
import re

CRITICAL = [
    # --- da World Monitor ---
    "nuclear strike", "nuclear attack", "nuclear war", "invasion",
    "declaration of war", "declares war", "declared war", "all-out war",
    "full-scale war", "martial law", "coup", "genocide", "ethnic cleansing",
    "chemical attack", "biological attack", "dirty bomb", "mass casualty",
    "massive strikes", "military strikes", "retaliatory strikes",
    "launches strikes", "strikes on iran", "strikes iran", "attack on iran",
    "attacks iran", "attack iran", "bombs iran", "war with iran", "war on iran",
    "iran retaliates", "iran strikes", "iran launches", "iran attacks",
    "pandemic declared", "health emergency", "nato article 5",
    "nuclear meltdown", "major combat operations",
    # --- oro / macro ---
    "emergency rate cut", "emergency rate hike", "emergency meeting",
    "fed cuts rates", "fed cuts interest rates", "fed raises rates",
    "fed raises interest rates", "fed hikes rates", "fed hikes interest rates",
    "gold hits record", "gold record high", "gold hits all-time high",
    "gold all-time high", "record high for gold", "gold tops $",
    "bank run", "bank collapse", "debt default", "stock market crash",
    "flash crash", "powell resigns", "powell fired", "fires powell",
]

HIGH = [
    # --- da World Monitor ---
    "armed conflict", "airstrike", "airstrikes", "air strike",
    "air strikes", "drone strike", "drone strikes", "missile", "missiles",
    "troops deployed", "military escalation", "military operation",
    "ground offensive", "bombing", "bombardment", "shelling", "casualties",
    "killed in", "hostage", "terrorist", "terror attack", "assassination",
    "cyber attack", "cyberattack", "earthquake",
    "tsunami", "hurricane", "typhoon", "strike on", "strikes on", "attack on",
    "attacks on", "launched attack", "launches attack", "explosions",
    "retaliatory strike", "retaliatory attack", "preemptive strike",
    "military offensive", "ballistic missile", "cruise missile",
    # --- oro / macro ---
    "powell", "us cpi", "u.s. cpi", "cpi data", "cpi report", "core cpi",
    "consumer price index", "nonfarm payrolls", "jobs report", "core pce",
    "pce inflation", "gold surges", "gold soars", "gold jumps", "gold plunges",
    "gold tumbles", "gold slumps", "gold crashes", "gold rallies",
    "gold sinks", "gold spikes", "opec cut", "government shutdown",
    "debt ceiling", "new tariffs", "tariffs on",
]

# Decisioni di Fed e BCE (le parole possono non essere vicine nel titolo).
HIGH_REGEX = [
    re.compile(r"\b(fed|federal reserve|fomc|ecb|european central bank)\b.*"
               r"\b(cuts?|hikes?|raises?|holds?|keeps?|leaves?|pauses?|decision)\b"),
]

MEDIUM = [
    "protest", "protests", "riot", "riots", "unrest", "military exercise",
    "naval exercise", "arms deal", "diplomatic crisis", "ambassador recalled",
    "expel diplomats", "trade war", "tariff", "tariffs", "recession",
    "inflation", "market crash", "flood", "flooding", "wildfire", "volcano",
    "eruption", "outbreak", "epidemic", "oil spill", "pipeline explosion",
    "blackout", "power outage", "internet outage", "treasury yields",
    "dollar index", "gdp", "unemployment", "ecb", "bank of japan",
    "war", "sanctions", "embargo", "fomc", "rate decision", "rate cut",
    "rate cuts", "rate hike", "rate hikes", "lagarde", "cpi", "pce",
    "payrolls", "safe haven", "safe-haven", "gold reserves",
    "central bank gold", "opec+",
]

LOW = [
    "election", "vote", "referendum", "summit", "treaty", "agreement",
    "negotiation", "talks", "ceasefire", "peace deal", "climate change",
    "vaccine", "virus", "interest rate", "regulation",
]

# Titoli da scartare sempre (gossip, sport, articoli "consigli"...).
EXCLUSIONS = [
    # da World Monitor
    "protein", "couples", "relationship", "dating", "diet", "fitness",
    "recipe", "cooking", "shopping", "fashion", "celebrity", "movie",
    "tv show", "sports", "game", "concert", "festival", "wedding",
    "vacation", "travel tips", "life hack", "self-care", "wellness",
    "strikes deal", "strikes agreement", "strikes partnership",
    # aggiunte per l'oro: articoli spam di previsioni/consigli
    "price prediction", "price forecast", "stocks to buy", "should you buy",
    "how to", "podcast", "quiz", "horoscope", "football", "soccer",
    "star wars", "war of words", "price war", "culture war", "bidding war",
    # articoli che non sono notizie nuove
    "earnings call", "transcript", "quarterly results", "dies at", "obituary",
    "live updates", "explained", "explainer",
]

# Titoli che iniziano così sono approfondimenti, video o opinioni.
EXCLUDED_STARTS = (
    "how ", "why ", "what ", "who ", "video", "watch", "opinion", "analysis",
    "explainer", "podcast", "column", "editorial", "letters",
)

GOLD_WORDS = re.compile(r"\b(gold|xau|xauusd|bullion|precious metals?)\b")

LEVEL_POINTS = {"critical": 100, "high": 60, "medium": 35, "low": 15, "info": 0}
TIER_POINTS = {1: 20, 2: 5, 3: 0, 4: -10}
GOLD_BONUS = 10
CONFIRM_POINTS = 10      # per ogni fonte in più che riporta la stessa notizia
CONFIRM_MAX = 30


def _pattern(keyword):
    # Inizio parola obbligatorio; le parole corte devono essere intere
    # (così "war" non scatta su "award" o "warn").
    escaped = re.escape(keyword)
    if len(keyword) <= 5:
        return re.compile(r"(?<![\w-])" + escaped + r"(?![\w-])")
    return re.compile(r"(?<![\w-])" + escaped)


_LEVELS = [
    ("critical", [_pattern(k) for k in CRITICAL]),
    ("high", [_pattern(k) for k in HIGH]),
    ("medium", [_pattern(k) for k in MEDIUM]),
    ("low", [_pattern(k) for k in LOW]),
]

# Come World Monitor: azione militare + obiettivo strategico => critical.
_ESCALATION_ACTIONS = re.compile(
    r"\b(attack|attacks|attacked|strikes|struck|bomb|bombs|bombed|"
    r"bombing|missile|missiles|retaliates|retaliation|invaded|invades)\b"
)
_ESCALATION_TARGETS = re.compile(
    r"\b(iran|tehran|russia|moscow|china|beijing|taiwan|north korea|"
    r"pyongyang|nato|us base|us forces|us military)\b"
)


def classify(title):
    """Ritorna il livello della notizia: critical/high/medium/low/info."""
    lower = title.lower()
    if any(ex in lower for ex in EXCLUSIONS):
        return "info"
    if lower.rstrip().endswith("?") or lower.startswith(EXCLUDED_STARTS):
        return "info"
    for level, patterns in _LEVELS:
        if level == "high" and any(r.search(lower) for r in HIGH_REGEX):
            return "high"
        if any(p.search(lower) for p in patterns):
            if (level == "high" and _ESCALATION_ACTIONS.search(lower)
                    and _ESCALATION_TARGETS.search(lower)):
                return "critical"
            return level
    return "info"


# Affidabilità per testata (come i "tier" di World Monitor). Serve per le notizie
# di Google News, dove la testata reale può essere qualsiasi sito.
PUBLISHER_TIERS = {
    "reuters": 1, "associated press": 1, "ap news": 1, "bloomberg": 1,
    "federal reserve": 1, "european central bank": 1, "european commission": 1,
    "afp": 1, "iaea": 1, "who": 1, "world health organization": 1,
    "bbc": 2, "bbc news": 2, "cnn": 2, "cnbc": 2, "financial times": 2,
    "the wall street journal": 2, "wall street journal": 2, "wsj": 2,
    "the new york times": 2, "new york times": 2, "the washington post": 2,
    "the guardian": 2, "al jazeera": 2, "nikkei asia": 2, "the economist": 2,
    "politico": 2, "axios": 2, "marketwatch": 2, "kitco": 2, "kitco news": 2,
    "barron's": 2, "fox business": 2, "abc news": 2, "nbc news": 2, "cbs news": 2,
    "sky news": 2, "euronews": 2, "dw": 2, "france 24": 2, "the telegraph": 2,
    "fxstreet": 3, "investing.com": 3, "yahoo finance": 3, "seeking alpha": 3,
    "fxempire": 3, "newsquawk": 3, "forexlive": 3, "benzinga": 3, "business insider": 3,
}


def publisher_tier(publisher, default=4):
    name = (publisher or "").strip().lower()
    for suffix in (".com", ".co.uk", ".org"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return PUBLISHER_TIERS.get(name, default)


def is_about_gold(title):
    return bool(GOLD_WORDS.search(title.lower()))


def base_score(title, tier):
    """Punteggio di una singola notizia (senza contare le conferme)."""
    score = LEVEL_POINTS[classify(title)] + TIER_POINTS.get(tier, -10)
    if is_about_gold(title):
        score += GOLD_BONUS
    return score


def confirm_bonus(num_sources):
    """Bonus per le fonti in più che riportano la stessa notizia."""
    return min(CONFIRM_MAX, max(0, num_sources - 1) * CONFIRM_POINTS)


# ---------- Riconoscere la stessa notizia da fonti diverse ----------

_STOPWORDS = set("""
the a an and or of to in on for with at by from as is are was were be been
its it this that after before over amid into about says said say new more
than will would could may might has have had not but his her their they
what who why how when where us u.s
""".split())


def keywords(title):
    words = re.findall(r"[a-z0-9$%]+", title.lower())
    return {w for w in words if len(w) >= 3 and w not in _STOPWORDS}


def same_story(words_a, words_b):
    """True se due titoli parlano molto probabilmente della stessa notizia."""
    if not words_a or not words_b:
        return False
    common = len(words_a & words_b)
    return common >= 3 and common / min(len(words_a), len(words_b)) >= 0.6
