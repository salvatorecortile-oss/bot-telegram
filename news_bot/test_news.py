"""
Test senza internet e senza Telegram:  python test_news.py
"""
import tempfile
import time
from datetime import datetime
from pathlib import Path

import classifier
import messages
from fetcher import parse_feed
from news_engine import NewsEngine
from storage import Storage

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Fed cuts rates by 50 basis points in surprise move - Reuters</title>
<link>https://example.com/1</link><source url="https://reuters.com">Reuters</source>
<pubDate>{now}</pubDate><description>Fed cuts rates by 50 basis points</description></item>
<item><title>Best fitness tips for traders - Blog</title>
<link>https://example.com/2</link><source url="https://blog.com">Blog</source>
<pubDate>{now}</pubDate></item>
</channel></rss>"""


def item(uid, title, source, tier=2, category="geopolitica", age=0):
    return {"uid": uid, "title": title, "summary": "", "link": "https://x/" + uid,
            "source": source, "tier": tier, "category": category,
            "published": time.time() - age}


def test_classifier():
    assert classifier.classify("Russia launches massive missile attack on NATO base") == "critical"
    assert classifier.classify("Fed cuts rates by 25 basis points") == "critical"
    assert classifier.classify("US CPI rises more than expected in September") == "high"
    assert classifier.classify("Gold hits record high above $4,000") == "critical"
    assert classifier.classify("Actor wins award at film festival") == "info"
    assert classifier.classify("Best fitness tips for the war on stress") == "info"
    assert classifier.classify("Company warns of weaker sales") == "info"   # "war" non in "warns"
    assert classifier.classify("Gold price prediction for next week") == "info"


def test_real_headlines():
    """Titoli veri dai test del 7 ottobre 2026."""
    import config

    def score(title, tier, sources):
        return classifier.base_score(title, tier) + classifier.confirm_bonus(sources)

    not_instant = [
        ("US military aid to Israel continues three years into Gaza genocide", 2, 2),
        ("Russia ‘pursuing strategy of terror’, EU’s von der Leyen says after deadly strikes on Ukraine – Europe live", 2, 1),
        ("Ukrainian drones kill two, hit fuel hub in one of biggest attacks on Moscow region, Russia", 1, 1),
        ("Fed minutes could detail rate-hike decision, policy path", 2, 2),
    ]
    for title, tier, sources in not_instant:
        assert score(title, tier, sources) < config.INSTANT_THRESHOLD, title
    discarded = [
        ("Ghana inflation accelerates for second month in September", 1, 2),
        ("Spanish Inflation Climbs to Three-And-a-Half Year High", 2, 3),
        ("Candles lit in memory of those killed in October 7 attacks", 2, 1),
        ("CPI Card Reports Q2 2026 Results: Full Earnings Call Transcript", 3, 1),
        ("How has Israel’s genocide changed Gaza?", 2, 1),
    ]
    for title, tier, sources in discarded:
        assert score(title, tier, sources) < config.RECAP_THRESHOLD, title
    instant = [
        ("Fed cuts rates by 50 basis points in surprise move", 1, 3),
        ("Fed holds rates steady, Powell signals cuts later this year", 1, 2),
        ("US CPI rises 0.4% in September, above expectations", 1, 2),
        ("Gold hits record high above $4,500 as Iran tensions escalate", 2, 2),
        ("Iran launches missiles at US base in Iraq", 1, 2),
    ]
    for title, tier, sources in instant:
        assert score(title, tier, sources) >= config.INSTANT_THRESHOLD, title


def test_market_relevance():
    """8 ottobre: golpe in Brasile e tempesta tropicale non interessano la community."""
    assert not classifier.is_market_relevant("Brazil military stages coup, arrests president")
    assert not classifier.is_market_relevant("Tropical Storm Isaias to threaten Gulf Coast as a dangerous hurricane")
    assert classifier.is_market_relevant("Houthis attack oil tankers in the Red Sea")
    assert classifier.is_market_relevant("Trump says new tariffs on Europe start next week")
    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(Path(tmp) / "t.db")
        engine = NewsEngine(storage)
        touched = engine.ingest([
            item("a", "Brazil military stages coup, arrests president", "Reuters", tier=1),
            item("b", "Tropical Storm Isaias to threaten Gulf Coast as a dangerous hurricane", "CNN", tier=2),
            item("c", "Houthis attack oil tankers in the Red Sea", "Reuters", tier=1),
            item("d", "Fed holds rates steady, Powell signals cuts later this year", "Reuters", tier=1),
        ])
        titles = [i["title"] for i in engine.instant_candidates(touched)]
        assert "Brazil military stages coup, arrests president" not in titles
        recap = [i["title"] for i in engine.recap()]
        assert not any("Brazil" in t or "Isaias" in t for t in recap)
        # Le ULTIM'ORA già inviate non finiscono nel riepilogo del mattino
        fed = next(i for i in engine.recap() if "Fed" in i["title"])
        storage.mark_sent(fed["story_id"], time.time())
        assert all("Fed" not in i["title"] for i in engine.recap())
        assert any("tankers" in i["title"] for i in engine.recap())
        storage.db.close()


def test_parse_feed():
    now = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    items = parse_feed(RSS.format(now=now).encode(), {"name": "GN", "tier": 1, "category": "macro"})
    assert len(items) == 2
    assert items[0]["title"] == "Fed cuts rates by 50 basis points in surprise move"
    assert items[0]["source"] == "Reuters"
    assert items[0]["summary"] == ""


def test_engine():
    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(Path(tmp) / "t.db")
        engine = NewsEngine(storage)

        # Notizia "high" da fonte tier 3: da sola non basta per l'invio immediato...
        t1 = engine.ingest([item("a", "Israel airstrikes hit southern Lebanon overnight", "CrisisWatch", tier=3)])
        assert engine.instant_candidates(t1) == []
        # ...ma se altre due fonti la confermano, diventa importante.
        t2 = engine.ingest([
            item("b", "Israeli airstrikes hit southern Lebanon overnight, officials say", "BBC", tier=2),
            item("c", "Airstrikes hit southern Lebanon overnight", "Al Jazeera", tier=2),
        ])
        assert t1 == t2, "le tre notizie devono essere la stessa storia"
        cands = engine.instant_candidates(t2)
        assert len(cands) == 1 and cands[0]["num_sources"] == 3
        storage.mark_sent(cands[0]["story_id"], time.time())
        assert engine.instant_candidates(t2) == [], "non deve essere inviata due volte"

        # Gossip e notizie vecchie scartati
        t3 = engine.ingest([item("d", "Celebrity wedding photos", "BBC")])
        assert engine.instant_candidates(t3) == []
        t4 = engine.ingest([item("e", "Iran launches missiles at US base", "Reuters", tier=1, age=5 * 3600)])
        assert engine.instant_candidates(t4) == [], "troppo vecchia per l'invio immediato"

        # Riepilogo del mattino
        engine.ingest([item("f", "Gold slips ahead of US CPI data", "Kitco", tier=2, category="oro")])
        recap = engine.recap()
        titles = [r["title"] for r in recap]
        assert not any("Lebanon" in t for t in titles), "già inviata come ULTIM'ORA"
        assert "Celebrity wedding photos" not in titles
        storage.db.close()


def test_translator():
    import translator

    class FakeDeepL:
        def translate_text(self, text, target_lang):
            assert target_lang == "IT"
            return type("R", (), {"text": "La Fed taglia i tassi"})()

    translator._deepl = FakeDeepL()
    translator._cache.clear()
    assert translator.to_italian("Fed cuts rates") == "La Fed taglia i tassi"
    assert translator.to_italian("") == ""


def test_messages():
    recap = [{"category": "oro", "title_it": "L'oro <scende>", "source": "Kitco", "link": "https://k"}]
    text = messages.format_morning(datetime(2026, 10, 6, 6, 0), recap)
    assert "Buongiorno a tutti" in text and "Martedì 6 ottobre 2026" in text
    assert "notizie più importanti di ieri" in text and "1. 🥇" in text
    assert "&lt;scende&gt;" in text
    alert = messages.format_alert("critical", "macro", "La Fed taglia i tassi", "", "Reuters", 2, "https://r")
    assert "ULTIM'ORA" in alert and "confermata da 2 fonti" in alert
    parts = messages.split_message("riga\n" * 3000)
    assert all(len(p) <= 4000 for p in parts)


if __name__ == "__main__":
    for test in (test_classifier, test_real_headlines, test_market_relevance, test_parse_feed, test_engine, test_translator, test_messages):
        test()
        print("OK", test.__name__)
