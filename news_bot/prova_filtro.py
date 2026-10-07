"""
Prova il filtro SENZA pubblicare nulla su Telegram.

    python prova_filtro.py            -> mostra le notizie con il loro punteggio
    python prova_filtro.py --traduci  -> in più traduce in italiano quelle che
                                         verrebbero pubblicate (prova di DeepL)

Legenda:
- [SUBITO]   = verrebbe inviata subito nel canale
- [MATTINO]  = finirebbe nel riepilogo delle 6:00
- [scarta]   = scartata
Utile per regolare INSTANT_THRESHOLD e RECAP_THRESHOLD nel file .env.
"""
import sys
import tempfile
from pathlib import Path

import config
from news_engine import NewsEngine, fetch_all
from storage import Storage

translate = "--traduci" in sys.argv
if translate:
    from translator import to_italian

with tempfile.TemporaryDirectory() as tmp:
    storage = Storage(Path(tmp) / "prova.db")
    engine = NewsEngine(storage)
    items = fetch_all()
    print(f"Notizie lette: {len(items)}\n")
    engine.ingest(items)
    infos = [engine.story_info(s["id"]) for s in storage.stories_since(0)]
    infos = [i for i in infos if i and i["score"] >= 30]
    infos.sort(key=lambda i: i["score"], reverse=True)
    for i in infos[:60]:
        if i["score"] >= config.INSTANT_THRESHOLD:
            tag = "[SUBITO] "
        elif i["score"] >= config.RECAP_THRESHOLD:
            tag = "[MATTINO]"
        else:
            tag = "[scarta] "
        print(f"{tag} {i['score']:>3}  {i['level']:<8} {i['category']:<11} "
              f"{i['num_sources']} fonti  {i['title'][:90]}  ({i['source']})")
        if translate and i["score"] >= config.RECAP_THRESHOLD:
            print(f"            IT: {to_italian(i['title'])}")
    storage.db.close()
