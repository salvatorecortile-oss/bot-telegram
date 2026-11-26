"""Lettura delle candele da MetaTrader 5 (solo lettura, nessun ordine)."""
import logging

import pandas as pd

import config

log = logging.getLogger(__name__)

# Timeframe accettati -> minuti per candela
TIMEFRAME_MINUTES = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 60, "H4": 240, "D1": 1440,
}


def normalize_timeframe(tf):
    tf = (tf or "").strip().upper()
    if tf not in TIMEFRAME_MINUTES:
        raise ValueError(f"Timeframe non valido: {tf}. Usa uno di {', '.join(TIMEFRAME_MINUTES)}")
    return tf


def rates_to_dataframe(rates):
    """Converte i dati di copy_rates_from_pos nel formato che vuole Kronos."""
    df = pd.DataFrame(rates)
    if df.empty:
        raise RuntimeError("MT5 non ha restituito candele")
    df["timestamps"] = pd.to_datetime(df["time"], unit="s")
    df["volume"] = df["tick_volume"].astype(float)
    df["amount"] = df["volume"] * df[["open", "high", "low", "close"]].mean(axis=1)
    return df[["timestamps", "open", "high", "low", "close", "volume", "amount"]].reset_index(drop=True)


def describe_terminal(mt5):
    """Quale MT5 e' collegato: cartella del programma e server del broker."""
    term = mt5.terminal_info()
    acc = mt5.account_info()
    path = getattr(term, "path", "?") if term else "?"
    server = getattr(acc, "server", "?") if acc else "nessun conto collegato"
    return f"cartella {path}, server {server}"


def similar_symbols(mt5, keywords=("XAU", "GOLD")):
    """Nomi dei simboli che contengono XAU o GOLD (per suggerire quello giusto)."""
    found = []
    for s in mt5.symbols_get() or []:
        name = getattr(s, "name", "")
        if any(k in name.upper() for k in keywords):
            found.append(name)
    return sorted(found)[:20]


class MT5Candles:
    """Collegamento a MT5 che si riconnette da solo se cade."""

    def __init__(self, path=None):
        self.path = path if path is not None else config.MT5_PATH
        self._mt5 = None

    def _connect(self):
        import MetaTrader5 as mt5
        if mt5.terminal_info() is not None:
            self._mt5 = mt5
            return mt5
        ok = mt5.initialize(path=self.path, timeout=20000) if self.path else mt5.initialize(timeout=20000)
        if not ok:
            raise RuntimeError(f"MT5 initialize fallito: {mt5.last_error()}. MetaTrader 5 e' aperto?")
        self._mt5 = mt5
        log.info("Collegato a MT5: %s", describe_terminal(mt5))
        return mt5

    def get_candles(self, symbol, timeframe, count):
        """Ultime `count` candele CHIUSE (la candela in corso viene esclusa)."""
        mt5 = self._connect()
        tf = getattr(mt5, f"TIMEFRAME_{normalize_timeframe(timeframe)}")
        if not mt5.symbol_select(symbol, True):
            similar = similar_symbols(mt5)
            hint = (f"Nomi simili presenti: {', '.join(similar)}" if similar
                    else "Nessun simbolo con XAU o GOLD in questo terminale")
            raise RuntimeError(
                f"Simbolo {symbol} non trovato nel MT5 collegato ({describe_terminal(mt5)}). "
                f"{hint}. Metti il nome giusto in .env alla riga KRONOS_SYMBOL=, "
                "oppure scegli il terminale giusto con MT5_PATH=")
        # posizione 1 = salta la candela ancora aperta
        rates = mt5.copy_rates_from_pos(symbol, tf, 1, count)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"Nessuna candela per {symbol} {timeframe}: {mt5.last_error()}")
        return rates_to_dataframe(rates)

    def shutdown(self):
        if self._mt5 is not None:
            self._mt5.shutdown()
            self._mt5 = None
