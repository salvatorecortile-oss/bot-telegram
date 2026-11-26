"""
Previsioni con Kronos.

Kronos genera tanti "scenari" possibili per le prossime candele.
Da questi scenari calcoliamo, come nella demo ufficiale:
- probabilita' di rialzo: quanti scenari chiudono sopra l'ultimo prezzo
- probabilita' di volatilita' piu' alta del solito
- prezzo medio previsto e intervallo (10% - 90%)

Questo modulo NON apre ordini: produce solo numeri.
"""
import logging
import sys
import threading
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import config
from mt5_data import TIMEFRAME_MINUTES, normalize_timeframe

log = logging.getLogger(__name__)


def future_timestamps(last_ts, timeframe, pred_len):
    """Orari delle prossime `pred_len` candele dopo `last_ts`."""
    step = pd.Timedelta(minutes=TIMEFRAME_MINUTES[normalize_timeframe(timeframe)])
    return pd.Series([last_ts + step * (i + 1) for i in range(pred_len)])


def _log_returns_std(closes):
    closes = np.asarray(closes, dtype=float)
    if len(closes) < 3:
        return 0.0
    return float(np.std(np.diff(np.log(closes))))


def summarize(history, paths, bullish=None, bearish=None):
    """
    history: DataFrame delle candele passate (colonna close)
    paths:   lista di DataFrame, uno per scenario (colonne open/high/low/close)
    """
    bullish = config.BULLISH_THRESHOLD if bullish is None else bullish
    bearish = config.BEARISH_THRESHOLD if bearish is None else bearish
    if not paths:
        raise ValueError("Nessuno scenario da riassumere")

    last_close = float(history["close"].iloc[-1])
    pred_len = len(paths[0])
    final_closes = np.array([float(p["close"].iloc[-1]) for p in paths])
    closes_matrix = np.array([p["close"].to_numpy(dtype=float) for p in paths])

    hist_vol = _log_returns_std(history["close"].iloc[-(pred_len + 1):])
    path_vols = [_log_returns_std(np.concatenate([[last_close], c])) for c in closes_matrix]

    upside = float(np.mean(final_closes > last_close))
    vol_up = float(np.mean([v > hist_vol for v in path_vols]))

    if upside >= bullish:
        bias = "RIALZO"
    elif upside <= bearish:
        bias = "RIBASSO"
    else:
        bias = "NEUTRO"

    mean_path = closes_matrix.mean(axis=0)
    return {
        "last_close": round(last_close, 5),
        "last_candle_time": str(history["timestamps"].iloc[-1]),
        "pred_len": pred_len,
        "samples": len(paths),
        "upside_probability": round(upside, 4),
        "volatility_up_probability": round(vol_up, 4),
        "mean_final_close": round(float(final_closes.mean()), 5),
        "p10_final_close": round(float(np.percentile(final_closes, 10)), 5),
        "p90_final_close": round(float(np.percentile(final_closes, 90)), 5),
        "expected_move": round(float(final_closes.mean() - last_close), 5),
        "max_high": round(float(max(p["high"].max() for p in paths)), 5),
        "min_low": round(float(min(p["low"].min() for p in paths)), 5),
        "mean_path": [round(float(x), 5) for x in mean_path],
        "bias": bias,
    }


def load_predictor():
    """Carica il modello Kronos ufficiale (cartella KRONOS_REPO_DIR)."""
    repo = config.KRONOS_REPO_DIR
    if not (repo / "model" / "kronos.py").exists():
        raise RuntimeError(
            f"Codice Kronos non trovato in {repo}. "
            "Esegui: git clone https://github.com/shiyu-coder/Kronos.git Kronos"
        )
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from model import Kronos, KronosPredictor, KronosTokenizer

    log.info("Carico tokenizer %s e modello %s ...", config.KRONOS_TOKENIZER, config.KRONOS_MODEL)
    tokenizer = KronosTokenizer.from_pretrained(config.KRONOS_TOKENIZER)
    model = Kronos.from_pretrained(config.KRONOS_MODEL)
    device = None if config.KRONOS_DEVICE == "auto" else config.KRONOS_DEVICE
    predictor = KronosPredictor(model, tokenizer, device=device, max_context=512)
    log.info("Kronos pronto su %s", predictor.device)
    return predictor


class Forecaster:
    """
    Unisce candele MT5 + Kronos. Tiene in memoria l'ultima previsione per
    ogni simbolo/timeframe e la ricalcola solo quando chiude una nuova candela.
    """

    def __init__(self, candles, predictor=None, predictor_loader=load_predictor):
        self.candles = candles
        self._predictor = predictor
        self._loader = predictor_loader
        self._lock = threading.RLock()
        self._cache = {}

    @property
    def predictor(self):
        if self._predictor is None:
            self._predictor = self._loader()
        return self._predictor

    def get_history(self, symbol, timeframe, count):
        """Candele chiuse da MT5 (un accesso a MT5 alla volta)."""
        with self._lock:
            return self.candles.get_candles(symbol, normalize_timeframe(timeframe), count)

    def forecast(self, symbol=None, timeframe=None, pred_len=None, samples=None, force=False):
        symbol = (symbol or config.DEFAULT_SYMBOL).strip()
        timeframe = normalize_timeframe(timeframe or config.DEFAULT_TIMEFRAME)
        pred_len = int(config.PRED_LEN if pred_len in (None, "") else pred_len)
        samples = int(config.SAMPLES if samples in (None, "") else samples)
        if not 1 <= pred_len <= 120:
            raise ValueError("pred_len deve essere tra 1 e 120")
        if not 1 <= samples <= 100:
            raise ValueError("samples deve essere tra 1 e 100")

        with self._lock:  # un calcolo alla volta (il modello e' pesante)
            history = self.candles.get_candles(symbol, timeframe, config.LOOKBACK)
            key = (symbol, timeframe, pred_len, samples)
            last_ts = history["timestamps"].iloc[-1]
            cached = self._cache.get(key)
            if cached and not force and cached["last_candle_time"] == str(last_ts):
                return dict(cached, cached=True)

            x_df = history[["open", "high", "low", "close", "volume", "amount"]]
            x_ts = history["timestamps"]
            y_ts = future_timestamps(last_ts, timeframe, pred_len)
            # stesso storico ripetuto N volte = N scenari indipendenti in parallelo
            paths = self.predictor.predict_batch(
                df_list=[x_df] * samples,
                x_timestamp_list=[x_ts] * samples,
                y_timestamp_list=[y_ts] * samples,
                pred_len=pred_len,
                T=config.TEMPERATURE,
                top_p=config.TOP_P,
                sample_count=1,
                verbose=False,
            )
            result = summarize(history, paths)
            result.update({
                "symbol": symbol,
                "timeframe": timeframe,
                "forecast_times": [str(t) for t in y_ts],
                "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "model": config.KRONOS_MODEL,
            })
            self._cache[key] = result
            return dict(result, cached=False)


def format_text(r):
    """Testo leggibile in italiano (per console o per un canale Telegram)."""
    arrow = {"RIALZO": "🟢", "RIBASSO": "🔴"}.get(r["bias"], "⚪")
    return (
        f"🔮 Kronos | {r['symbol']} {r['timeframe']}\n"
        f"Ultima chiusura: {r['last_close']} ({r['last_candle_time']})\n"
        f"Prossime {r['pred_len']} candele, {r['samples']} scenari\n"
        f"{arrow} Tendenza: {r['bias']}\n"
        f"Probabilità rialzo: {r['upside_probability'] * 100:.1f}%\n"
        f"Probabilità volatilità in aumento: {r['volatility_up_probability'] * 100:.1f}%\n"
        f"Prezzo medio previsto: {r['mean_final_close']} "
        f"(range 10-90%: {r['p10_final_close']} - {r['p90_final_close']})\n"
        f"⚠️ Previsione statistica, non è un consiglio di trading."
    )
