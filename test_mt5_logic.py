"""
Test statici della logica MT5 senza MetaTrader5 reale.
Non apre ordini.
"""
import sys
import types

# Stub minimo per poter importare mt5_executor anche su un PC senza MT5.
mt5 = types.SimpleNamespace(
    SYMBOL_FILLING_FOK=1,
    SYMBOL_FILLING_IOC=2,
    SYMBOL_TRADE_EXECUTION_MARKET=2,
    ORDER_FILLING_FOK=0,
    ORDER_FILLING_IOC=1,
    ORDER_FILLING_RETURN=2,
)
sys.modules["MetaTrader5"] = mt5

import mt5_executor


class Info:
    point = 0.01
    trade_stops_level = 100
    trade_freeze_level = 0
    filling_mode = 2
    trade_exemode = 2


info = Info()

assert mt5_executor._get_filling_mode(info) == mt5.ORDER_FILLING_IOC

mt5_executor._validate_stops("BUY", 4372, 4360, 4384, info)
mt5_executor._validate_stops("SELL", 4372, 4384, 4360, info)

try:
    mt5_executor._validate_stops("BUY", 4372, 4371.5, 4384, info)
except ValueError:
    pass
else:
    raise AssertionError("SL troppo vicino non è stato rifiutato.")

print("OK - MT5 logic tests superati (nessun ordine reale).")
