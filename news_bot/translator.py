"""
Traduzione in italiano.

1. DeepL API Free (se DEEPL_API_KEY è nel file .env): gratis fino a 500.000
   caratteri al mese. Il bot traduce solo le notizie che pubblica, quindi
   ne usa una piccola parte.
2. Se DeepL non è configurato, non risponde o la quota del mese è finita:
   Google Translate gratuito.
3. Se anche questo non funziona: testo originale in inglese.
"""
import logging

import deepl
from deep_translator import GoogleTranslator

import config

log = logging.getLogger("news_bot")

_cache = {}
_deepl = deepl.Translator(config.DEEPL_API_KEY) if config.DEEPL_API_KEY else None


def _with_deepl(text):
    global _deepl
    try:
        return _deepl.translate_text(text, target_lang="IT").text
    except deepl.QuotaExceededException:
        log.warning("Quota mensile DeepL finita: uso Google Translate fino al mese prossimo.")
    except deepl.AuthorizationException:
        log.error("DEEPL_API_KEY non valida: uso Google Translate.")
        _deepl = None
    except deepl.DeepLException as exc:
        log.warning("DeepL non disponibile (%s): uso Google Translate.", exc)
    return None


def _with_google(text):
    try:
        return GoogleTranslator(source="auto", target="it").translate(text)
    except Exception as exc:
        log.warning("Traduzione non riuscita, uso il testo originale: %s", exc)
        return None


def to_italian(text):
    text = (text or "").strip()
    if not text:
        return ""
    if text in _cache:
        return _cache[text]
    result = (_with_deepl(text) if _deepl else None) or _with_google(text)
    if not result:
        return text
    if len(_cache) > 2000:
        _cache.clear()
    _cache[text] = result
    return result
