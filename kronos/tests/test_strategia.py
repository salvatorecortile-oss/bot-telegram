"""
Test del backtest della strategia (senza MT5 e senza modello).

    python tests/test_strategia.py
"""
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from strategia import (detect_signals, format_trade_stats, load_forecasts_csv,  # noqa: E402
                       plan_trade, simulate, trade_stats)

T0 = pd.Timestamp("2026-11-24 10:00")


def ts(i):
    return str(T0 + pd.Timedelta(minutes=15 * i))


def fc(i, bias, close=2000.0, p10=1990.0, p90=2010.0):
    return {"last_candle_time": ts(i), "last_close": close, "bias": bias,
            "upside_probability": 0.7 if bias == "RIALZO" else 0.3,
            "p10_final_close": p10, "p90_final_close": p90, "mean_final_close": close}


def candles(rows):
    """rows: lista di (high, low, close)."""
    return pd.DataFrame({"timestamps": [T0 + pd.Timedelta(minutes=15 * i) for i in range(len(rows))],
                         "high": [r[0] for r in rows], "low": [r[1] for r in rows],
                         "close": [r[2] for r in rows]})


def test_detect_signals_only_on_change():
    seq = ["RIBASSO", "RIBASSO", "RIBASSO", "RIALZO", "NEUTRO", "RIALZO", "RIALZO",
           "RIBASSO", "RIALZO", "RIBASSO", "RIBASSO"]
    f = [fc(i, b) for i, b in enumerate(seq)]
    s1 = detect_signals(f, conferma=1)
    assert [(x["last_candle_time"], x["direction"]) for x in s1] == [
        (ts(3), "BUY"), (ts(7), "SELL"), (ts(8), "BUY"), (ts(9), "SELL")]
    # con conferma 2: il RIALZO isolato all'indice 8 non basta, NEUTRO non interrompe
    s2 = detect_signals(f, conferma=2)
    assert [(x["last_candle_time"], x["direction"]) for x in s2] == [(ts(5), "BUY"), (ts(10), "SELL")]
    # la prima tendenza non e' un segnale
    assert detect_signals([fc(0, "RIALZO"), fc(1, "RIALZO")], conferma=1) == []


def test_plan_trade():
    buy = dict(fc(0, "RIALZO", 2000, 1994, 2010), direction="BUY")
    assert plan_trade(buy) == {"entry": 2000.0, "tp": 2010.0, "sl": 1994.0}
    sell = dict(fc(0, "RIBASSO", 2000, 1990, 2004), direction="SELL")
    assert plan_trade(sell) == {"entry": 2000.0, "tp": 1990.0, "sl": 2004.0}
    # TP piu' corto dello SL -> scartato
    bad = dict(fc(0, "RIALZO", 2000, 1990, 2004), direction="BUY")
    assert plan_trade(bad) is None
    assert plan_trade(bad, min_rr=0.3) == {"entry": 2000.0, "tp": 2004.0, "sl": 1990.0}
    # distanza minima
    tiny = dict(fc(0, "RIALZO", 2000, 1999.5, 2000.5), direction="BUY")
    assert plan_trade(tiny, min_dist=2) == {"entry": 2000.0, "tp": 2002.0, "sl": 1998.0}


def _sig(i, direction, p10=1990.0, p90=2010.0):
    return dict(fc(i, "RIALZO" if direction == "BUY" else "RIBASSO", 2000, p10, p90), direction=direction)


def test_simulate_tp_sl_timeout_reverse():
    flat = (2001, 1999, 2000)
    # TP: BUY a 2000, TP 2010 toccato alla candela 3
    c = candles([flat, flat, flat, (2011, 1999, 2009), flat])
    tr, _ = simulate([_sig(0, "BUY")], c, spread=0.5)
    assert tr[0]["esito"] == "TP" and tr[0]["profitto"] == 9.5 and tr[0]["candele"] == 3
    # TP e SL nella stessa candela -> conta SL
    c = candles([flat, (2011, 1989, 2000), flat])
    tr, _ = simulate([_sig(0, "BUY")], c, spread=0.5)
    assert tr[0]["esito"] == "SL" and tr[0]["profitto"] == -10.5
    # SELL con TP
    c = candles([flat, (2001, 1989, 1990)])
    tr, _ = simulate([_sig(0, "SELL")], c, spread=0.0)
    assert tr[0]["esito"] == "TP" and tr[0]["profitto"] == 10.0
    # a tempo
    c = candles([flat] * 5 + [(2003, 1999, 2003)])
    tr, _ = simulate([_sig(0, "BUY")], c, spread=0.0, max_candele=5)
    assert tr[0]["esito"] == "TEMPO" and tr[0]["profitto"] == 3.0
    # cambio opposto con operazione aperta: chiude e gira
    c = candles([flat, flat, (2001, 1996, 1997), flat, (2001, 1986, 1987)])
    sigs = [_sig(0, "BUY"), dict(_sig(2, "SELL", 1987, 2007), last_close=1997.0)]
    tr, _ = simulate(sigs, c, spread=0.0)
    assert [t["esito"] for t in tr] == ["GIRATA", "TP"]
    assert tr[0]["profitto"] == -3.0 and tr[1]["entry"] == 1997.0 and tr[1]["profitto"] == 10.0


def test_stats_and_format():
    flat = (2001, 1999, 2000)
    c = candles([flat, (2011, 1999, 2009), flat, flat, (2001, 1989, 1990), flat])
    sigs = [_sig(0, "BUY"), _sig(3, "BUY")]
    tr, skipped = simulate(sigs, c, spread=0.0)
    s = trade_stats(tr, skipped)
    assert s["operazioni"] == 2 and s["vinte"] == 1 and s["totale"] == 0.0
    assert s["profit_factor"] == 1.0 and s["max_drawdown"] == 10.0 and s["peggior_serie_perdite"] == 1
    txt = format_trade_stats(s, "Prova", 0.0)
    assert "Vinte 1 / perse 1" in txt and "Risultato totale: 0.0 $" in txt
    assert "Nessuna operazione" in format_trade_stats(trade_stats([]), "Prova", 0.3)


def test_csv_roundtrip_with_backtest():
    from backtest import save_csv
    rows = [dict(fc(i, b), volatility_up_probability=0.5, actual_close=2001.5, actual_high=2002.0,
                 actual_low=1999.0, p10_final_close=1990.25)
            for i, b in [(1, "RIALZO"), (0, "RIBASSO")]]
    out = Path(tempfile.mkdtemp()) / "bt.csv"
    save_csv(rows, out)
    back = load_forecasts_csv(out)
    assert [r["last_candle_time"] for r in back] == [ts(0), ts(1)]       # riordinate per ora
    assert back[0]["p10_final_close"] == 1990.25 and back[1]["bias"] == "RIALZO"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK  {t.__name__}")
    print(f"\nTutti i {len(tests)} test superati.")
