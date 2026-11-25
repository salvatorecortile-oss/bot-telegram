"""
Configurazione del servizio previsioni Kronos.

Nessuna credenziale qui: MT5 deve essere solo aperto sul PC.
Le impostazioni si cambiano nel file .env di questa cartella
(copia .env.example in .env).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "kronos.log"

# Cartella dove hai scaricato il codice ufficiale di Kronos
# (git clone https://github.com/shiyu-coder/Kronos.git dentro questa cartella)
KRONOS_REPO_DIR = Path(os.getenv("KRONOS_REPO_DIR", str(BASE_DIR / "Kronos")))

# Modello: nome HuggingFace oppure percorso di una cartella locale con i pesi.
KRONOS_MODEL = os.getenv("KRONOS_MODEL", "NeoQuasar/Kronos-small")
KRONOS_TOKENIZER = os.getenv("KRONOS_TOKENIZER", "NeoQuasar/Kronos-Tokenizer-base")
# "auto" = usa la scheda video se c'e', altrimenti il processore (cpu)
KRONOS_DEVICE = os.getenv("KRONOS_DEVICE", "auto")

# MetaTrader 5 (vuoto = usa il terminale gia' aperto)
MT5_PATH = os.getenv("MT5_PATH", "")

DEFAULT_SYMBOL = os.getenv("KRONOS_SYMBOL", "XAUUSD")
DEFAULT_TIMEFRAME = os.getenv("KRONOS_TIMEFRAME", "M15")

# Quante candele passate leggere (massimo utile per Kronos: 512)
LOOKBACK = int(os.getenv("KRONOS_LOOKBACK", "400"))
# Quante candele future prevedere
PRED_LEN = int(os.getenv("KRONOS_PRED_LEN", "12"))
# Quanti scenari diversi far generare (piu' sono, piu' la probabilita' e' stabile ma piu' e' lento)
SAMPLES = int(os.getenv("KRONOS_SAMPLES", "20"))
TEMPERATURE = float(os.getenv("KRONOS_TEMPERATURE", "1.0"))
TOP_P = float(os.getenv("KRONOS_TOP_P", "0.9"))

# Soglie per la parola "RIALZO"/"RIBASSO" (solo informativa, non apre ordini)
BULLISH_THRESHOLD = float(os.getenv("KRONOS_BULLISH_THRESHOLD", "0.65"))
BEARISH_THRESHOLD = float(os.getenv("KRONOS_BEARISH_THRESHOLD", "0.35"))

# Servizio locale per gli altri bot: solo dal tuo PC (127.0.0.1)
HOST = os.getenv("KRONOS_HOST", "127.0.0.1")
PORT = int(os.getenv("KRONOS_PORT", "8765"))
