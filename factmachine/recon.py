"""
FactMachine - Passo 2: ricognizione delle chiamate di rete.

Riapre il browser gia' loggato (usa il profilo salvato da login.py) e registra
TUTTE le chiamate di rete mentre TU fai, a mano, un voto e un'operazione.

Scopo: capire quali richieste HTTP il sito manda quando voti e quando apri
l'operazione, cosi' nel passo 3 il bot le puo' "risparare" all'istante invece
di cliccare la UI (molto piu' veloce = prezzo migliore).

Uso:
    python factmachine/recon.py
    -> fai UN voto e UNA operazione a mano nella finestra
    -> premi INVIO qui
    -> mandami il file factmachine/recon_capture.json
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent
USER_DATA_DIR = BASE_DIR / "browser_profile"
CAPTURE_FILE = BASE_DIR / "recon_capture.json"

LOGIN_URL = "https://alpha.factmachine.com/"

# Registriamo solo chiamate "API" (XHR/fetch), non immagini/css/font.
INTERESTING_TYPES = {"xhr", "fetch"}


async def main():
    if not USER_DATA_DIR.exists():
        print("Profilo non trovato. Esegui prima: python factmachine/login.py")
        return

    captured = []

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        async def on_request(request):
            if request.resource_type not in INTERESTING_TYPES:
                return
            entry = {
                "t": datetime.now().isoformat(timespec="milliseconds"),
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "post_data": request.post_data,
                "resource_type": request.resource_type,
            }
            captured.append(entry)
            print(f"-> {request.method} {request.url}")

        async def on_response(response):
            if response.request.resource_type not in INTERESTING_TYPES:
                return
            # Proviamo ad allegare il corpo della risposta alla richiesta.
            try:
                body = await response.text()
            except Exception:
                body = None
            for e in reversed(captured):
                if e["url"] == response.url and "status" not in e:
                    e["status"] = response.status
                    e["response_body"] = body[:5000] if body else None
                    break

        context.on("request", lambda r: asyncio.create_task(on_request(r)))
        context.on("response", lambda r: asyncio.create_task(on_response(r)))

        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(LOGIN_URL)

        print("=" * 60)
        print("RICOGNIZIONE IN CORSO. Nella finestra del browser:")
        print("  1. Vai su un sondaggio")
        print("  2. VOTA una opzione")
        print("  3. APRI l'operazione (trade) come faresti normalmente")
        print("  4. Torna qui e premi INVIO")
        print("Sto registrando tutte le chiamate di rete...")
        print("=" * 60)

        await asyncio.get_event_loop().run_in_executor(None, input)

        CAPTURE_FILE.write_text(
            json.dumps(captured, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nCatturate {len(captured)} chiamate.")
        print(f"Salvato in: {CAPTURE_FILE}")
        print("Mandami questo file (togli eventuali token se ti preoccupano).")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
