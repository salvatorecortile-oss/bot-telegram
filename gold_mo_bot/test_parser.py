from signal_parser import parse_signal


TESTS = [
    (
        # Il messaggio 2 a volte "rilancia" anche la riga di apertura
        # insieme a SL/TP: deve comunque essere trattato come SET_SLTP
        # (completa il trade gia' aperto dal messaggio 1), MAI come una
        # nuova apertura duplicata.
        """Gold buy now 4379.8 - 4376
SL: 4372
TP: 4382
TP: 4384
TP. 4386
TP: 4388
TP: open""",
        {
            "action": "SET_SLTP",
            "symbol": "XAUUSD",
            "sl": 4372.0,
            "tp1": 4382.0,
            "tp2": 4384.0,
            "tp3": 4386.0,
            "tp4": 4388.0,
            "tp_open_runner": True,
        },
    ),
    (
        "Gold buy now 4379.8 - 4376",
        {
            "action": "OPEN",
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_zone_high": 4379.8,
            "entry_zone_low": 4376.0,
            "entry": 4377.9,
        },
    ),
    (
        "Gold sell now 4379.8 - 4383",
        {
            "action": "OPEN",
            "symbol": "XAUUSD",
            "direction": "SELL",
            "entry_zone_high": 4379.8,
            "entry_zone_low": 4383.0,
            "entry": 4381.4,
        },
    ),
    (
        """SL: 4372

TP: 4382
TP: 4384
TP. 4386
TP: 4388
TP: open""",
        {
            "action": "SET_SLTP",
            "symbol": "XAUUSD",
            "sl": 4372.0,
            "tp1": 4382.0,
            "tp2": 4384.0,
            "tp3": 4386.0,
            "tp4": 4388.0,
            "tp_open_runner": True,
        },
    ),
    (
        # Senza "open" finale e con meno TP: TP3 resta l'unico operativo.
        """SL: 4372
TP: 4382
TP: 4384
TP: 4386""",
        {
            "action": "SET_SLTP",
            "symbol": "XAUUSD",
            "sl": 4372.0,
            "tp1": 4382.0,
            "tp2": 4384.0,
            "tp3": 4386.0,
            "tp4": None,
            "tp_open_runner": False,
        },
    ),
    ("good morning everyone", None),
    ("SL: 4372", None),  # SL senza alcun TP: ignorato, non associabile.
    (
        # Zona di prezzo assente: apre comunque, l'entry reale arriva da MT5.
        "Gold buy now",
        {
            "action": "OPEN",
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_zone_high": None,
            "entry_zone_low": None,
            "entry": None,
        },
    ),
]


for text, expected in TESTS:
    result = parse_signal(text)
    assert result == expected, f"Expected {expected}, got {result!r}"

print(f"OK - {len(TESTS)} parser test superati.")
