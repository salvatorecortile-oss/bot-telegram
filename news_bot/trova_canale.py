"""
Mostra i canali e gruppi del tuo account con il loro ID.
Copia l'ID giusto in NEWS_CHANNEL nel file .env.

    python trova_canale.py

I gruppi "vecchi" trasformati in supergruppo sono segnati come NON USABILE:
per quelli va usato il nuovo ID (che inizia con -100).
"""
from telethon.sync import TelegramClient

import config

with TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH) as client:
    for dialog in client.iter_dialogs():
        if not (dialog.is_channel or dialog.is_group):
            continue
        entity = dialog.entity
        if getattr(entity, "deactivated", False) or getattr(entity, "migrated_to", None):
            kind = "NON USABILE (diventato supergruppo)"
        elif getattr(entity, "broadcast", False):
            kind = "canale"
        elif getattr(entity, "megagroup", False):
            kind = "supergruppo"
        else:
            kind = "gruppo"
        print(f"{dialog.id:>16}  {kind:<36} {dialog.name}")
