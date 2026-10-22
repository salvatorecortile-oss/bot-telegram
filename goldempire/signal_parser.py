"""
Parser del canale "Gold empire signals room".

Formati reali gestiti (i numeri usano la virgola come separatore decimale):

APERTURA
    🟣 SIGNAL 2 ⬇️ VENDI XAUUSD
    Ingresso 4204,38
    Stop 4214,33 · rischio 9,95 $
    Obiettivo 1 4169,15 · +35,23 $ · primo di 4 obiettivi
    Valori per 0,01 lotti · XAUUSD

    🟢 SIGNAL 4 ⬆️ COMPRA XAUUSD
    Ingresso 4155,08
    Stop 4107,80 · rischio 47,28 $
    Obiettivo 4486,04 · +331,0 $

AGGIORNAMENTI (sempre in reply al segnale di apertura)
    🟣 SIGNAL 2 ✅ OBIETTIVO RAGGIUNTO   Uscita 4169,14  Risultato +352,4 pips
    🟣 SIGNAL 2 ⚪ STOP A PAREGGIO       Nuovo stop 4203,40 · al prezzo d'ingresso
    🟡 SIGNAL 3 ❌ STOP                  Uscita 4135,92  Risultato −241,6 pips
    🟢 SIGNAL 4 🏁 CHIUSA                Uscita 4086,87  Risultato +308,2 pips

Azioni restituite: OPEN, TP_HIT, BREAKEVEN, SL_HIT, CLOSE (oppure None).
"""
import re

SYMBOL = "XAUUSD"

# Numero con virgola o punto decimale (4204,38 / 4204.38 / 4204).
_NUMBER = r"[-+]?\d+(?:[.,]\d+)?"


def _clean(text):
    text = text or ""
    for old, new in (
        ("​", ""), ("‌", ""), ("‍", ""), ("️", ""),
        ("\xa0", " "), (" ", " "), ("\r", "\n"),
        ("−", "-"), ("–", "-"), ("—", "-"),
        ("*", ""), ("_", ""), ("`", ""),
    ):
        text = text.replace(old, new)
    return text.strip()


def _to_float(value):
    return float(value.replace(" ", "").replace(",", "."))


def _number_after(label_regex, text):
    match = re.search(label_regex + r"\s*[:=]?\s*(" + _NUMBER + r")", text, re.IGNORECASE)
    if not match:
        return None
    return _to_float(match.group(1))


def _signal_number(text):
    match = re.search(r"\bSIGNAL\s*#?\s*(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _header(text):
    """Prima riga che contiene 'SIGNAL' (es. '🟣 SIGNAL 2 ✅ OBIETTIVO RAGGIUNTO')."""
    for line in text.splitlines():
        if re.search(r"\bSIGNAL\b", line, re.IGNORECASE):
            return line
    return ""


def _exit_and_pips(text):
    exit_price = _number_after(r"\b(?:USCITA|EXIT)\b", text)
    pips_match = re.search(
        r"\bRISULTATO\b\s*[:=]?\s*([-+]?\s*\d+(?:[.,]\d+)?)\s*PIPS?\b",
        text,
        re.IGNORECASE,
    )
    pips = _to_float(pips_match.group(1).replace(" ", "")) if pips_match else None
    return exit_price, pips


def parse_signal(text):
    clean = _clean(text)
    if not clean:
        return None

    header = _header(clean)
    if not header:
        return None

    signal_no = _signal_number(header)
    upper_header = header.upper()

    # ------------------------------------------------------------
    # APERTURA. Due formati del canale:
    #   "SIGNAL 2 ⬇️ VENDI XAUUSD" + Ingresso / Stop / Obiettivo (1)
    #   "SIGNAL 2 – XAUUSD BUY"    + Ingresso: / TP1: / SL:
    # ------------------------------------------------------------
    direction_match = re.search(r"\b(VENDI|COMPRA|SELL|BUY)\b", upper_header)
    if direction_match:
        # Solo XAUUSD: qualunque altro strumento viene ignorato.
        if not re.search(r"\bXAU\s*/?\s*USD\b", clean, re.IGNORECASE):
            return None

        direction = "SELL" if direction_match.group(1) in {"VENDI", "SELL"} else "BUY"
        # "BUY LIMIT" / "SELL LIMIT" / "BUY STOP" / "SELL STOP" -> ordine pendente
        # al prezzo di Ingresso; altrimenti apertura a mercato.
        if re.search(r"\bLIMIT\b", upper_header):
            order_type = "LIMIT"
        elif re.search(r"\b(?:BUY|SELL|COMPRA|VENDI)\s+STOP\b", upper_header):
            order_type = "STOP"
        else:
            order_type = "MARKET"
        entry = _number_after(r"\b(?:INGRESSO|ENTRATA|ENTRY)\b", clean)
        # Il numero deve seguire subito l'etichetta: righe come
        # "SL a 0.01 lot = -6,31$" non vengono confuse con lo stop.
        sl = _number_after(r"\b(?:STOP\s*LOSS|STOP|SL)\b", clean)
        # "Obiettivo 4486,04", "Obiettivo 1 4169,15", "TP1: 4163,40":
        # si usa sempre il primo obiettivo.
        tp_match = re.search(
            r"\b(?:OBIETTIVO|TAKE\s*PROFIT|TP)\s*(?:1\s*)?[:=]?\s*(" + _NUMBER + r")",
            clean,
            re.IGNORECASE,
        )
        tp = _to_float(tp_match.group(1)) if tp_match else None
        targets_match = re.search(r"\bDI\s+(\d+)\s+OBIETTIVI\b", clean, re.IGNORECASE)
        if targets_match:
            targets_total = int(targets_match.group(1))
        else:
            tp_indexes = [int(n) for n in re.findall(r"\bTP\s*([1-9])\b", clean, re.IGNORECASE)]
            targets_total = max(tp_indexes) if tp_indexes else 1

        # Senza obiettivo ("Uscita: al segnale della strategia") si apre con
        # il solo SL: la chiusura arrivera' con il messaggio del canale.
        if entry is None or sl is None:
            return None
        if tp is None and not re.search(r"\bUSCITA\b", clean, re.IGNORECASE):
            return None

        # Coerenza dei livelli: evita di aprire con un numero letto male.
        if direction == "BUY" and not (sl < entry and (tp is None or entry < tp)):
            return None
        if direction == "SELL" and not (sl > entry and (tp is None or entry > tp)):
            return None

        return {
            "action": "OPEN",
            "symbol": SYMBOL,
            "signal_no": signal_no,
            "direction": direction,
            "order_type": order_type,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "targets_total": targets_total,
        }

    # ------------------------------------------------------------
    # AGGIORNAMENTI (l'ordine dei controlli conta: "STOP A PAREGGIO"
    # va riconosciuto prima del semplice "STOP").
    # ------------------------------------------------------------
    # Ordine pendente annullato dal canale.
    if re.search(r"\b(?:ANNULLAT[OA]|CANCELLAT[OA]|CANCELL?ED|CANCEL|ELIMINAT[OA])\b", upper_header):
        return {"action": "CANCEL", "symbol": SYMBOL, "signal_no": signal_no}

    if re.search(
        r"\bOBIETTIVO\s+RAGGIUNTO\b|\bTP\s*\d?\s*(?:RAGGIUNTO|HIT|PRESO|COLPITO|CENTRATO)\b",
        upper_header,
    ):
        exit_price, pips = _exit_and_pips(clean)
        return {
            "action": "TP_HIT",
            "symbol": SYMBOL,
            "signal_no": signal_no,
            "exit_price": exit_price,
            "pips": pips,
        }

    if re.search(r"\bPAREGGIO\b|\bBREAK\s*-?\s*EVEN\b|\bBE\b", upper_header):
        return {
            "action": "BREAKEVEN",
            "symbol": SYMBOL,
            "signal_no": signal_no,
            "new_sl": _number_after(r"\bNUOVO\s+(?:STOP|SL)\b", clean),
        }

    if re.search(r"\bCHIUS[AO]\b|\bCLOSED?\b", upper_header):
        exit_price, pips = _exit_and_pips(clean)
        return {
            "action": "CLOSE",
            "symbol": SYMBOL,
            "signal_no": signal_no,
            "exit_price": exit_price,
            "pips": pips,
        }

    if re.search(r"\bSTOP\b|\bSL\b", upper_header):
        exit_price, pips = _exit_and_pips(clean)
        return {
            "action": "SL_HIT",
            "symbol": SYMBOL,
            "signal_no": signal_no,
            "exit_price": exit_price,
            "pips": pips,
        }

    return None
