"""
Configurazione Telegram -> MetaTrader 5.

IMPORTANTE:
- Le credenziali/segreti NON sono salvati in questo file.
- Inseriscili nel file .env copiato da .env.example.
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

# =========================
# TELEGRAM
# =========================
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "telegram_copier_final2")

SOURCE_CHAT = int(os.getenv("TELEGRAM_SOURCE_CHAT", "-1003543239308"))
DESTINATION_CHAT = int(os.getenv("TELEGRAM_DESTINATION_CHAT", "-1004390393606"))

# =========================
# MT5
# =========================
MT5_PATH = os.getenv(
    "MT5_PATH",
    r"C:\Program Files\MetaTrader 5\terminal64.exe"
)
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

# =========================
# TRADING
# =========================
MT5_SYMBOL = os.getenv("MT5_SYMBOL", "XAUUSD-P")
LOT_SIZE = float(os.getenv("LOT_SIZE", "0.01"))

# Entry valida: entry +/- ENTRY_RANGE in USD.
ENTRY_RANGE = float(os.getenv("ENTRY_RANGE", "2.0"))

# Tempo massimo di ricerca del prezzo valido.
ENTRY_TIMEOUT_SECONDS = float(os.getenv("ENTRY_TIMEOUT_SECONDS", "20"))

# Frequenza di controllo del prezzo.
PRICE_CHECK_INTERVAL = float(os.getenv("PRICE_CHECK_INTERVAL", "0.10"))

MAX_SIGNAL_AGE_SECONDS = float(os.getenv("MAX_SIGNAL_AGE_SECONDS", "60"))
MAX_SIMULTANEOUS_SIGNALS = int(os.getenv("MAX_SIMULTANEOUS_SIGNALS", "3"))

# Slippage/deviation MT5 in points.
DEVIATION = int(os.getenv("DEVIATION", "50"))

MAGIC_NUMBER = int(os.getenv("MAGIC_NUMBER", "26090102"))
ORDER_COMMENT = os.getenv("ORDER_COMMENT", "Telegram Copier")

# =========================
# LOGGING / DEBUG
# =========================
DEBUG = os.getenv("DEBUG", "true").lower() in {"1", "true", "yes", "on"}
LOG_FILE = LOG_DIR / "bot.log"

# Solo il segnale di apertura mercato previsto dal bot.
# TP2/TP3/BE/trailing NON vengono gestiti.
TRADING_ENABLED = os.getenv("TRADING_ENABLED", "true").lower() in {
    "1", "true", "yes", "on"
}
