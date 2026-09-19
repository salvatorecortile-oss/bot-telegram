from signal_parser import parse_signal


TESTS = [
    (
        """XAUUSD SELL 4372

SL 4382

TP1 4362
TP2 4352""",
        {"action": "UPDATE_PARAMS", "symbol": "XAUUSD-P", "direction": "SELL", "entry": 4372.0, "sl": 4382.0, "tp1": 4362.0},
    ),
    (
        """XAUUSD BUY 4372
SL: 4362
TP1: 4382""",
        {"action": "UPDATE_PARAMS", "symbol": "XAUUSD-P", "direction": "BUY", "entry": 4372.0, "sl": 4362.0, "tp1": 4382.0},
    ),
    (
        """GOLD SELL 4372
SL 4382
TP1 4362""",
        {"action": "UPDATE_PARAMS", "symbol": "XAUUSD-P", "direction": "SELL", "entry": 4372.0, "sl": 4382.0, "tp1": 4362.0},
    ),
    (
        """XAU/USD SELL
Prezzo di: 4372
Stop Loss 🔴 `4382`
TP1 🟢 `4362`
TP2 4352""",
        {"action": "UPDATE_PARAMS", "symbol": "XAUUSD-P", "direction": "SELL", "entry": 4372.0, "sl": 4382.0, "tp1": 4362.0},
    ),
    (
        """XAUUSD SELL @4372
SL 4382
TP1 4362""",
        None,
    ),
    (
        "Segnale in arrivo long GOLD! 4430📲",
        {"action": "OPEN_SIGNAL", "symbol": "XAUUSD-P", "direction": "BUY", "entry": 4430.0},
    ),
    (
        """**XAU/USD BUY**

🟢 **Prezzo di: 4430**

🚫 **Stop Loss (SL):** 4410

🎯 **Take Profit (TP):**
- TP1: 4466
- TP2: 4503""",
        {"action": "UPDATE_PARAMS", "symbol": "XAUUSD-P", "direction": "BUY", "entry": 4430.0, "sl": 4410.0, "tp1": 4466.0},
    ),
]


for text, expected in TESTS:
    result = parse_signal(text)
    assert result == expected, f"Expected {expected}, got {result!r}"

print(f"OK - {len(TESTS)} parser test superati.")
