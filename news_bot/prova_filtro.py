"""
Prova il filtro SENZA pubblicare nulla su Telegram.

    python prova_filtro.py          -> solo filtro a parole chiave (gratis)
    python prova_filtro.py --ai     -> in più fa valutare a Claude le prime 25 notizie
                                       (1 chiamata, costa qualche centesimo)

Legenda senza AI:
- [SUBITO]   = verrebbe inviata subito nel canale
- [MATTINO]  = finirebbe nel riepilogo delle 6:00
- [-> AI]    = con Claude attivo verrebbe mandata a Claude per il voto
"""
import sys
import tempfile
from pathlib import Path

import config
from news_engine import NewsEngine, fetch_all
from storage import Storage

use_ai = "--ai" in sys.argv

with tempfile.TemporaryDirectory() as tmp:
    storage = Storage(Path(tmp) / "prova.db")
    engine = NewsEngine(storage)
    items = fetch_all()
    print(f"Notizie lette: {len(items)}\n")
    engine.ingest(items)
    infos = [engine.story_info(s["id"]) for s in storage.stories_since(0)]
    infos = [i for i in infos if i and i["score"] >= 30]
    infos.sort(key=lambda i: i["score"], reverse=True)

    print("=== Filtro a parole chiave ===")
    for i in infos[:60]:
        if i["score"] >= config.INSTANT_THRESHOLD:
            tag = "[SUBITO] "
        elif i["score"] >= config.RECAP_THRESHOLD:
            tag = "[MATTINO]"
        elif i["score"] >= config.AI_PREFILTER:
            tag = "[-> AI]  "
        else:
            tag = "[scarta] "
        print(f"{tag} {i['score']:>3}  {i['level']:<8} {i['category']:<11} "
              f"{i['num_sources']} fonti  {i['title'][:90]}  ({i['source']})")

    if use_ai:
        if not config.AI_ENABLED:
            sys.exit("\nPer --ai serve ANTHROPIC_API_KEY nel file .env")
        from ai_editor import AIEditor
        batch = [i for i in infos if i["score"] >= config.AI_PREFILTER][: config.AI_BATCH_SIZE]
        print(f"\n=== Voto di Claude ({config.CLAUDE_MODEL}) sulle prime {len(batch)} ===")
        results = AIEditor().evaluate(batch, []) or {}
        by_id = {i["story_id"]: i for i in batch}
        for sid, r in sorted(results.items(), key=lambda kv: -kv[1]["importanza"]):
            voto = r["importanza"]
            if voto >= config.AI_INSTANT_MIN:
                tag = "[SUBITO] "
            elif voto >= config.AI_RECAP_MIN:
                tag = "[MATTINO]"
            else:
                tag = "[scarta] "
            print(f"{tag} {voto:>2}/10  {r['titolo']}")
            if voto >= config.AI_RECAP_MIN:
                print(f"            {r['testo']}")
                if r["impatto_oro"]:
                    print(f"            Oro: {r['impatto_oro']}")
            print(f"            (orig.: {by_id[sid]['title'][:90]})")
    storage.db.close()
