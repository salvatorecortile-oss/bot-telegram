"""
Diagnosi della connessione MT5. Avvio (con MT5 aperto e loggato):
    python diagnose_mt5.py

Prova prima ad agganciarsi al terminale cosi' com'e' (senza login), poi con
i dati del .env, e spiega cosa non va.
"""
import platform
import struct
import sys

from config import MT5_LOGIN, MT5_PASSWORD, MT5_PATH, MT5_SERVER, MT5_SYMBOL

ERRORI = {
    -6: "Autorizzazione fallita: login, password o nome server sbagliati.",
    -10003: "Impossibile avviare il terminale: MT5_PATH sbagliato?",
    -10004: "Il terminale non risponde (IPC).",
    -10005: "Timeout: il terminale non risponde (rotellina). Vedi i consigli sotto.",
}

print("=" * 60)
print(f"Python {platform.python_version()} {struct.calcsize('P') * 8} bit")
if struct.calcsize("P") * 8 != 64:
    print("❌ Serve Python a 64 bit per la libreria MetaTrader5.")
    sys.exit(1)

try:
    import MetaTrader5 as mt5
except ImportError:
    print("❌ Libreria mancante: pip install MetaTrader5")
    sys.exit(1)

print(f"MT5_PATH   : {MT5_PATH}")
print(f"MT5_LOGIN  : {MT5_LOGIN}")
print(f"MT5_SERVER : {MT5_SERVER!r}")
print(f"MT5_SYMBOL : {MT5_SYMBOL}")
print("=" * 60)


def spiega(err):
    code = err[0] if err else None
    print(f"   errore MT5: {err}")
    if code in ERRORI:
        print(f"   -> {ERRORI[code]}")


def info_terminale():
    term = mt5.terminal_info()
    acc = mt5.account_info()
    if term:
        print(f"   Terminale : {term.path}")
        print(f"   Connesso al broker: {term.connected} | Trading algoritmico attivo: {term.trade_allowed}")
        if not term.trade_allowed:
            print("   ⚠️ Attiva il pulsante 'Trading algoritmico' in alto su MT5, altrimenti gli ordini vengono rifiutati.")
    if acc:
        print(f"   Account   : {acc.login} | Server: {acc.server!r} | Balance {acc.balance}")
        print(f"   -> In .env metti MT5_LOGIN={acc.login} e MT5_SERVER={acc.server}")
    sym = mt5.symbol_info(MT5_SYMBOL)
    if sym is None:
        oro = [s.name for s in (mt5.symbols_get("*XAU*") or [])]
        print(f"   ❌ Simbolo {MT5_SYMBOL!r} non trovato. Simboli oro su questo broker: {oro}")
        print("   -> Metti in .env MT5_SYMBOL uguale a uno di questi (es. XAUUSD).")
    else:
        print(f"   ✅ Simbolo {MT5_SYMBOL} OK (digits={sym.digits}, lotto min={sym.volume_min})")


print("\n1) Aggancio al terminale gia' aperto, SENZA login...")
if mt5.initialize(path=MT5_PATH, timeout=20000) if MT5_PATH else mt5.initialize(timeout=20000):
    print("   ✅ Agganciato.")
    info_terminale()
    mt5.shutdown()
else:
    spiega(mt5.last_error())
    print("   Se MT5_PATH e' sbagliato provo senza percorso...")
    if mt5.initialize(timeout=20000):
        print("   ✅ Agganciato SENZA percorso: il tuo MT5_PATH non e' quello del terminale Fortune Prime.")
        info_terminale()
        mt5.shutdown()
    else:
        spiega(mt5.last_error())

if MT5_LOGIN:
    print("\n2) Connessione con login/password/server del .env...")
    kwargs = {"login": int(MT5_LOGIN), "password": MT5_PASSWORD, "server": MT5_SERVER, "timeout": 20000}
    if MT5_PATH:
        kwargs["path"] = MT5_PATH
    if mt5.initialize(**kwargs):
        print("   ✅ Login riuscito.")
        info_terminale()
        mt5.shutdown()
    else:
        spiega(mt5.last_error())

print("""
CONSIGLI se resta la rotellina / timeout:
 - MT5_PATH deve puntare al terminal64.exe del terminale FORTUNE PRIME
   (tasto destro sull'icona MT5 -> Apri percorso file).
 - Avvia MT5 e il bot con gli stessi permessi (entrambi normali, o entrambi
   "Esegui come amministratore").
 - MT5_SERVER deve essere scritto ESATTAMENTE come in MT5
   (File -> Login al conto di trading -> campo Server).
 - Lascia MT5 aperto e gia' loggato prima di avviare il bot.
""")
