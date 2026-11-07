"""
FactMachine - button dashboard.

For EACH option (1 and 2) there is a row per amount:
    [ fixed amount ]  [ percentage field ]  [ Buy button ]
Pick the option, type the percentage on that row, click the button: it does
vote + buy instantly (one API call fired inside the already-logged-in browser).

Market detection: AUTO stays on and listens; when the site refreshes and a new
market appears, the dashboard grabs it by itself (no forced page reloads).

======================================================================
 CONFIG - CHANGE HERE
======================================================================
"""
import json
import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, simpledialog

# --- .exe (PyInstaller) support: bundled browser + files saved next to the exe
#     (not in the temp folder that gets wiped). ---
if getattr(sys, "frozen", False):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(sys._MEIPASS, "pw-browsers")
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

from playwright.sync_api import sync_playwright

import license_client

# ---- YOUR DEFAULTS (change here) ----
IMPORTI = [25, 50, 100, 300, 500]   # fixed-button amounts (USDC)
DEFAULT_SLIPPAGE_BPS = 10000        # 100%
BUY_MAX_PRICE_PCT = 100.0           # max buy price (100 = same as the site)
PREZZO_REFRESH_SEC = 2.0            # how often to refresh shown prices
AUTO_OPEN_DEFAULT = True            # AUTO on by default (listens for new market)
DEFAULT_LANG = "en"                 # "en" or "it"
AUTO_POLL_SEC = 0.3                 # how often to read the light "bell" (event mode)
AUTO_SAFETY_SEC = 15.0             # safety net: full re-check every so often
LIGHT_MODE = True                   # blocca video/audio/font pesanti (PC deboli)
BLOCK_IMAGES = False                # True = blocca anche le immagini (ancora piu' leggero)
# --------------------------------------

BASE_DIR = APP_DIR
USER_DATA_DIR = BASE_DIR / "browser_profile"

ORIGIN = "https://alpha.factmachine.com"
VOTE_PATH = "/api/v1/vote/market/cast"       # 1) the VOTE (wheel = consensusGuess)
BUY_PATH = "/api/v1/order/transactions/buy"  # 2) the BUY
MARKET_PATH = "/api/v1/market/"

# Osservatore (event-driven): sta DENTRO la pagina e, appena compare un id di
# mercato nuovo nella home, aumenta window.__fmNew. I cambiamenti dei soli
# countdown (testo) non aggiungono id nuovi, quindi non lo fanno scattare.
FM_OBSERVER_JS = r"""
(() => {
  if (window.__fmInit) return; window.__fmInit = true;
  window.__fmKnown = new Set();
  window.__fmNew = 0;
  let pending = false;
  function scan() {
    pending = false;
    try {
      const html = document.documentElement.innerHTML;
      const re = /\/market\/([a-z0-9]{10,})/g; let m;
      while ((m = re.exec(html))) {
        if (!window.__fmKnown.has(m[1])) { window.__fmKnown.add(m[1]); window.__fmNew++; }
      }
    } catch (e) {}
  }
  scan();
  try {
    new MutationObserver(() => {
      if (!pending) { pending = true; setTimeout(scan, 700); }
    }).observe(document.documentElement, { childList: true, subtree: true });
  } catch (e) {}
})();
"""


# ======================================================================
# TRANSLATIONS
# ======================================================================
LANG = DEFAULT_LANG

TR = {
    "en": {
        "waiting": "Waiting... the market loads automatically (AUTO on)",
        "lang": "Language:",
        "auto_cb": "AUTO (grab the new market automatically)",
        "btn_refresh": "Refresh prices",
        "btn_find": "Find active market",
        "col_amount": "amount",
        "custom_hint": "^ custom amount (type it)",
        "opt": "OPTION {n}",
        "winning": "▲ WINNING: {opt} — {name}  ({pct})",
        "voted_tag": "  [ALREADY VOTED]",
        "log_label": "Log:",
        "err_amount": "ERROR: invalid custom amount (type a number, e.g. 150).",
        "lic_title": "License",
        "lic_valid": "License valid.\nDays left: {d}\nExpires: {e}",
        "lic_prompt": "{msg}\n\nEnter your license key (FM-XXXX-XXXX-XXXX):",
        "lic_toomany": "Too many attempts. Closing.",
        "lic_no_key": "No key entered.",
        "lic_invalid": "Invalid license key.",
        "lic_revoked": "License revoked. Contact the seller.",
        "lic_expired": "License expired. Renew to continue.",
        "lic_wrong_machine": "This license is already active on another PC.",
        "lic_offline": "Cannot reach the license server. Check your internet and try again.",
        "lic_bad_sig": "Invalid server response (bad signature).",
        "w_not_logged": "Not logged in: LOG IN in the browser (phone number + SMS code). The session is saved.",
        "w_session_ok": "Session OK (userId: {id})",
        "w_auto_on": "AUTO ON: listening. I'll grab the new market as soon as the page updates.",
        "w_auto_off": "AUTO OFF.",
        "w_no_market": "No market found. Turn on AUTO and wait for the new market.",
        "w_voted_only": "Market already voted -> skipping vote, buying only.",
        "w_need_pct": "Market NOT voted: enter the percentage to vote, then click Buy again.",
        "w_bad_pct": "Invalid percentage (e.g. 77).",
        "w_vote_line": ">>> VOTE: opt{n} '{name}'  guess {pct}%",
        "w_vote_ok": "    VOTE ok ({ms} ms)",
        "w_vote_err": "    VOTE status {s} ({ms} ms): {t}",
        "w_buy_line": ">>> BUY: {usdc}$ on '{name}'",
        "w_buy_ok": "    BUY ok ({ms} ms)  signature: {sig}",
        "w_buy_err": "    BUY status {s} ({ms} ms): {t}",
        "w_auto_new": "AUTO: new market detected -> entering",
        "w_market_err": "market error (status {s})",
        "w_find_searching": "Searching active market...",
        "w_find_none": "No market found.",
        "w_browser_closed": "Browser closed.",
    },
    "it": {
        "waiting": "In attesa... il mercato si carica da solo (AUTO attivo)",
        "lang": "Lingua:",
        "auto_cb": "AUTO (aggancia il nuovo mercato da solo)",
        "btn_refresh": "Aggiorna prezzi",
        "btn_find": "Trova mercato attivo",
        "col_amount": "importo",
        "custom_hint": "^ importo libero (scrivi tu)",
        "opt": "OPZIONE {n}",
        "winning": "▲ IN TESTA: {opt} — {name}  ({pct})",
        "voted_tag": "  [GIÀ VOTATO]",
        "log_label": "Log:",
        "err_amount": "ERRORE: importo libero non valido (scrivi un numero, es. 150).",
        "lic_title": "Licenza",
        "lic_valid": "Licenza valida.\nGiorni rimasti: {d}\nScade: {e}",
        "lic_prompt": "{msg}\n\nInserisci la tua chiave di licenza (FM-XXXX-XXXX-XXXX):",
        "lic_toomany": "Troppi tentativi. Chiudo.",
        "lic_no_key": "Nessuna chiave inserita.",
        "lic_invalid": "Chiave di licenza non valida.",
        "lic_revoked": "Licenza revocata. Contatta il venditore.",
        "lic_expired": "Licenza scaduta. Rinnova per continuare.",
        "lic_wrong_machine": "Questa licenza e' gia' attiva su un altro PC.",
        "lic_offline": "Impossibile contattare il server licenze. Controlla internet e riprova.",
        "lic_bad_sig": "Risposta del server non valida (firma errata).",
        "w_not_logged": "Non sei loggato: fai il LOGIN nel browser (numero + codice SMS). La sessione resta salvata.",
        "w_session_ok": "Sessione OK (userId: {id})",
        "w_auto_on": "AUTO ON: in ascolto. Aggancio il nuovo mercato appena la pagina si aggiorna.",
        "w_auto_off": "AUTO OFF.",
        "w_no_market": "Nessun mercato trovato. Attiva AUTO e aspetta il nuovo mercato.",
        "w_voted_only": "Mercato gia' votato -> salto il voto, solo acquisto.",
        "w_need_pct": "Mercato NON votato: inserisci la percentuale per votare, poi riclicca Buy.",
        "w_bad_pct": "Percentuale non valida (es. 77).",
        "w_vote_line": ">>> VOTO: opz{n} '{name}'  consenso {pct}%",
        "w_vote_ok": "    VOTO ok ({ms} ms)",
        "w_vote_err": "    VOTO status {s} ({ms} ms): {t}",
        "w_buy_line": ">>> ACQUISTO: {usdc}$ su '{name}'",
        "w_buy_ok": "    ACQUISTO ok ({ms} ms)  signature: {sig}",
        "w_buy_err": "    ACQUISTO status {s} ({ms} ms): {t}",
        "w_auto_new": "AUTO: nuovo mercato rilevato -> entro",
        "w_market_err": "errore mercato (status {s})",
        "w_find_searching": "Cerco il mercato attivo...",
        "w_find_none": "Nessun mercato trovato.",
        "w_browser_closed": "Browser chiuso.",
    },
}


def tr(key, **kw):
    s = TR.get(LANG, TR["en"]).get(key) or TR["en"].get(key, key)
    return s.format(**kw) if kw else s


def pct_to_fraction(value: float) -> float:
    return value / 100.0 if value > 1 else value


def market_id_from_url(url: str):
    m = re.search(r"/market/([a-z0-9]+)", url or "")
    return m.group(1) if m else None


# ======================================================================
# WORKER: separate thread, owns Playwright and the browser.
# ======================================================================
class Worker(threading.Thread):
    def __init__(self, cmd_q, evt_q):
        super().__init__(daemon=True)
        self.cmd_q = cmd_q
        self.evt_q = evt_q
        self.ctx = None
        self.page = None
        self.market = None
        self.last_market_id = None
        self.auto_open = AUTO_OPEN_DEFAULT
        self.seen = {}          # market id seen in traffic -> timestamp
        self.api_urls = []      # /api/v1 GET urls seen (debug/support)
        self.last_fm = -1       # ultimo valore di window.__fmNew (event-driven)
        self.last_poll = 0.0    # ultimo check del "campanello"
        self.last_full = 0.0    # ultimo controllo pieno di sicurezza
        self._stop = False

    def emit(self, kind, **data):
        self.evt_q.put({"kind": kind, **data})

    def _on_response(self, response):
        """Listen to traffic: capture market ids the browser loads."""
        try:
            url = response.url
            method = response.request.method
        except Exception:
            return
        if "/api/v1/" not in url or method != "GET":
            return
        base = url.split("?")[0]
        if base not in self.api_urls:
            self.api_urls.append(base)
            if len(self.api_urls) > 300:
                self.api_urls.pop(0)
        for mid in re.findall(r"/market/([a-z0-9]{10,})", url):
            self.seen[mid] = time.time()
        m = re.search(r"marketId=([a-z0-9]{10,})", url)
        if m:
            self.seen[m.group(1)] = time.time()

    def pick_best(self, ids):
        """Among the ids, pick the LIVE (activated), not-expired, NOT-voted,
        most recent market. Returns the id or None."""
        best = None  # (when, mid)
        for mid in ids:
            status, mkt = self.api_get(MARKET_PATH + mid)
            if status != 200 or not isinstance(mkt, dict):
                continue
            if mkt.get("isComplete"):
                continue
            if not mkt.get("activatedAt"):   # non ancora live (es. "Coming Soon")
                continue
            if not self._in_future(mkt.get("endTime")):
                continue
            # NB: carichiamo anche i mercati gia' votati (cosi' puoi comunque
            # comprare); si sceglie comunque il LIVE piu' recente.
            when = mkt.get("activatedAt")
            if best is None or when > best[0]:
                best = (when, mid)
        return best[1] if best else None

    def _ids_from_page(self):
        """Estrae gli id dei mercati dal contenuto della pagina corrente
        (le tile Live & Upcoming della home), senza ricaricare."""
        try:
            html = self.page.content()
        except Exception:
            return []
        ids = []
        for mid in re.findall(r"/market/([a-z0-9]{10,})", html or ""):
            if mid not in ids:
                ids.append(mid)
        return ids

    def candidate_ids(self):
        """Id candidati: prima quelli nella pagina (home), poi quelli visti nel
        traffico, dal piu' recente."""
        ids = self._ids_from_page()
        for mid in sorted(self.seen, key=lambda k: self.seen[k], reverse=True):
            if mid not in ids:
                ids.append(mid)
        return ids[:15]

    def api_get(self, path):
        url = (ORIGIN + path) if path.startswith("/") else path
        try:
            res = self.page.evaluate(
                """async (p) => { const r = await fetch(p,{credentials:'include'});
                   return {status:r.status, text: await r.text()}; }""", url)
        except Exception:
            return 0, ""      # pagina in transizione/chiusa: non bloccare il bot
        try:
            return res["status"], json.loads(res["text"])
        except Exception:
            return res["status"], res["text"]

    def api_post(self, path, body):
        url = (ORIGIN + path) if path.startswith("/") else path
        return self.page.evaluate(
            """async ([path, b]) => { const t0=performance.now();
               const r = await fetch(path,{method:'POST',
                 headers:{'content-type':'application/json'},
                 body: JSON.stringify(b), credentials:'include'});
               return {status:r.status, text: await r.text(),
                       ms: Math.round(performance.now()-t0)}; }""", [url, body])

    def _market_view(self, mkt):
        o1, o2 = mkt.get("optionOne", {}), mkt.get("optionTwo", {})
        lp = mkt.get("latestPrice") or {}
        return {
            "id": mkt.get("id"), "subject": mkt.get("subject"),
            "voted": bool((mkt.get("userVoteState") or {}).get("hasVoted")),
            "name1": o1.get("name"), "price1": lp.get("optionOnePrice"),
            "name2": o2.get("name"), "price2": lp.get("optionTwoPrice"),
        }

    def _fetch_prices(self, market_id):
        """Quote correnti dall'endpoint dedicato: disponibili ANCHE prima di
        votare (sono quelle che vedi sulla home)."""
        status, lp = self.api_get(MARKET_PATH + market_id + "/latest-price")
        if status == 200 and isinstance(lp, dict) and isinstance(lp.get("latestPrice"), dict):
            return lp["latestPrice"]
        return None

    def load_market(self, market_id):
        status, mkt = self.api_get(MARKET_PATH + market_id)
        if status == 200 and isinstance(mkt, dict):
            lp = self._fetch_prices(market_id)
            if lp:
                mkt["latestPrice"] = lp   # quote vive, anche prima del voto
            self.market = mkt
            self.last_market_id = market_id
            self.emit("market", market=self._market_view(mkt))
        else:
            self.emit("log", text=tr("w_market_err", s=status))

    def refresh_price(self):
        if not self.market:
            return
        mid = self.market["id"]
        status, mkt = self.api_get(MARKET_PATH + mid)
        if status != 200 or not isinstance(mkt, dict):
            return
        lp = self._fetch_prices(mid)           # quote vive (anche prima del voto)
        if lp:
            mkt["latestPrice"] = lp
        self.market = mkt
        self.emit("market", market=self._market_view(mkt))

    def current_market_page(self):
        """Look through ALL open tabs for one on a market."""
        pages = self.ctx.pages if self.ctx else [self.page]
        for pg in pages:
            try:
                mid = market_id_from_url(pg.url)
            except Exception:
                mid = None
            if mid:
                return pg, mid
        return None, None

    def auto_watch(self):
        """No page reload: read the market ids on the current page (home tiles)
        plus traffic, and if the most recent LIVE & not-voted market differs
        from the current one, switch to it."""
        cand = self.candidate_ids()
        if not cand:
            return
        best = self.pick_best(cand)
        if best and best != self.last_market_id:
            self.emit("log", text=tr("w_auto_new"))
            self.load_market(best)

    def ensure_market(self):
        """Find a market to use: 1) an open tab on a market; 2) ids captured
        from traffic (most recent not voted)."""
        pg, mid = self.current_market_page()
        if mid:
            self.page = pg
            if mid != self.last_market_id or not self.market:
                self.load_market(mid)
            return bool(self.market)
        cand = self.candidate_ids()
        best = self.pick_best(cand) if cand else None
        if best:
            if best != self.last_market_id or not self.market:
                self.load_market(best)
            return bool(self.market)
        return bool(self.market)

    def do_buy(self, option_index, usdc, pct_raw):
        """One click does it all: find market -> (VOTE if not voted) -> BUY."""
        if not self.ensure_market():
            self.emit("log", text=tr("w_no_market"))
            return

        opt = self.market["optionOne"] if option_index == 1 else self.market["optionTwo"]
        market_id, option_id, oname = self.market["id"], opt["id"], opt.get("name")
        already_voted = bool((self.market.get("userVoteState") or {}).get("hasVoted"))

        # --- 1) VOTE (only if NOT already voted) ---
        if already_voted:
            self.emit("log", text=tr("w_voted_only"))
        else:
            praw = (pct_raw or "").strip().replace(",", ".")
            if praw == "":
                self.emit("log", text=tr("w_need_pct"))
                return
            try:
                pct = float(praw)
            except ValueError:
                self.emit("log", text=tr("w_bad_pct"))
                return
            vb = {"marketId": market_id, "optionId": option_id, "consensusGuess": int(round(pct))}
            self.emit("log", text=tr("w_vote_line", n=option_index, name=oname, pct=int(round(pct))))
            vres = self.api_post(VOTE_PATH, vb)
            try:
                vj = json.loads(vres["text"])
                voted_ok = bool(vj.get("hasVoted")) if isinstance(vj, dict) else False
            except Exception:
                voted_ok = False
            if vres["status"] == 200 and voted_ok:
                self.emit("log", text=tr("w_vote_ok", ms=vres["ms"]))
            else:
                self.emit("log", text=tr("w_vote_err", s=vres["status"], ms=vres["ms"], t=vres["text"][:200]))

        # --- 2) BUY ---
        buy_body = {
            "marketId": market_id,
            "optionId": option_id,
            "usdcInD6String": str(int(round(usdc * 1_000_000))),
            "maxPriceD6String": str(int(round(pct_to_fraction(BUY_MAX_PRICE_PCT) * 1_000_000))),
            "maxSlippageBps": int(DEFAULT_SLIPPAGE_BPS),
        }
        self.emit("log", text=tr("w_buy_line", usdc=usdc, name=oname))
        bres = self.api_post(BUY_PATH, buy_body)
        try:
            bj = json.loads(bres["text"])
            sig = bj.get("signature") if isinstance(bj, dict) else None
        except Exception:
            sig = None
        if bres["status"] == 200 and sig:
            self.emit("log", text=tr("w_buy_ok", ms=bres["ms"], sig=sig))
        else:
            self.emit("log", text=tr("w_buy_err", s=bres["status"], ms=bres["ms"], t=bres["text"][:300]))
        self.refresh_price()

    @staticmethod
    def _in_future(iso):
        if not iso:
            return True
        try:
            t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
            return t > datetime.now(timezone.utc)
        except Exception:
            return True

    def run(self):
        with sync_playwright() as p:
            USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            ctx = p.chromium.launch_persistent_context(
                str(USER_DATA_DIR), headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--mute-audio",                       # niente audio
                    "--disable-dev-shm-usage",            # usa meno memoria condivisa
                    "--disable-background-timer-throttling",  # AUTO resta attivo anche ridotto a icona
                    "--disable-renderer-backgrounding",
                ])
            self.ctx = ctx

            # MODALITA' LEGGERA: blocca SOLO i video/audio (la vera causa dei
            # crash su PC deboli). Non tocca le chiamate API ne' le immagini.
            if LIGHT_MODE:
                blocked = {"media"} | ({"image"} if BLOCK_IMAGES else set())

                def _route(route):
                    try:
                        if route.request.resource_type in blocked:
                            route.abort()
                        else:
                            route.continue_()
                    except Exception:
                        try:
                            route.continue_()
                        except Exception:
                            pass
                try:
                    ctx.route("**/*", _route)
                except Exception:
                    pass

            ctx.on("response", self._on_response)
            try:
                ctx.add_init_script(FM_OBSERVER_JS)  # osservatore su ogni pagina
            except Exception:
                pass
            self.page = ctx.pages[0] if ctx.pages else ctx.new_page()
            self.page.goto(ORIGIN + "/")
            try:
                self.page.evaluate(FM_OBSERVER_JS)   # anche sulla pagina gia' aperta
            except Exception:
                pass

            status, me = self.api_get("/api/v1/user/current")
            if status == 200 and isinstance(me, dict):
                self.emit("log", text=tr("w_session_ok", id=me.get("id")))
            else:
                self.emit("log", text=tr("w_not_logged"))

            last_price = 0.0
            while not self._stop:
                try:
                    cmd = self.cmd_q.get(timeout=0.1)
                except queue.Empty:
                    cmd = None
                if cmd:
                    if cmd[0] == "buy":
                        _, idx, usdc, pct = cmd
                        self.do_buy(idx, usdc, pct)
                    elif cmd[0] == "refresh":
                        self.refresh_price()
                    elif cmd[0] == "auto":
                        self.auto_open = bool(cmd[1])
                        self.emit("log", text=tr("w_auto_on") if self.auto_open else tr("w_auto_off"))
                    elif cmd[0] == "scan":
                        self.emit("log", text=tr("w_find_searching"))
                        if not self.ensure_market():
                            self.emit("log", text=tr("w_find_none"))
                    elif cmd[0] == "apis":
                        self.emit("log", text=f"--- {len(self.api_urls)} API endpoints seen ---")
                        for u in self.api_urls[-30:]:
                            self.emit("log", text="  " + u.replace(ORIGIN, ""))
                        self.emit("log", text=f"--- market ids captured: {list(self.seen.keys())} ---")
                        # diagnostica prezzi/voto del mercato corrente
                        if self.market:
                            mid = self.market["id"]
                            st, raw = self.api_get(MARKET_PATH + mid + "/latest-price")
                            self.emit("log", text=f"--- latest-price status {st}: {str(raw)[:200]}")
                            uvs = (self.market.get("userVoteState") or {})
                            self.emit("log", text=f"--- hasVoted={uvs.get('hasVoted')}  embedded latestPrice={self.market.get('latestPrice')}")
                    elif cmd[0] == "quit":
                        break
                    continue

                # tutta la parte periodica e' protetta: un errore momentaneo
                # (pagina in transizione, scheda chiusa) non deve fermare il bot.
                try:
                    # AUTO event-driven: leggi il "campanello" (window.__fmNew),
                    # leggerissimo. Lavoro pesante (auto_watch) SOLO quando
                    # compare un mercato nuovo. Rete di sicurezza ogni AUTO_SAFETY_SEC.
                    nowt = time.time()
                    if self.auto_open and (nowt - self.last_poll) >= AUTO_POLL_SEC:
                        self.last_poll = nowt
                        try:
                            n = self.page.evaluate("window.__fmNew || 0")
                        except Exception:
                            n = self.last_fm
                        if n != self.last_fm:
                            self.last_fm = n
                            self.auto_watch()
                            self.last_full = nowt
                        elif (nowt - self.last_full) >= AUTO_SAFETY_SEC:
                            self.auto_watch()
                            self.last_full = nowt

                    # detect a market from ANY tab the user opened
                    pg, mid = self.current_market_page()
                    if mid and mid != self.last_market_id:
                        self.page = pg
                        self.load_market(mid)

                    # periodic price refresh
                    now = time.time()
                    if self.market and (now - last_price) >= PREZZO_REFRESH_SEC:
                        self.refresh_price()
                        last_price = now
                except Exception:
                    time.sleep(0.2)   # errore transitorio: ignora e riprova

            ctx.close()
        self.emit("log", text=tr("w_browser_closed"))

    def stop(self):
        self._stop = True


# ======================================================================
# GUI (main thread)
# ======================================================================
class App:
    def __init__(self, root):
        self.root = root
        self.cmd_q = queue.Queue()
        self.evt_q = queue.Queue()
        self.worker = Worker(self.cmd_q, self.evt_q)
        self.pct_vars = {}
        self.custom_amt = {}
        self.custom_pct = {}
        self.last_market = None   # per ri-render su cambio lingua

        root.title("FactMachine")
        root.geometry("860x600")
        self.lang_choice = tk.StringVar(value="English" if LANG == "en" else "Italiano")

        self._build_ui()

        self.worker.start()
        root.after(80, self._drain_events)
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- costruzione interfaccia (ricreabile su cambio lingua) ----------
    def _build_ui(self):
        root = self.root
        for w in root.winfo_children():
            w.destroy()
        self.pct_vars.clear()
        self.custom_amt.clear()
        self.custom_pct.clear()

        # market title
        self.subject_var = tk.StringVar(value=tr("waiting"))
        tk.Label(root, textvariable=self.subject_var, font=("Segoe UI", 11, "bold"),
                 wraplength=820, justify="left").pack(pady=(10, 2), padx=10, anchor="w")
        self.info_var = tk.StringVar(value="")
        tk.Label(root, textvariable=self.info_var, fg="#555").pack(padx=10, anchor="w")

        # riga grande: chi sta vincendo (a colpo d'occhio)
        self.winner_var = tk.StringVar(value="")
        self.winner_lbl = tk.Label(root, textvariable=self.winner_var,
                                   font=("Segoe UI", 14, "bold"), fg="#1b8a2f")
        self.winner_lbl.pack(padx=10, anchor="w", pady=(2, 2))

        # control bar
        bar = tk.Frame(root)
        bar.pack(fill="x", padx=10, pady=4)
        self.auto_var = tk.BooleanVar(value=self.worker.auto_open)
        tk.Checkbutton(bar, text=tr("auto_cb"),
                       variable=self.auto_var, command=self._toggle_auto).pack(side="left")
        tk.Label(bar, text=tr("lang")).pack(side="left", padx=(16, 2))
        tk.OptionMenu(bar, self.lang_choice, "English", "Italiano",
                      command=self._change_lang).pack(side="left")
        tk.Button(bar, text=tr("btn_refresh"),
                  command=lambda: self.cmd_q.put(("refresh",))).pack(side="right")
        tk.Button(bar, text=tr("btn_find"),
                  command=lambda: self.cmd_q.put(("scan",))).pack(side="right", padx=6)
        tk.Button(bar, text="debug API",
                  command=lambda: self.cmd_q.put(("apis",))).pack(side="right")

        # two columns: option 1 and option 2
        cols = tk.Frame(root)
        cols.pack(fill="x", padx=10, pady=6)
        self.opt1_label = tk.LabelFrame(cols, text=tr("opt", n=1), font=("Segoe UI", 10, "bold"),
                                        fg="#1565c0", padx=8, pady=8)
        self.opt1_label.grid(row=0, column=0, padx=(0, 6), sticky="n")
        self._option_rows(self.opt1_label, 1, "#1565c0")
        self.opt2_label = tk.LabelFrame(cols, text=tr("opt", n=2), font=("Segoe UI", 10, "bold"),
                                        fg="#c62828", padx=8, pady=8)
        self.opt2_label.grid(row=0, column=1, padx=(6, 0), sticky="n")
        self._option_rows(self.opt2_label, 2, "#c62828")

        # log
        tk.Label(root, text=tr("log_label")).pack(anchor="w", padx=10)
        self.log = tk.Text(root, height=8, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # re-render current market (after a language rebuild)
        if self.last_market:
            self._render_market(self.last_market)

    def _option_rows(self, parent, option_index, color):
        tk.Label(parent, text=tr("col_amount"), width=8, fg="#777").grid(row=0, column=0)
        tk.Label(parent, text="%", width=6, fg="#777").grid(row=0, column=1)
        tk.Label(parent, text="", width=8).grid(row=0, column=2)
        for i, amt in enumerate(IMPORTI, start=1):
            tk.Label(parent, text=f"{amt}$", width=8,
                     font=("Segoe UI", 11, "bold")).grid(row=i, column=0, pady=3)
            var = tk.StringVar(value="")
            self.pct_vars[(option_index, amt)] = var
            tk.Entry(parent, textvariable=var, width=6, justify="center",
                     font=("Segoe UI", 12)).grid(row=i, column=1, padx=4)
            tk.Button(parent, text=f"Buy {option_index}", width=8, height=1,
                      font=("Segoe UI", 10, "bold"), fg="white", bg=color,
                      activebackground=color,
                      command=lambda oi=option_index, a=amt: self._click_buy(oi, a)
                      ).grid(row=i, column=2, padx=4, pady=3)
        r = len(IMPORTI) + 1
        amt_var = tk.StringVar(value="")
        self.custom_amt[option_index] = amt_var
        tk.Entry(parent, textvariable=amt_var, width=8, justify="center",
                 font=("Segoe UI", 11)).grid(row=r, column=0, pady=(10, 3))
        pvar = tk.StringVar(value="")
        self.custom_pct[option_index] = pvar
        tk.Entry(parent, textvariable=pvar, width=6, justify="center",
                 font=("Segoe UI", 12)).grid(row=r, column=1, padx=4)
        tk.Button(parent, text=f"Buy {option_index}", width=8, height=1,
                  font=("Segoe UI", 10, "bold"), fg="white", bg=color,
                  activebackground=color,
                  command=lambda oi=option_index: self._click_buy_custom(oi)
                  ).grid(row=r, column=2, padx=4, pady=(10, 3))
        tk.Label(parent, text=tr("custom_hint"),
                 fg="#777").grid(row=r + 1, column=0, columnspan=3)

    # ---------- azioni ----------
    def _click_buy(self, option_index, amount):
        raw = self.pct_vars[(option_index, amount)].get().strip()
        self.cmd_q.put(("buy", option_index, float(amount), raw))

    def _click_buy_custom(self, option_index):
        araw = self.custom_amt[option_index].get().strip().replace(",", ".")
        try:
            usdc = float(araw)
        except ValueError:
            self._log(tr("err_amount"))
            return
        praw = self.custom_pct[option_index].get().strip()
        self.cmd_q.put(("buy", option_index, usdc, praw))

    def _toggle_auto(self):
        self.cmd_q.put(("auto", self.auto_var.get()))

    def _change_lang(self, _choice):
        global LANG
        LANG = "it" if self.lang_choice.get() == "Italiano" else "en"
        self._build_ui()

    def _log(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def _fmt_price(self, p):
        return f"{p*100:.1f}%" if isinstance(p, (int, float)) else "?"

    def _render_market(self, m):
        self.subject_var.set(m.get("subject") or "-")
        voted = tr("voted_tag") if m.get("voted") else ""
        self.info_var.set(f"id: {m.get('id')}{voted}")
        self.opt1_label.config(
            text=f"{tr('opt', n=1)}: {m.get('name1')}  —  {self._fmt_price(m.get('price1'))}")
        self.opt2_label.config(
            text=f"{tr('opt', n=2)}: {m.get('name2')}  —  {self._fmt_price(m.get('price2'))}")

        # riga grande: chi sta vincendo (col colore dell'opzione)
        p1, p2 = m.get("price1"), m.get("price2")
        if isinstance(p1, (int, float)) and isinstance(p2, (int, float)):
            if p1 >= p2:
                self.winner_var.set(tr("winning", opt=tr("opt", n=1),
                                       name=m.get("name1"), pct=self._fmt_price(p1)))
                self.winner_lbl.config(fg="#1565c0")   # blu = opzione 1
            else:
                self.winner_var.set(tr("winning", opt=tr("opt", n=2),
                                       name=m.get("name2"), pct=self._fmt_price(p2)))
                self.winner_lbl.config(fg="#c62828")   # rosso = opzione 2
        else:
            self.winner_var.set("")

    def _drain_events(self):
        try:
            while True:
                evt = self.evt_q.get_nowait()
                if evt["kind"] == "log":
                    self._log(evt["text"])
                elif evt["kind"] == "market":
                    self.last_market = evt["market"]
                    self._render_market(evt["market"])
        except queue.Empty:
            pass
        self.root.after(80, self._drain_events)

    def _on_close(self):
        self.cmd_q.put(("quit",))
        self.worker.stop()
        self.root.after(300, self.root.destroy)


def license_gate(root) -> bool:
    """Check the license with the server. If missing/invalid, ask for the key."""
    for _ in range(3):
        res = license_client.check()
        if res["ok"]:
            messagebox.showinfo(tr("lic_title"),
                                tr("lic_valid", d=res.get("days_left"), e=res.get("expires_at", "")))
            return True

        status = res["status"]
        msg = tr("lic_" + status) if ("lic_" + status) in TR[LANG] else res.get("message", status)
        if status in ("offline", "bad_sig"):
            messagebox.showerror(tr("lic_title"), msg)
            return False
        if status in ("revoked", "expired", "wrong_machine", "invalid"):
            messagebox.showerror(tr("lic_title"), msg)
        key = simpledialog.askstring(tr("lic_title"), tr("lic_prompt", msg=msg))
        if not key:
            return False
        license_client.save_key(key)
    messagebox.showerror(tr("lic_title"), tr("lic_toomany"))
    return False


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    if not license_gate(root):
        root.destroy()
        raise SystemExit
    root.deiconify()
    App(root)
    root.mainloop()
