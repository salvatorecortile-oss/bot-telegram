from telethon import TelegramClient

from config import API_HASH, API_ID, BASE_DIR, SESSION_NAME

if not API_ID or not API_HASH:
    raise RuntimeError(
        "Telegram non configurato: imposta TELEGRAM_API_ID e TELEGRAM_API_HASH "
        "nel file .env della cartella segnali_kairos."
    )

client = TelegramClient(
    str(BASE_DIR / SESSION_NAME),
    API_ID,
    API_HASH,
    connection_retries=5,
    retry_delay=1,
    auto_reconnect=True,
)
