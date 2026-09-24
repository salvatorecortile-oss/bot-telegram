import re

_NUMBER = r"([0-9]+(?:[.,][0-9]+)?)"


def _clean(text):
    return (
        (text or "")
        .replace("​", "")
        .replace("\xa0", " ")
        .replace("\r", "\n")
        .strip()
    )


def _float(value):
    return float(value.replace(",", "."))


def _first_number_after_label(text, labels):
    clean = _clean(text)
    for label in labels:
        pattern = re.compile(label, re.IGNORECASE)
        for line in clean.splitlines():
            match_label = pattern.search(line)
            if not match_label:
                continue
            after = line[match_label.end():]
            number = re.search(_NUMBER, after)
            if number:
                return _float(number.group(1))
    return None


# ------------------------------------------------------------
# MESSAGGIO 1: "Gold buy now 4379.8 - 4376"
# ------------------------------------------------------------
# Apre SUBITO a mercato. Lo zero/range indicato dal provider e' solo
# informativo: NON viene usato per aspettare/validare il prezzo di entrata
# (vedi mt5_executor.open_market_order), esattamente come richiesto.
_OPEN_NOW_PATTERN = re.compile(
    r"\b(?:GOLD|XAU\s*/?\s*USD)\b\s+(BUY|SELL)\s+NOW\b"
    rf"(?:\s*{_NUMBER}\s*-\s*{_NUMBER})?",
    re.IGNORECASE,
)


def _parse_open_now(clean):
    match = _OPEN_NOW_PATTERN.search(clean)
    if not match:
        return None

    direction = match.group(1).upper()
    zone_high_raw = match.group(2)
    zone_low_raw = match.group(3)

    zone_high = _float(zone_high_raw) if zone_high_raw else None
    zone_low = _float(zone_low_raw) if zone_low_raw else None

    if zone_high is not None and zone_low is not None:
        entry_reference = (zone_high + zone_low) / 2.0
    elif zone_high is not None:
        entry_reference = zone_high
    else:
        entry_reference = None

    return {
        "action": "OPEN",
        "symbol": "XAUUSD",
        "direction": direction,
        "entry_zone_high": zone_high,
        "entry_zone_low": zone_low,
        # Riferimento solo informativo/per DB matching: l'apertura reale
        # usa sempre il prezzo live MT5 (ASK per BUY, BID per SELL).
        "entry": entry_reference,
    }


# ------------------------------------------------------------
# MESSAGGIO 2: "SL: 4372" + righe "TP: 4382" / "TP. 4386" / "TP: open"
# ------------------------------------------------------------
_TP_LINE_PATTERN = re.compile(
    rf"^\s*TP\s*\d*\s*[:.]?\s*(OPEN|{_NUMBER})\s*$",
    re.IGNORECASE,
)


def _parse_sl_tp(clean):
    sl = _first_number_after_label(clean, [r"\bSTOP\s*LOSS\b", r"\bSL\b"])
    if sl is None:
        return None

    tp_values = []
    open_runner = False

    for line in clean.splitlines():
        match = _TP_LINE_PATTERN.match(line)
        if not match:
            continue
        raw = match.group(1)
        if raw.upper() == "OPEN":
            open_runner = True
            continue
        tp_values.append(_float(raw))

    if not tp_values:
        return None

    result = {
        "action": "SET_SLTP",
        "symbol": "XAUUSD",
        "sl": sl,
        "tp1": tp_values[0] if len(tp_values) > 0 else None,
        "tp2": tp_values[1] if len(tp_values) > 1 else None,
        # TP3 e' l'UNICO take profit realmente impostato su MT5.
        "tp3": tp_values[2] if len(tp_values) > 2 else None,
        "tp4": tp_values[3] if len(tp_values) > 3 else None,
        "tp_open_runner": open_runner,
    }
    return result


def parse_signal(text):
    """
    BOT Gold MO. Il segnale arriva in DUE messaggi separati:

    1. `Gold buy now 4379.8 - 4376` (o `Gold sell now ...`)
       -> action "OPEN": apre SUBITO a mercato (la zona di prezzo e' solo
       indicativa, NON viene aspettata/validata: si usa sempre il prezzo
       live MT5). Nessun SL/TP ancora: il trade resta "in attesa" dei
       parametri.

    2. Messaggio successivo che porta SL e i take profit:
           SL: 4372
           TP: 4382
           TP: 4384
           TP. 4386
           TP: 4388
           TP: open
       -> action "SET_SLTP": applica SL e TP3 (l'UNICO TP realmente
       impostato su MT5) al trade aperto al punto 1 e pubblica il
       messaggio nel canale (solo ora, completo di entry/SL/TP).
       TP1 resta memorizzato solo per il trigger interno del Break Even,
       TP2/TP4/"open" sono ignorati.

    IMPORTANTE: questo messaggio a volte ripete anche la riga
    "Gold buy/sell now ..." insieme a SL/TP (un "rilancio" del segnale
    ormai completo). La presenza di SL/TP ha SEMPRE la priorita': se un
    messaggio contiene SL/TP viene trattato come SET_SLTP anche se
    ripete la riga di apertura, per non aprire un secondo trade
    duplicato quando il primo e' gia' stato aperto dal messaggio 1.
    """
    clean = _clean(text)
    if not clean:
        return None

    sltp_signal = _parse_sl_tp(clean)
    if sltp_signal is not None:
        return sltp_signal

    open_signal = _parse_open_now(clean)
    if open_signal is not None:
        return open_signal

    return None
