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
INSTANT_THRESHOLD = int(os.getenv("INSTANT_THRESHOLD", "85"))
RECAP_THRESHOLD = int(os.getenv("RECAP_THRESHOLD", "60"))
# Quante notizie "ULTIM'ORA" al massimo al giorno (dalla mezzanotte).
# Nessuna attesa tra una e l'altra: se ne escono due a 2 minuti di distanza, partono entrambe.
MAX_ALERTS_PER_DAY = int(os.getenv("MAX_ALERTS_PER_DAY", "5"))
# Quante notizie al massimo nel riepilogo delle 6:00.
RECAP_MAX_ITEMS = int(os.getenv("RECAP_MAX_ITEMS", "5"))

# Notizie più vecchie di così non vengono mai inviate come "istantanee".
MAX_INSTANT_AGE_HOURS = 3
# Il riepilogo del mattino guarda le notizie delle ultime N ore.
RECAP_WINDOW_HOURS = 24

# =========================
# TRADUZIONE (DeepL API Free)
# =========================
# Chiave gratuita da https://www.deepl.com/pro-api (piano "DeepL API Free").
# Se manca, o se la quota mensile gratuita finisce, si usa Google Translate gratuito.
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "").strip()

DRY_RUN = _bool("DRY_RUN", "false")
