"""
Collega il tuo account Telegram al bot notizie (da fare UNA sola volta).

    python login.py

Telethon chiede numero di telefono e codice ricevuto su Telegram.
La sessione viene salvata nel file news_bot.session (non condividerlo mai).
"""
from telethon.sync import TelegramClient

import config

if not config.API_ID or not config.API_HASH:
    raise SystemExit("Configura TELEGRAM_API_ID e TELEGRAM_API_HASH nel file .env")

with TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH) as client:
    me = client.get_me()
    print(f"Login riuscito: {me.first_name} (ID {me.id})")
