"""
Configurazione Bot Sicurezza (controllo iscritti della sala elite e del canale).

Le credenziali NON stanno in questo file: vanno nel file .env di questa
cartella (copia .env.example in .env e compilalo).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

REPORT_DIR = BASE_DIR / "report"
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "guardiano.log"


def _lista_int(name):
    valori = []
    for pezzo in os.getenv(name, "").replace(";", ",").split(","):
        pezzo = pezzo.strip()
        if pezzo:
            valori.append(int(pezzo))
    return valori


def _lista_testo(name):
    return [p.strip() for p in os.getenv(name, "").replace(";", ",").split(",") if p.strip()]


# =========================
# TELEGRAM (tuo account: serve per il REPORT)
# =========================
API_ID = int(os.getenv("TELEGRAM_API_ID", "0") or 0)
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "sicurezza_session")

# ID della sala elite e del canale da controllare, separati da virgola
# (li trovi con: python get_chats.py ; di solito iniziano con -100...)
CHATS = _lista_int("TELEGRAM_CHATS")

# =========================
# BOT GUARDIANO (facoltativo: captcha per chi chiede di entrare)
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_SESSION_NAME = os.getenv("BOT_SESSION_NAME", "sicurezza_bot")

# Il tuo ID Telegram: il bot ti avvisa in privato di ogni richiesta
# (prima scrivi /start al bot, altrimenti non puo' scriverti). 0 = nessun avviso.
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0") or 0)

# Tempo per rispondere al captcha e tentativi a disposizione.
CAPTCHA_TIMEOUT_SECONDS = float(os.getenv("CAPTCHA_TIMEOUT_SECONDS", "60"))
CAPTCHA_TENTATIVI = int(os.getenv("CAPTCHA_TENTATIVI", "2"))

# =========================
# ANALISI
# =========================
# Nomi da proteggere dalle imitazioni (es. il tuo nome, il nome della sala).
# Chi ha un nome che li contiene viene segnalato come "possibile imitazione".
NOMI_PROTETTI = _lista_testo("NOMI_PROTETTI")

# ID Telegram da cui in poi un account si considera "creato di recente".
# E' una stima: gli ID crescono nel tempo, ma non dicono la data esatta.
ID_ACCOUNT_RECENTE = int(os.getenv("ID_ACCOUNT_RECENTE", "7000000000") or 0)
