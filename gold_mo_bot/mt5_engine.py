"""
Motore MT5 generico e parametrizzato per simbolo/lotto/magic/commento.

Usato sia dal conto principale (import diretto in main.py/mt5_executor.py,
stesso processo) sia dal conto secondario (dentro il processo separato
avviato da mt5_worker.py). Ogni processo ha una propria connessione MT5
indipendente: il modulo MetaTrader5 tiene una sola connessione attiva per
processo, per questo il secondo conto gira sempre in un processo a parte.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TradeResult:
    order: int
    deal: int
    volume: float
    price: float
    retcode: int
    comment: str
    filling_mode: int
    position_ticket: int


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def connect_mt5(path, login, password, server, symbol, label="MT5"):
    print("=" * 72)
    print(f"🔌 CONNESSIONE {label}")
    print("=" * 72)
    print(f"Terminale : {path}")

    initialized = mt5.initialize(
        path=path,
        login=int(login),
        password=password,
        server=server,
    )

    if not initialized:
        print(f"❌ {label} initialize fallito: {mt5.last_error()}")
        return False

    account = mt5.account_info()
    if account is None:
        print(f"❌ {label} account non disponibile: {mt5.last_error()}")
        return False

    print(f"Login     : {account.login}")
    print(f"Server    : {account.server}")
    print(f"Balance   : {account.balance}")
    print(f"Equity    : {account.equity}")

    if int(account.login) != int(login):
        print(f"❌ {label} ACCOUNT SBAGLIATO: atteso {login}, trovato {account.login}")
        return False

    if server and account.server != server:
        print(f"❌ {label} SERVER DIVERSO: atteso {server}, trovato {account.server}")
        return False

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"❌ {label} simbolo {symbol} non trovato.")
        return False

    if not symbol_info.visible and not mt5.symbol_select(symbol, True):
        print(f"❌ {label} impossibile rendere visibile {symbol}.")
        return False

    print(f"Symbol    : {symbol}")
    print(f"Digits    : {symbol_info.digits}")
    print(f"Point     : {symbol_info.point}")
    print(f"Min lot   : {symbol_info.volume_min}")
    print(f"Max lot   : {symbol_info.volume_max}")
    print(f"✅ {label} PRONTO.")
    print("=" * 72)
    return True


def _symbol_info(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"Simbolo {symbol} non disponibile: {mt5.last_error()}")
    if not info.visible and not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Impossibile attivare {symbol}.")
    return info


def _normalize_price(value, digits):
    return round(float(value), int(digits))


def _normalize_volume(volume, info):
    step = float(info.volume_step or 0.01)
    minimum = float(info.volume_min or step)
    maximum = float(info.volume_max or volume)

    steps = int((float(volume) + 1e-12) / step)
    normalized = steps * step

    if normalized < minimum:
        normalized = minimum
    if normalized > maximum:
        normalized = maximum

    decimals = max(0, len(str(step).split(".")[-1].rstrip("0")))
    return round(normalized, decimals)


def _get_filling_mode(info):
    filling_flags = int(getattr(info, "filling_mode", 0) or 0)
    symbol_fok = getattr(mt5, "SYMBOL_FILLING_FOK", 1)
    symbol_ioc = getattr(mt5, "SYMBOL_FILLING_IOC", 2)

    if filling_flags & symbol_ioc:
        return mt5.ORDER_FILLING_IOC
    if filling_flags & symbol_fok:
        return mt5.ORDER_FILLING_FOK

    execution = getattr(info, "trade_exemode", None)
    market_execution = getattr(mt5, "SYMBOL_TRADE_EXECUTION_MARKET", 2)
    if execution != market_execution:
        return mt5.ORDER_FILLING_RETURN

    return mt5.ORDER_FILLING_IOC


def _current_price(symbol, direction):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    if direction == "BUY":
        return float(tick.ask)
    return float(tick.bid)


def current_price(symbol, direction=None):
    """Prezzo live: ASK per BUY, BID per SELL, mid-price se direction=None."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    if direction == "BUY":
        return float(tick.ask)
    if direction == "SELL":
        return float(tick.bid)
    bid = float(getattr(tick, "bid", 0.0) or 0.0)
    ask = float(getattr(tick, "ask", 0.0) or 0.0)
    if bid and ask:
        return (bid + ask) / 2.0
    return bid or ask or None


def _send_order(request):
    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"MT5 order_send ha restituito None: {mt5.last_error()}")

    accepted = {
        getattr(mt5, "TRADE_RETCODE_DONE", 10009),
        getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010),
    }
    if result.retcode not in accepted:
        raise RuntimeError(
            f"Ordine rifiutato: retcode={result.retcode}, comment={getattr(result, 'comment', '')}"
        )
    return result


def _find_position_ticket(symbol, magic, direction, volume, open_price):
    order_type = mt5.POSITION_TYPE_BUY if direction == "BUY" else mt5.POSITION_TYPE_SELL
    positions = mt5.positions_get(symbol=symbol) or []

    candidates = []
    for position in positions:
        if getattr(position, "magic", None) != int(magic):
            continue
        if getattr(position, "type", None) != order_type:
            continue
        pos_volume = float(getattr(position, "volume", 0.0) or 0.0)
        pos_price = float(getattr(position, "price_open", 0.0) or 0.0)
        if abs(pos_volume - float(volume)) < 1e-9 and abs(pos_price - float(open_price)) <= 0.05:
            candidates.append(position)

    if not candidates:
        for position in positions:
            if getattr(position, "magic", None) == int(magic) and getattr(position, "type", None) == order_type:
                candidates.append(position)

    if not candidates:
        return 0

    candidates.sort(key=lambda p: getattr(p, "time_msc", getattr(p, "time", 0)), reverse=True)
    return int(candidates[0].ticket)


def open_market_order(symbol, direction, volume, magic, comment, deviation, sl=0.0):
    """
    Apre immediatamente a mercato. BUY usa ASK, SELL usa BID.
    Lo SL e' opzionale: il segnale Gold MO apre senza SL (arriva col
    messaggio successivo), il TP non viene mai impostato in apertura.
    """
    direction = direction.upper()
    if direction not in {"BUY", "SELL"}:
        raise ValueError(f"Direzione non valida: {direction}")

    info = _symbol_info(symbol)
    digits = int(info.digits)

    lot = _normalize_volume(volume, info)

    valid_price = _current_price(symbol, direction)
    if valid_price is None:
        raise RuntimeError(f"Prezzo corrente non disponibile per {symbol}: {mt5.last_error()}")
    valid_price = _normalize_price(valid_price, digits)

    sl_price = _normalize_price(sl, digits) if sl else 0.0

    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    filling_mode = _get_filling_mode(info)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": valid_price,
        "sl": sl_price,
        "tp": 0.0,
        "deviation": int(deviation),
        "magic": int(magic),
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }

    result = _send_order(request)
    actual_price = float(getattr(result, "price", valid_price) or valid_price)

    position_ticket = _find_position_ticket(
        symbol, magic, direction, float(getattr(result, "volume", lot) or lot), actual_price
    )
    if not position_ticket:
        raise RuntimeError(
            "Ordine eseguito ma POSITION ticket non individuato: il trade non viene considerato gestibile dal bot."
        )

    return TradeResult(
        order=int(getattr(result, "order", 0) or 0),
        deal=int(getattr(result, "deal", 0) or 0),
        volume=float(getattr(result, "volume", lot) or lot),
        price=actual_price,
        retcode=int(result.retcode),
        comment=str(getattr(result, "comment", "")),
        filling_mode=int(filling_mode),
        position_ticket=int(position_ticket),
    )


def _get_position(symbol, magic, position_ticket):
    positions = mt5.positions_get(ticket=int(position_ticket))
    if not positions:
        raise RuntimeError(f"Posizione {position_ticket} non trovata o gia' chiusa.")
    position = positions[0]
    if getattr(position, "symbol", None) != symbol:
        raise RuntimeError(f"Posizione {position_ticket} appartiene a {getattr(position, 'symbol', 'N/D')}, non a {symbol}.")
    if getattr(position, "magic", None) != int(magic):
        raise RuntimeError(f"Posizione {position_ticket} non appartiene al MAGIC {magic}.")
    return position


def modify_position_sl_tp(symbol, magic, comment, position_ticket, new_sl, new_tp):
    """
    Applica SL e/o TP alla posizione esistente.
    - SL ha priorita': se SL e' valido e TP no, applica comunque SL.
    - Se TP e' valido e SL no, applica comunque TP.
    - new_tp=0 o None disattiva/lascia invariato il TP a seconda del caso.
    """
    info = _symbol_info(symbol)
    position = _get_position(symbol, magic, position_ticket)

    digits = int(info.digits)
    current = float(position.price_current)
    position_type = int(position.type)
    existing_sl = float(getattr(position, "sl", 0.0) or 0.0)
    existing_tp = float(getattr(position, "tp", 0.0) or 0.0)

    requested_sl = _normalize_price(new_sl, digits) if new_sl else None
    requested_tp = _normalize_price(new_tp, digits) if new_tp else None

    sl_valid = requested_sl is not None
    tp_valid = requested_tp is not None

    if position_type == mt5.POSITION_TYPE_BUY:
        direction = "BUY"
        if sl_valid and not requested_sl < current:
            sl_valid = False
        if tp_valid and not requested_tp > current:
            tp_valid = False
    elif position_type == mt5.POSITION_TYPE_SELL:
        direction = "SELL"
        if sl_valid and not requested_sl > current:
            sl_valid = False
        if tp_valid and not requested_tp < current:
            tp_valid = False
    else:
        raise RuntimeError(f"Tipo posizione non gestito: {position_type}")

    point = float(info.point)
    stops_level = int(getattr(info, "trade_stops_level", 0) or 0)
    freeze_level = int(getattr(info, "trade_freeze_level", 0) or 0)
    min_distance = max(stops_level, freeze_level) * point

    if min_distance > 0:
        if direction == "BUY":
            if sl_valid and current - requested_sl < min_distance:
                sl_valid = False
            if tp_valid and requested_tp - current < min_distance:
                tp_valid = False
        else:
            if sl_valid and requested_sl - current < min_distance:
                sl_valid = False
            if tp_valid and current - requested_tp < min_distance:
                tp_valid = False

    final_sl = requested_sl if sl_valid else existing_sl
    final_tp = requested_tp if tp_valid else existing_tp

    if not sl_valid and new_sl:
        logger.warning("⚠️ SL NON APPLICATO | Position=%s | richiesto=%s", position_ticket, new_sl)
    if not tp_valid and new_tp:
        logger.warning("⚠️ TP NON APPLICATO | Position=%s | richiesto=%s", position_ticket, new_tp)

    if new_sl and not sl_valid and new_tp and not tp_valid:
        raise ValueError("Nessun parametro (SL/TP) valido da applicare.")

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": int(position_ticket),
        "sl": final_sl,
        "tp": final_tp,
        "magic": int(magic),
        "comment": comment,
    }

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"Modifica SL/TP fallita: order_send=None, last_error={mt5.last_error()}")
    accepted = {getattr(mt5, "TRADE_RETCODE_DONE", 10009)}
    if result.retcode not in accepted:
        raise RuntimeError(f"Modifica SL/TP rifiutata: retcode={result.retcode}, comment={getattr(result, 'comment', '')}")

    return {
        "position_ticket": int(position_ticket),
        "sl": final_sl,
        "tp": final_tp,
        "sl_applied": bool(sl_valid) if new_sl else None,
        "tp_applied": bool(tp_valid) if new_tp else None,
        "direction": direction,
    }


def move_position_to_breakeven(symbol, magic, comment, position_ticket):
    """Sposta lo SL al prezzo di apertura (breakeven), mantenendo il TP esistente."""
    info = _symbol_info(symbol)
    position = _get_position(symbol, magic, position_ticket)

    digits = int(info.digits)
    breakeven = _normalize_price(float(position.price_open), digits)
    current = float(position.price_current)
    position_type = int(position.type)

    if position_type == mt5.POSITION_TYPE_BUY and not breakeven < current:
        raise ValueError(f"BUY: BE {breakeven:.2f} non e' sotto il prezzo corrente {current:.2f}.")
    if position_type == mt5.POSITION_TYPE_SELL and not breakeven > current:
        raise ValueError(f"SELL: BE {breakeven:.2f} non e' sopra il prezzo corrente {current:.2f}.")

    point = float(info.point)
    stops_level = int(getattr(info, "trade_stops_level", 0) or 0)
    freeze_level = int(getattr(info, "trade_freeze_level", 0) or 0)
    min_distance = max(stops_level, freeze_level) * point

    if min_distance > 0:
        distance = current - breakeven if position_type == mt5.POSITION_TYPE_BUY else breakeven - current
        if distance < min_distance:
            raise ValueError(f"BE troppo vicino al prezzo corrente: distanza {distance:.2f}, minima {min_distance:.2f}.")

    existing_sl = float(getattr(position, "sl", 0.0) or 0.0)
    existing_tp = float(getattr(position, "tp", 0.0) or 0.0)

    if position_type == mt5.POSITION_TYPE_BUY and existing_sl > 0 and existing_sl >= breakeven:
        return existing_sl
    if position_type == mt5.POSITION_TYPE_SELL and existing_sl > 0 and existing_sl <= breakeven:
        return existing_sl

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": int(position_ticket),
        "sl": breakeven,
        "tp": existing_tp,
        "magic": int(magic),
        "comment": comment,
    }
    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"Break Even fallito: order_send=None, last_error={mt5.last_error()}")
    accepted = {getattr(mt5, "TRADE_RETCODE_DONE", 10009)}
    if result.retcode not in accepted:
        raise RuntimeError(f"Break Even rifiutato: retcode={result.retcode}, comment={getattr(result, 'comment', '')}")

    return breakeven


def close_position(symbol, magic, comment, position_ticket, deviation):
    """Chiude a mercato la posizione. Non usa alcun prezzo del messaggio Telegram."""
    info = _symbol_info(symbol)
    position = _get_position(symbol, magic, position_ticket)

    position_type = int(position.type)
    volume = float(position.volume)

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError("Tick MT5 non disponibile per la chiusura.")

    if position_type == mt5.POSITION_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = float(tick.bid)
    elif position_type == mt5.POSITION_TYPE_SELL:
        order_type = mt5.ORDER_TYPE_BUY
        price = float(tick.ask)
    else:
        raise RuntimeError(f"Tipo posizione non gestito: {position_type}")

    price = _normalize_price(price, int(info.digits))
    filling_mode = _get_filling_mode(info)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "position": int(position_ticket),
        "price": price,
        "deviation": int(deviation),
        "magic": int(magic),
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    result = _send_order(request)

    return TradeResult(
        order=int(getattr(result, "order", 0) or 0),
        deal=int(getattr(result, "deal", 0) or 0),
        volume=float(getattr(result, "volume", volume) or volume),
        price=float(getattr(result, "price", price) or price),
        retcode=int(result.retcode),
        comment=str(getattr(result, "comment", "")),
        filling_mode=int(filling_mode),
        position_ticket=int(position_ticket),
    )


def position_is_open(position_ticket):
    return bool(mt5.positions_get(ticket=int(position_ticket)))


def list_open_positions(symbol, magic):
    """Elenco delle posizioni aperte del bot (usato dal comando *_status)."""
    positions = mt5.positions_get(symbol=symbol) or []
    summary = []
    for position in positions:
        if int(getattr(position, "magic", 0) or 0) != int(magic):
            continue
        is_buy = int(position.type) == mt5.POSITION_TYPE_BUY
        summary.append({
            "ticket": int(position.ticket),
            "direction": "BUY" if is_buy else "SELL",
            "volume": float(position.volume),
            "price_open": float(position.price_open),
            "price_current": float(position.price_current),
            "profit": float(position.profit),
            "sl": float(position.sl),
            "tp": float(position.tp),
        })
    return sorted(summary, key=lambda item: item["ticket"])


def close_all_positions(symbol, magic, comment, deviation):
    """
    Chiude a mercato tutte le posizioni del bot su symbol/magic.
    Ritorna (closed_tickets, errors) dove errors e' una lista di tuple
    (ticket, messaggio_errore).
    """
    closed = []
    errors = []

    positions = mt5.positions_get(symbol=symbol) or []
    for position in positions:
        if int(getattr(position, "magic", 0) or 0) != int(magic):
            continue
        ticket = int(position.ticket)
        try:
            close_position(symbol, magic, comment, ticket, deviation)
            closed.append(ticket)
        except Exception as e:
            errors.append((ticket, str(e)))

    return closed, errors


REPORT_PIP_SIZE = 0.10
REPORT_BE_TOLERANCE_PIPS = 0.5


def _deal_attr(deal, name, default=None):
    return getattr(deal, name, default)


def get_closed_trades_for_period(symbol, magic, start_local_utc, end_local_utc):
    """
    Legge dallo storico MT5 le posizioni chiuse nel periodo [start, end)
    (datetime timezone-aware, gia' convertiti in UTC dal chiamante),
    filtrando per symbol/magic. Una voce per posizione chiusa.
    """
    start_utc = start_local_utc - timedelta(days=7)
    deals = mt5.history_deals_get(start_utc, end_local_utc)
    if deals is None:
        logger.warning("⚠️ MT5 history_deals_get vuoto/errore: %s", mt5.last_error())
        return []

    grouped = {}
    for deal in deals:
        if str(_deal_attr(deal, "symbol", "")).upper() != str(symbol).upper():
            continue
        if int(_deal_attr(deal, "magic", 0) or 0) != int(magic):
            continue
        position_id = int(_deal_attr(deal, "position_id", 0) or 0)
        if position_id <= 0:
            continue
        grouped.setdefault(position_id, []).append(deal)

    entry_in = getattr(mt5, "DEAL_ENTRY_IN", 0)
    entry_out = getattr(mt5, "DEAL_ENTRY_OUT", 1)
    entry_out_by = getattr(mt5, "DEAL_ENTRY_OUT_BY", 3)
    reason_tp = getattr(mt5, "DEAL_REASON_TP", 6)
    reason_sl = getattr(mt5, "DEAL_REASON_SL", 4)
    buy_type = getattr(mt5, "DEAL_TYPE_BUY", 0)

    closed = []
    for position_id, position_deals in grouped.items():
        entries = [d for d in position_deals if int(_deal_attr(d, "entry", -1)) == int(entry_in)]
        exits = [d for d in position_deals if int(_deal_attr(d, "entry", -1)) in {int(entry_out), int(entry_out_by)}]
        if not entries or not exits:
            continue

        exits = sorted(exits, key=lambda d: float(_deal_attr(d, "time", 0) or 0))
        last_exit_time = float(_deal_attr(exits[-1], "time", 0) or 0)
        if not (start_local_utc.timestamp() <= last_exit_time < end_local_utc.timestamp()):
            continue

        entries = sorted(entries, key=lambda d: float(_deal_attr(d, "time", 0) or 0))
        entry_deal = entries[0]
        direction_type = int(_deal_attr(entry_deal, "type", 0) or 0)
        direction = "BUY" if direction_type == buy_type else "SELL"
        entry_price = float(_deal_attr(entry_deal, "price", 0.0) or 0.0)

        total_exit_volume = 0.0
        weighted_pips = 0.0
        total_profit = 0.0
        hit_tp = False
        hit_sl = False

        for exit_deal in exits:
            volume = float(_deal_attr(exit_deal, "volume", 0.0) or 0.0)
            close_price = float(_deal_attr(exit_deal, "price", 0.0) or 0.0)
            pips = (
                (close_price - entry_price) if direction == "BUY" else (entry_price - close_price)
            ) / REPORT_PIP_SIZE

            total_exit_volume += volume
            weighted_pips += pips * volume
            total_profit += float(_deal_attr(exit_deal, "profit", 0.0) or 0.0)

            reason = int(_deal_attr(exit_deal, "reason", -1))
            hit_tp = hit_tp or reason == reason_tp
            hit_sl = hit_sl or reason == reason_sl

        if total_exit_volume <= 0:
            continue

        pips_total = weighted_pips / total_exit_volume
        if abs(pips_total) <= REPORT_BE_TOLERANCE_PIPS:
            result = "BE"
        elif pips_total > 0:
            result = "WIN"
        else:
            result = "LOSS"

        closed.append({
            "position_id": position_id,
            "direction": direction,
            "entry": entry_price,
            "pips": pips_total,
            "profit": total_profit,
            "result": result,
            "hit_tp": hit_tp,
            "hit_sl": hit_sl,
        })

    return sorted(closed, key=lambda item: item["position_id"])


def get_closed_position_info(position_ticket):
    """
    Recupera dallo storico MT5 le informazioni di chiusura di una posizione
    gia' chiusa. Ritorna None se lo storico non e' ancora disponibile.
    """
    ticket = int(position_ticket)
    deals = mt5.history_deals_get(position=ticket)
    if not deals:
        return None

    exit_entries = {
        getattr(mt5, "DEAL_ENTRY_OUT", 1),
        getattr(mt5, "DEAL_ENTRY_OUT_BY", 3),
    }
    exit_deals = [d for d in deals if int(getattr(d, "entry", -1)) in exit_entries]
    candidates = exit_deals if exit_deals else list(deals)
    if not candidates:
        return None

    close_deal = max(
        candidates,
        key=lambda d: (int(getattr(d, "time_msc", 0) or 0), int(getattr(d, "ticket", 0) or 0)),
    )

    reason = int(getattr(close_deal, "reason", -1))
    sl_reason = getattr(mt5, "DEAL_REASON_SL", 4)
    tp_reason = getattr(mt5, "DEAL_REASON_TP", 6)

    return {
        "price": float(getattr(close_deal, "price", 0.0) or 0.0),
        "reason": reason,
        "is_sl": reason == sl_reason,
        "is_tp": reason == tp_reason,
        "deal_ticket": int(getattr(close_deal, "ticket", 0) or 0),
    }
