"""
FactMachine - il bot che vota e apre l'operazione all'istante.

Come funziona (verificato dalla ricognizione):
- Su FactMachine votare una risposta = prendere posizione = fare trade.
  E' TUTTO in UN'UNICA chiamata:
      POST /api/v1/order/transactions/buy
      body: {marketId, optionId, usdcInD6String, maxPriceD6String, maxSlippageBps}
  dove:
      optionId          = il VOTO (quale risposta scegli)
      maxPriceD6String  = la PERCENTUALE/prezzo max per quota (77% -> "770000")
      usdcInD6String    = l'IMPORTO in USDC (100$ -> "100000000")
  Il server esegue e risponde con una "signature" Solana.
- L'autenticazione sta nei cookie della sessione (Clerk): spariamo la chiamata
  DENTRO il browser gia' loggato, cosi' i cookie vanno da soli. E' anche la via
  piu' veloce.

Le opzioni CAMBIANO ad ogni round (non sempre Yes/No): il bot le legge in
automatico dal mercato e tu voti con 1 o 2 (o col nome).

======================================================================
 CONFIG - MODIFICABILE DA TE (valori di partenza)
======================================================================
"""
import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright

# ---- I TUOI DEFAULT (cambiali qui, oppure a runtime con i comandi) ----
DEFAULT_USDC = 100.0        # importo fisso per operazione, in USDC
DEFAULT_PCT = 77.0          # percentuale/prezzo max per quota (es. 77 = 77%)
DEFAULT_SLIPPAGE_BPS = 10000  # tolleranza slippage in bps (10000 = 100%)
# -----------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
USER_DATA_DIR = BASE_DIR / "browser_profile"

ORIGIN = "https://alpha.factmachine.com"
BUY_PATH = "/api/v1/order/transactions/buy"
MARKET_PATH = "/api/v1/market/"


def pct_to_fraction(value: float) -> float:
    """77 -> 0.77 ; 0.77 -> 0.77. (valori > 1 trattati come percentuale)."""
    return value / 100.0 if value > 1 else value


def market_id_from(text: str) -> str:
    """Accetta un id o un URL tipo .../market/<id>."""
    text = text.strip()
    m = re.search(r"/market/([a-z0-9]+)", text)
    return m.group(1) if m else text


async def ainput(prompt: str = "") -> str:
    if prompt:
        print(prompt, end="", flush=True)
    return await asyncio.get_event_loop().run_in_executor(None, input)


async def api_get(page, path: str):
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


def build_body(market_id, option_id, usdc, pct, slippage_bps) -> dict:
    return {
        "marketId": market_id,
        "optionId": option_id,
        "usdcInD6String": str(int(round(usdc * 1_000_000))),
        "maxPriceD6String": str(int(round(pct_to_fraction(pct) * 1_000_000))),
        "maxSlippageBps": int(slippage_bps),
    }


def resolve_option(mkt: dict, token: str):
    """Da '1'/'2'/nome all'(optionId, nome). Funziona con qualsiasi risposta."""
    o1, o2 = mkt.get("optionOne", {}), mkt.get("optionTwo", {})
    t = token.strip().lower()
    if t in ("1", "one", (o1.get("name") or "").lower()):
        return o1.get("id"), o1.get("name")
    if t in ("2", "two", (o2.get("name") or "").lower()):
        return o2.get("id"), o2.get("name")
    return None, None


def show_market(mkt: dict):
    o1, o2 = mkt.get("optionOne", {}), mkt.get("optionTwo", {})
    lp = mkt.get("latestPrice") or {}
    p1, p2 = lp.get("optionOnePrice"), lp.get("optionTwoPrice")
    pct1 = f"{p1*100:.1f}%" if isinstance(p1, (int, float)) else "?"
    pct2 = f"{p2*100:.1f}%" if isinstance(p2, (int, float)) else "?"
    print(f"\n  MERCATO: {mkt.get('subject')}")
    print(f"  id: {mkt.get('id')}  fase: {mkt.get('phase')}  gia' votato: {bool(mkt.get('userVoteState'))}")
    print(f"    [1/{o1.get('name')}]  prezzo attuale: {pct1}")
    print(f"    [2/{o2.get('name')}]  prezzo attuale: {pct2}")


class State:
    def __init__(self):
        self.market = None
        # ordine pre-armato
        self.option_id = None
        self.option_name = None
        self.usdc = DEFAULT_USDC
        self.pct = DEFAULT_PCT
        self.slippage_bps = DEFAULT_SLIPPAGE_BPS

    def armed(self) -> bool:
        return bool(self.market and self.option_id)


HELP = f"""
Comandi (tutto modificabile al volo):
  load <url|id>          carica il mercato e mostra opzioni + prezzi
  price                  aggiorna i prezzi del mercato caricato

  buy <1|2> [usdc] [pct] SPARA SUBITO voto+operazione (il piu' veloce).
                         es:  buy 1          -> opzione 1, {DEFAULT_USDC}$ al {DEFAULT_PCT}%
                              buy 2 100 77    -> opzione 2, 100$, max 77%

  arm <1|2> [usdc] [pct] pre-arma l'ordine (poi INVIO o 'go' per sparare)
  go  (o INVIO vuoto)    spara l'ordine pre-armato

  usdc <importo>         cambia l'importo di default (es. usdc 100)
  pct <percentuale>      cambia la percentuale/prezzo max (es. pct 77)
  slippage <bps>         cambia lo slippage (default {DEFAULT_SLIPPAGE_BPS})
  show                   mostra impostazioni e ordine armato
  help / quit
"""


async def do_fire(page, st, option_id, option_name, usdc, pct, slippage):
    body = build_body(st.market["id"], option_id, usdc, pct, slippage)
    print(f">>> SPARO: {option_name}  {usdc}$  max {pct}%  (slippage {slippage}bps)")
    res = await fire_buy(page, body)
    print(f"    status {res['status']} in {res['ms']} ms")
    try:
        j = json.loads(res["text"])
        if isinstance(j, dict) and j.get("signature"):
            print(f"    OK  signature: {j['signature']}")
        else:
            print(f"    risposta: {j}")
    except Exception:
        print(f"    risposta: {res['text'][:500]}")


async def main():
    if not USER_DATA_DIR.exists():
        print("Profilo non trovato. Esegui prima: python login.py")
        return

    st = State()

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(ORIGIN + "/")

        status, me = await api_get(page, "/api/v1/user/current")
        if status != 200:
            print(f"ATTENZIONE: sessione non valida (status {status}). Rifai login.py")
        else:
            uid = me.get("id") if isinstance(me, dict) else "?"
            print(f"Sessione OK (userId: {uid})")

        print(HELP)
        print(f"Default attuali: importo {st.usdc}$  |  percentuale {st.pct}%  |  slippage {st.slippage_bps}bps")

        while True:
            raw = (await ainput("\nfm> ")).strip()

            # INVIO vuoto o 'go' = spara l'armato
            if raw == "" or raw.lower() == "go":
                if not st.armed():
                    print("Niente di armato. Usa 'arm 1' oppure 'buy 1'.")
                    continue
                await do_fire(page, st, st.option_id, st.option_name,
                              st.usdc, st.pct, st.slippage_bps)
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
                    print(f"errore caricamento (status {status}): {mkt}")
                    continue
                st.market = mkt
                st.option_id = None
                await page.goto(f"{ORIGIN}/market/{mid}")
                show_market(mkt)

            elif cmd == "price":
                if not st.market:
                    print("prima: load <url|id>")
                    continue
                status, mkt = await api_get(page, MARKET_PATH + st.market["id"])
                if status == 200 and isinstance(mkt, dict):
                    st.market = mkt
                    show_market(mkt)
                else:
                    print(f"errore (status {status})")

            elif cmd in ("buy", "arm"):
                if not st.market:
                    print("prima: load <url|id>")
                    continue
                if len(parts) < 2:
                    print(f"uso: {cmd} <1|2> [usdc] [pct]")
                    continue
                oid, oname = resolve_option(st.market, parts[1])
                if not oid:
                    print("opzione non riconosciuta (usa 1 o 2, o il nome)")
                    continue
                usdc = st.usdc
                pct = st.pct
                if len(parts) >= 3:
                    try:
                        usdc = float(parts[2])
                    except ValueError:
                        print("importo non valido")
                        continue
                if len(parts) >= 4:
                    try:
                        pct = float(parts[3])
                    except ValueError:
                        print("percentuale non valida")
                        continue

                if cmd == "buy":
                    # spara subito
                    await do_fire(page, st, oid, oname, usdc, pct, st.slippage_bps)
                else:
                    # arma e aspetta INVIO
                    st.option_id, st.option_name, st.usdc, st.pct = oid, oname, usdc, pct
                    print(f"ARMATO: {oname}  {usdc}$  max {pct}%. Premi INVIO (o 'go').")

            elif cmd == "usdc":
                try:
                    st.usdc = float(parts[1]); print(f"importo default = {st.usdc}$")
                except (IndexError, ValueError):
                    print("uso: usdc <importo>")

            elif cmd == "pct":
                try:
                    st.pct = float(parts[1]); print(f"percentuale default = {st.pct}%")
                except (IndexError, ValueError):
                    print("uso: pct <percentuale>")

            elif cmd == "slippage":
                try:
                    st.slippage_bps = int(parts[1]); print(f"slippage = {st.slippage_bps} bps")
                except (IndexError, ValueError):
                    print("uso: slippage <bps>")

            elif cmd == "show":
                print(f"Default: importo {st.usdc}$ | pct {st.pct}% | slippage {st.slippage_bps}bps")
                if st.armed():
                    print(f"ARMATO: {st.option_name}  {st.usdc}$  max {st.pct}%")
                    print(f"body: {build_body(st.market['id'], st.option_id, st.usdc, st.pct, st.slippage_bps)}")
                else:
                    print("niente armato")

            else:
                print("comando sconosciuto. 'help' per la guida.")

        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
