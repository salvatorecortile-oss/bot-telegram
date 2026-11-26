"""
Backtest: verifica Kronos sul PASSATO, senza aspettare giorni.

Prende le candele vecchie da MT5 e, in tanti momenti del passato, fa fare a
Kronos la previsione usando SOLO le candele fino a quel momento. Poi la
confronta subito con quello che e' successo davvero dopo.

    python backtest.py                    -> 300 prove, una ogni ora (M15)
    python backtest.py --prove 100        -> prova veloce
    python backtest.py --prove 1000       -> piu' affidabile (piu' lento)

Non apre ordini. Alla fine stampa il report e salva un file da aprire con
Excel nella cartella data.
"""
import argparse
import csv
import time
from datetime import datetime

import numpy as np

import config
from forecast import load_predictor, run_forecasts
from journal import compute_stats, format_stats
from mt5_data import MT5Candles, normalize_timeframe


def test_points(n_candles, lookback, pred_len, prove, passo):
    """Indici delle candele 'ultime viste' per ogni prova (dalla piu' vecchia)."""
    last_possible = n_candles - pred_len - 1        # servono pred_len candele dopo
    first_possible = lookback - 1                   # servono lookback candele prima
    points = list(range(last_possible, first_possible - 1, -passo))[:prove]
    return sorted(points)


def evaluate_point(history, idx, pred_len, summary):
    """Aggiunge al riassunto il prezzo vero dopo pred_len candele."""
    window = history.iloc[idx + 1: idx + 1 + pred_len]
    row = dict(summary)
    row.update({
        "status": "verificata",
        "actual_close": round(float(window["close"].iloc[-1]), 5),
        "actual_high": round(float(window["high"].max()), 5),
        "actual_low": round(float(window["low"].min()), 5),
    })
    return row


def momentum_baseline(history, points, pred_len):
    """
    Regola semplicissima da battere: 'continua come le ultime pred_len candele'.
    Ritorna la % di volte che ha indovinato la direzione.
    """
    closes = history["close"].to_numpy(dtype=float)
    ok = tot = 0
    for i in points:
        past = closes[i] - closes[i - pred_len]
        future = closes[i + pred_len] - closes[i]
        if past == 0 or future == 0:
            continue
        tot += 1
        ok += (past > 0) == (future > 0)
    return round(100 * ok / tot, 1) if tot else None


def run_backtest(history, predictor, timeframe, pred_len, samples, prove, passo,
                 batch=5, lookback=None, progress=print):
    lookback = lookback or config.LOOKBACK
    points = test_points(len(history), lookback, pred_len, prove, passo)
    if not points:
        raise RuntimeError("Troppe poche candele per il backtest: riduci --prove o --passo")
    rows = []
    t0 = time.time()
    for k in range(0, len(points), batch):
        chunk = points[k:k + batch]
        hists = [history.iloc[i - lookback + 1: i + 1] for i in chunk]
        summaries = run_forecasts(predictor, hists, timeframe, pred_len, samples)
        rows += [evaluate_point(history, i, pred_len, s) for i, s in zip(chunk, summaries)]
        done = len(rows)
        eta = (time.time() - t0) / done * (len(points) - done)
        progress(f"  {done}/{len(points)} prove fatte  (mancano circa {eta / 60:.0f} minuti)")
    return rows, momentum_baseline(history, points, pred_len)


def save_csv(rows, path):
    """CSV per Excel italiano: separatore ; e virgola decimale."""
    cols = ["last_candle_time", "last_close", "bias", "upside_probability",
            "volatility_up_probability", "mean_final_close", "p10_final_close",
            "p90_final_close", "actual_close", "actual_high", "actual_low"]
    names = ["ora candela", "prezzo", "tendenza", "prob. rialzo", "prob. volatilita",
             "prezzo previsto", "range basso", "range alto", "prezzo vero", "massimo vero",
             "minimo vero", "corretto?"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(names)
        for r in rows:
            up = r["actual_close"] > r["last_close"]
            if r["bias"] == "NEUTRO":
                ok = "-"
            else:
                ok = "SI" if up == (r["bias"] == "RIALZO") else "NO"
            vals = [str(r[c]).replace(".", ",") if isinstance(r[c], float) else r[c] for c in cols]
            w.writerow(vals + [ok])


def main(argv=None):
    p = argparse.ArgumentParser(description="Backtest Kronos sulle candele passate di MT5")
    p.add_argument("--symbol", default=config.DEFAULT_SYMBOL)
    p.add_argument("--timeframe", default=config.DEFAULT_TIMEFRAME)
    p.add_argument("--prove", type=int, default=300, help="quante previsioni fare (default 300)")
    p.add_argument("--passo", type=int, default=4, help="ogni quante candele fare una prova (default 4)")
    p.add_argument("--scenari", type=int, default=10, help="scenari per previsione (default 10)")
    p.add_argument("--candele-future", type=int, default=config.PRED_LEN, dest="pred_len")
    a = p.parse_args(argv)

    tf = normalize_timeframe(a.timeframe)
    need = config.LOOKBACK + a.prove * a.passo + a.pred_len + 5
    print(f"Backtest {a.symbol} {tf}: {a.prove} prove, una ogni {a.passo} candele, "
          f"{a.scenari} scenari, previsione a {a.pred_len} candele")

    candles = MT5Candles()
    try:
        history = candles.get_candles(a.symbol, tf, need)
    finally:
        candles.shutdown()
    print(f"Candele lette da MT5: {len(history)} "
          f"(dal {history['timestamps'].iloc[0]} al {history['timestamps'].iloc[-1]})")

    print("Carico Kronos...")
    predictor = load_predictor()
    rows, baseline = run_backtest(history, predictor, tf, a.pred_len, a.scenari, a.prove, a.passo)

    stats = compute_stats(rows)
    period = f"{rows[0]['last_candle_time'][:10]} → {rows[-1]['last_candle_time'][:10]}"
    print()
    print(format_stats(stats, f"Backtest Kronos {a.symbol} {tf} ({period})"))
    if baseline is not None:
        print(f"Confronto: la regola 'continua come le ultime {a.pred_len} candele' "
              f"indovina la direzione il {baseline}% delle volte")
    ups = np.mean([r["actual_close"] > r["last_close"] for r in rows]) * 100
    print(f"Nel periodo l'oro è salito nel {ups:.0f}% delle prove "
          "(se è molto lontano da 50%, il periodo era in forte tendenza)")

    out = config.DATA_DIR / f"backtest_{a.symbol}_{tf}_{datetime.now():%Y%m%d_%H%M}.csv"
    save_csv(rows, out)
    print(f"\nTutte le prove una per una (apribile con Excel): {out}")


if __name__ == "__main__":
    main()
