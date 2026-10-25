"""
Lettura delle operazioni da MetaTrader 5. Solo lettura: non apre, non
modifica e non chiude niente.
"""
import logging

try:
    import MetaTrader5 as mt5
except ImportError:  # es. Linux / test: il modulo esiste solo su Windows
    mt5 = None

from config import MAGIC_NUMBERS, MT5_LOGIN, MT5_PASSWORD, MT5_PATH, MT5_SERVER, MT5_SYMBOL

logger = logging.getLogger(__name__)


def _require_mt5():
    if mt5 is None:
        raise RuntimeError("Modulo MetaTrader5 non installato: pip install MetaTrader5 (solo Windows).")


def connect():
    """Si collega al terminale MT5 gia' aperto (con login se indicato nel .env)."""
    _require_mt5()
    kwargs = {"path": MT5_PATH} if MT5_PATH else {}
    if MT5_LOGIN:
        kwargs.update(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    if not mt5.initialize(**kwargs):
        logger.error("❌ MT5 initialize fallito: %s", mt5.last_error())
        return False
    account = mt5.account_info()
    if account is None:
        logger.error("❌ MT5 collegato ma nessun conto loggato: %s", mt5.last_error())
        return False
    logger.info("✅ MT5 collegato | Conto %s | %s", account.login, account.server)
    return True


def is_connected():
    return mt5 is not None and mt5.terminal_info() is not None and mt5.account_info() is not None


def get_positions():
    """
    Posizioni aperte dei magic number seguiti, come dizionari.
    None se MT5 non risponde: in quel caso NON vanno considerate chiuse.
    """
    _require_mt5()
    positions = mt5.positions_get(symbol=MT5_SYMBOL) if MT5_SYMBOL else mt5.positions_get()
    if positions is None:
        logger.warning("⚠️ positions_get non ha risposto: %s", mt5.last_error())
        return None
    result = []
    for p in positions:
        if int(p.magic) not in MAGIC_NUMBERS:
            continue
        result.append({
            "ticket": int(p.ticket),
            "magic": int(p.magic),
            "symbol": p.symbol,
            "direction": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
            "open_price": float(p.price_open),
            "sl": float(p.sl or 0.0),
            "tp": float(p.tp or 0.0),
            "volume": float(p.volume),
            "time": int(p.time),          # ora del server MT5
            "profit": float(p.profit),
        })
    return result


def server_now(symbol):
    """Ora del server MT5 (dall'ultimo tick), per sapere da quanto e' aperta una posizione."""
    _require_mt5()
    tick = mt5.symbol_info_tick(symbol)
    return int(tick.time) if tick is not None else None


def get_close_info(ticket):
    """
    Come si e' chiusa una posizione: prezzo, motivo (TP / SL / OTHER) e profitto
    netto. None se lo storico non ha ancora l'uscita.
    """
    _require_mt5()
    deals = mt5.history_deals_get(position=int(ticket))
    if not deals:
        return None
    exits = [d for d in deals if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY)]
    if not exits:
        return None
    last = max(exits, key=lambda d: (d.time_msc, d.ticket))
    if last.reason == mt5.DEAL_REASON_TP:
        reason = "TP"
    elif last.reason == mt5.DEAL_REASON_SL:
        reason = "SL"
    else:
        reason = "OTHER"
    profit = sum(float(d.profit) + float(d.commission) + float(d.swap) + float(getattr(d, "fee", 0.0)) for d in deals)
    return {"price": float(last.price), "reason": reason, "profit": profit}
