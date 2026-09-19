import re


_NUMBER = r"([0-9]+(?:[.,][0-9]+)?)"


def _clean(text):
    return (
        (text or "")
        .replace("\u200b", "")
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


def _find_symbol(text):
    upper = text.upper()
    if re.search(r"\bXAU\s*/\s*USD\b", upper):
        return "XAUUSD-P"
    if re.search(r"\bXAUUSD\b", upper):
        return "XAUUSD-P"
    if re.search(r"\bGOLD\b", upper):
        return "XAUUSD-P"
    return None


def _find_direction(text):
    upper = text.upper()
    match = re.search(r"\b(BUY|SELL|LONG|SHORT)\b", upper)
    if not match:
        return None
    value = match.group(1)
    return {"LONG": "BUY", "SHORT": "SELL"}.get(value, value)


def _extract_entry(text):
    # Supporta:
    # BUY XAUUSD ➡ Entry: 4345.16
    # XAUUSD BUY 4345.16
    # XAU/USD SELL Entry 4389.27
    value = _first_number_after_label(
        text,
        [r"\bENTRY\b", r"\bPREZZO\s+DI\b", r"\bPREZZO\b", r"\bPRICE\b"],
    )
    if value is not None:
        return value

    compact = re.search(
        rf"\b(?:XAU\s*/?\s*USD|GOLD)\b\s+"
        rf"(?:BUY|SELL|LONG|SHORT)\b[^0-9]*{_NUMBER}",
        text,
        re.IGNORECASE,
    )
    if compact:
        return _float(compact.group(1))

    reverse = re.search(
        rf"\b(?:BUY|SELL|LONG|SHORT)\b\s+"
        rf"(?:XAU\s*/?\s*USD|GOLD)\b[^0-9]*{_NUMBER}",
        text,
        re.IGNORECASE,
    )
    if reverse:
        return _float(reverse.group(1))

    return None


def _extract_update_entry(text):
    # Estrazione STRETTA per i messaggi di correzione (UPDATE_PARAMS):
    # accetta solo un'etichetta esplicita (Entry/Prezzo di/Prezzo/Price) o
    # il numero incollato subito dopo simbolo+direzione con al massimo
    # spazi/tab in mezzo (es. "XAUUSD SELL 4372"). Un formato ambiguo come
    # "SELL @4372" NON viene interpretato: meglio ignorare il messaggio
    # che rischiare di associare un'entry sbagliata.
    value = _first_number_after_label(
        text,
        [r"\bENTRY\b", r"\bPREZZO\s+DI\b", r"\bPREZZO\b", r"\bPRICE\b"],
    )
    if value is not None:
        return value

    strict = re.search(
        rf"\b(?:XAU\s*/?\s*USD|GOLD)\b\s+"
        rf"(?:BUY|SELL|LONG|SHORT)\b[ \t]*{_NUMBER}\b",
        text,
        re.IGNORECASE,
    )
    if strict:
        return _float(strict.group(1))

    strict_reverse = re.search(
        rf"\b(?:BUY|SELL|LONG|SHORT)\b[ \t]*{_NUMBER}\b\s+"
        rf"(?:XAU\s*/?\s*USD|GOLD)\b",
        text,
        re.IGNORECASE,
    )
    if strict_reverse:
        return _float(strict_reverse.group(1))

    return None


def parse_signal(text):
    """
    BOT 2 - Cédric FX ÉLITE.

    Segnale completo:
        BUY XAUUSD -> Entry: 4345.16
        SL: 4330.16
        TP1: 4350.16
        TP2: 4355.16
        TP3: 4385.16

    Il segnale completo apre DIRETTAMENTE il trade.
    - SL viene impostato subito.
    - TP3 è l'unico TP impostato su MT5.
    - TP1/TP2 sono solo informazioni del provider.

    Aggiornamenti:
    - TP1 HIT +50pips -> solo informazione Telegram; la protezione viene
      calcolata autonomamente dal prezzo live di MT5.
    - TP2/TP3/PIPS successivi -> solo informazione Telegram; il trailing
      viene calcolato autonomamente dal prezzo live di MT5.
    - STOP LOSS ... -> evento informativo.
    - Riepilogo giornaliero -> DAILY_RECAP, mai tradato.
    """
    clean = _clean(text)
    if not clean:
        return None

    # ------------------------------------------------------------
    # RIEPILOGO GIORNALIERO
    # ------------------------------------------------------------
    if re.search(r"\bRIEPILOGO\s+GIORNALIERO\b", clean, re.IGNORECASE):
        return {
            "action": "DAILY_RECAP",
            "symbol": "XAUUSD-P",
            "raw_recap": clean,
        }

    symbol = _find_symbol(clean)

    # ------------------------------------------------------------
    # SEGNALE COMPLETO -> APERTURA DIRETTA
    # ------------------------------------------------------------
    direction = _find_direction(clean)
    entry = _extract_entry(clean) if symbol == "XAUUSD-P" else None

    sl = _first_number_after_label(
        clean,
        [r"\bSTOP\s*LOSS\b", r"\bSL\b"],
    )
    tp3 = _first_number_after_label(
        clean,
        [r"\bTP\s*3\b", r"\bTP3\b"],
    )
    tp1 = _first_number_after_label(clean, [r"\bTP\s*1\b", r"\bTP1\b"])
    tp2 = _first_number_after_label(clean, [r"\bTP\s*2\b", r"\bTP2\b"])

    if (
        symbol == "XAUUSD-P"
        and direction is not None
        and entry is not None
        and sl is not None
        and tp3 is not None
    ):
        return {
            "action": "OPEN",
            "symbol": "XAUUSD-P",
            "direction": direction,
            "entry": entry,
            "sl": sl,
            "tp1": tp1,   # informativo
            "tp2": tp2,   # informativo
            "tp3": tp3,   # TP operativo
        }

    # ------------------------------------------------------------
    # MESSAGGIO DI CORREZIONE -> UPDATE_PARAMS
    # ------------------------------------------------------------
    # Il provider a volte rimanda SL/TP1 senza TP3 (es. per correggere un
    # segnale già inviato). NON apre un nuovo trade: aggiorna solo la
    # posizione già aperta nella stessa direzione (vedi process_update_params
    # in main.py). TP2 viene sempre ignorato.
    if symbol == "XAUUSD-P" and direction is not None and sl is not None and tp1 is not None:
        update_entry = _extract_update_entry(clean)
        if update_entry is not None:
            return {
                "action": "UPDATE_PARAMS",
                "symbol": "XAUUSD-P",
                "direction": direction,
                "entry": update_entry,
                "sl": sl,
                "tp1": tp1,
            }

    # ------------------------------------------------------------
    # ANNUNCIO "SEGNALE IN ARRIVO" -> OPEN_SIGNAL
    # ------------------------------------------------------------
    # Puro annuncio informativo: viene copiato nel canale destinazione ma
    # NON apre alcuna posizione. L'apertura reale avviene solo quando arriva
    # il segnale completo (SL + TP3) gestito sopra come azione OPEN.
    if re.search(r"\bSEGNALE\s+IN\s+ARRIVO\b", clean, re.IGNORECASE):
        announce_direction = _find_direction(clean)
        announce_symbol = _find_symbol(clean) or "XAUUSD-P"
        number_match = re.search(_NUMBER, clean)
        announce_entry = _float(number_match.group(1)) if number_match else None
        if announce_direction is not None and announce_entry is not None:
            return {
                "action": "OPEN_SIGNAL",
                "symbol": announce_symbol,
                "direction": announce_direction,
                "entry": announce_entry,
            }

    # Gli aggiornamenti della ÉLITE spesso non ripetono "XAUUSD":
    # il bot li interpreta comunque perché SOURCE_CHAT è dedicato alla
    # sala ÉLITE XAUUSD.
    # ------------------------------------------------------------
    # TP1 +50 PIPS -> SOLO INFORMATIVO, NESSUN MOVIMENTO SL DA TELEGRAM
    # ------------------------------------------------------------
    tp1_hit = re.search(
        r"\bTP\s*1\s*(?:HIT)?\s*\+?\s*(\d+(?:[.,]\d+)?)\s*PIPS?\b",
        clean,
        re.IGNORECASE,
    )
    if tp1_hit:
        pips = _float(tp1_hit.group(1))
        if abs(pips - 50.0) < 1e-9:
            return {
                "action": "PIPS_UPDATE",
                "symbol": "XAUUSD-P",
                "pips": pips,
                "milestone": "TP1",
            }
        return {
            "action": "PIPS_UPDATE",
            "symbol": "XAUUSD-P",
            "pips": pips,
            "milestone": "TP1",
        }

    # ------------------------------------------------------------
    # STOP LOSS PRESO
    # Esempi: "❌ STOP LOSS -150pips", "SL"
    # ------------------------------------------------------------
    if re.search(r"\bSTOP\s*LOSS\b", clean, re.IGNORECASE) or re.fullmatch(
        r"\s*SL\s*",
        clean,
        re.IGNORECASE,
    ):
        return {
            "action": "SL_HIT",
            "symbol": "XAUUSD-P",
        }

    # ------------------------------------------------------------
    # TP2 / TP3 / GENERIC PIPS -> SOLO INFORMATIVI
    # ------------------------------------------------------------
    pips_match = re.search(
        r"(?<![\d.])\+?\s*(\d+(?:[.,]\d+)?)\s*PIPS?\b",
        clean,
        re.IGNORECASE,
    )
    if pips_match:
        return {
            "action": "PIPS_UPDATE",
            "symbol": "XAUUSD-P",
            "pips": _float(pips_match.group(1)),
        }

    # ------------------------------------------------------------
    # MODIFICA SL ESPRESSA
    # ------------------------------------------------------------
    sl_modified = re.search(
        rf"\bSL\s+MODIFICATO\s*[:\-]?\s*{_NUMBER}\b",
        clean,
        re.IGNORECASE,
    )
    if sl_modified:
        return {
            "action": "MODIFY_SL",
            "symbol": "XAUUSD-P",
            "sl": _float(sl_modified.group(1)),
        }

    # Messaggi generici di profitto: solo informazione, mai gestione SL/chiusura.
    if re.search(r"\bOPERAZIONE\s+IN\s+PROFITTO\b", clean, re.IGNORECASE):
        return {"action": "INFO_ONLY", "symbol": "XAUUSD-P"}

    return None
