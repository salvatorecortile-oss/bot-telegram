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
        last = float(df_list[0]["close"].iloc[-1])
        out = []
        for i in range(len(df_list)):
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


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK  {t.__name__}")
    print(f"\nTutti i {len(tests)} test superati.")
