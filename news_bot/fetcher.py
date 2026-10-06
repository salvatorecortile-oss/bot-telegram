"""
Lettura dei feed RSS.
"""
import calendar
import hashlib
import html
import logging
import re
import time

import feedparser
import requests

log = logging.getLogger("news_bot")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}


def clean_text(text):
    """Toglie HTML e spazi in eccesso."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _repeats_title(title, summary):
    """True se il riassunto ripete solo il titolo."""
    return not summary or summary.lower().startswith(title.lower()[:60])


def _published(entry):
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return float(calendar.timegm(value))
    return time.time()


def parse_feed(content, feed):
    """Trasforma il contenuto di un feed nella lista di notizie."""
    parsed = feedparser.parse(content)
    items = []
    for entry in parsed.entries[:40]:
        title = clean_text(entry.get("title"))
        if not title:
            continue
        source = feed["name"]
        # Google News mette la testata in fondo al titolo: "Titolo - Reuters"
        publisher = (entry.get("source") or {}).get("title")
        if publisher:
            source = publisher
            if title.endswith(" - " + publisher):
                title = title[: -len(" - " + publisher)].strip()
        link = entry.get("link", "")
        summary = clean_text(entry.get("summary"))
        if publisher or _repeats_title(title, summary):
            summary = ""  # su Google News il riassunto è solo il titolo ripetuto
        uid = hashlib.sha1((link or title).encode("utf-8")).hexdigest()
        items.append({
            "uid": uid,
            "title": title,
            "summary": summary[:400],
            "link": link,
            "source": source,
            "tier": feed["tier"],
            "category": feed["category"],
            "published": _published(entry),
        })
    return items


def fetch_feed(feed, timeout=20):
    """Scarica un feed. In caso di errore ritorna una lista vuota."""
    try:
        response = requests.get(feed["url"], headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        return parse_feed(response.content, feed)
    except Exception as exc:
        log.warning("Feed %s non disponibile: %s", feed["name"], exc)
        return []
