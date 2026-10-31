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


def _to_signal_no(value):
    """'5.3' -> 5.3 (strategie SIGNAL 5.1 ... 5.8), '6' -> 6."""
    value = value.replace(",", ".")
    return float(value) if "." in value else int(value)


def _signal_number(text):
    match = re.search(r"\bSIGNAL\s*#?\s*(\d+(?:[.,]\d+)?)", text, re.IGNORECASE)
    return _to_signal_no(match.group(1)) if match else None


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


# Numero del segnale citato nel testo ("segnale 6", "signal 6").
_BLOCK_NUMBER = r"\b(?:SEGNALE|SIGNAL)\s*#?\s*(\d+(?:[.,]\d+)?)\b"

# Chiusura scritta a parole, senza "SIGNAL N" (es. "Chiudiamo quindi 1 trade su 4").
_FREE_CLOSE_VERB = r"\b(?:CHIUDIAMO|CHIUDETE|CHIUDERE|CHIUDO|CHIUDI|USCIAMO|USCITE)\b"
# "non chiudiamo", "non lo chiudiamo ancora"...
_FREE_CLOSE_NEGATION = r"\bNON\s+(?:\w+\s+){0,2}?(?:CHIUD|USC)"
# "chiudiamo domani", "chiudiamo al TP", "chiudiamo se..." -> non e' una chiusura adesso
_FREE_CLOSE_LATER = (
    _FREE_CLOSE_VERB
    + r"(?:\s+\w+){0,3}?\s+(?:DOMANI|DOPO|PIU|PIÙ|STASERA|STANOTTE|LUNEDI|LUNEDÌ|A\s+TP|AL\s+TP|IN\s+TP|"
    r"ALLO\s+SL|SE|QUANDO|APPENA)\b"
)


# "Non apriamo" in reply a un segnale: segnale mandato per errore -> si chiude.
_CANCEL_SIGNAL = r"\bNON\s+(?:LO\s+|LA\s+)?(?:APRIAMO|APRITE|APRIRE|ENTRIAMO|ENTRATE|ENTRARE)\b"


def _parse_free_close(clean):
    upper = clean.upper()
    if re.search(_CANCEL_SIGNAL, upper):
        # Vale solo in risposta a un segnale (vedi handle_free_close in main.py).
        return {"action": "FREE_CLOSE", "symbol": SYMBOL, "signal_no": None, "reply_only": True}
    if not re.search(_FREE_CLOSE_VERB, upper):
        return None
    if re.search(_FREE_CLOSE_NEGATION, upper) or re.search(_FREE_CLOSE_LATER, upper):
        return None
    # Domanda ("chiudiamo?"): non e' un'istruzione.
    if re.search(_FREE_CLOSE_VERB + r"[^.!\n]*\?", upper):
        return None
    # "Chiudiamo il segnale 6": se nomina il numero, si chiude quel SIGNAL.
    number = re.search(_BLOCK_NUMBER, upper)
    return {"action": "FREE_CLOSE", "symbol": SYMBOL,
            "signal_no": _to_signal_no(number.group(1)) if number else None, "reply_only": False}


# "Se dovesse arrivare un altro segnale 6 di oggi non lo apriamo":
# blocca le nuove aperture di quel SIGNAL fino a fine giornata.
_BLOCK_NOT_OPEN = r"\bNON\s+(?:LO\s+|LA\s+|LI\s+)?(?:APRIAMO|APRITE|APRIRE|APRIREMO|ENTRIAMO|ENTRATE|ENTRARE)\b"


def _parse_block(clean):
    upper = clean.upper()
    number = re.search(_BLOCK_NUMBER, upper)
    if not number or not re.search(_BLOCK_NOT_OPEN, upper):
        return None
    # Deve parlare di un segnale FUTURO ("se arriva", "un altro", "di oggi"...),
    # non di un segnale gia' mandato.
    if not re.search(r"\b(?:SE|ALTRO|ALTRI|PROSSIMO|PROSSIMI|NUOVO|NUOVI|ARRIVA|ARRIVASSE|DOVESSE|DOVVESSE|"
                     r"OGGI|PIU|PIÙ)\b", upper):
        return None
    return {"action": "BLOCK_SIGNAL", "symbol": SYMBOL, "signal_no": _to_signal_no(number.group(1))}


# Prima riga dei messaggi del formato "ENTRA ORA / CHIUDI ORA / SPOSTA LO STOP".
_ENTER_NOW = r"\bENTRA(?:TE)?\s+ORA\b|\bENTRIAMO\s+ORA\b"
_UPDATE_HEADER = (
    r"\bCHIUD[IO]\b|\bCHIUDIAMO\b|\bCHIUS[AO]\b|\bSPOSTA\b|\bSPOSTIAMO\b|\bCOLPITO\b|"
    r"\bRAGGIUNTO\b|\bPAREGGIO\b"
)
# Altri strumenti (Forex, cripto): i loro "ENTRA ORA" vengono ignorati.
_OTHER_SYMBOL = (
    r"\b(?:EUR|GBP|USD|JPY|AUD|NZD|CAD|CHF)\s*/?\s*(?:USD|JPY|GBP|EUR|CHF|CAD|AUD|NZD)\b|"
    r"\b(?:BTC|ETH|XRP|SOL|BNB|DOGE|CRYPTO|CRIPTO)\w*"
)


def _new_stop_price(clean):
    """Prezzo del nuovo stop in "SPOSTA LO STOP" (None se non c'e' un prezzo)."""
    for label in (
        r"\bNUOVO\s+(?:STOP\s*LOSS|STOP|SL)\b",
        r"\bSTOP\s*(?:LOSS)?\s+A\b",
        r"\b(?:STOP\s*LOSS|STOP|SL)\b",
    ):
        for match in re.finditer(label + r"\s*[:=]?\s*(" + _NUMBER + r")", clean, re.IGNORECASE):
            value = _to_float(match.group(1))
            # "Stop a 0,01: -40 $" e' il lotto, non un prezzo.
            if value >= 1:
                return value
    return None


def parse_signal(text):
    clean = _clean(text)
    if not clean:
        return None

    block = _parse_block(clean)
    if block is not None:
        return block

    header = _header(clean)
    if not header:
        return _parse_free_close(clean)

    signal_no = _signal_number(header)
    upper_header = header.upper()

    # ------------------------------------------------------------
    # APERTURA. Due formati del canale:
    #   "SIGNAL 2 ⬇️ VENDI XAUUSD" + Ingresso / Stop / Obiettivo (1)
    #   "SIGNAL 2 – XAUUSD BUY"    + Ingresso: / TP1: / SL:
    # ------------------------------------------------------------
    if re.search(r"\bINVERSIONE\b", upper_header):
        # "SIGNAL 5 🔄 INVERSIONE XAUUSD" + "CHIUDI ⬇️ VENDI" + "APRI ⬆️ COMPRA":
        # la direzione nuova e' quella della riga APRI (la chiusura della
        # vecchia la fa l'inversione del SIGNAL 5/6 prima di aprire).
        direction_match = re.search(r"\bAPRI\b[^\n]*?\b(VENDI|COMPRA|SELL|BUY)\b", clean.upper())
        if direction_match is None:
            # Solo "CHIUDI" senza nuova apertura: chiusura del SIGNAL.
            exit_price, pips = _exit_and_pips(clean)
            return {"action": "CLOSE", "symbol": SYMBOL, "signal_no": signal_no,
                    "exit_price": exit_price, "pips": pips}
    elif re.search(_UPDATE_HEADER, upper_header):
        # "🔴 CHIUDI ORA · SIGNAL 5.3 BUY", "🟡 SPOSTA LO STOP"...: mai un'apertura.
        direction_match = None
    else:
        direction_match = re.search(r"\b(VENDI|COMPRA|SELL|BUY)\b", upper_header)
        if direction_match is None and _ENTER_NOW and re.search(_ENTER_NOW, upper_header):
            # "🟢 ENTRA ORA · SIGNAL 5.3": la direzione puo' stare in un'altra riga.
            direction_match = re.search(r"\b(VENDI|COMPRA|SELL|BUY)\b", clean.upper())
    if direction_match:
        # Solo XAUUSD: qualunque altro strumento viene ignorato. Nei messaggi
        # "ENTRA ORA" senza simbolo si assume l'oro (la Sala lavora solo sull'oro),
        # ma se compare un altro strumento il segnale viene scartato.
        if not re.search(r"\bXAU\s*/?\s*USD\b", clean, re.IGNORECASE):
            if not re.search(_ENTER_NOW, upper_header) or re.search(_OTHER_SYMBOL, clean.upper()):
                return None

        direction = "SELL" if direction_match.group(1) in {"VENDI", "SELL"} else "BUY"
        # "BUY LIMIT" / "SELL LIMIT" / "BUY STOP" / "SELL STOP" -> ordine pendente
        # al prezzo di Ingresso; altrimenti apertura a mercato.
        direction_line = next(
            (line.upper() for line in clean.splitlines() if direction_match.group(1) in line.upper()),
            upper_header,
        )
        if re.search(r"\bLIMIT\b", upper_header) or re.search(r"\bLIMIT\b", direction_line):
            order_type = "LIMIT"
        elif re.search(r"\b(?:BUY|SELL|COMPRA|VENDI)\s+STOP\b", direction_line):
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
        # SIGNAL 5.x ("ENTRA ORA" senza TP) o "Uscita: al segnale della strategia".
        if tp is None and not re.search(r"\bUSCITA\b", clean, re.IGNORECASE) \
                and not re.search(_ENTER_NOW, upper_header):
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

    # "🟡 SPOSTA LO STOP" al nuovo prezzo (prima del semplice "STOP", che
    # altrimenti verrebbe letto come stop colpito e chiuderebbe l'operazione).
    if re.search(r"\bSPOSTA\b|\bSPOSTIAMO\b|\bSPOSTATE\b|\bNUOVO\s+(?:STOP|SL)\b", upper_header):
        return {
            "action": "MOVE_SL",
            "symbol": SYMBOL,
            "signal_no": signal_no,
            "new_sl": _new_stop_price(clean),
        }

    if re.search(r"\bCHIUS[AO]\b|\bCHIUD[IO]\b|\bCHIUDIAMO\b|\bCLOSED?\b", upper_header):
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
