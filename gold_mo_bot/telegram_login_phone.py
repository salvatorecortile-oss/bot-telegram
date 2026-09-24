import asyncio

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

    # Login classico: numero di telefono + codice ricevuto (+ password
    # 2FA se l'account ce l'ha). Percorso alternativo al QR di
    # telegram_login.py, utile quando lo scanner QR non è disponibile.
    await client.start(
        phone=lambda: input("Numero di telefono (es. +39...): "),
        code_callback=lambda: input("Codice ricevuto da Telegram: "),
        password=lambda: input("Password 2FA (invio se non ce l'hai): "),
    )

    me = await client.get_me()
    print(f"Login riuscito: {me.first_name} (ID {me.id})")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
