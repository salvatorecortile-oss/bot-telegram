"""
Test del motore V-Formation su percorsi di prezzo costruiti a mano.
Esecuzione: python backtest/test_vformation.py  (oppure con pytest)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vformation_engine import D_BROKEN, D_FILLED, Params, run_backtest  # noqa: E402

PIP = 0.0001
STEP = 0.0005          # movimento per barra
WICK = 0.0001

# A=1.1000 → B=1.1100 (impulso) → C=1.1060 → D=1.1080 → E=1.1040 (V, sotto C, ritraccio 60%)
# → F=1.1090 (sopra D: rango S) → ritorno al 50% di E-F (1.1065) → salita oltre B (TP2)
WAYPOINTS_OK = [1.1030, 1.1000, 1.1100, 1.1060, 1.1080, 1.1040, 1.1090, 1.1060, 1.1130]
# la gamba destra si ferma sotto D (V non confermata) e il prezzo crolla sotto E: nessun ordine
WAYPOINTS_BROKEN = [1.1030, 1.1000, 1.1100, 1.1060, 1.1080, 1.1040, 1.1070, 1.1000]


def make_bars(waypoints, mirror=False):
    closes = [waypoints[0]] * 20                       # barre piatte iniziali per l'ATR
    for a, b in zip(waypoints[:-1], waypoints[1:]):
        steps = max(1, int(round(abs(b - a) / STEP)))
        closes += list(np.linspace(a, b, steps + 1)[1:])
    closes += [waypoints[-1]] * 20
    c = np.array(closes)
    if mirror:                                         # stesso percorso ribaltato (per lo short)
        c = 2.2 - c
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) + WICK
    l = np.minimum(o, c) - WICK
    t = pd.date_range("2025-03-03 08:00", periods=len(c), freq="5min")
    return pd.DataFrame({"time": t, "open": o, "high": h, "low": l, "close": c})


def params(**kw):
    base = dict(bias_mode="off", use_session=False, imp_min_atr=2.0, spread_pips=0.0)
    base.update(kw)
    return Params(**base)


def run(df, p):
    return run_backtest(df, p, point=0.00001, pip=PIP, server_tz="UTC")


def test_long_v_hits_tp1_and_tp2():
    trades, diag = run(make_bars(WAYPOINTS_OK), params())
    assert len(trades) == 1, trades
    tr = trades.iloc[0]
    assert tr["lato"] == "long" and tr["rango"] == "S"
    assert abs(tr["entry"] - 1.1065) < 2 * PIP, tr["entry"]     # 50% della gamba destra
    assert abs(tr["tp1"] - (1.1090 + WICK)) < 1e-9               # massimo della gamba destra
    assert abs(tr["tp2"] - (1.1100 + WICK)) < 1e-9               # massimo dell'impulso
    assert "TP1" in tr["uscite"] and "TP2" in tr["uscite"]
    assert tr["R"] > 0.8, tr["R"]
    assert diag[D_FILLED] == 1


def test_short_is_mirror_of_long():
    long_tr, _ = run(make_bars(WAYPOINTS_OK), params())
    short_tr, _ = run(make_bars(WAYPOINTS_OK, mirror=True), params())
    assert len(short_tr) == 1 and short_tr.iloc[0]["lato"] == "short"
    assert abs(short_tr.iloc[0]["R"] - long_tr.iloc[0]["R"]) < 1e-6


def test_no_trade_if_v_is_broken_before_entry():
    trades, diag = run(make_bars(WAYPOINTS_BROKEN), params())
    assert trades.empty, trades
    assert diag[D_BROKEN] >= 1


def test_spread_requires_deeper_pullback():
    # il long compra all'ASK: con spread di 10 pips il ritraccio fino a 1.1059 (bid)
    # non basta più per eseguire il limite a ~1.1065
    no_cost, _ = run(make_bars(WAYPOINTS_OK), params())
    with_cost, _ = run(make_bars(WAYPOINTS_OK), params(spread_pips=10.0))
    assert len(no_cost) == 1
    assert with_cost.empty


def test_bias_filter_blocks_counter_trend():
    # lunga discesa da 1.2000: sull'H1 il prezzo resta sotto l'EMA 50 → bias short, il long è vietato
    df = make_bars([1.2000] + WAYPOINTS_OK[1:])
    blocked, _ = run(df, params(bias_mode="ema", htf="1h", htf_ema_len=50))
    allowed, _ = run(df, params(bias_mode="off"))
    assert (allowed["lato"] == "long").sum() == 1
    assert blocked.empty or not (blocked["lato"] == "long").any()


if __name__ == "__main__":
    tests = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for fn in tests:
        fn()
        print(f"OK  {fn.__name__}")
    print(f"\n{len(tests)} test superati")
