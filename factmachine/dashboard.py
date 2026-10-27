"""
FactMachine - DASHBOARD a bottoni (niente da scrivere, solo click).

Per OGNI opzione (1 e 2) c'e' una riga per ogni importo:
    [ importo fisso ]  [ campo percentuale ]  [ bottone Buy ]
Scegli l'opzione, scrivi la percentuale su quella riga, clicchi il bottone:
parte voto + percentuale + acquisto all'istante (una sola chiamata API,
sparata dentro il browser gia' loggato -> cookie automatici).

Rilevamento mercato:
- apri il mercato nel browser e la dashboard lo riconosce da sola; oppure
- attiva "AUTO-apri nuovo mercato": quando la pagina (es. la home) mostra un
  nuovo mercato, la dashboard ci entra automaticamente.

Uso:
    python factmachine/dashboard.py     (dopo aver fatto login.py almeno una volta)

Serve Playwright (Tkinter e' gia' incluso in Python su Windows):
    pip install playwright
    playwright install chromium

======================================================================
 CONFIG - MODIFICABILE DA TE
======================================================================
"""
import json
import queue
import re
import threading
import time
import tkinter as tk
from pathlib import Path

from playwright.sync_api import sync_playwright

# ---- I TUOI DEFAULT (cambiali qui) ----
IMPORTI = [25, 50, 100, 300, 500]   # importi (USDC) -> una riga di bottoni ciascuno
DEFAULT_SLIPPAGE_BPS = 10000        # 100%
PREZZO_REFRESH_SEC = 2.0            # ogni quanto aggiornare i prezzi mostrati
AUTO_OPEN_DEFAULT = False           # auto-apri il nuovo mercato dalla pagina
# ----------------------------------------

BASE_DIR = Path(__file__).resolve().parent
USER_DATA_DIR = BASE_DIR / "browser_profile"

ORIGIN = "https://alpha.factmachine.com"
BUY_PATH = "/api/v1/order/transactions/buy"
MARKET_PATH = "/api/v1/market/"


def pct_to_fraction(value: float) -> float:
    return value / 100.0 if value > 1 else value


def market_id_from_url(url: str):
    m = re.search(r"/market/([a-z0-9]+)", url or "")
    return m.group(1) if m else None


# ======================================================================
# WORKER: thread separato, possiede Playwright e il browser.
# ======================================================================
class Worker(threading.Thread):
    def __init__(self, cmd_q, evt_q):
        super().__init__(daemon=True)
        self.cmd_q = cmd_q
        self.evt_q = evt_q
        self.page = None
        self.market = None
        self.last_market_id = None
        self.auto_open = AUTO_OPEN_DEFAULT
        self._stop = False

    def emit(self, kind, **data):
        self.evt_q.put({"kind": kind, **data})

    def api_get(self, path):
        res = self.page.evaluate(
            """async (p) => { const r = await fetch(p,{credentials:'include'});
               return {status:r.status, text: await r.text()}; }""", path)
        try:
            return res["status"], json.loads(res["text"])
        except Exception:
            return res["status"], res["text"]

    def fire_buy(self, body):
        return self.page.evaluate(
            """async (b) => { const t0=performance.now();
               const r = await fetch('%s',{method:'POST',
                 headers:{'content-type':'application/json'},
                 body: JSON.stringify(b), credentials:'include'});
               return {status:r.status, text: await r.text(),
                       ms: Math.round(performance.now()-t0)}; }""" % BUY_PATH, body)

    def _market_view(self, mkt):
        o1, o2 = mkt.get("optionOne", {}), mkt.get("optionTwo", {})
        lp = mkt.get("latestPrice") or {}
        return {
            "id": mkt.get("id"), "subject": mkt.get("subject"),
            "voted": bool(mkt.get("userVoteState")),
            "name1": o1.get("name"), "price1": lp.get("optionOnePrice"),
            "name2": o2.get("name"), "price2": lp.get("optionTwoPrice"),
        }

    def load_market(self, market_id):
        status, mkt = self.api_get(MARKET_PATH + market_id)
        if status == 200 and isinstance(mkt, dict):
            self.market = mkt
            self.last_market_id = market_id
            self.emit("market", market=self._market_view(mkt))
        else:
            self.emit("log", text=f"errore mercato (status {status})")

    def refresh_price(self):
        if not self.market:
            return
        status, mkt = self.api_get(MARKET_PATH + self.market["id"])
        if status == 200 and isinstance(mkt, dict):
            self.market = mkt
            self.emit("market", market=self._market_view(mkt))

    def do_buy(self, option_index, usdc, pct):
        # se non c'e' mercato, prova a rilevarlo dalla pagina corrente
        if not self.market:
            mid = None
            try:
                mid = market_id_from_url(self.page.url)
            except Exception:
                pass
            if mid:
                self.load_market(mid)
        if not self.market:
            self.emit("log", text="Nessun mercato: apri il mercato nel browser.")
            return
        opt = self.market["optionOne"] if option_index == 1 else self.market["optionTwo"]
        body = {
            "marketId": self.market["id"],
            "optionId": opt["id"],
            "usdcInD6String": str(int(round(usdc * 1_000_000))),
            "maxPriceD6String": str(int(round(pct_to_fraction(pct) * 1_000_000))),
            "maxSlippageBps": int(DEFAULT_SLIPPAGE_BPS),
        }
        self.emit("log", text=f">>> SPARO: opz{option_index} '{opt.get('name')}'  {usdc}$  max {pct}%")
        res = self.fire_buy(body)
        try:
            j = json.loads(res["text"])
            sig = j.get("signature") if isinstance(j, dict) else None
        except Exception:
            sig = None
        if res["status"] == 200 and sig:
            self.emit("log", text=f"    OK ({res['ms']} ms)  signature: {sig}")
        else:
            self.emit("log", text=f"    status {res['status']} ({res['ms']} ms): {res['text'][:300]}")
        self.refresh_price()

    def try_auto_open(self):
        """Se la pagina NON e' un mercato, cerca un link a un mercato e ci entra."""
        try:
            url = self.page.url
        except Exception:
            return
        if market_id_from_url(url):
            return  # gia' su un mercato: ci pensa l'auto-detect
        try:
            hrefs = self.page.eval_on_selector_all(
                "a[href*='/market/']",
                "els => els.map(e => e.getAttribute('href'))")
        except Exception:
            return
        for h in hrefs or []:
            mid = market_id_from_url(h)
            if mid and mid != self.last_market_id:
                self.emit("log", text=f"AUTO: trovato nuovo mercato {mid}, entro...")
                try:
                    self.page.goto(ORIGIN + (h if h.startswith("/") else "/" + h))
                except Exception:
                    pass
                return

    def run(self):
        with sync_playwright() as p:
            if not USER_DATA_DIR.exists():
                self.emit("log", text="Profilo non trovato. Esegui prima login.py")
                return
            ctx = p.chromium.launch_persistent_context(
                str(USER_DATA_DIR), headless=False,
                args=["--disable-blink-features=AutomationControlled"])
            self.page = ctx.pages[0] if ctx.pages else ctx.new_page()
            self.page.goto(ORIGIN + "/")

            status, me = self.api_get("/api/v1/user/current")
            if status == 200 and isinstance(me, dict):
                self.emit("log", text=f"Sessione OK (userId: {me.get('id')})")
            else:
                self.emit("log", text=f"ATTENZIONE: sessione non valida ({status}). Rifai login.py")

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
                    elif cmd[0] == "load":
                        self.load_market(cmd[1])
                    elif cmd[0] == "refresh":
                        self.refresh_price()
                    elif cmd[0] == "auto":
                        self.auto_open = bool(cmd[1])
                        self.emit("log", text=f"AUTO-apri: {'ON' if self.auto_open else 'OFF'}")
                    elif cmd[0] == "quit":
                        break
                    continue

                # auto-apri nuovo mercato (se attivo)
                if self.auto_open:
                    self.try_auto_open()

                # rileva mercato dalla URL del browser
                try:
                    mid = market_id_from_url(self.page.url)
                except Exception:
                    mid = None
                if mid and mid != self.last_market_id:
                    self.load_market(mid)

                # refresh periodico prezzi
                now = time.time()
                if self.market and (now - last_price) >= PREZZO_REFRESH_SEC:
                    self.refresh_price()
                    last_price = now

            ctx.close()
        self.emit("log", text="Browser chiuso.")

    def stop(self):
        self._stop = True


# ======================================================================
# GUI (thread principale)
# ======================================================================
class App:
    def __init__(self, root):
        self.root = root
        self.cmd_q = queue.Queue()
        self.evt_q = queue.Queue()
        self.worker = Worker(self.cmd_q, self.evt_q)
        self.pct_vars = {}  # (option_index, amount) -> StringVar della percentuale

        root.title("FactMachine - Dashboard")
        root.geometry("860x600")

        # Titolo mercato
        self.subject_var = tk.StringVar(value="In attesa... apri il mercato nel browser")
        tk.Label(root, textvariable=self.subject_var, font=("Segoe UI", 11, "bold"),
                 wraplength=820, justify="left").pack(pady=(10, 2), padx=10, anchor="w")
        self.info_var = tk.StringVar(value="")
        tk.Label(root, textvariable=self.info_var, fg="#555").pack(padx=10, anchor="w")

        # Barra controlli
        bar = tk.Frame(root)
        bar.pack(fill="x", padx=10, pady=4)
        self.auto_var = tk.BooleanVar(value=AUTO_OPEN_DEFAULT)
        tk.Checkbutton(bar, text="AUTO-apri nuovo mercato dalla pagina",
                       variable=self.auto_var, command=self._toggle_auto).pack(side="left")
        tk.Button(bar, text="Aggiorna prezzi",
                  command=lambda: self.cmd_q.put(("refresh",))).pack(side="right")

        # Due colonne: opzione 1 e opzione 2
        cols = tk.Frame(root)
        cols.pack(fill="x", padx=10, pady=6)

        self.opt1_label = tk.LabelFrame(cols, text="OPZIONE 1", font=("Segoe UI", 10, "bold"),
                                        fg="#1565c0", padx=8, pady=8)
        self.opt1_label.grid(row=0, column=0, padx=(0, 6), sticky="n")
        self._option_rows(self.opt1_label, 1, "#1565c0")

        self.opt2_label = tk.LabelFrame(cols, text="OPZIONE 2", font=("Segoe UI", 10, "bold"),
                                        fg="#c62828", padx=8, pady=8)
        self.opt2_label.grid(row=0, column=1, padx=(6, 0), sticky="n")
        self._option_rows(self.opt2_label, 2, "#c62828")

        # Log
        tk.Label(root, text="Log:").pack(anchor="w", padx=10)
        self.log = tk.Text(root, height=8, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.worker.start()
        root.after(80, self._drain_events)
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _option_rows(self, parent, option_index, color):
        # intestazione colonne
        tk.Label(parent, text="importo", width=8, fg="#777").grid(row=0, column=0)
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

    def _click_buy(self, option_index, amount):
        raw = self.pct_vars[(option_index, amount)].get().strip().replace(",", ".")
        if raw == "":
            self._log(f"ERRORE: inserisci la percentuale per {amount}$ (opz {option_index}).")
            return
        try:
            pct = float(raw)
        except ValueError:
            self._log("ERRORE: percentuale non valida (es. 77).")
            return
        self.cmd_q.put(("buy", option_index, float(amount), pct))

    def _toggle_auto(self):
        self.cmd_q.put(("auto", self.auto_var.get()))

    def _log(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def _fmt_price(self, p):
        return f"{p*100:.1f}%" if isinstance(p, (int, float)) else "?"

    def _drain_events(self):
        try:
            while True:
                evt = self.evt_q.get_nowait()
                if evt["kind"] == "log":
                    self._log(evt["text"])
                elif evt["kind"] == "market":
                    m = evt["market"]
                    self.subject_var.set(m.get("subject") or "(senza titolo)")
                    voted = "  [GIA' VOTATO]" if m.get("voted") else ""
                    self.info_var.set(f"id: {m.get('id')}{voted}")
                    self.opt1_label.config(
                        text=f"OPZIONE 1: {m.get('name1')}  —  {self._fmt_price(m.get('price1'))}")
                    self.opt2_label.config(
                        text=f"OPZIONE 2: {m.get('name2')}  —  {self._fmt_price(m.get('price2'))}")
        except queue.Empty:
            pass
        self.root.after(80, self._drain_events)

    def _on_close(self):
        self.cmd_q.put(("quit",))
        self.worker.stop()
        self.root.after(300, self.root.destroy)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
