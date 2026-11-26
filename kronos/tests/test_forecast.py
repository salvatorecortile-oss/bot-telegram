"""
Test senza MT5 e senza modello vero: candele finte + Kronos finto.

    python tests/test_forecast.py
"""
import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forecast import Forecaster, format_text, future_timestamps, summarize  # noqa: E402
from main import make_handler  # noqa: E402


def fake_history(n=50, start=2000.0):
    ts = pd.Series(pd.date_range("2026-11-24 10:00", periods=n, freq="15min"))
    close = start + np.arange(n) * 0.5
    return pd.DataFrame({
        "timestamps": ts, "open": close - 0.2, "high": close + 1, "low": close - 1,
        "close": close, "volume": 100.0, "amount": 100.0 * close,
    })


def path(closes, ts):
    closes = np.asarray(closes, dtype=float)
    return pd.DataFrame({"open": closes, "high": closes + 1, "low": closes - 1, "close": closes,
                         "volume": 1.0, "amount": 1.0}, index=ts)


class FakeCandles:
    def __init__(self):
        self.history = fake_history()
        self.calls = 0

    def get_candles(self, symbol, timeframe, count):
        self.calls += 1
        return self.history

    def shutdown(self):
        pass


class FakePredictor:
    """3 scenari su 4 salgono."""
    def __init__(self):
        self.calls = 0

    def predict_batch(self, df_list, x_timestamp_list, y_timestamp_list, pred_len, **kw):
        self.calls += 1
        out = []
        for i in range(len(df_list)):
            last = float(df_list[i]["close"].iloc[-1])
            step = -1.0 if i % 4 == 0 else 1.0
            out.append(path(last + step * np.arange(1, pred_len + 1), y_timestamp_list[i]))
        return out


def test_future_timestamps():
    ts = future_timestamps(pd.Timestamp("2026-11-24 10:00"), "M15", 3)
    assert list(ts) == [pd.Timestamp("2026-11-24 10:15"), pd.Timestamp("2026-11-24 10:30"),
                        pd.Timestamp("2026-11-24 10:45")]


def test_summarize_bias():
    h = fake_history()
    last = h["close"].iloc[-1]
    ts = future_timestamps(h["timestamps"].iloc[-1], "M15", 4)
    up = [path(last + np.arange(1, 5), ts) for _ in range(9)] + [path(last - np.arange(1, 5), ts)]
    r = summarize(h, up, bullish=0.65, bearish=0.35)
    assert r["upside_probability"] == 0.9 and r["bias"] == "RIALZO"
    down = [path(last - np.arange(1, 5), ts) for _ in range(10)]
    assert summarize(h, down, bullish=0.65, bearish=0.35)["bias"] == "RIBASSO"
    mixed = up[:5] + down[:5]
    assert summarize(h, mixed, bullish=0.65, bearish=0.35)["bias"] == "NEUTRO"


def test_forecaster_and_cache():
    c, p = FakeCandles(), FakePredictor()
    f = Forecaster(c, predictor=p)
    r = f.forecast("XAUUSD", "M15", pred_len=6, samples=8)
    assert r["upside_probability"] == 0.75 and not r["cached"]
    assert len(r["forecast_times"]) == 6 and len(r["mean_path"]) == 6
    r2 = f.forecast("XAUUSD", "M15", pred_len=6, samples=8)
    assert r2["cached"] and p.calls == 1          # stessa candela -> niente ricalcolo
    c.history = fake_history(n=51)                # chiude una nuova candela
    assert not f.forecast("XAUUSD", "M15", pred_len=6, samples=8)["cached"] and p.calls == 2
    assert "Probabilità rialzo: 75.0%" in format_text(r)


def test_invalid_input():
    f = Forecaster(FakeCandles(), predictor=FakePredictor())
    for kw in ({"timeframe": "M7"}, {"samples": 0}, {"pred_len": 500}):
        try:
            f.forecast(**kw)
        except ValueError:
            continue
        raise AssertionError(f"doveva fallire: {kw}")


def test_http_server():
    f = Forecaster(FakeCandles(), predictor=FakePredictor())
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(f))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        assert json.load(urllib.request.urlopen(base + "/health"))["ok"]
        r = json.load(urllib.request.urlopen(base + "/forecast?symbol=XAUUSD&timeframe=M15&samples=4"))
        assert r["ok"] and r["symbol"] == "XAUUSD" and r["samples"] == 4
        txt = urllib.request.urlopen(base + "/forecast?format=text").read().decode("utf-8")
        assert "Kronos" in txt
        try:
            urllib.request.urlopen(base + "/forecast?timeframe=M7")
            raise AssertionError("doveva dare 400")
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        srv.shutdown()


def test_symbol_not_found_message():
    import types
    import mt5_data

    sym = lambda n: types.SimpleNamespace(name=n)
    fake = types.SimpleNamespace(
        terminal_info=lambda: types.SimpleNamespace(path=r"C:\\MT5 Broker"),
        account_info=lambda: types.SimpleNamespace(server="Broker-Live"),
        symbol_select=lambda name, on: False,
        symbols_get=lambda: [sym("EURUSD"), sym("XAUUSD.m"), sym("GOLDmicro")],
        TIMEFRAME_M15=15,
    )
    c = mt5_data.MT5Candles(path="")
    c._connect = lambda: fake
    try:
        c.get_candles("XAUUSD-P", "M15", 10)
        raise AssertionError("doveva fallire")
    except RuntimeError as e:
        msg = str(e)
    assert "GOLDmicro, XAUUSD.m" in msg and "Broker-Live" in msg and "EURUSD" not in msg


def _tmp_journal():
    import tempfile
    from journal import Journal
    d = tempfile.mkdtemp()
    return Journal(Path(d) / "test.db")


def test_journal_save_and_evaluate():
    j = _tmp_journal()
    c, p = FakeCandles(), FakePredictor()
    f = Forecaster(c, predictor=p)
    r = f.forecast("XAUUSD", "M15", pred_len=4, samples=8)   # 75% rialzo -> RIALZO
    assert j.save(r) and not j.save(r)                       # niente doppioni
    full = fake_history(n=60)                                # dopo arrivano 10 candele che salgono
    hist_part = full.iloc[:52]                               # solo 2 candele dopo: troppo presto
    assert j.evaluate("XAUUSD", "M15", hist_part) == 0 and len(j.pending()) == 1
    assert j.evaluate("XAUUSD", "M15", full) == 1 and not j.pending()
    s = j.stats()
    assert s["verificate"] == 1 and s["RIALZO"]["corretti"] == 1
    assert s["RIALZO"]["percentuale"] == 100.0 and s["direzione_maggioranza_pct"] == 100.0
    # 4 candele dopo l'ultima (indice 49): chiusura vera = close dell'indice 53
    assert abs(s["errore_medio"] - abs(float(full["close"].iloc[53]) - r["mean_final_close"])) < 0.01
    from journal import format_stats
    assert "RIALZO: 1/1 corretti" in format_stats(s)


def test_journal_expired_and_weekend_gap():
    j = _tmp_journal()
    h = fake_history(n=50)
    r = summarize(h, [path(h["close"].iloc[-1] - np.arange(1, 4),
                           future_timestamps(h["timestamps"].iloc[-1], "M15", 3))] * 5)
    r.update(symbol="XAUUSD", timeframe="M15", model="x")
    assert r["bias"] == "RIBASSO"
    j.save(r)
    # 3 candele dopo un "weekend" di 2 giorni: conta le candele, non le ore
    later = pd.DataFrame({"timestamps": pd.date_range(h["timestamps"].iloc[-1] + pd.Timedelta(days=2),
                                                      periods=3, freq="15min"),
                          "open": 1.0, "high": 1.0, "low": 1.0, "close": [2000.0, 1990.0, 1980.0]})
    assert j.evaluate("XAUUSD", "M15", pd.concat([h, later], ignore_index=True)) == 1
    assert j.stats()["RIBASSO"]["corretti"] == 1
    # previsione troppo vecchia rispetto alle candele disponibili -> scaduta
    j2 = _tmp_journal()
    j2.save(r)
    assert j2.evaluate("XAUUSD", "M15", later) == 0 and j2.stats()["scadute"] == 1


def test_auto_runner_step():
    from auto import AutoRunner
    j = _tmp_journal()
    c = FakeCandles()
    f = Forecaster(c, predictor=FakePredictor())
    f.forecast("XAUUSD", "M15")             # un "altro bot" la chiede per primo
    runner = AutoRunner(f, j, "XAUUSD", "M15")
    runner.step()
    assert j.stats()["totale"] == 1         # salvata lo stesso
    runner.step()
    assert j.stats()["totale"] == 1         # stessa candela: niente doppione
    c.history = fake_history(n=51)
    runner.step()
    assert j.stats()["totale"] == 2


def test_http_stats():
    j = _tmp_journal()
    f = Forecaster(FakeCandles(), predictor=FakePredictor())
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(f, j))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        txt = urllib.request.urlopen(base + "/stats").read().decode("utf-8")
        assert "Registro Kronos" in txt
        assert json.load(urllib.request.urlopen(base + "/stats?format=json"))["totale"] == 0
    finally:
        srv.shutdown()


def test_backtest():
    import tempfile
    from backtest import run_backtest, save_csv, test_points
    from journal import compute_stats, format_stats

    # nessuna prova "vede" il futuro: servono lookback candele prima e pred_len dopo
    pts = test_points(100, lookback=20, pred_len=5, prove=50, passo=3)
    assert pts and pts[0] >= 19 and pts[-1] <= 100 - 5 - 1 and pts == sorted(pts)

    h = fake_history(n=120)                      # prezzo sempre in salita
    seen = []

    class Spy(FakePredictor):
        def predict_batch(self, df_list, **kw):
            seen.extend(float(d["close"].iloc[-1]) for d in df_list)
            return super().predict_batch(df_list, **kw)

    rows, base = run_backtest(h, Spy(), "M15", pred_len=4, samples=4, prove=10, passo=5,
                              batch=3, lookback=30, progress=lambda m: None)
    assert len(rows) == 10
    for r in rows:                               # la previsione parte dall'ultima candela vista
        i = h.index[h["timestamps"].astype(str) == r["last_candle_time"]][0]
        assert r["last_close"] == float(h["close"].iloc[i])
        assert r["actual_close"] == float(h["close"].iloc[i + 4])
    assert max(seen) <= float(h["close"].iloc[-5])   # mai usate le ultime candele "future"
    s = compute_stats(rows)
    assert s["RIALZO"]["percentuale"] == 100.0 and base == 100.0
    assert s["movimento_medio_segnali"] == 2.0       # 4 candele x 0,5 $
    assert "Movimento medio a favore" in format_stats(s)
    out = Path(tempfile.mkdtemp()) / "bt.csv"
    save_csv(rows, out)
    text = out.read_text(encoding="utf-8-sig")
    assert text.startswith("ora candela;") and ";SI" in text and "," in text


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK  {t.__name__}")
    print(f"\nTutti i {len(tests)} test superati.")
