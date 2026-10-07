"""
Manda nel canale (NEWS_CHANNEL) due messaggi di PROVA con le notizie vere di adesso:
1. il buongiorno con il riepilogo (le 5 notizie più importanti delle ultime 24 ore)
2. un'ULTIM'ORA con la notizia più importante del momento

    python invia_prova.py

Pubblica anche se nel .env c'è DRY_RUN=true. Non tocca il database del bot,
quindi non cambia niente nel funzionamento normale.
"""
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from telethon import TelegramClient

import config
import messages
from news_engine import NewsEngine, fetch_all
from storage import Storage
from translator import to_italian

PROVA = "🧪 <i>Messaggio di prova</i>\n\n"


def build_messages():
    with tempfile.TemporaryDirectory() as tmp:
        storage = Storage(Path(tmp) / "prova.db")
        engine = NewsEngine(storage)
        print("Leggo le notizie...")
        engine.ingest(fetch_all())
        recap_infos = engine.recap()
        all_infos = [engine.story_info(s["id"]) for s in storage.stories_since(0)]
        storage.db.close()

    print("Traduco...")
    recap = [{
        "category": info["category"],
        "title_it": to_italian(info["title"]),
        "source": info["source"],
        "link": info["link"],
    } for info in recap_infos]
    morning = messages.format_morning(datetime.now(ZoneInfo(config.TIMEZONE)), recap)

    top = max((i for i in all_infos if i), key=lambda i: i["score"])
    alert = messages.format_alert(
        top["level"], top["category"], to_italian(top["title"]),
        to_italian(top["summary"]) if top["summary"] else "",
        top["source"], top["num_sources"], top["link"],
    )
    return [PROVA + morning, PROVA + alert]


async def main():
    texts = build_messages()
    async with TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH) as client:
        await client.get_dialogs()
        channel = await client.get_entity(config.NEWS_CHANNEL)
        for text in texts:
            for part in messages.split_message(text):
                await client.send_message(channel, part, parse_mode="html", link_preview=False)
        print(f"Inviati 2 messaggi di prova in: {getattr(channel, 'title', config.NEWS_CHANNEL)}")


if __name__ == "__main__":
    asyncio.run(main())
