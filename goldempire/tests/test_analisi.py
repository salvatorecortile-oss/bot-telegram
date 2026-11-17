"""
Test dell'analisi dei segnali (senza MT5).
Avvio: python tests/test_analisi.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analisi_segnali as A  # noqa: E402
import database as db  # noqa: E402

path = os.path.join(tempfile.mkdtemp(), "a.db")
db.set_db_path(path)
db.init_database()

sid = 0


def trade(signal_no, direction, pips, status="CLOSED_TP"):
    global sid
    sid += 1
    db.insert_signal(sid, {"signal_no": signal_no, "direction": direction, "entry": 4000, "sl": 3990, "tp": None})
    db.mark_opened(sid, 5000 + sid, 4000, 0.01, 3990, None)
    assert db.claim_close(sid, status, 4000 + pips / 10, pips)


for _ in range(8):           # SIGNAL 5: guadagna
    trade(5.3, "SELL", 100)
trade(5.1, "BUY", -50, "CLOSED_SL")
for _ in range(6):           # SIGNAL 7: perde
    trade(7, "BUY", -200, "CLOSED_SL")
for _ in range(3):
    trade(7, "SELL", 50)
trade(2, "BUY", 30)          # SIGNAL 2: pochi dati

trades = A.load_trades(path)
assert len(trades) == 19
fam, _ = A.analyze(trades, {})
s5, s7 = A.stats(fam["5"]), A.stats(fam["7"])
assert abs(s5["net"] - 75.0) < 1e-6 and s5["n"] == 9, s5        # 8*10 - 5
assert abs(s7["net"] - (-105.0)) < 1e-6 and s7["streak"] == 6, s7
assert A.verdict(s5) == "TENERE" and A.verdict(s7) == "BLOCCARE" and A.verdict(A.stats(fam["2"])) == "POCHI DATI"
# Profitto reale da MT5, se disponibile, al posto della stima
assert A.trade_usd(trades[0], {int(trades[0]["position_ticket"]): 12.5}) == 12.5

text = A.report(trades, {})
assert "EXCLUDED_SIGNALS=7" in text and "BLOCCARE" in text, text
csv_path = os.path.join(tempfile.mkdtemp(), "a.csv")
A.write_csv(trades, {}, csv_path)
assert open(csv_path, encoding="utf-8-sig").read().count("\n") == 20
print(text)
print("OK - analisi segnali.")
