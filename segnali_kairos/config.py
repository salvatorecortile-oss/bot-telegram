"""
Configurazione della sala segnali Kairos: legge le operazioni da MetaTrader 5
e le pubblica come messaggi in un canale Telegram.

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

DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "segnali.db"
LOG_FILE = LOG_DIR / "segnali.log"


def _int_list(value):
    return {int(n) for n in value.replace(";", ",").split(",") if n.strip()}


# =========================
# TELEGRAM
# =========================
API_ID = int(os.getenv("TELEGRAM_API_ID", "0") or 0)
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "segnali_kairos_session")

# Canale (sala segnali) dove vengono pubblicate le operazioni.
DESTINATION_CHAT = int(os.getenv("TELEGRAM_DESTINATION_CHAT", "0") or 0)

# Comandi da "Messaggi salvati" (es. segnali_status, segnali_pausa ...).
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "segnali_").strip().lower()

# =========================
# MT5 (solo lettura: il bot non apre e non chiude niente)
# =========================
MT5_PATH = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0") or 0)
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

# Magic number delle operazioni da pubblicare (Fibonacci 61800, Kairos RSI 54001).
MAGIC_NUMBERS = _int_list(os.getenv("MAGIC_NUMBERS", "61800,54001"))

# Solo questo simbolo (vuoto = tutti i simboli con quei magic number).
MT5_SYMBOL = os.getenv("MT5_SYMBOL", "").strip()

# Nome del simbolo nei messaggi (vuoto = quello di MT5 senza suffisso: XAUUSD-P -> XAUUSD).
DISPLAY_SYMBOL = os.getenv("DISPLAY_SYMBOL", "").strip()

# Dimensione di 1 pip (0,10 $ sull'oro: 35,24 $ = 352,4 pips).
PIP_SIZE = float(os.getenv("PIP_SIZE", "0.1"))

# Ogni quanti secondi legge le posizioni da MT5.
POLL_INTERVAL_SECONDS = float(os.getenv("POLL_INTERVAL_SECONDS", "2"))

# All'avvio: le posizioni gia' aperte vengono pubblicate solo se aperte da meno
# di questi secondi (le altre vengono seguite in silenzio, senza messaggi).
MAX_OPEN_AGE_SECONDS = float(os.getenv("MAX_OPEN_AGE_SECONDS", "300"))
