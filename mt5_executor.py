import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import MetaTrader5 as mt5

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

# Usa lo stesso root logger configurato da main.py (scrive anche su
# logs/bot.log). Un semplice getLogger(__name__) qui basta perché eredita
# gli handler impostati da setup_logging() in main.py.
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


def connect_mt5():
    """
    Connette direttamente il terminale configurato e verifica che l'account
    sia quello atteso.
    """
    print("=" * 72)
    print("🔌 CONNESSIONE META TRADER 5")
    print("=" * 72)
    print(f"Terminale : {MT5_PATH}")

    initialized = mt5.initialize(
        path=MT5_PATH,
        login=int(MT5_LOGIN),
        password=MT5_PASSWORD,
        server=MT5_SERVER,
    )

    if not initialized:
        print(f"❌ MT5 initialize fallito: {mt5.last_error()}")
        return False

    account = mt5.account_info()
    if account is None:
        print(f"❌ Account MT5 non disponibile: {mt5.last_error()}")
        return False

    print(f"Login     : {account.login}")
    print(f"Server    : {account.server}")
    print(f"Balance   : {account.balance}")
    print(f"Equity    : {account.equity}")
    print(f"Leverage  : {getattr(account, 'leverage', 'N/D')}")

    if int(account.login) != int(MT5_LOGIN):
        print(
            f"❌ ACCOUNT SBAGLIATO: atteso {MT5_LOGIN}, "
            f"trovato {account.login}"
        )
        return False

    if MT5_SERVER and account.server != MT5_SERVER:
        print(
            f"❌ SERVER DIVERSO: atteso {MT5_SERVER}, "
            f"trovato {account.server}"
        )
        return False

    symbol_info = mt5.symbol_info(MT5_SYMBOL)
    if symbol_info is None:
        print(f"❌ Simbolo {MT5_SYMBOL} non trovato.")
        return False

    if not symbol_info.visible:
        if not mt5.symbol_select(MT5_SYMBOL, True):
            print(f"❌ Impossibile rendere visibile {MT5_SYMBOL}.")
            return False

    print(f"Symbol    : {MT5_SYMBOL}")
    print(f"Digits    : {symbol_info.digits}")
    print(f"Point     : {symbol_info.point}")
    print(f"Min lot   : {symbol_info.volume_min}")
    print(f"Max lot   : {symbol_info.volume_max}")
    print(f"Step      : {symbol_info.volume_step}")
    print(f"Filling   : {getattr(symbol_info, 'filling_mode', 'N/D')}")
    print("✅ MT5 PRONTO.")
    print("=" * 72)
    return True


def _symbol_info():
    info = mt5.symbol_info(MT5_SYMBOL)
    if info is None:
        raise RuntimeError(
            f"Simbolo {MT5_SYMBOL} non disponibile: {mt5.last_error()}"
        )

    if not info.visible and not mt5.symbol_select(MT5_SYMBOL, True):
        raise RuntimeError(f"Impossibile attivare {MT5_SYMBOL}.")

    return info


def _normalize_price(value, digits):
    return round(float(value), int(digits))


def _normalize_volume(volume, info):
    step = float(info.volume_step or 0.01)
    minimum = float(info.volume_min or step)
    maximum = float(info.volume_max or volume)

    # Arrotondamento verso il basso a uno step valido.
    steps = int((float(volume) + 1e-12) / step)
    normalized = steps * step

    if normalized < minimum:
        normalized = minimum
    if normalized > maximum:
        normalized = maximum

    # Evita errori floating point nel request.
    decimals = max(0, len(str(step).split(".")[-1].rstrip("0")))
    return round(normalized, decimals)


def _get_filling_mode(info):
    """
    Seleziona un filling mode realmente supportato dal simbolo.
    Per execution MARKET, RETURN non è valido: preferiamo IOC/FOK.
    """
    filling_flags = int(getattr(info, "filling_mode", 0) or 0)

    # Costanti ufficiali MT5: FOK=1, IOC=2, BOC=4.
    symbol_fok = getattr(mt5, "SYMBOL_FILLING_FOK", 1)
    symbol_ioc = getattr(mt5, "SYMBOL_FILLING_IOC", 2)

    if filling_flags & symbol_ioc:
        return mt5.ORDER_FILLING_IOC

    if filling_flags & symbol_fok:
        return mt5.ORDER_FILLING_FOK

    execution = getattr(info, "trade_exemode", None)
    market_execution = getattr(
        mt5, "SYMBOL_TRADE_EXECUTION_MARKET", 2
    )

    if execution != market_execution:
        return mt5.ORDER_FILLING_RETURN

    # Ultimo fallback per broker che non espone correttamente il flag.
    return mt5.ORDER_FILLING_IOC


def _validate_volume(volume, info):
    minimum = float(info.volume_min)
    maximum = float(info.volume_max)
    step = float(info.volume_step)

    if volume < minimum - 1e-12:
        raise ValueError(
            f"Lotto {volume} sotto il minimo broker {minimum}."
        )
    if volume > maximum + 1e-12:
        raise ValueError(
            f"Lotto {volume} sopra il massimo broker {maximum}."
        )

    steps = round((volume - minimum) / step)
    if abs(minimum + steps * step - volume) > max(step * 1e-6, 1e-10):
        raise ValueError(
            f"Lotto {volume} non rispetta lo step broker {step}."
        )


def _validate_stops(direction, price, sl, tp, info):
    point = float(info.point)
    stops_level = int(getattr(info, "trade_stops_level", 0) or 0)
    freeze_level = int(getattr(info, "trade_freeze_level", 0) or 0)

    min_distance = max(stops_level, freeze_level) * point

    if direction == "BUY":
        if not sl < price:
            raise ValueError(
                f"BUY non valido: SL {sl:.2f} non è sotto il prezzo {price:.2f}."
            )
        if min_distance > 0 and price - sl < min_distance:
            raise ValueError(
                f"BUY SL troppo vicino: distanza {price-sl:.2f}, minima {min_distance:.2f}."
            )
        if tp and tp <= price:
            raise ValueError(
                f"BUY non valido: TP {tp:.2f} non è sopra il prezzo {price:.2f}."
            )
        if min_distance > 0 and tp and tp - price < min_distance:
            raise ValueError(
                f"BUY TP troppo vicino: distanza {tp-price:.2f}, minima {min_distance:.2f}."
            )
    else:
        if not sl > price:
            raise ValueError(
                f"SELL non valido: SL {sl:.2f} non è sopra il prezzo {price:.2f}."
            )
        if min_distance > 0 and sl - price < min_distance:
            raise ValueError(
                f"SELL SL troppo vicino: distanza {sl-price:.2f}, minima {min_distance:.2f}."
            )
        if tp and tp >= price:
            raise ValueError(
                f"SELL non valido: TP {tp:.2f} non è sotto il prezzo {price:.2f}."
            )
        if min_distance > 0 and tp and price - tp < min_distance:
            raise ValueError(
                f"SELL TP troppo vicino: distanza {price-tp:.2f}, minima {min_distance:.2f}."
            )


def _current_price(direction):
    tick = mt5.symbol_info_tick(MT5_SYMBOL)
    if tick is None:
        return None

    if direction == "BUY":
        return float(tick.ask)
    return float(tick.bid)


def _send_order(request):
    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(
            f"MT5 order_send ha restituito None: {mt5.last_error()}"
        )

    accepted = {
        getattr(mt5, "TRADE_RETCODE_DONE", 10009),
        getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010),
    }

    if result.retcode not in accepted:
        raise RuntimeError(
            f"Ordine rifiutato: retcode={result.retcode}, "
            f"comment={getattr(result, 'comment', '')}"
        )

    return result


def _find_position_ticket(direction, volume, open_price):
    """
    Cerca la posizione appena aperta e restituisce il vero POSITION ticket.
    Questo è il ticket corretto da usare per SL/TP e chiusura.
    """
    order_type = (
        mt5.POSITION_TYPE_BUY
        if direction == "BUY"
        else mt5.POSITION_TYPE_SELL
    )

    positions = mt5.positions_get(symbol=MT5_SYMBOL) or []

    candidates = []
    for position in positions:
        if getattr(position, "magic", None) != int(MAGIC_NUMBER):
            continue
        if getattr(position, "type", None) != order_type:
            continue

        pos_volume = float(getattr(position, "volume", 0.0) or 0.0)
        pos_price = float(getattr(position, "price_open", 0.0) or 0.0)

        volume_match = abs(pos_volume - float(volume)) < 1e-9
        price_match = abs(pos_price - float(open_price)) <= 0.05

        if volume_match and price_match:
            candidates.append(position)

    if not candidates:
        # Fallback: ultima posizione del nostro magic/direzione.
        for position in positions:
            if getattr(position, "magic", None) == int(MAGIC_NUMBER):
                if getattr(position, "type", None) == order_type:
                    candidates.append(position)

    if not candidates:
        return 0

    candidates.sort(
        key=lambda p: getattr(p, "time_msc", getattr(p, "time", 0)),
        reverse=True,
    )
    return int(candidates[0].ticket)


def open_market_order(signal, received_monotonic=None, source_timestamp=None):
    """
    Apre immediatamente l'operazione al prezzo corrente di mercato.

    BUY usa ASK, SELL usa BID.
    Non viene effettuato alcun controllo ENTRY_RANGE e non viene
    utilizzato alcun timeout di attesa.
    """
    del received_monotonic
    del source_timestamp

    info = _symbol_info()
    digits = int(info.digits)

    volume = _normalize_volume(LOT_SIZE, info)
    _validate_volume(volume, info)

    direction = signal["direction"].upper()
    if direction not in {"BUY", "SELL"}:
        raise ValueError(f"Direzione non valida: {direction}")

    # Apertura immediata al prezzo corrente MT5:
    # BUY -> ASK
    # SELL -> BID
    valid_price = _current_price(direction)

    if valid_price is None:
        raise RuntimeError(
            f"Prezzo corrente non disponibile per {MT5_SYMBOL}: {mt5.last_error()}"
        )

    valid_price = _normalize_price(valid_price, digits)

    raw_sl = signal.get("sl")

    # TP1/TP2/TP3 sono solo livelli informativi del provider.
    # Il trade resta aperto oltre +400 PIPS e viene gestito dal trailing live.
    sl = _normalize_price(raw_sl, digits) if raw_sl is not None else 0.0
    tp = 0.0

    if not sl:
        raise ValueError("Nel segnale ÉLITE lo SL deve essere presente.")
    _validate_stops(direction, valid_price, sl, 0.0, info)

    order_type = (
        mt5.ORDER_TYPE_BUY
        if direction == "BUY"
        else mt5.ORDER_TYPE_SELL
    )

    filling_mode = _get_filling_mode(info)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": MT5_SYMBOL,
        "volume": volume,
        "type": order_type,
        "price": valid_price,
        "sl": sl,
        "tp": tp,
        "deviation": int(DEVIATION),
        "magic": int(MAGIC_NUMBER),
        "comment": ORDER_COMMENT,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }

    result = _send_order(request)

    actual_price = float(
        getattr(result, "price", valid_price) or valid_price
    )

    position_ticket = _find_position_ticket(
        direction,
        float(getattr(result, "volume", volume) or volume),
        actual_price,
    )

    if not position_ticket:
        raise RuntimeError(
            "Ordine eseguito ma POSITION ticket non individuato. "
            "Per sicurezza il trade non viene considerato gestibile dal bot."
        )

    return TradeResult(
        order=int(getattr(result, "order", 0) or 0),
        deal=int(getattr(result, "deal", 0) or 0),
        volume=float(getattr(result, "volume", volume) or volume),
        price=actual_price,
        retcode=int(result.retcode),
        comment=str(getattr(result, "comment", "")),
        filling_mode=int(filling_mode),
        position_ticket=int(position_ticket),
    )



def get_closed_position_info(position_ticket):
    """
    Recupera dal registro storico MT5 le informazioni della chiusura
    di una posizione già chiusa.

    Restituisce un dizionario compatibile con il monitor di main.py:
        {
            "price": prezzo effettivo del deal di uscita,
            "reason": codice reason MT5,
            "is_sl": True se la chiusura è stata causata da Stop Loss,
        }

    Se lo storico non è ancora disponibile, restituisce None.
    Non invia ordini e non modifica la posizione.
    """
    ticket = int(position_ticket)

    # Cerchiamo i deal associati alla posizione. Un deal di uscita ha
    # entry=DEAL_ENTRY_OUT / OUT_BY.
    deals = mt5.history_deals_get(position=ticket)
    if not deals:
        return None

    exit_entries = {
        getattr(mt5, "DEAL_ENTRY_OUT", 1),
        getattr(mt5, "DEAL_ENTRY_OUT_BY", 3),
    }

    exit_deals = [
        deal for deal in deals
        if int(getattr(deal, "entry", -1)) in exit_entries
    ]

    # Alcuni broker/ambienti possono non valorizzare entry come previsto.
    # In quel caso usiamo comunque l'ultimo deal associato alla posizione.
    candidates = exit_deals if exit_deals else list(deals)
    if not candidates:
        return None

    close_deal = max(
        candidates,
        key=lambda d: (
            int(getattr(d, "time_msc", 0) or 0),
            int(getattr(d, "ticket", 0) or 0),
        ),
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


def move_position_to_breakeven(position_ticket):
    """
    Porta lo Stop Loss della posizione al prezzo di apertura (Break Even),
    mantenendo invariato il TP esistente.
    """
    info = _symbol_info()
    positions = mt5.positions_get(ticket=int(position_ticket))
    if not positions:
        raise RuntimeError(f"Posizione {position_ticket} non trovata o già chiusa.")

    position = positions[0]

    if getattr(position, "symbol", None) != MT5_SYMBOL:
        raise RuntimeError(
            f"Posizione {position_ticket} appartiene a "
            f"{getattr(position, 'symbol', 'N/D')}, non a {MT5_SYMBOL}."
        )

    if getattr(position, "magic", None) != int(MAGIC_NUMBER):
        raise RuntimeError(
            f"Posizione {position_ticket} non appartiene al MAGIC {MAGIC_NUMBER}."
        )

    digits = int(info.digits)
    breakeven = _normalize_price(float(position.price_open), digits)
    current_price = float(position.price_current)
    position_type = int(position.type)

    if position_type == mt5.POSITION_TYPE_BUY and not breakeven < current_price:
        raise ValueError(
            f"BUY: Break Even {breakeven:.2f} non è sotto il prezzo corrente {current_price:.2f}."
        )
    if position_type == mt5.POSITION_TYPE_SELL and not breakeven > current_price:
        raise ValueError(
            f"SELL: Break Even {breakeven:.2f} non è sopra il prezzo corrente {current_price:.2f}."
        )

    point = float(info.point)
    stops_level = int(getattr(info, "trade_stops_level", 0) or 0)
    freeze_level = int(getattr(info, "trade_freeze_level", 0) or 0)
    min_distance = max(stops_level, freeze_level) * point

    if min_distance > 0:
        distance = (
            current_price - breakeven
            if position_type == mt5.POSITION_TYPE_BUY
            else breakeven - current_price
        )
        if distance < min_distance:
            raise ValueError(
                f"Break Even troppo vicino al prezzo corrente: "
                f"distanza {distance:.2f}, minima {min_distance:.2f}."
            )

    existing_sl = float(getattr(position, "sl", 0.0) or 0.0)
    existing_tp = float(getattr(position, "tp", 0.0) or 0.0)

    if position_type == mt5.POSITION_TYPE_BUY and existing_sl > 0 and existing_sl >= breakeven:
        return existing_sl
    if position_type == mt5.POSITION_TYPE_SELL and existing_sl > 0 and existing_sl <= breakeven:
        return existing_sl

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": MT5_SYMBOL,
        "position": int(position_ticket),
        "sl": breakeven,
        "tp": existing_tp,
        "magic": int(MAGIC_NUMBER),
        "comment": ORDER_COMMENT,
    }

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(
            f"Break Even fallito: order_send=None, last_error={mt5.last_error()}"
        )

    accepted = {getattr(mt5, "TRADE_RETCODE_DONE", 10009)}
    if result.retcode not in accepted:
        raise RuntimeError(
            f"Break Even rifiutato: retcode={result.retcode}, "
            f"comment={getattr(result, 'comment', '')}"
        )

    return breakeven


def move_position_to_profit_protection(position_ticket, profit_pips, protection_percentage):
    """
    Calcola e applica uno SL protettivo in base ai PIPS comunicati dal provider.

    Per XAUUSD-P il pip viene ricavato dinamicamente come 10 * point del broker.
    Esempio con point=0.01: 1 pip = 0.10 di prezzo.

    BUY: SL = entry + (profit_pips * pip_size * percentuale)
    SELL: SL = entry - (profit_pips * pip_size * percentuale)

    Lo SL non può mai arretrare rispetto a quello già presente.
    """
    info = _symbol_info()

    positions = mt5.positions_get(ticket=int(position_ticket))
    if not positions:
        raise RuntimeError(
            f"Posizione {position_ticket} non trovata o già chiusa."
        )

    position = positions[0]

    if getattr(position, "symbol", None) != MT5_SYMBOL:
        raise RuntimeError(
            f"Posizione {position_ticket} appartiene a "
            f"{getattr(position, 'symbol', 'N/D')}, non a {MT5_SYMBOL}."
        )

    if getattr(position, "magic", None) != int(MAGIC_NUMBER):
        raise RuntimeError(
            f"Posizione {position_ticket} non appartiene al MAGIC {MAGIC_NUMBER}."
        )

    profit_pips = float(profit_pips)
    protection_percentage = float(protection_percentage)

    if profit_pips <= 0:
        raise ValueError("Il profitto in PIPS deve essere positivo.")
    if not 0 < protection_percentage <= 1:
        raise ValueError("La percentuale di protezione deve essere tra 0 e 1.")

    point = float(info.point)
    pip_size = point * 10.0

    entry = float(position.price_open)
    current_price = float(position.price_current)
    existing_sl = float(getattr(position, "sl", 0.0) or 0.0)

    position_type = int(position.type)
    protected_pips = profit_pips * protection_percentage
    price_distance = protected_pips * pip_size

    if position_type == mt5.POSITION_TYPE_BUY:
        direction = "BUY"
        calculated_sl = entry + price_distance

        if calculated_sl >= current_price:
            raise ValueError(
                f"BUY: SL calcolato {calculated_sl:.2f} non è sotto "
                f"il prezzo corrente {current_price:.2f}."
            )

        # Mai arretrare uno SL già più alto.
        if existing_sl > 0 and existing_sl >= calculated_sl:
            return {
                "sl": existing_sl,
                "changed": False,
                "protected_pips": protected_pips,
                "pip_size": pip_size,
            }

        new_sl = calculated_sl

    elif position_type == mt5.POSITION_TYPE_SELL:
        direction = "SELL"
        calculated_sl = entry - price_distance

        if calculated_sl <= current_price:
            raise ValueError(
                f"SELL: SL calcolato {calculated_sl:.2f} non è sopra "
                f"il prezzo corrente {current_price:.2f}."
            )

        # Mai arretrare uno SL già più basso.
        if existing_sl > 0 and existing_sl <= calculated_sl:
            return {
                "sl": existing_sl,
                "changed": False,
                "protected_pips": protected_pips,
                "pip_size": pip_size,
            }

        new_sl = calculated_sl

    else:
        raise RuntimeError(f"Tipo posizione non gestito: {position_type}")

    digits = int(info.digits)
    new_sl = _normalize_price(new_sl, digits)

    # Verifica distanza minima broker/freeze level.
    stops_level = int(getattr(info, "trade_stops_level", 0) or 0)
    freeze_level = int(getattr(info, "trade_freeze_level", 0) or 0)
    min_distance = max(stops_level, freeze_level) * point

    distance_from_price = (
        current_price - new_sl
        if position_type == mt5.POSITION_TYPE_BUY
        else new_sl - current_price
    )

    if min_distance > 0 and distance_from_price < min_distance:
        raise ValueError(
            f"{direction}: SL {new_sl:.2f} troppo vicino al prezzo corrente "
            f"{current_price:.2f}; distanza {distance_from_price:.2f}, "
            f"minima {min_distance:.2f}."
        )

    existing_tp = float(getattr(position, "tp", 0.0) or 0.0)

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": MT5_SYMBOL,
        "position": int(position_ticket),
        "sl": new_sl,
        "tp": existing_tp,
        "magic": int(MAGIC_NUMBER),
        "comment": ORDER_COMMENT,
    }

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(
            f"Trailing SL fallito: order_send=None, last_error={mt5.last_error()}"
        )

    accepted = {getattr(mt5, "TRADE_RETCODE_DONE", 10009)}
    if result.retcode not in accepted:
        raise RuntimeError(
            f"Trailing SL rifiutato: retcode={result.retcode}, "
            f"comment={getattr(result, 'comment', '')}"
        )

    return {
        "sl": new_sl,
        "changed": True,
        "protected_pips": protected_pips,
        "pip_size": pip_size,
    }


def modify_position_sl(position_ticket, new_sl):
    """Modifica esclusivamente lo Stop Loss di una posizione del bot."""
    info = _symbol_info()

    positions = mt5.positions_get(ticket=int(position_ticket))
    if not positions:
        raise RuntimeError(
            f"Posizione {position_ticket} non trovata o già chiusa."
        )

    position = positions[0]

    if getattr(position, "symbol", None) != MT5_SYMBOL:
        raise RuntimeError(
            f"Posizione {position_ticket} appartiene a "
            f"{getattr(position, 'symbol', 'N/D')}, non a {MT5_SYMBOL}."
        )

    if getattr(position, "magic", None) != int(MAGIC_NUMBER):
        raise RuntimeError(
            f"Posizione {position_ticket} non appartiene al MAGIC {MAGIC_NUMBER}."
        )

    new_sl = _normalize_price(new_sl, int(info.digits))
    position_type = int(position.type)
    current_price = float(position.price_current)

    if position_type == mt5.POSITION_TYPE_BUY and not new_sl < current_price:
        raise ValueError(
            f"BUY: nuovo SL {new_sl:.2f} deve essere sotto il prezzo corrente {current_price:.2f}."
        )
    if position_type == mt5.POSITION_TYPE_SELL and not new_sl > current_price:
        raise ValueError(
            f"SELL: nuovo SL {new_sl:.2f} deve essere sopra il prezzo corrente {current_price:.2f}."
        )

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": MT5_SYMBOL,
        "position": int(position_ticket),
        "sl": new_sl,
        "tp": float(getattr(position, "tp", 0.0) or 0.0),
        "magic": int(MAGIC_NUMBER),
        "comment": ORDER_COMMENT,
    }

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(
            f"Modifica SL fallita: order_send=None, last_error={mt5.last_error()}"
        )

    accepted = {
        getattr(mt5, "TRADE_RETCODE_DONE", 10009),
    }
    if result.retcode not in accepted:
        raise RuntimeError(
            f"Modifica SL rifiutata: retcode={result.retcode}, "
            f"comment={getattr(result, 'comment', '')}"
        )

    return new_sl



def modify_position_sl_tp(position_ticket, new_sl, new_tp):
    """
    Modifica SL/TP della posizione esistente del bot.

    Regola importante:
    - SL ha priorità.
    - Se SL è valido e TP è invalido, applica comunque SL e mantiene il TP esistente.
    - Se TP è valido e SL è invalido, applica comunque TP e mantiene lo SL esistente.
    - Se entrambi sono validi, applica entrambi.
    - Se entrambi sono invalidi, non modifica la posizione.
    """
    info = _symbol_info()

    positions = mt5.positions_get(ticket=int(position_ticket))
    if not positions:
        raise RuntimeError(
            f"Posizione {position_ticket} non trovata o già chiusa."
        )

    position = positions[0]

    if getattr(position, "symbol", None) != MT5_SYMBOL:
        raise RuntimeError(
            f"Posizione {position_ticket} appartiene a "
            f"{getattr(position, 'symbol', 'N/D')}, non a {MT5_SYMBOL}."
        )

    if getattr(position, "magic", None) != int(MAGIC_NUMBER):
        raise RuntimeError(
            f"Posizione {position_ticket} non appartiene al MAGIC {MAGIC_NUMBER}."
        )

    digits = int(info.digits)
    current_price = float(position.price_current)
    position_type = int(position.type)
    existing_sl = float(getattr(position, "sl", 0.0) or 0.0)
    existing_tp = float(getattr(position, "tp", 0.0) or 0.0)

    requested_sl = _normalize_price(new_sl, digits)
    requested_tp = _normalize_price(new_tp, digits)

    if position_type == mt5.POSITION_TYPE_BUY:
        direction = "BUY"
        sl_valid = requested_sl < current_price
        tp_valid = requested_tp > current_price
        sl_reason = (
            f"BUY: SL {requested_sl:.2f} deve essere sotto il prezzo corrente {current_price:.2f}."
        )
        tp_reason = (
            f"BUY: TP {requested_tp:.2f} deve essere sopra il prezzo corrente {current_price:.2f}."
        )
    elif position_type == mt5.POSITION_TYPE_SELL:
        direction = "SELL"
        sl_valid = requested_sl > current_price
        tp_valid = requested_tp < current_price
        sl_reason = (
            f"SELL: SL {requested_sl:.2f} deve essere sopra il prezzo corrente {current_price:.2f}."
        )
        tp_reason = (
            f"SELL: TP {requested_tp:.2f} deve essere sotto il prezzo corrente {current_price:.2f}."
        )
    else:
        raise RuntimeError(f"Tipo posizione non gestito: {position_type}")

    # Validazione broker-specifica separata per SL e TP.
    # Non usiamo _validate_stops() direttamente perché richiede entrambi validi.
    point = float(info.point)
    stops_level = int(getattr(info, "trade_stops_level", 0) or 0)
    freeze_level = int(getattr(info, "trade_freeze_level", 0) or 0)
    min_distance = max(stops_level, freeze_level) * point

    if min_distance > 0:
        if direction == "BUY":
            if current_price - requested_sl < min_distance:
                sl_valid = False
                sl_reason = (
                    f"BUY SL troppo vicino: distanza {current_price-requested_sl:.2f}, "
                    f"minima {min_distance:.2f}."
                )
            if requested_tp - current_price < min_distance:
                tp_valid = False
                tp_reason = (
                    f"BUY TP troppo vicino: distanza {requested_tp-current_price:.2f}, "
                    f"minima {min_distance:.2f}."
                )
        else:
            if requested_sl - current_price < min_distance:
                sl_valid = False
                sl_reason = (
                    f"SELL SL troppo vicino: distanza {requested_sl-current_price:.2f}, "
                    f"minima {min_distance:.2f}."
                )
            if current_price - requested_tp < min_distance:
                tp_valid = False
                tp_reason = (
                    f"SELL TP troppo vicino: distanza {current_price-requested_tp:.2f}, "
                    f"minima {min_distance:.2f}."
                )

    # Prepara i valori da inviare mantenendo il parametro esistente quando
    # quello nuovo è invalido. In questo modo un parametro errato non blocca
    # automaticamente l'altro.
    final_sl = requested_sl if sl_valid else existing_sl
    final_tp = requested_tp if tp_valid else existing_tp

    if not sl_valid:
        logger.warning("⚠️ SL NON APPLICATO | Position=%s | %s", position_ticket, sl_reason)
    if not tp_valid:
        logger.warning("⚠️ TP NON APPLICATO | Position=%s | %s", position_ticket, tp_reason)

    if not sl_valid and not tp_valid:
        raise ValueError(
            f"Nessun parametro valido da applicare. SL: {sl_reason} | TP: {tp_reason}"
        )

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": MT5_SYMBOL,
        "position": int(position_ticket),
        "sl": final_sl,
        "tp": final_tp,
        "magic": int(MAGIC_NUMBER),
        "comment": ORDER_COMMENT,
    }

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(
            f"Modifica SL/TP fallita: order_send=None, last_error={mt5.last_error()}"
        )

    accepted = {getattr(mt5, "TRADE_RETCODE_DONE", 10009)}
    if result.retcode not in accepted:
        raise RuntimeError(
            f"Modifica SL/TP rifiutata: retcode={result.retcode}, "
            f"comment={getattr(result, 'comment', '')}"
        )

    return {
        "position_ticket": int(position_ticket),
        "sl": final_sl,
        "tp": final_tp,
        "sl_applied": bool(sl_valid),
        "tp_applied": bool(tp_valid),
        "sl_requested": requested_sl,
        "tp_requested": requested_tp,
        "sl_error": None if sl_valid else sl_reason,
        "tp_error": None if tp_valid else tp_reason,
        "retcode": int(result.retcode),
        "direction": direction,
    }


def close_position(position_ticket):
    """
    Chiude a mercato una specifica POSITION ticket appartenente al bot.
    Non usa alcun prezzo contenuto nel messaggio Telegram.
    """
    info = _symbol_info()

    positions = mt5.positions_get(ticket=int(position_ticket))
    if not positions:
        raise RuntimeError(
            f"Posizione {position_ticket} non trovata o già chiusa."
        )

    position = positions[0]

    if getattr(position, "symbol", None) != MT5_SYMBOL:
        raise RuntimeError(
            f"Posizione {position_ticket} appartiene a "
            f"{getattr(position, 'symbol', 'N/D')}, non a {MT5_SYMBOL}."
        )

    if getattr(position, "magic", None) != int(MAGIC_NUMBER):
        raise RuntimeError(
            f"Posizione {position_ticket} non appartiene al MAGIC "
            f"{MAGIC_NUMBER}."
        )

    position_type = int(position.type)
    volume = float(position.volume)

    if position_type == mt5.POSITION_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(MT5_SYMBOL)
        if tick is None:
            raise RuntimeError("Tick MT5 non disponibile per chiusura BUY.")
        price = float(tick.bid)
    elif position_type == mt5.POSITION_TYPE_SELL:
        order_type = mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(MT5_SYMBOL)
        if tick is None:
            raise RuntimeError("Tick MT5 non disponibile per chiusura SELL.")
        price = float(tick.ask)
    else:
        raise RuntimeError(
            f"Tipo posizione non gestito: {position_type}"
        )

    price = _normalize_price(price, int(info.digits))
    filling_mode = _get_filling_mode(info)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": MT5_SYMBOL,
        "volume": volume,
        "type": order_type,
        "position": int(position_ticket),
        "price": price,
        "deviation": int(DEVIATION),
        "magic": int(MAGIC_NUMBER),
        "comment": ORDER_COMMENT,
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
