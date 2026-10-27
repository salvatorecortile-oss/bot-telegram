"""
FactMachine - Passo 3: il bot che vota e apre l'operazione all'istante.

Come funziona (basato sulla ricognizione):
- Su FactMachine votare = prendere posizione = fare trade. Un'unica chiamata:
      POST /api/v1/order/transactions/buy
      body: {marketId, optionId, usdcInD6String, maxPriceD6String, maxSlippageBps}
  Il server esegue l'operazione e risponde con una "signature" Solana.
- L'autenticazione viaggia nei cookie della sessione (Clerk), quindi spariamo
  la chiamata DENTRO il browser gia' loggato (page.evaluate + fetch): i cookie
  vanno in automatico, niente token da gestire. E' anche la via piu' veloce.

Idea d'uso (per entrare PRIMA che il prezzo salga):
1. 'load <url o id mercato>'  -> carica il mercato e mostra opzioni + prezzi
2. 'arm yes 10'               -> ti PRE-ARMI: opzione "Yes", 10 USDC
3. INVIO (o 'go')             -> SPARA subito voto+operazione

Uso:
    python factmachine/bot.py

Requisiti: aver gia' fatto login.py (sessione salvata in browser_profile/).
"""
import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent
USER_DATA_DIR = BASE_DIR / "browser_profile"

ORIGIN = "https://alpha.factmachine.com"
BUY_PATH = "/api/v1/order/transactions/buy"
MARKET_PATH = "/api/v1/market/"

# Default dell'ordine
DEFAULT_SLIPPAGE_BPS = 10000   # 100% (come nella ricognizione)
DEFAULT_MAX_PRICE = 1.0        # prezzo massimo per quota (1.0 = nessun limite)


def market_id_from(text: str) -> str:
    """Accetta un id oppure un URL tipo https://alpha.factmachine.com/market/<id>."""
    text = text.strip()
    m = re.search(r"/market/([a-z0-9]+)", text)
    return m.group(1) if m else text


async def ainput(prompt: str = "") -> str:
    if prompt:
        print(prompt, end="", flush=True)
    return await asyncio.get_event_loop().run_in_executor(None, input)


async def api_get(page, path: str):
    """GET verso l'API usando la sessione del browser (cookie automatici)."""
    js = """
    async (path) => {
      const r = await fetch(path, { credentials: 'include' });
      const text = await r.text();
      return { status: r.status, text };
    }"""
    res = await page.evaluate(js, path)
    try:
        return res["status"], json.loads(res["text"])
    except Exception:
        return res["status"], res["text"]


async def fire_buy(page, body: dict):
    """POST buy DENTRO il browser loggato. Ritorna status, testo e latenza ms."""
    js = """
    async (body) => {
      const t0 = performance.now();
      const r = await fetch('%s', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(body),
        credentials: 'include'
      });
      const text = await r.text();
      return { status: r.status, text, ms: Math.round(performance.now() - t0) };
    }""" % BUY_PATH
    return await page.evaluate(js, body)


class Armed:
    """Ordine pre-armato, pronto a partire."""
    def __init__(self):
        self.market = None       # dict del mercato
        self.option_id = None
        self.option_name = None
        self.usdc = None         # importo in USDC (float)
        self.max_price = DEFAULT_MAX_PRICE
        self.slippage_bps = DEFAULT_SLIPPAGE_BPS

    def ready(self) -> bool:
        return self.market and self.option_id and self.usdc

    def body(self) -> dict:
        return {
            "marketId": self.market["id"],
            "optionId": self.option_id,
            "usdcInD6String": str(int(round(self.usdc * 1_000_000))),
            "maxPriceD6String": str(int(round(self.max_price * 1_000_000))),
            "maxSlippageBps": self.slippage_bps,
        }


def show_market(mkt: dict):
    o1, o2 = mkt.get("optionOne", {}), mkt.get("optionTwo", {})
    lp = mkt.get("latestPrice") or {}
    p1 = lp.get("optionOnePrice")
    p2 = lp.get("optionTwoPrice")
    print(f"\n  MERCATO: {mkt.get('subject')}")
    print(f"  id: {mkt.get('id')}  fase: {mkt.get('phase')}  completo: {mkt.get('isComplete')}")
    print(f"    [1/{o1.get('name')}]  prezzo: {p1}")
    print(f"    [2/{o2.get('name')}]  prezzo: {p2}")


def resolve_option(mkt: dict, token: str):
    """Da 'yes'/'no'/'1'/'2' all'(optionId, nome)."""
    o1, o2 = mkt.get("optionOne", {}), mkt.get("optionTwo", {})
    t = token.strip().lower()
    if t in ("1", "one", (o1.get("name") or "").lower()):
        return o1.get("id"), o1.get("name")
    if t in ("2", "two", (o2.get("name") or "").lower()):
        return o2.get("id"), o2.get("name")
    return None, None


HELP = """
Comandi:
  load <url|id>        carica un mercato e mostra opzioni + prezzi
  price                aggiorna e rimostra i prezzi del mercato caricato
  arm <opz> <usdc>     pre-arma l'ordine. opz = yes/no o 1/2. es: arm yes 10
  maxprice <0..1>      (opz.) prezzo massimo per quota, protegge dallo spike
  slippage <bps>       (opz.) slippage in bps (default 10000 = 100%)
  show                 mostra l'ordine pre-armato
  go  (o INVIO vuoto)  SPARA l'ordine pre-armato ADESSO
  help                 questa guida
  quit                 esci
"""


async def main():
    if not USER_DATA_DIR.exists():
        print("Profilo non trovato. Esegui prima: python login.py")
        return

    armed = Armed()

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(ORIGIN + "/")

        # Verifica sessione
        status, me = await api_get(page, "/api/v1/user/current")
        if status != 200:
            print(f"ATTENZIONE: sessione non valida (status {status}). Rifai login.py")
        else:
            uid = me.get("id") if isinstance(me, dict) else "?"
            print(f"Sessione OK (userId: {uid})")

        print(HELP)

        while True:
            raw = (await ainput("\nfm> ")).strip()

            # INVIO vuoto = spara (se armato)
            if raw == "" or raw.lower() == "go":
                if not armed.ready():
                    print("Niente da sparare. Prima: load ... e arm ...")
                    continue
                body = armed.body()
                print(f"SPARO: {armed.option_name} {armed.usdc} USDC ...")
                res = await fire_buy(page, body)
                print(f"  status {res['status']} in {res['ms']} ms")
                try:
                    j = json.loads(res["text"])
                    if "signature" in j:
                        print(f"  OK signature: {j['signature']}")
                    else:
                        print(f"  risposta: {j}")
                except Exception:
                    print(f"  risposta: {res['text'][:500]}")
                continue

            parts = raw.split()
            cmd = parts[0].lower()

            if cmd == "help":
                print(HELP)

            elif cmd == "quit":
                break

            elif cmd == "load":
                if len(parts) < 2:
                    print("uso: load <url|id>")
                    continue
                mid = market_id_from(parts[1])
                status, mkt = await api_get(page, MARKET_PATH + mid)
                if status != 200 or not isinstance(mkt, dict):
                    print(f"errore caricamento mercato (status {status}): {mkt}")
                    continue
                armed.market = mkt
                armed.option_id = None
                # Tieni la pagina del mercato aperta (prezzi vivi, meno latenza)
                await page.goto(f"{ORIGIN}/market/{mid}")
                show_market(mkt)

            elif cmd == "price":
                if not armed.market:
                    print("prima: load <url|id>")
                    continue
                status, mkt = await api_get(page, MARKET_PATH + armed.market["id"])
                if status == 200 and isinstance(mkt, dict):
                    armed.market = mkt
                    show_market(mkt)
                else:
                    print(f"errore (status {status})")

            elif cmd == "arm":
                if not armed.market:
                    print("prima: load <url|id>")
                    continue
                if len(parts) < 3:
                    print("uso: arm <yes|no|1|2> <usdc>")
                    continue
                oid, oname = resolve_option(armed.market, parts[1])
                if not oid:
                    print("opzione non riconosciuta (usa yes/no o 1/2)")
                    continue
                try:
                    usdc = float(parts[2])
                except ValueError:
                    print("importo non valido")
                    continue
                armed.option_id, armed.option_name, armed.usdc = oid, oname, usdc
                print(f"ARMATO: {oname} ({oid}) per {usdc} USDC "
                      f"| maxprice {armed.max_price} | slippage {armed.slippage_bps}bps")
                print("Premi INVIO (o 'go') per sparare.")

            elif cmd == "maxprice":
                try:
                    armed.max_price = float(parts[1])
                    print(f"max price per quota = {armed.max_price}")
                except (IndexError, ValueError):
                    print("uso: maxprice <0..1>")

            elif cmd == "slippage":
                try:
                    armed.slippage_bps = int(parts[1])
                    print(f"slippage = {armed.slippage_bps} bps")
                except (IndexError, ValueError):
                    print("uso: slippage <bps>")

            elif cmd == "show":
                if armed.ready():
                    print(f"ARMATO: {armed.option_name} {armed.usdc} USDC "
                          f"| maxprice {armed.max_price} | slippage {armed.slippage_bps}bps")
                    print(f"body: {armed.body()}")
                else:
                    print("non ancora armato")

            else:
                print("comando sconosciuto. 'help' per la guida.")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
