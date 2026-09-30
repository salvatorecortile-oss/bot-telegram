"""
Parser dedicato al canale "BL Tech pro (Paid) channel".

Formato completamente diverso da Cédric (vedi signal_parser.py):
un unico messaggio con Open/SL/TP, e una reply successiva al segnale
originale che segnala "Running +N pips profit" quando vogliono prendere
profitto. Trattiamo solo XAUUSD: qualunque altra coppia viene ignorata.

Esempi reali:
    "XAUUSD BUY now\n⚪ Open:  4151.44\n🔻 SL   4111.50\n🔷 TP:  4220.00\nUse Small Lot"
    "XAUUSD Running +50 pips profit ✅✅✅Take some Partial Profit🔥🔥🔥And Set Stop Loss Entry Price🔥"
"""
import re

_NUMBER = r"[-+]?\d+(?:[.,]\d+)?"


def _float(value):
    return float(value.replace(",", "."))


def parse_bltech_signal(text):
    if not text:
        return None

    clean = text.strip()

    # Solo XAUUSD: qualunque altra coppia (forex ecc.) viene ignorata subito.
    if not re.match(r"^\s*XAUUSD\b", clean, re.IGNORECASE):
        return None

    # ------------------------------------------------------------
    # CHIUSURA: reply al segnale con "Running ... pips profit".
    # I pips indicati nel testo sono solo informativi/trigger: il calcolo
    # vero viene fatto dal prezzo reale di MT5, non da questo numero.
    # ------------------------------------------------------------
    if re.search(r"\bRUNNING\b", clean, re.IGNORECASE):
        return {"action": "CLOSE_SIGNAL", "symbol": "XAUUSD"}

    # ------------------------------------------------------------
    # APERTURA: "XAUUSD BUY now" / "SELL now" / "BUY limit" / "SELL limit"
    # ------------------------------------------------------------
    order_match = re.search(
        r"XAUUSD\s+(BUY|SELL)\s+(now|limit)",
        clean,
        re.IGNORECASE,
    )
    if not order_match:
        return None

    direction = order_match.group(1).upper()
    order_type = "MARKET" if order_match.group(2).lower() == "now" else "LIMIT"

    open_match = re.search(rf"\bOpen:?\s*({_NUMBER})", clean, re.IGNORECASE)
    sl_match = re.search(rf"\bSL:?\s*({_NUMBER})", clean, re.IGNORECASE)
    tp_match = re.search(rf"\bTP:?\s*({_NUMBER})", clean, re.IGNORECASE)

    if not open_match or not sl_match or not tp_match:
        return None

    return {
        "action": "OPEN",
        "symbol": "XAUUSD",
        "direction": direction,
        "order_type": order_type,
        "entry": _float(open_match.group(1)),
        "sl": _float(sl_match.group(1)),
        "tp": _float(tp_match.group(1)),
    }
