"""
Esecuzione ordini MetaTrader 5 per il bot Gold Empire.

Tutte le operazioni filtrano sul MAGIC_NUMBER di questo bot: non tocca mai
posizioni aperte a mano o da altri bot sullo stesso conto.
"""
import logging
import threading
from dataclasses import dataclass

try:
    import MetaTrader5 as mt5
except ImportError:  # es. Linux / modalita' test senza MT5
    mt5 = None

from config import (
    DEVIATION,
    LOT_SIZE,
    MAGIC_NUMBER,
    MAX_ENTRY_DISTANCE,
    MT5_LOGIN,
    MT5_PASSWORD,
    MT5_PATH,
    MT5_SERVER,
    MT5_SYMBOL,
    ORDER_COMMENT,
    PIP_SIZE,
)

logger = logging.getLogger(__name__)

# La libreria MetaTrader5 non va usata da piu' thread insieme.
_MT5_LOCK = threading.RLock()


@dataclass(frozen=True)
class TradeResult:
    position_ticket: int
    price: float
    volume: float
    sl: float
    tp: float


def _require_mt5():
    if mt5 is None:
        raise RuntimeError("Libreria MetaTrader5 non installata (pip install MetaTrader5).")


def connect_mt5():
    _require_mt5()
    with _MT5_LOCK:
        logger.info("🔌 Connessione MT5 | Terminale: %s", MT5_PATH)
        base = {"timeout": 20000}
        if MT5_PATH:
            base["path"] = MT5_PATH
        connected = False
        if MT5_LOGIN and MT5_PASSWORD:
            connected = mt5.initialize(
                login=int(MT5_LOGIN), password=MT5_PASSWORD, server=MT5_SERVER, **base
            )
            if not connected:
                logger.warning(
                    "⚠️ Login MT5 con password fallito (%s): provo ad agganciarmi al terminale gia' loggato.",
                    mt5.last_error(),
                )
                mt5.shutdown()
        if not connected:
            connected = mt5.initialize(**base)
        if not connected:
            logger.error(
                "❌ MT5 initialize fallito: %s | Controlla MT5_PATH (terminale Fortune Prime) "
                "e lancia: python diagnose_mt5.py", mt5.last_error(),
            )
            return False

        account = mt5.account_info()
        if account is None:
            logger.error("❌ Account MT5 non disponibile: %s", mt5.last_error())
            return False
        if MT5_LOGIN and int(account.login) != int(MT5_LOGIN):
            logger.error("❌ ACCOUNT SBAGLIATO: atteso %s, trovato %s", MT5_LOGIN, account.login)
            return False

        hedging = getattr(mt5, "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", 2)
        if int(getattr(account, "margin_mode", hedging)) != int(hedging):
            logger.warning(
                "⚠️ Il conto NON e' in modalita' hedging: BUY e SELL insieme "
                "si compenseranno invece di restare due posizioni separate."
            )

        info = mt5.symbol_info(MT5_SYMBOL)
        if info is None:
            logger.error("❌ Simbolo %s non trovato sul broker.", MT5_SYMBOL)
            return False
        if not info.visible and not mt5.symbol_select(MT5_SYMBOL, True):
            logger.error("❌ Impossibile attivare il simbolo %s.", MT5_SYMBOL)
            return False

        logger.info(
            "✅ MT5 PRONTO | Login %s | Server %s | Balance %.2f | %s digits=%s min_lot=%s",
            account.login, account.server, account.balance, MT5_SYMBOL,
            info.digits, info.volume_min,
        )
        return True


def pip_size():
    """Pip XAUUSD = 10 point (0,10 $ con 2 decimali), come il canale."""
    if mt5 is not None:
        with _MT5_LOCK:
            info = mt5.symbol_info(MT5_SYMBOL)
        if info is not None and float(info.point) > 0:
            return float(info.point) * 10.0
    return PIP_SIZE


def _symbol_info():
    info = mt5.symbol_info(MT5_SYMBOL)
    if info is None:
        raise RuntimeError(f"Simbolo {MT5_SYMBOL} non disponibile: {mt5.last_error()}")
    if not info.visible and not mt5.symbol_select(MT5_SYMBOL, True):
        raise RuntimeError(f"Impossibile attivare {MT5_SYMBOL}.")
    return info


def _normalize_volume(volume, info):
    step = float(info.volume_step or 0.01)
    minimum = float(info.volume_min or step)
    maximum = float(info.volume_max or volume)
    normalized = int((float(volume) + 1e-9) / step) * step
    normalized = min(max(normalized, minimum), maximum)
    decimals = max(0, len(f"{step:.8f}".rstrip("0").split(".")[-1]))
    return round(normalized, decimals)


def _filling_mode(info):
    flags = int(getattr(info, "filling_mode", 0) or 0)
    if flags & getattr(mt5, "SYMBOL_FILLING_IOC", 2):
        return mt5.ORDER_FILLING_IOC
    if flags & getattr(mt5, "SYMBOL_FILLING_FOK", 1):
        return mt5.ORDER_FILLING_FOK
    if getattr(info, "trade_exemode", None) != getattr(mt5, "SYMBOL_TRADE_EXECUTION_MARKET", 2):
        return mt5.ORDER_FILLING_RETURN
    return mt5.ORDER_FILLING_IOC


def _min_stop_distance(info):
    levels = max(
        int(getattr(info, "trade_stops_level", 0) or 0),
        int(getattr(info, "trade_freeze_level", 0) or 0),
    )
    return levels * float(info.point)


def _validate_stops(direction, price, sl, tp, info):
    min_distance = _min_stop_distance(info)
    if direction == "BUY":
        if not sl < price:
            raise ValueError(f"BUY: SL {sl:.2f} non e' sotto il prezzo {price:.2f} (stop gia' superato).")
        if tp and not tp > price:
            raise ValueError(f"BUY: TP {tp:.2f} non e' sopra il prezzo {price:.2f} (obiettivo gia' superato).")
        if min_distance and (price - sl < min_distance or (tp and tp - price < min_distance)):
            raise ValueError(f"BUY: SL/TP troppo vicini al prezzo (minimo {min_distance:.2f}).")
    else:
        if not sl > price:
            raise ValueError(f"SELL: SL {sl:.2f} non e' sopra il prezzo {price:.2f} (stop gia' superato).")
        if tp and not tp < price:
            raise ValueError(f"SELL: TP {tp:.2f} non e' sotto il prezzo {price:.2f} (obiettivo gia' superato).")
        if min_distance and (sl - price < min_distance or (tp and price - tp < min_distance)):
            raise ValueError(f"SELL: SL/TP troppo vicini al prezzo (minimo {min_distance:.2f}).")


def _send(request):
    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"order_send ha restituito None: {mt5.last_error()}")
    accepted = {
        getattr(mt5, "TRADE_RETCODE_PLACED", 10008),  # ordine pendente piazzato
        getattr(mt5, "TRADE_RETCODE_DONE", 10009),
        getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010),
    }
    if result.retcode not in accepted:
        raise RuntimeError(
            f"Ordine rifiutato: retcode={result.retcode} comment={getattr(result, 'comment', '')}"
        )
    return result


def _find_position_ticket(result, direction):
    """Ticket della POSIZIONE appena aperta (serve per BE e chiusure)."""
    order_ticket = int(getattr(result, "order", 0) or 0)
    if order_ticket and mt5.positions_get(ticket=order_ticket):
        return order_ticket

    deal_ticket = int(getattr(result, "deal", 0) or 0)
    if deal_ticket:
        deals = mt5.history_deals_get(ticket=deal_ticket) or []
        for deal in deals:
            position_id = int(getattr(deal, "position_id", 0) or 0)
            if position_id:
                return position_id

    # Ultima riserva: posizione piu' recente del nostro magic e direzione.
    wanted_type = mt5.POSITION_TYPE_BUY if direction == "BUY" else mt5.POSITION_TYPE_SELL
    candidates = [
        p for p in (mt5.positions_get(symbol=MT5_SYMBOL) or [])
        if int(p.magic) == int(MAGIC_NUMBER) and int(p.type) == int(wanted_type)
    ]
    if not candidates:
        return 0
    candidates.sort(key=lambda p: getattr(p, "time_msc", p.time), reverse=True)
    return int(candidates[0].ticket)


def open_market_order(signal):
    """Apre subito a mercato (BUY=ASK, SELL=BID) con SL e TP del segnale."""
    _require_mt5()
    with _MT5_LOCK:
        info = _symbol_info()
        digits = int(info.digits)
        direction = signal["direction"].upper()
        if direction not in {"BUY", "SELL"}:
            raise ValueError(f"Direzione non valida: {direction}")

        tick = mt5.symbol_info_tick(MT5_SYMBOL)
        if tick is None:
            raise RuntimeError(f"Prezzo non disponibile per {MT5_SYMBOL}: {mt5.last_error()}")
        price = round(float(tick.ask if direction == "BUY" else tick.bid), digits)

        if MAX_ENTRY_DISTANCE > 0 and abs(price - float(signal["entry"])) > MAX_ENTRY_DISTANCE:
            raise ValueError(
                f"Prezzo {price:.2f} troppo lontano dall'ingresso {signal['entry']:.2f} "
                f"(massimo {MAX_ENTRY_DISTANCE:.2f})."
            )

        sl = round(float(signal["sl"]), digits)
        # 0 = nessun TP su MT5 (segnali con uscita "al segnale della strategia").
        tp = round(float(signal["tp"]), digits) if signal.get("tp") else 0.0
        _validate_stops(direction, price, sl, tp, info)

        volume = _normalize_volume(LOT_SIZE, info)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": MT5_SYMBOL,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": int(DEVIATION),
            "magic": int(MAGIC_NUMBER),
            "comment": ORDER_COMMENT,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": _filling_mode(info),
        }
        result = _send(request)

        position_ticket = _find_position_ticket(result, direction)
        if not position_ticket:
            raise RuntimeError(
                "Ordine eseguito ma ticket della posizione non trovato: "
                "controlla MT5, il bot non puo' gestire questa posizione."
            )

        actual_price = float(getattr(result, "price", 0.0) or 0.0) or price
        positions = mt5.positions_get(ticket=position_ticket)
        if positions:
            actual_price = float(positions[0].price_open) or actual_price

        return TradeResult(
            position_ticket=int(position_ticket),
            price=actual_price,
            volume=float(getattr(result, "volume", volume) or volume),
            sl=sl,
            tp=tp,
        )


def _own_position(position_ticket):
    positions = mt5.positions_get(ticket=int(position_ticket))
    if not positions:
        return None
    position = positions[0]
    if int(position.magic) != int(MAGIC_NUMBER) or position.symbol != MT5_SYMBOL:
        raise RuntimeError(f"La posizione {position_ticket} non appartiene a questo bot.")
    return position


def get_position_tp(position_ticket):
    """TP attuale della posizione su MT5 (0.0 = nessun TP), None se non e' piu' aperta."""
    _require_mt5()
    with _MT5_LOCK:
        positions = mt5.positions_get(ticket=int(position_ticket))
        if not positions:
            return None
        return float(positions[0].tp or 0.0)


def is_position_open(position_ticket):
    _require_mt5()
    with _MT5_LOCK:
        return bool(mt5.positions_get(ticket=int(position_ticket)))


def move_stop_loss(position_ticket, new_sl):
    """
    Sposta lo SL (TP invariato). Se il prezzo e' gia' oltre il nuovo SL
    solleva ValueError: il chiamante decide cosa fare.
    """
    _require_mt5()
    with _MT5_LOCK:
        info = _symbol_info()
        position = _own_position(position_ticket)
        if position is None:
            raise RuntimeError(f"Posizione {position_ticket} non trovata o gia' chiusa.")

        new_sl = round(float(new_sl), int(info.digits))
        tick = mt5.symbol_info_tick(MT5_SYMBOL)
        min_distance = _min_stop_distance(info)
        if int(position.type) == mt5.POSITION_TYPE_BUY:
            current = float(tick.bid) if tick else float(position.price_current)
            if not new_sl < current - min_distance:
                raise ValueError(f"BUY: nuovo SL {new_sl:.2f} non valido col prezzo {current:.2f}.")
        else:
            current = float(tick.ask) if tick else float(position.price_current)
            if not new_sl > current + min_distance:
                raise ValueError(f"SELL: nuovo SL {new_sl:.2f} non valido col prezzo {current:.2f}.")

        _send({
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": MT5_SYMBOL,
            "position": int(position_ticket),
            "sl": new_sl,
            "tp": float(position.tp or 0.0),
            "magic": int(MAGIC_NUMBER),
            "comment": ORDER_COMMENT,
        })
        return new_sl


def close_position(position_ticket):
    """Chiude a mercato la posizione. Restituisce il prezzo di chiusura."""
    _require_mt5()
    with _MT5_LOCK:
        info = _symbol_info()
        position = _own_position(position_ticket)
        if position is None:
            raise RuntimeError(f"Posizione {position_ticket} non trovata o gia' chiusa.")

        tick = mt5.symbol_info_tick(MT5_SYMBOL)
        if tick is None:
            raise RuntimeError("Tick MT5 non disponibile per la chiusura.")
        is_buy = int(position.type) == mt5.POSITION_TYPE_BUY
        price = round(float(tick.bid if is_buy else tick.ask), int(info.digits))

        result = _send({
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": MT5_SYMBOL,
            "volume": float(position.volume),
            "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
            "position": int(position_ticket),
            "price": price,
            "deviation": int(DEVIATION),
            "magic": int(MAGIC_NUMBER),
            "comment": ORDER_COMMENT,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": _filling_mode(info),
        })
        return float(getattr(result, "price", 0.0) or 0.0) or price


def get_closed_position_info(position_ticket):
    """
    Dati della chiusura di una posizione gia' chiusa (dallo storico MT5):
    {"price", "is_sl", "is_tp"} oppure None se lo storico non e' ancora pronto.
    """
    _require_mt5()
    with _MT5_LOCK:
        deals = mt5.history_deals_get(position=int(position_ticket))
        if not deals:
            return None
        exit_entries = {getattr(mt5, "DEAL_ENTRY_OUT", 1), getattr(mt5, "DEAL_ENTRY_OUT_BY", 3)}
        exits = [d for d in deals if int(getattr(d, "entry", -1)) in exit_entries]
        if not exits:
            return None
        deal = max(exits, key=lambda d: (int(getattr(d, "time_msc", 0) or 0), int(d.ticket)))
        reason = int(getattr(deal, "reason", -1))
        return {
            "price": float(deal.price),
            "is_sl": reason == getattr(mt5, "DEAL_REASON_SL", 4),
            "is_tp": reason == getattr(mt5, "DEAL_REASON_TP", 5),
        }


def get_bot_positions():
    _require_mt5()
    with _MT5_LOCK:
        return [
            p for p in (mt5.positions_get(symbol=MT5_SYMBOL) or [])
            if int(p.magic) == int(MAGIC_NUMBER)
        ]


# ============================================================
# ORDINI PENDENTI (BUY/SELL LIMIT, BUY/SELL STOP)
# ============================================================

@dataclass(frozen=True)
class PendingResult:
    order_ticket: int
    price: float


def _pending_type(direction, order_type):
    return {
        ("BUY", "LIMIT"): mt5.ORDER_TYPE_BUY_LIMIT,
        ("SELL", "LIMIT"): mt5.ORDER_TYPE_SELL_LIMIT,
        ("BUY", "STOP"): mt5.ORDER_TYPE_BUY_STOP,
        ("SELL", "STOP"): mt5.ORDER_TYPE_SELL_STOP,
    }[(direction, order_type)]


def _already_reached(direction, order_type, entry, bid, ask):
    """True se il prezzo di mercato ha gia' raggiunto (o superato in meglio) l'ingresso."""
    if order_type == "LIMIT":
        return ask <= entry if direction == "BUY" else bid >= entry
    return ask >= entry if direction == "BUY" else bid <= entry


def place_pending_order(signal):
    """
    Piazza l'ordine pendente al prezzo di Ingresso con SL e TP del segnale.
    Se il mercato ha gia' raggiunto l'ingresso apre subito a mercato e
    restituisce un TradeResult; altrimenti restituisce un PendingResult.
    """
    _require_mt5()
    with _MT5_LOCK:
        info = _symbol_info()
        digits = int(info.digits)
        direction = signal["direction"].upper()
        order_type = signal["order_type"]
        entry = round(float(signal["entry"]), digits)

        tick = mt5.symbol_info_tick(MT5_SYMBOL)
        if tick is None:
            raise RuntimeError(f"Prezzo non disponibile per {MT5_SYMBOL}: {mt5.last_error()}")

        if _already_reached(direction, order_type, entry, float(tick.bid), float(tick.ask)):
            logger.info(
                "⚡ %s %s: prezzo gia' all'ingresso %.2f, apro a mercato.", direction, order_type, entry,
            )
            return open_market_order(signal)

        sl = round(float(signal["sl"]), digits)
        tp = round(float(signal["tp"]), digits) if signal.get("tp") else 0.0
        _validate_stops(direction, entry, sl, tp, info)

        volume = _normalize_volume(LOT_SIZE, info)
        result = _send({
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": MT5_SYMBOL,
            "volume": volume,
            "type": _pending_type(direction, order_type),
            "price": entry,
            "sl": sl,
            "tp": tp,
            "deviation": int(DEVIATION),
            "magic": int(MAGIC_NUMBER),
            "comment": ORDER_COMMENT,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        })
        return PendingResult(order_ticket=int(result.order), price=entry)


def check_pending_order(order_ticket):
    """
    None = ancora pendente (o storico non ancora pronto).
    {"filled": True, "position_ticket", "price", "volume"} = eseguito.
    {"filled": False} = annullato / scaduto / rifiutato.
    """
    _require_mt5()
    with _MT5_LOCK:
        order_ticket = int(order_ticket)
        if mt5.orders_get(ticket=order_ticket):
            return None

        entry_in = getattr(mt5, "DEAL_ENTRY_IN", 0)
        for deal in mt5.history_deals_get(ticket=order_ticket) or []:
            if int(getattr(deal, "entry", -1)) == entry_in:
                position_ticket = int(getattr(deal, "position_id", 0) or 0) or order_ticket
                price = float(deal.price)
                positions = mt5.positions_get(ticket=position_ticket)
                if positions:
                    price = float(positions[0].price_open) or price
                return {"filled": True, "position_ticket": position_ticket,
                        "price": price, "volume": float(deal.volume)}

        positions = mt5.positions_get(ticket=order_ticket)
        if positions:
            p = positions[0]
            return {"filled": True, "position_ticket": int(p.ticket),
                    "price": float(p.price_open), "volume": float(p.volume)}

        orders = mt5.history_orders_get(ticket=order_ticket) or []
        if orders:
            state = int(getattr(orders[0], "state", -1))
            if state == getattr(mt5, "ORDER_STATE_FILLED", 4):
                return None  # eseguito, ma il deal non e' ancora nello storico
            return {"filled": False}
        return None


def cancel_pending_order(order_ticket):
    """True se annullato, False se non c'e' piu' (es. appena eseguito)."""
    _require_mt5()
    with _MT5_LOCK:
        if not mt5.orders_get(ticket=int(order_ticket)):
            return False
        _send({"action": mt5.TRADE_ACTION_REMOVE, "order": int(order_ticket)})
        return True
