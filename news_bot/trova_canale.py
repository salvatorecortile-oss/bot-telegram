"""
Mostra i canali e gruppi del tuo account con il loro ID.
Copia l'ID del canale Community in NEWS_CHANNEL nel file .env.

    python trova_canale.py
"""
from telethon.sync import TelegramClient

import config

with TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH) as client:
    for dialog in client.iter_dialogs():
        if dialog.is_channel or dialog.is_group:
            print(f"{dialog.id:>16}  {dialog.name}")
