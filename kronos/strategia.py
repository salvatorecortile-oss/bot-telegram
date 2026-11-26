"""
Backtest della STRATEGIA: segnale solo quando Kronos cambia tendenza
(RIBASSO -> RIALZO o RIALZO -> RIBASSO), con entrata, TP e SL presi dagli
scenari di Kronos. Simula candela per candela cosa tocca prima il prezzo,
il TP o lo SL, togliendo lo spread.

Usa le previsioni gia' calcolate da backtest.py (file CSV in data), quindi
gira in pochi secondi e si possono provare impostazioni diverse:

    python strategia.py                         -> usa l'ultimo backtest in data
    python strategia.py --spread 0.4            -> spread del broker in $
    python strategia.py --conferma 1            -> cambio senza conferma
    python strategia.py --tp 0.5 --sl 1         -> TP piu' vicino

Non apre ordini. I risultati sono in $ con 0,01 lotti (1 oncia):
1 $ di movimento dell'oro = 1 $ di guadagno o perdita.

COME CALCOLA TP E SL (posizione BUY; per SELL e' tutto speculare):
- entrata = chiusura della candela che conferma il cambio
- TP = entrata + distanza fino al 90% degli scenari (p90) x --tp
- SL = entrata - distanza fino al 10% degli scenari (p10) x --sl
- distanze minime --min-dist $; segnale scartato se TP/SL < --min-rr
- se dopo --max-candele non ha toccato nulla, chiude a mercato
- se arriva il cambio opposto con un'operazione aperta, la chiude e gira
- se nella stessa candela tocca sia TP sia SL, conta SL (ipotesi pessimista)
"""
import argparse
import csv
from datetime import datetime
from pathlib import Path

import pandas as pd

import config
from mt5_data import MT5Candles, normalize_timeframe

CSV_COLS = {
    "ora candela": "last_candle_time", "prezzo": "last_close", "tendenza": "bias",
    "prob. rialzo": "upside_probability", "range basso": "p10_final_close",
    "range alto": "p90_final_close", "prezzo previsto": "mean_final_close",
}


def _num(x):
    return float(str(x).replace(",", "."))


def load_forecasts_csv(path):
    """Legge il CSV di backtest.py (separatore ; e virgola decimale)."""
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            d = {new: r[old] for old, new in CSV_COLS.items()}
            for k in ("last_close", "upside_probability", "p10_final_close",
                      "p90_final_close", "mean_final_close"):
                d[k] = _num(d[k])
            rows.append(d)
    rows.sort(key=lambda d: d["last_candle_time"])
    return rows


def detect_signals(forecasts, conferma=2):
    """
    Segnali solo ai cambi di tendenza. NEUTRO non cambia nulla.
    Il cambio vale solo dopo `conferma` previsioni di fila con la nuova tendenza.
    La prima tendenza dell'elenco e' il punto di partenza, non un segnale.
    """
    signals = []
    current = None
    streak_dir, streak = None, 0
    for f in forecasts:
        b = f["bias"]
        if b not in ("RIALZO", "RIBASSO"):
            continue
        if b == current:
            streak_dir, streak = None, 0
            continue
        if b == streak_dir:
            streak += 1
        else:
            streak_dir, streak = b, 1
        if current is None:
            if streak >= conferma:
                current, streak_dir, streak = b, None, 0
            continue
        if streak >= conferma:
            current, streak_dir, streak = b, None, 0
            signals.append(dict(f, direction="BUY" if b == "RIALZO" else "SELL"))
    return signals


def plan_trade(sig, tp_mult=1.0, sl_mult=1.0, min_dist=2.0, min_rr=1.0):
    """Entrata, TP, SL di un segnale; None se il rapporto TP/SL e' troppo basso."""
    entry = sig["last_close"]
    if sig["direction"] == "BUY":
        tp_dist = (sig["p90_final_close"] - entry) * tp_mult
        sl_dist = (entry - sig["p10_final_close"]) * sl_mult
    else:
        tp_dist = (entry - sig["p10_final_close"]) * tp_mult
        sl_dist = (sig["p90_final_close"] - entry) * sl_mult
    tp_dist, sl_dist = max(tp_dist, min_dist), max(sl_dist, min_dist)
    if tp_dist / sl_dist < min_rr:
        return None
    sign = 1 if sig["direction"] == "BUY" else -1
    return {"entry": round(entry, 2), "tp": round(entry + sign * tp_dist, 2),
            "sl": round(entry - sign * sl_dist, 2)}


def simulate(signals, candles, spread=0.3, max_candele=24, **plan_kw):
    """
    candles: DataFrame con timestamps, high, low, close (tutte le candele del periodo).
    Ritorna la lista delle operazioni chiuse.
    """
    times = pd.to_datetime(candles["timestamps"]).astype(str).tolist()
    pos = {t: i for i, t in enumerate(times)}
    highs = candles["high"].to_numpy(dtype=float)
    lows = candles["low"].to_numpy(dtype=float)
    closes = candles["close"].to_numpy(dtype=float)
    sig_at = {}
    for s in signals:
        i = pos.get(str(pd.Timestamp(s["last_candle_time"])))
        if i is not None:
            sig_at[i] = s

    trades, skipped = [], 0
    open_t = None

    def close(t, i, price, why):
        sign = 1 if t["direction"] == "BUY" else -1
        t.update(exit_time=times[i], exit=round(price, 2), esito=why,
                 profitto=round((price - t["entry"]) * sign - spread, 2), candele=i - t["i"])
        trades.append(t)

    for i in range(len(times)):
        # 1) l'operazione aperta tocca SL o TP in questa candela?
        if open_t is not None and i > open_t["i"]:
            buy = open_t["direction"] == "BUY"
            hit_sl = lows[i] <= open_t["sl"] if buy else highs[i] >= open_t["sl"]
            hit_tp = highs[i] >= open_t["tp"] if buy else lows[i] <= open_t["tp"]
            if hit_sl:
                close(open_t, i, open_t["sl"], "SL")
                open_t = None
            elif hit_tp:
                close(open_t, i, open_t["tp"], "TP")
                open_t = None
            elif i - open_t["i"] >= max_candele:
                close(open_t, i, closes[i], "TEMPO")
                open_t = None
        # 2) alla chiusura di questa candela arriva un nuovo segnale?
        s = sig_at.get(i)
        if s is None:
            continue
        if open_t is not None and open_t["direction"] != s["direction"]:
            close(open_t, i, closes[i], "GIRATA")
            open_t = None
        if open_t is not None:
            continue
        plan = plan_trade(s, **plan_kw)
        if plan is None:
            skipped += 1
            continue
        open_t = dict(plan, direction=s["direction"], entry_time=times[i], i=i,
                      prob_rialzo=s["upside_probability"])
    return trades, skipped


def trade_stats(trades, skipped=0):
    out = {"operazioni": len(trades), "scartate": skipped}
    if not trades:
        return out
    p = [t["profitto"] for t in trades]
    wins = [x for x in p if x > 0]
    losses = [x for x in p if x <= 0]
    equity, peak, dd = 0.0, 0.0, 0.0
    streak = worst = 0
    for x in p:
        equity += x
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
        streak = streak + 1 if x <= 0 else 0
        worst = max(worst, streak)
    first = pd.Timestamp(trades[0]["entry_time"])
    last = pd.Timestamp(trades[-1]["exit_time"])
    days = max((last - first).total_seconds() / 86400, 1)
    out.update({
        "vinte": len(wins), "perse": len(losses),
        "percentuale_vinte": round(100 * len(wins) / len(p), 1),
        "per_esito": {e: sum(t["esito"] == e for t in trades) for e in ("TP", "SL", "TEMPO", "GIRATA")},
        "totale": round(sum(p), 2),
        "media_vincita": round(sum(wins) / len(wins), 2) if wins else 0.0,
        "media_perdita": round(sum(losses) / len(losses), 2) if losses else 0.0,
        "profit_factor": round(sum(wins) / -sum(losses), 2) if losses and sum(losses) < 0 else None,
        "max_drawdown": round(dd, 2),
        "peggior_serie_perdite": worst,
        "operazioni_al_giorno": round(len(p) / days, 1),
    })
    return out


def format_trade_stats(s, title, spread):
    lines = [f"📈 {title}", f"Operazioni: {s['operazioni']} (scartate per TP/SL sfavorevole: {s['scartate']})"]
    if not s["operazioni"]:
        lines.append("Nessuna operazione: troppo pochi cambi di tendenza nel periodo.")
        return "\n".join(lines)
    e = s["per_esito"]
    pf = s["profit_factor"] if s["profit_factor"] is not None else "-"
    lines += [
        f"Vinte {s['vinte']} / perse {s['perse']} ({s['percentuale_vinte']}% vinte)",
        f"Chiusura: TP {e['TP']}, SL {e['SL']}, a tempo {e['TEMPO']}, girate al cambio {e['GIRATA']}",
        f"💰 Risultato totale: {s['totale']} $ con 0,01 lotti (spread {spread} $ già tolto)",
        f"Vincita media {s['media_vincita']} $ | perdita media {s['media_perdita']} $",
        f"Profit factor: {pf} (sopra 1 = guadagna, sopra 1,3 = interessante)",
        f"Peggior calo dal massimo: {s['max_drawdown']} $ | peggior serie di perdite: {s['peggior_serie_perdite']}",
        f"Operazioni al giorno: {s['operazioni_al_giorno']}",
    ]
    if s["operazioni"] < 30:
        lines.append(f"⚠️ Solo {s['operazioni']} operazioni: troppo poche per conclusioni sicure.")
    return "\n".join(lines)


def save_trades_csv(trades, path):
    cols = ["entry_time", "direction", "entry", "tp", "sl", "exit_time", "exit", "esito", "profitto", "candele"]
    names = ["ora entrata", "tipo", "entrata", "TP", "SL", "ora uscita", "uscita", "esito", "profitto $", "candele"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(names)
        for t in trades:
            w.writerow([str(t[c]).replace(".", ",") if isinstance(t[c], float) else t[c] for c in cols])


def latest_backtest_csv(symbol, timeframe):
    files = sorted(config.DATA_DIR.glob(f"backtest_{symbol}_{timeframe}_*.csv"))
    return files[-1] if files else None


def main(argv=None):
    p = argparse.ArgumentParser(description="Backtest della strategia 'cambio di tendenza' di Kronos")
    p.add_argument("--da-file", help="CSV di backtest.py (default: l'ultimo in data)")
    p.add_argument("--symbol", default=config.DEFAULT_SYMBOL)
    p.add_argument("--timeframe", default=config.DEFAULT_TIMEFRAME)
    p.add_argument("--conferma", type=int, default=2, help="previsioni di fila per confermare il cambio (default 2)")
    p.add_argument("--tp", type=float, default=1.0, help="moltiplicatore distanza TP (default 1)")
    p.add_argument("--sl", type=float, default=1.0, help="moltiplicatore distanza SL (default 1)")
    p.add_argument("--min-dist", type=float, default=2.0, help="distanza minima TP e SL in $ (default 2)")
    p.add_argument("--min-rr", type=float, default=1.0, help="minimo rapporto TP/SL (default 1)")
    p.add_argument("--spread", type=float, default=0.3, help="spread del broker in $ (default 0,30)")
    p.add_argument("--max-candele", type=int, default=24, help="chiude a mercato dopo N candele (default 24)")
    a = p.parse_args(argv)

    tf = normalize_timeframe(a.timeframe)
    path = Path(a.da_file) if a.da_file else latest_backtest_csv(a.symbol, tf)
    if not path or not path.exists():
        raise SystemExit("Nessun file di backtest trovato: lancia prima  python backtest.py")
    forecasts = load_forecasts_csv(path)
    print(f"Previsioni lette: {len(forecasts)} da {path.name}")

    start = pd.Timestamp(forecasts[0]["last_candle_time"])
    candles_src = MT5Candles()
    try:
        candles = candles_src.get_candles(a.symbol, tf, 20000)
    finally:
        candles_src.shutdown()
    if pd.Timestamp(candles["timestamps"].iloc[0]) > start:
        raise SystemExit("MT5 non ha candele abbastanza vecchie per questo backtest")
    candles = candles[candles["timestamps"] >= start].reset_index(drop=True)

    signals = detect_signals(forecasts, a.conferma)
    trades, skipped = simulate(signals, candles, spread=a.spread, max_candele=a.max_candele,
                               tp_mult=a.tp, sl_mult=a.sl, min_dist=a.min_dist, min_rr=a.min_rr)
    s = trade_stats(trades, skipped)
    title = (f"Strategia Kronos {a.symbol} {tf} | conferma {a.conferma}, TP x{a.tp}, SL x{a.sl}, "
             f"min {a.min_dist}$, R/R {a.min_rr}")
    print(f"Cambi di tendenza trovati: {len(signals)}\n")
    print(format_trade_stats(s, title, a.spread))
    out = config.DATA_DIR / f"strategia_{a.symbol}_{tf}_{datetime.now():%Y%m%d_%H%M}.csv"
    save_trades_csv(trades, out)
    print(f"\nOperazioni una per una (apribile con Excel): {out}")


if __name__ == "__main__":
    main()
