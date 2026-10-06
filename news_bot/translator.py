"""
Traduzione in italiano (Google Translate gratuito, nessuna chiave richiesta).
Se la traduzione non riesce, viene usato il testo originale.
"""
import logging

from deep_translator import GoogleTranslator

log = logging.getLogger("news_bot")

_cache = {}


def to_italian(text):
    text = (text or "").strip()
    if not text:
        return ""
    if text in _cache:
        return _cache[text]
    try:
        result = GoogleTranslator(source="auto", target="it").translate(text) or text
    except Exception as exc:
        log.warning("Traduzione non riuscita, uso il testo originale: %s", exc)
        return text
    if len(_cache) > 2000:
        _cache.clear()
    _cache[text] = result
    return result
