"""
FactMachine - Passo 1: login manuale una volta sola.

Apre un browser Chromium (visibile), tu fai login a mano con numero di
telefono + codice SMS. Lo stato della sessione (cookie + localStorage) viene
salvato su file, cosi' le volte successive il bot riparte gia' loggato senza
richiedere di nuovo il codice.

Uso:
    python factmachine/login.py

Requisiti (sul TUO PC):
    pip install playwright
    playwright install chromium
"""
import asyncio
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent
# Cartella profilo persistente: qui Chromium tiene cookie/sessione tra un avvio
# e l'altro. Cosi' il login (e l'SMS) serve una volta sola, finche' il sito non
# scade la sessione.
USER_DATA_DIR = BASE_DIR / "browser_profile"
# File separato con lo "storage state" (utile per riusarlo altrove/debug).
STORAGE_STATE = BASE_DIR / "storage_state.json"

LOGIN_URL = "https://alpha.factmachine.com/"


async def main():
    USER_DATA_DIR.mkdir(exist_ok=True)

    async with async_playwright() as p:
        # Profilo persistente + finestra visibile: fai tu il login a mano.
        context = await p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(LOGIN_URL)

        print("=" * 60)
        print("FAI IL LOGIN NELLA FINESTRA DEL BROWSER:")
        print("  1. Inserisci il numero di telefono")
        print("  2. Inserisci il codice che ricevi via SMS")
        print("  3. Quando sei DENTRO e vedi la tua dashboard,")
        print("     torna qui e premi INVIO.")
        print("=" * 60)

        # Aspetta che tu finisca il login a mano.
        await asyncio.get_event_loop().run_in_executor(None, input)

        # Salva lo stato della sessione.
        await context.storage_state(path=str(STORAGE_STATE))
        print(f"\nSessione salvata in:\n  {USER_DATA_DIR}\n  {STORAGE_STATE}")
        print("Da ora il bot puo' ripartire gia' loggato.")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
