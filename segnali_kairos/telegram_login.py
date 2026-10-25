"""Primo login Telegram tramite QR code (in alternativa al login con numero all'avvio)."""
import asyncio

import qrcode
from telethon import TelegramClient

from config import API_HASH, API_ID, BASE_DIR, SESSION_NAME


async def main():
    client = TelegramClient(str(BASE_DIR / SESSION_NAME), API_ID, API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Account gia' autorizzato: {me.first_name} (ID {me.id})")
        await client.disconnect()
        return

    qr_login = await client.qr_login()
    path = BASE_DIR / "telegram_login_qr.png"
    qrcode.make(qr_login.url).save(path)
    print(f"QR salvato in: {path}")
    print("Telegram -> Impostazioni -> Dispositivi -> Collega dispositivo desktop")

    try:
        await qr_login.wait()
    except asyncio.TimeoutError:
        print("QR scaduto. Riesegui lo script.")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"Login riuscito: {me.first_name} (ID {me.id})")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
