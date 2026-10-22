"""
Configurazione bot Gold Empire -> canale Telegram + MetaTrader 5.

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

DB_PATH = DATA_DIR / "goldempire.db"
LOG_FILE = LOG_DIR / "bot.log"


def _bool(name, default):
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


# =========================
# TELEGRAM
# =========================
API_ID = int(os.getenv("TELEGRAM_API_ID", "0") or 0)
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "goldempire_session")

# Canale sorgente "Gold empire signals room" e tuo canale di destinazione.
SOURCE_CHAT = int(os.getenv("TELEGRAM_SOURCE_CHAT", "0") or 0)
DESTINATION_CHAT = int(os.getenv("TELEGRAM_DESTINATION_CHAT", "0") or 0)

# Comandi da "Messaggi salvati" (es. bot3_status, bot3_pausa ...). Non usare bot2_ (e' dell'altro bot).
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "bot3_").strip().lower()

# =========================
# MT5
# =========================
MT5_PATH = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0") or 0)
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

# =========================
# TRADING
# =========================
# false = modalita' TEST: copia i messaggi nel canale ma NON apre ordini
# (usa i prezzi scritti nei messaggi del canale sorgente).
TRADING_ENABLED = _bool("TRADING_ENABLED", "true")

MT5_SYMBOL = os.getenv("MT5_SYMBOL", "XAUUSD")
LOT_SIZE = float(os.getenv("LOT_SIZE", "0.01"))
DEVIATION = int(os.getenv("DEVIATION", "50"))
MAGIC_NUMBER = int(os.getenv("MAGIC_NUMBER", "26090110"))
ORDER_COMMENT = os.getenv("ORDER_COMMENT", "GoldEmpire")

# Un segnale di apertura piu' vecchio di cosi' (secondi) viene ignorato
# (es. messaggi recuperati dopo una disconnessione).
MAX_SIGNAL_AGE_SECONDS = float(os.getenv("MAX_SIGNAL_AGE_SECONDS", "120"))

# Distanza massima (in $) tra prezzo di mercato e "Ingresso" del segnale.
# 0 = nessun limite: si apre sempre a mercato.
MAX_ENTRY_DISTANCE = float(os.getenv("MAX_ENTRY_DISTANCE", "0"))

# Ordini pendenti (BUY/SELL LIMIT, BUY/SELL STOP): dopo quanti minuti
# vengono annullati se non eseguiti (0 = restano finche' il canale non li annulla).
PENDING_EXPIRY_MINUTES = float(os.getenv("PENDING_EXPIRY_MINUTES", "1440"))

# Dimensione di 1 pip su XAUUSD (0,10 $ come il canale: 35,24 $ = 352,4 pips).
PIP_SIZE = float(os.getenv("PIP_SIZE", "0.1"))

# Ogni quanti secondi il monitor controlla le posizioni chiuse da MT5.
MONITOR_INTERVAL_SECONDS = float(os.getenv("MONITOR_INTERVAL_SECONDS", "3"))
