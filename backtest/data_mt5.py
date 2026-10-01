"""
Caricamento dei dati storici: da MetaTrader 5 (con cache su CSV) oppure da un CSV.

Il CSV ha le colonne: time, open, high, low, close[, spread]
- time: ora del server del broker (come la mostra MT5)
- spread: in point (come nelle barre di MT5), opzionale
"""
from __future__ import annotations

import json
import sys
import time as _time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(__file__).resolve().parent / "data_cache"

TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4"]


def infer_digits(close: np.ndarray) -> int:
    sample = close[: min(len(close), 2000)]
    for d in range(0, 7):
        scaled = sample * 10 ** d
        if np.allclose(scaled, np.round(scaled), atol=1e-6):
            return d
    return 5


def pip_size(point: float, digits: int) -> float:
    """1 pip = 10 point sulle coppie a 5 o 3 decimali, altrimenti 1 point."""
    return point * 10 if digits in (3, 5) else point


def load_csv(path: str | Path, point: float | None = None) -> tuple[pd.DataFrame, float, int]:
    path = Path(path)
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = {"time", "open", "high", "low", "close"} - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: colonne mancanti {sorted(missing)}")
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    meta_path = path.with_suffix(".json")
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        digits, point = int(meta["digits"]), float(meta["point"])
    else:
        digits = infer_digits(df["close"].to_numpy(float))
        point = point or 10 ** -digits
    return df, point, digits


def _connect_mt5():
    import MetaTrader5 as mt5

    sys.path.insert(0, str(ROOT))
    try:
        from config import MT5_LOGIN, MT5_PASSWORD, MT5_PATH, MT5_SERVER
    except Exception:            # config non disponibile: usa il terminale già aperto
        MT5_LOGIN, MT5_PASSWORD, MT5_PATH, MT5_SERVER = 0, "", None, ""

    kwargs = {}
    if MT5_PATH and Path(MT5_PATH).exists():
        kwargs["path"] = MT5_PATH
    if MT5_LOGIN:
        kwargs.update(login=int(MT5_LOGIN), password=MT5_PASSWORD, server=MT5_SERVER)
    if not mt5.initialize(**kwargs):
        raise RuntimeError(f"MT5 initialize fallito: {mt5.last_error()}")
    return mt5


def load_mt5(symbol: str, timeframe: str, date_from: str, date_to: str,
             refresh: bool = False) -> tuple[pd.DataFrame, float, int]:
    """Scarica le barre da MT5 (solo lettura, nessun ordine) e le salva in cache."""
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Timeframe non supportato: {timeframe} (usa {', '.join(TIMEFRAMES)})")
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / f"{symbol}_{timeframe}_{date_from}_{date_to}.csv"
    if cache.exists() and not refresh:
        print(f"  dati da cache: {cache.name}")
        return load_csv(cache)

    mt5 = _connect_mt5()
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Simbolo {symbol} non trovato sul broker (controlla eventuali suffissi, es. EURUSD-P)")
        if not info.visible:
            mt5.symbol_select(symbol, True)

        tick = mt5.symbol_info_tick(symbol)
        if tick is not None:
            offset = round((tick.time - _time.time()) / 3600)
            print(f"  ora server ≈ UTC{offset:+d} (calcolata dall'ultimo tick; affidabile solo a mercato aperto)")

        tf = getattr(mt5, f"TIMEFRAME_{timeframe}")
        start = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
        rates = mt5.copy_rates_range(symbol, tf, start, end)
        if rates is None or len(rates) == 0:
            raise RuntimeError(
                f"Nessuna barra ricevuta per {symbol} {timeframe}: {mt5.last_error()}.\n"
                "  Suggerimenti: apri il grafico del simbolo in MT5 e scorri indietro per scaricare lo storico;\n"
                "  in Strumenti → Opzioni → Grafici imposta 'Max barre nel grafico' su Illimitato."
            )
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df[["time", "open", "high", "low", "close", "spread"]]
        df.to_csv(cache, index=False)
        cache.with_suffix(".json").write_text(json.dumps({"digits": info.digits, "point": info.point}))
        first, last = df["time"].iloc[0], df["time"].iloc[-1]
        print(f"  scaricate {len(df):,} barre ({first:%Y-%m-%d} → {last:%Y-%m-%d})")
        if first > pd.Timestamp(date_from) + pd.Timedelta(days=7):
            print("  ⚠ lo storico parte dopo la data richiesta: aumenta 'Max barre nel grafico' in MT5")
        return df, float(info.point), int(info.digits)
    finally:
        mt5.shutdown()
