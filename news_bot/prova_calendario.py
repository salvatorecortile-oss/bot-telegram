"""
Prova il calendario economico della settimana.

    python prova_calendario.py          -> mostra il messaggio qui, senza pubblicarlo
    python prova_calendario.py --invia  -> lo pubblica nel canale (NEWS_CHANNEL)
"""
import asyncio
import re
import sys

import calendario
import config
import messages

text = calendario.build_weekly_message()
print(re.sub(r"<[^>]+>", "", text))  # senza i tag HTML, per leggerlo meglio

if "--invia" in sys.argv:
    from telethon import TelegramClient

    async def send():
        async with TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH) as client:
            await client.get_dialogs()
            channel = await client.get_entity(config.NEWS_CHANNEL)
            for part in messages.split_message(text):
                await client.send_message(channel, part, parse_mode="html", link_preview=False)
            print(f"\nInviato in: {getattr(channel, 'title', config.NEWS_CHANNEL)}")

    asyncio.run(send())
