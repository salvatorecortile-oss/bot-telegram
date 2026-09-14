import asyncio
from telegram_client import client


async def main():
    print("=" * 70)
    print("GRUPPI E CANALI TELEGRAM")
    print("=" * 70)
    await client.start()

    count = 0
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        if getattr(entity, "megagroup", False) or getattr(entity, "broadcast", False):
            count += 1
            print(f"{count:03d} | {dialog.id} | {dialog.name}")

    print(f"\nTotale: {count}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
