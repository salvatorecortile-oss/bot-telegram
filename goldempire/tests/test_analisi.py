"""
Test dell'analisi dei segnali (senza MT5 ne' Telegram).
Avvio: python tests/test_analisi.py
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import analisi_segnali as A  # noqa: E402
import database as db  # noqa: E402
import test_parser as T  # noqa: E402

# ---------------- operazioni vere del bot (database) ----------------
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


for _ in range(8):
    trade(5.3, "SELL", 100)
trade(5.1, "BUY", -50, "CLOSED_SL")
for _ in range(9):
    trade(7, "BUY", -200, "CLOSED_SL")
trade(2, "BUY", 30)

trades = A.load_trades(path)
assert len(trades) == 19
assert abs(A.trade_usd(trades[0], {}) - 10.0) < 1e-9
assert A.trade_usd(trades[0], {int(trades[0]["position_ticket"]): 12.5}) == 12.5
s7 = A.stats([A.trade_usd(r, {}) for r in trades if r["signal_no"] == 7])
assert A.verdict(s7) == "BLOCCARE" and s7["streak"] == 9
assert A.verdict(A.stats([3.0])) == "POCHI DATI" and A.verdict(A.stats([-3.0])) == "POCHI DATI (finora perde)"
print("OK - statistiche del bot.")

# ---------------- ricostruzione della sala ----------------
t0 = datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)


def m(mid, minutes, text, reply=None):
    return {"id": mid, "date": (t0 + timedelta(minutes=minutes)).isoformat(), "reply_to": reply, "text": text}


# candele M1: prezzo fermo a 4100 tranne dove indicato
base = int(t0.timestamp())
bars = {base + 60 * i: (base + 60 * i, 4100.0, 4100.5, 4099.5, 4100.0) for i in range(0, 600)}
bars[base + 60 * 30] = (base + 60 * 30, 4100.0, 4100.5, 4079.0, 4080.0)   # minuto 30: scende fino a 4079
bars[base + 60 * 200] = (base + 60 * 200, 4100.0, 4170.0, 4099.0, 4100.0)  # minuto 200: picco a 4170

SIGNAL_3_SELL = T.SIGNAL_3_BUY.replace("COMPRA", "VENDI").replace("4160,08", "4100,00") \
    .replace("4135,99", "4120,00").replace("4255,99", "4080,00")
messages = [
    m(1, 0, SIGNAL_3_SELL),                         # TP 4080 toccato al minuto 30 (nessun messaggio)
    m(2, 40, T.ENTRA_53_SELL),                      # 5.3 SELL 4100,50, SL 4350
    m(3, 60, T.SIGNAL_4_BUY.replace("4155,08", "4100,00").replace("4107,80", "4050,00")),
    m(4, 90, T.SIGNAL_4_CLOSED, reply=3),           # chiusa dalla sala con +308,2 pips (dal messaggio)
    m(5, 100, T.SIGNAL_2_SELL.replace("4204,38", "4100,00").replace("4214,33", "4160,00")
      .replace("4169,15", "4000,00")),
    m(6, 120, T.SIGNAL_2_BE, reply=5),              # "Nuovo stop 4203,40": usa il valore del messaggio
    m(7, 150, "🔴 CHIUDI ORA · SIGNAL 5.3 SELL", reply=2),
    m(8, 160, T.SIGNAL_6_SELL_2PCT.replace("3954,23", "4100,00").replace("3888,97", "4000,00")
      .replace("3986,47", "4150,00")),              # SL 4150 colpito al minuto 200 (picco 4170)
]
sala = A.simulate(messages, list(bars.values()), now=base + 60 * 599)
by_id = {t["id"]: t for t in sala}
assert by_id[1]["status"] == "CHIUSA" and by_id[1]["reason"] == "TP" and abs(by_id[1]["pips"] - 200) < 1e-6, by_id[1]
assert by_id[3]["reason"] == "CHIUSA DALLA SALA" and by_id[3]["pips"] == 308.2, by_id[3]
assert by_id[2]["reason"] == "CHIUSA DALLA SALA" and abs(by_id[2]["pips"] - 5.0) < 1e-6, by_id[2]  # 4100,50 -> 4100
assert by_id[8]["reason"] == "SL" and abs(by_id[8]["pips"] + 500) < 1e-6, by_id[8]
assert by_id[5]["sl"] == 4203.40 and by_id[5]["be"]                   # BE applicato
assert by_id[5]["status"] == "APERTA" and by_id[5]["reason"] == "ANCORA APERTA"  # il picco 4170 non tocca 4203,40
print("OK - sala ricostruita: TP/SL dalle candele, chiusure dai messaggi.")

# Inversione SIGNAL 5: un 5 BUY chiude il 5 SELL aperto
inv = A.simulate([m(1, 0, T.ENTRA_53_SELL.replace("5.3", "5")),
                  m(2, 50, T.SIGNAL_5_INVERSIONE)], list(bars.values()), now=base + 60 * 100)
assert inv[0]["reason"] == "INVERSIONE" and inv[1]["status"] == "APERTA", inv
print("OK - inversione SIGNAL 5.")

# Report e CSV
bot_signals = A.load_all_signals(path)
text = A.report(sala, trades, {}, bot_signals, t0)
assert "LA SALA" in text and "Per singolo segnale" in text and "GIUDIZIO FINALE" in text and "NON aperti" in text
csv_path = os.path.join(tempfile.mkdtemp(), "s.csv")
A.write_sala_csv(sala, bot_signals, csv_path)
assert open(csv_path, encoding="utf-8-sig").read().count("\n") == len(sala) + 1
print(text)
print("OK - analisi segnali.")
