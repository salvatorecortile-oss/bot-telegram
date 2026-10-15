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
    exit_price = _number_after(r"\bUSCITA\b", text)
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
    # APERTURA: VENDI/COMPRA + Ingresso + Stop + Obiettivo
    # ------------------------------------------------------------
    direction_match = re.search(r"\b(VENDI|COMPRA)\b", upper_header)
    if direction_match:
        # Solo XAUUSD: qualunque altro strumento viene ignorato.
        if not re.search(r"\bXAU\s*/?\s*USD\b", clean, re.IGNORECASE):
            return None

        direction = "SELL" if direction_match.group(1) == "VENDI" else "BUY"
        entry = _number_after(r"\bINGRESSO\b", clean)
        sl = _number_after(r"\bSTOP\b", clean)
        # "Obiettivo 4486,04" oppure "Obiettivo 1 4169,15": il "1" e' l'indice.
        tp_match = re.search(
            r"\bOBIETTIVO\b\s*(?:([1-9])\s+)?[:=]?\s*(" + _NUMBER + r")",
            clean,
            re.IGNORECASE,
        )
        tp = _to_float(tp_match.group(2)) if tp_match else None
        targets_match = re.search(r"\bDI\s+(\d+)\s+OBIETTIVI\b", clean, re.IGNORECASE)
        targets_total = int(targets_match.group(1)) if targets_match else 1

        if entry is None or sl is None or tp is None:
            return None

        # Coerenza dei livelli: evita di aprire con un numero letto male.
        if direction == "BUY" and not (sl < entry < tp):
            return None
        if direction == "SELL" and not (tp < entry < sl):
            return None

        return {
            "action": "OPEN",
            "symbol": SYMBOL,
            "signal_no": signal_no,
            "direction": direction,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "targets_total": targets_total,
        }

    # ------------------------------------------------------------
    # AGGIORNAMENTI (l'ordine dei controlli conta: "STOP A PAREGGIO"
    # va riconosciuto prima del semplice "STOP").
    # ------------------------------------------------------------
    if re.search(r"\bOBIETTIVO\s+RAGGIUNTO\b", upper_header):
        exit_price, pips = _exit_and_pips(clean)
        return {
            "action": "TP_HIT",
            "symbol": SYMBOL,
            "signal_no": signal_no,
            "exit_price": exit_price,
            "pips": pips,
        }

    if re.search(r"\bSTOP\s+A\s+PAREGGIO\b|\bPAREGGIO\b", upper_header):
        return {
            "action": "BREAKEVEN",
            "symbol": SYMBOL,
            "signal_no": signal_no,
            "new_sl": _number_after(r"\bNUOVO\s+STOP\b", clean),
        }

    if re.search(r"\bCHIUSA\b", upper_header):
        exit_price, pips = _exit_and_pips(clean)
        return {
            "action": "CLOSE",
            "symbol": SYMBOL,
            "signal_no": signal_no,
            "exit_price": exit_price,
            "pips": pips,
        }

    if re.search(r"\bSTOP\b", upper_header):
        exit_price, pips = _exit_and_pips(clean)
        return {
            "action": "SL_HIT",
            "symbol": SYMBOL,
            "signal_no": signal_no,
            "exit_price": exit_price,
            "pips": pips,
        }

    return None
