import asyncio
from pathlib import Path

import qrcode
from telethon import TelegramClient

from config import API_ID, API_HASH, SESSION_NAME


async def main():
    client = TelegramClient(
        SESSION_NAME,
        API_ID,
        API_HASH,
        timeout=20,
        connection_retries=3,
    )

    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Account già autorizzato: {me.first_name} (ID {me.id})")
        await client.disconnect()
        return

    qr_login = await client.qr_login()

    img = qrcode.make(qr_login.url)
    path = Path(__file__).resolve().parent / "telegram_login_qr.png"
    img.save(path)

    print(f"QR salvato in: {path}")
    print("Telegram -> Impostazioni -> Dispositivi -> Collega dispositivo desktop")
    print("Scansiona il QR e attendi...")

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
