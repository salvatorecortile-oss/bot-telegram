"""
Configurazione del bot notizie.

Tutti i valori si cambiano dal file .env (vedi .env.example).
Questo bot NON usa MT5 e NON fa trading: pubblica solo notizie.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "news.db"
LOG_FILE = LOG_DIR / "news_bot.log"


def _bool(name, default):
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


# =========================
# TELEGRAM (Telethon, account utente)
# =========================
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = str(BASE_DIR / os.getenv("NEWS_SESSION_NAME", "news_bot"))
NEWS_CHANNEL = int(os.getenv("NEWS_CHANNEL", "0"))

# =========================
# ORARI
# =========================
TIMEZONE = os.getenv("TIMEZONE", "Europe/Rome")
MORNING_HOUR = int(os.getenv("MORNING_HOUR", "6"))
MORNING_MINUTE = int(os.getenv("MORNING_MINUTE", "0"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "120"))
QUIET_HOURS = os.getenv("QUIET_HOURS", "").strip()

# =========================
# FILTRO IMPORTANZA
# =========================
INSTANT_THRESHOLD = int(os.getenv("INSTANT_THRESHOLD", "75"))
RECAP_THRESHOLD = int(os.getenv("RECAP_THRESHOLD", "60"))
MAX_ALERTS_PER_HOUR = int(os.getenv("MAX_ALERTS_PER_HOUR", "4"))
RECAP_MAX_ITEMS = int(os.getenv("RECAP_MAX_ITEMS", "10"))

# Notizie più vecchie di così non vengono mai inviate come "istantanee".
MAX_INSTANT_AGE_HOURS = 3
# Il riepilogo del mattino guarda le notizie delle ultime N ore.
RECAP_WINDOW_HOURS = 24

# =========================
# CLAUDE (redattore AI)
# =========================
# Senza chiave il bot funziona lo stesso, con il solo filtro a parole chiave
# e la traduzione gratuita di Google.
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
AI_ENABLED = bool(ANTHROPIC_API_KEY)
CLAUDE_MODEL = os.getenv("AI_MODEL", "claude-opus-5-5")
CLAUDE_EFFORT = os.getenv("AI_EFFORT", "low")
# Solo le notizie con punteggio parole chiave >= AI_PREFILTER vanno a Claude.
AI_PREFILTER = int(os.getenv("AI_PREFILTER", "50"))
# Voto Claude (1-10) minimo per l'invio immediato e per il riepilogo.
AI_INSTANT_MIN = int(os.getenv("AI_INSTANT_MIN", "9"))
AI_RECAP_MIN = int(os.getenv("AI_RECAP_MIN", "7"))
# Notizie mandate a Claude in una sola chiamata, e tetto di chiamate al giorno.
AI_BATCH_SIZE = 25
MAX_AI_CALLS_PER_DAY = int(os.getenv("MAX_AI_CALLS_PER_DAY", "150"))

DRY_RUN = _bool("DRY_RUN", "false")
