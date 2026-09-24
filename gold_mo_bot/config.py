"""
Configurazione Telegram -> MetaTrader 5 per il bot Gold MO.

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
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "gold_mo_copier")

SOURCE_CHAT = int(os.getenv("TELEGRAM_SOURCE_CHAT", "-1002495224665"))
DESTINATION_CHAT = int(os.getenv("TELEGRAM_DESTINATION_CHAT", "-1004456671842"))

# =========================
# MT5 - CONTO PRINCIPALE
# =========================
MT5_PATH = os.getenv(
    "MT5_PATH",
    r"C:\Program Files\MetaTrader 5\terminal64.exe"
)
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

# =========================
# MT5 - SECONDO CONTO (copia in parallelo)
# =========================
# Disattivato finche' non vengono fornite le credenziali reali. Quando
# SECOND_ACCOUNT_ENABLED=true il bot avvia un secondo processo che si
# collega a un secondo terminale MT5 installato sulla stessa macchina
# (es. C:\MT5_Account2\terminal64.exe) e apre la stessa operazione anche
# li'.
SECOND_ACCOUNT_ENABLED = os.getenv("SECOND_ACCOUNT_ENABLED", "false").lower() in {
    "1", "true", "yes", "on"
}
MT5_PATH_2 = os.getenv("MT5_PATH_2", "")
MT5_LOGIN_2 = int(os.getenv("MT5_LOGIN_2", "0"))
MT5_PASSWORD_2 = os.getenv("MT5_PASSWORD_2", "")
MT5_SERVER_2 = os.getenv("MT5_SERVER_2", "")

MAGIC_NUMBER_2 = int(os.getenv("MAGIC_NUMBER_2", "26090202"))

# =========================
# TRADING
# =========================
MT5_SYMBOL = os.getenv("MT5_SYMBOL", "XAUUSD")

# Lotto usato su ENTRAMBI i conti (stesso valore su conto 1 e conto 2).
LOT_SIZE = float(os.getenv("LOT_SIZE", "0.01"))

MAX_SIGNAL_AGE_SECONDS = float(os.getenv("MAX_SIGNAL_AGE_SECONDS", "60"))

# Slippage/deviation MT5 in points.
DEVIATION = int(os.getenv("DEVIATION", "50"))

MAGIC_NUMBER = int(os.getenv("MAGIC_NUMBER", "26090201"))
ORDER_COMMENT = os.getenv("ORDER_COMMENT", "Gold MO Copier")

# Intervallo (secondi) del ciclo che controlla il prezzo live per
# TP1 -> Break Even e la chiusura reale delle posizioni.
MONITOR_INTERVAL_SECONDS = float(os.getenv("MONITOR_INTERVAL_SECONDS", "0.5"))

# =========================
# COMANDI REMOTI (da "Messaggi Salvati")
# =========================
# Prefisso distinto da altri eventuali bot sullo stesso account Telegram.
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "bot5_")

# =========================
# CHIUSURA AUTOMATICA DI FINE GIORNATA + REPORT
# =========================
DAILY_CLOSE_HOUR = int(os.getenv("DAILY_CLOSE_HOUR", "22"))
DAILY_CLOSE_MINUTE = int(os.getenv("DAILY_CLOSE_MINUTE", "45"))
DAILY_REPORT_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "23"))
DAILY_REPORT_MINUTE = int(os.getenv("DAILY_REPORT_MINUTE", "0"))
GOOD_MORNING_HOUR = int(os.getenv("GOOD_MORNING_HOUR", "6"))
GOOD_MORNING_MINUTE = int(os.getenv("GOOD_MORNING_MINUTE", "0"))
WEEKLY_REPORT_HOUR = int(os.getenv("WEEKLY_REPORT_HOUR", "10"))
WEEKLY_REPORT_MINUTE = int(os.getenv("WEEKLY_REPORT_MINUTE", "0"))

# Branding usato nei messaggi di report/buongiorno.
BRAND_NAME = os.getenv("BRAND_NAME", "GOLD MO")

# =========================
# LOGGING / DEBUG
# =========================
DEBUG = os.getenv("DEBUG", "true").lower() in {"1", "true", "yes", "on"}
LOG_FILE = LOG_DIR / "bot.log"

TRADING_ENABLED = os.getenv("TRADING_ENABLED", "true").lower() in {
    "1", "true", "yes", "on"
}
