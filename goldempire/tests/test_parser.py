"""Test del parser sui messaggi reali del canale (screen). Avvio: python tests/test_parser.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_parser import parse_signal  # noqa: E402

SIGNAL_2_SELL = """🟣 SIGNAL 2  ⬇️ VENDI   XAUUSD

Ingresso    4204,38
Stop        4214,33  ·  rischio 9,95 $
Obiettivo 1 4169,15  ·  +35,23 $  ·  primo di 4 obiettivi

Valori per 0,01 lotti · XAUUSD"""

SIGNAL_2_TP = """🟣 SIGNAL 2  ✅ OBIETTIVO RAGGIUNTO

Uscita      4169,14
Risultato   +352,4 pips  ·  +35,24 $

Valori per 0,01 lotti"""

SIGNAL_2_BE = """🟣 SIGNAL 2  ⚪ STOP A PAREGGIO

Nuovo stop  4203,40  ·  al prezzo d'ingresso

L’operazione resta aperta."""

SIGNAL_4_SELL = """🟢 SIGNAL 4  ⬇️ VENDI   XAUUSD

Ingresso    4117,69
Stop        4162,11  ·  rischio 44,42 $
Obiettivo   3806,75  ·  +310,9 $

Valori per 0,01 lotti · XAUUSD"""

SIGNAL_4_CLOSED = """🟢 SIGNAL 4  🏁 CHIUSA

Uscita      4086,87
Risultato   +308,2 pips  ·  +30,82 $

Valori per 0,01 lotti"""

SIGNAL_4_BUY = """🟢 SIGNAL 4  ⬆️ COMPRA   XAUUSD

Ingresso    4155,08
Stop        4107,80  ·  rischio 47,28 $
Obiettivo   4486,04  ·  +331,0 $

Valori per 0,01 lotti · XAUUSD"""

SIGNAL_3_BUY = """🟡 SIGNAL 3  ⬆️ COMPRA   XAUUSD

Ingresso    4160,08
Stop        4135,99  ·  rischio 24,09 $
Obiettivo   4255,99  ·  +95,91 $

Valori per 0,01 lotti · XAUUSD"""

SIGNAL_3_STOP = """🟡 SIGNAL 3  ❌ STOP

Uscita      4135,92
Risultato   −241,6 pips  ·  −24,16 $

Valori per 0,01 lotti"""

# Formato nuovo del canale (ottobre 2026).
SIGNAL_2_BUY_NEW = """🟣 SIGNAL 2 – XAUUSD BUY

📥 Ingresso: 4137,44

🎯 TP1: 4163,40
🎯 TP2: comunicato alla chiusura del TP1

🛑 SL: 4131,13

💰 TP1 a 0.01 lot = +25,96$
❌ SL a 0.01 lot = -6,31$

📏 Rischio consigliato: 2% del conto per segnale, contando TUTTE le gambe

⚠️ Questo messaggio non costituisce un consiglio di investimento ed è esclusivamente a scopo didattico."""

# Segnale senza obiettivo: si esce quando lo dice il canale.
SIGNAL_5_BUY_NO_TP = """🟠 SIGNAL 5 – XAUUSD BUY

📥 Ingresso: 4118,78

🎯 Uscita: al segnale della strategia

🛑 SL: 3871,65 (stop d’emergenza, non l’uscita prevista)

📏 Rischio consigliato: 2% del conto per segnale, contando TUTTE le gambe

⚠️ Questo messaggio non costituisce un consiglio di investimento ed è esclusivamente a scopo didattico."""

TESTS = [
    # Ordini pendenti
    (SIGNAL_2_BUY_NEW.replace("XAUUSD BUY", "XAUUSD BUY LIMIT"),
     {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 2, "direction": "BUY", "order_type": "LIMIT",
      "entry": 4137.44, "sl": 4131.13, "tp": 4163.40, "targets_total": 2}),
    (SIGNAL_2_BUY_NEW.replace("XAUUSD BUY", "XAUUSD SELL LIMIT").replace("4163,40", "4100,00")
     .replace("4131,13", "4150,00"),
     {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 2, "direction": "SELL", "order_type": "LIMIT",
      "entry": 4137.44, "sl": 4150.0, "tp": 4100.0, "targets_total": 2}),
    (SIGNAL_2_BUY_NEW.replace("XAUUSD BUY", "XAUUSD BUY STOP"),
     {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 2, "direction": "BUY", "order_type": "STOP",
      "entry": 4137.44, "sl": 4131.13, "tp": 4163.40, "targets_total": 2}),
    ("🟢 SIGNAL 4 ⬇️ VENDI LIMIT XAUUSD\nIngresso 4117,69\nStop 4162,11\nObiettivo 3806,75",
     {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 4, "direction": "SELL", "order_type": "LIMIT",
      "entry": 4117.69, "sl": 4162.11, "tp": 3806.75, "targets_total": 1}),
    ("🟣 SIGNAL 2 – ORDINE ANNULLATO", {"action": "CANCEL", "symbol": "XAUUSD", "signal_no": 2}),
    ("🟣 SIGNAL 2 ❌ CANCELLATO", {"action": "CANCEL", "symbol": "XAUUSD", "signal_no": 2}),
    (SIGNAL_5_BUY_NO_TP, {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 5, "direction": "BUY",
                          "entry": 4118.78, "sl": 3871.65, "tp": None, "targets_total": 1}),
    # Senza TP e senza "Uscita" il messaggio e' incompleto: non si apre.
    ("🟠 SIGNAL 5 – XAUUSD BUY\nIngresso: 4118,78\nSL: 3871,65", None),
    # SL dal lato sbagliato anche senza TP: non si apre.
    (SIGNAL_5_BUY_NO_TP.replace("BUY", "SELL"), None),
    (SIGNAL_2_BUY_NEW, {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 2, "direction": "BUY",
                        "entry": 4137.44, "sl": 4131.13, "tp": 4163.40, "targets_total": 2}),
    (SIGNAL_2_BUY_NEW.replace("BUY", "SELL").replace("4163,40", "4100,00").replace("4131,13", "4150,00"),
     {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 2, "direction": "SELL",
      "entry": 4137.44, "sl": 4150.0, "tp": 4100.0, "targets_total": 2}),
    ("🟣 SIGNAL 2 – TP1 RAGGIUNTO ✅", {"action": "TP_HIT", "symbol": "XAUUSD", "signal_no": 2,
                                       "exit_price": None, "pips": None}),
    ("🟣 SIGNAL 2 – SL HIT", {"action": "SL_HIT", "symbol": "XAUUSD", "signal_no": 2,
                             "exit_price": None, "pips": None}),
    ("🟣 SIGNAL 2 – BREAKEVEN\nNuovo SL: 4137,44", {"action": "BREAKEVEN", "symbol": "XAUUSD",
                                                   "signal_no": 2, "new_sl": 4137.44}),
    ("🟣 SIGNAL 2 – CHIUSO", {"action": "CLOSE", "symbol": "XAUUSD", "signal_no": 2,
                             "exit_price": None, "pips": None}),
    (SIGNAL_2_SELL, {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 2, "direction": "SELL",
                     "entry": 4204.38, "sl": 4214.33, "tp": 4169.15, "targets_total": 4}),
    (SIGNAL_2_TP, {"action": "TP_HIT", "symbol": "XAUUSD", "signal_no": 2,
                   "exit_price": 4169.14, "pips": 352.4}),
    (SIGNAL_2_BE, {"action": "BREAKEVEN", "symbol": "XAUUSD", "signal_no": 2, "new_sl": 4203.40}),
    (SIGNAL_4_SELL, {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 4, "direction": "SELL",
                     "entry": 4117.69, "sl": 4162.11, "tp": 3806.75, "targets_total": 1}),
    (SIGNAL_4_CLOSED, {"action": "CLOSE", "symbol": "XAUUSD", "signal_no": 4,
                       "exit_price": 4086.87, "pips": 308.2}),
    (SIGNAL_4_BUY, {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 4, "direction": "BUY",
                    "entry": 4155.08, "sl": 4107.80, "tp": 4486.04, "targets_total": 1}),
    (SIGNAL_3_BUY, {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 3, "direction": "BUY",
                    "entry": 4160.08, "sl": 4135.99, "tp": 4255.99, "targets_total": 1}),
    (SIGNAL_3_STOP, {"action": "SL_HIT", "symbol": "XAUUSD", "signal_no": 3,
                     "exit_price": 4135.92, "pips": -241.6}),
    # Varianti: grassetto markdown, punto decimale, altro strumento, testo libero.
    ("**🟢 SIGNAL 1 ⬆️ COMPRA XAUUSD**\n\nIngresso **4155.08**\nStop **4107.80**\nObiettivo **4486.04**",
     {"action": "OPEN", "symbol": "XAUUSD", "signal_no": 1, "direction": "BUY",
      "entry": 4155.08, "sl": 4107.80, "tp": 4486.04, "targets_total": 1}),
    ("🟢 SIGNAL 1 ⬆️ COMPRA EURUSD\n\nIngresso 1,0850\nStop 1,0800\nObiettivo 1,0950", None),
    ("Buongiorno a tutti, oggi mercato volatile!", None),
    # Livelli incoerenti (stop dal lato sbagliato): meglio non aprire.
    ("🟢 SIGNAL 1 ⬆️ COMPRA XAUUSD\nIngresso 4155,08\nStop 4200,00\nObiettivo 4486,04", None),
]


def run():
    for text, expected in TESTS:
        if expected and expected["action"] == "OPEN":
            expected = {"order_type": "MARKET", **expected}
        result = parse_signal(text)
        assert result == expected, f"\nTesto:\n{text}\nAtteso: {expected}\nOttenuto: {result}"
    print(f"OK - {len(TESTS)} test parser superati.")


if __name__ == "__main__":
    run()
