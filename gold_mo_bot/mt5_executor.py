"""
Esecutore MT5 per il CONTO PRINCIPALE, agganciato direttamente al
processo del bot (stessa logica del vecchio bot ELITE, vedi mt5_engine.py
per l'implementazione generica condivisa con il secondo conto).
"""
import mt5_engine as engine

from config import (
    DEVIATION,
    LOT_SIZE,
    MAGIC_NUMBER,
    MT5_LOGIN,
    MT5_PASSWORD,
    MT5_PATH,
    MT5_SERVER,
    MT5_SYMBOL,
    ORDER_COMMENT,
)

TradeResult = engine.TradeResult


def connect_mt5():
    return engine.connect_mt5(
        MT5_PATH, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_SYMBOL, label="MT5 CONTO PRINCIPALE"
    )


def current_price(direction=None):
    return engine.current_price(MT5_SYMBOL, direction)


def open_market_order(direction, sl=0.0):
    return engine.open_market_order(
        MT5_SYMBOL, direction, LOT_SIZE, MAGIC_NUMBER, ORDER_COMMENT, DEVIATION, sl
    )


def modify_position_sl_tp(position_ticket, new_sl, new_tp):
    return engine.modify_position_sl_tp(
        MT5_SYMBOL, MAGIC_NUMBER, ORDER_COMMENT, position_ticket, new_sl, new_tp
    )


def move_position_to_breakeven(position_ticket):
    return engine.move_position_to_breakeven(MT5_SYMBOL, MAGIC_NUMBER, ORDER_COMMENT, position_ticket)


def close_position(position_ticket):
    return engine.close_position(MT5_SYMBOL, MAGIC_NUMBER, ORDER_COMMENT, position_ticket, DEVIATION)


def position_is_open(position_ticket):
    return engine.position_is_open(position_ticket)


def get_closed_position_info(position_ticket):
    return engine.get_closed_position_info(position_ticket)


def list_open_positions():
    return engine.list_open_positions(MT5_SYMBOL, MAGIC_NUMBER)


def close_all_positions():
    return engine.close_all_positions(MT5_SYMBOL, MAGIC_NUMBER, ORDER_COMMENT, DEVIATION)


def get_closed_trades_for_period(start_utc, end_utc):
    return engine.get_closed_trades_for_period(MT5_SYMBOL, MAGIC_NUMBER, start_utc, end_utc)
