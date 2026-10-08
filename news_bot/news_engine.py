"""
Il "cervello" del bot: raccoglie le notizie, raggruppa quelle uguali,
calcola l'importanza e decide cosa inviare.

Non contiene codice Telegram, così si può provare da solo (vedi prova_filtro.py).
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import classifier
import config
from feeds import FEEDS
from fetcher import fetch_feed

log = logging.getLogger("news_bot")


def fetch_all(feeds=FEEDS):
    """Scarica tutte le fonti in parallelo."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(fetch_feed, feeds)
    items = []
    for feed_items in results:
        items.extend(feed_items)
    return items


class NewsEngine:
    def __init__(self, storage):
        self.storage = storage

    def ingest(self, items, now=None):
        """
        Salva le notizie nuove e le aggancia alla "storia" giusta
        (stessa notizia da fonti diverse = stessa storia).
        Ritorna gli id delle storie toccate.
        """
        now = now or time.time()
        recent = [
            (row["story_id"], classifier.keywords(row["title"]))
            for row in self.storage.recent_items(now - 24 * 3600)
        ]
        touched = set()
        for item in items:
            if self.storage.has_item(item["uid"]):
                continue
            # Notizie troppo vecchie: le ignoriamo del tutto.
            if item["published"] < now - config.RECAP_WINDOW_HOURS * 3600:
                continue
            words = classifier.keywords(item["title"])
            story_id = next(
                (sid for sid, other in recent if classifier.same_story(words, other)),
                None,
            )
            if story_id is None:
                story_id = self.storage.new_story(now)
            score = classifier.base_score(item["title"], item["tier"])
            self.storage.add_item(item, story_id, score, now)
            recent.append((story_id, words))
            touched.add(story_id)
        return touched

    def story_info(self, story_id):
        """Riassume una storia: notizia migliore, numero di fonti, punteggio."""
        rows = self.storage.story_items(story_id)
        if not rows:
            return None
        best = rows[0]
        sources = {r["source"].lower() for r in rows}
        score = best["base_score"] + classifier.confirm_bonus(len(sources))
        # Notizie che non riguardano i mercati (oro, USA, Medio Oriente...): fuori.
        if not classifier.is_market_relevant(best["title"]):
            score = min(score, classifier.NOT_RELEVANT_CAP)
        category = best["category"]
        # Una notizia arrivata dalle ricerche sull'oro ma che non parla di oro va in Macro.
        if category == "oro" and not classifier.is_about_gold(best["title"]):
            category = "macro"
        return {
            "story_id": story_id,
            "title": best["title"],
            "summary": best["summary"],
            "link": best["link"],
            "source": best["source"],
            "category": category,
            "level": classifier.classify(best["title"]),
            "num_sources": len(sources),
            "score": score,
            "published": min(r["published"] for r in rows),
        }

    def instant_candidates(self, story_ids, now=None):
        """Storie da inviare subito, dalla più importante."""
        now = now or time.time()
        out = []
        for sid in story_ids:
            story = self.storage.story(sid)
            if story is None or story["sent_at"] is not None:
                continue
            info = self.story_info(sid)
            if info is None or info["score"] < config.INSTANT_THRESHOLD:
                continue
            if info["published"] < now - config.MAX_INSTANT_AGE_HOURS * 3600:
                continue
            out.append(info)
        out.sort(key=lambda i: i["score"], reverse=True)
        return out

    def recap(self, now=None):
        """Notizie per il riepilogo del mattino (ultime 24 ore)."""
        now = now or time.time()
        since = now - config.RECAP_WINDOW_HOURS * 3600
        infos = []
        for story in self.storage.stories_since(since):
            # Le notizie già uscite come ULTIM'ORA non si ripetono nel riepilogo.
            # (sent_at = 0 vuol dire solo "vista al primo avvio", non inviata.)
            if story["sent_at"] is not None and story["sent_at"] >= 1:
                continue
            info = self.story_info(story["id"])
            if info and info["score"] >= config.RECAP_THRESHOLD:
                infos.append(info)
        infos.sort(key=lambda i: i["score"], reverse=True)
        return infos[: config.RECAP_MAX_ITEMS]
