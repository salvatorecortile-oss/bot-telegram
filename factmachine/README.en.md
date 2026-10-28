# FactMachine Bot — Guide (English)

A bot that, on `alpha.factmachine.com`, **votes** the option you choose and
**immediately opens the trade** (buy), so you enter at a better price before it
moves. It runs on **your own PC**, started by you, using **your** account.

> ⚠️ Check the site's Terms of Service: some platforms forbid bots and may ban
> the account. Use it at your own risk.

---

## 1. What you need (one time)

1. **Python 3** installed (on Windows: from python.org; tick "Add Python to
   PATH" during setup).
2. Open the **Command Prompt (CMD)** in the bot's folder and install Playwright:
   ```
   pip install playwright
   playwright install chromium
   ```
   (Tkinter, the window interface, already ships with Python on Windows.)

All the bot files (`login.py`, `dashboard.py`, etc.) must be in the **same
folder**.

---

## 2. First login (one time)

```
python login.py
```

- A browser opens: **log in manually** with your phone number + the code you
  receive by **SMS**.
- Once you're in and see your dashboard on the site, go back to the CMD and
  press **ENTER**.
- The session is saved in the `browser_profile/` folder, so it **won't ask for
  the SMS code every time**.

> Don't delete `browser_profile/` and don't share it: it's your session. If one
> day it asks you to log in again, run `python login.py` again.

---

## 3. Daily use — the button dashboard

```
python dashboard.py
```

Two things open:
- the **already-logged-in browser**;
- the **button window** (Option 1 and Option 2, with amounts and % fields).

### 3.1 Load the market (safe method: paste the URL)

1. In the browser, open the market you want to trade.
2. **Copy the URL** from the address bar (like
   `https://alpha.factmachine.com/market/xxxxxxxx`).
3. In the dashboard, paste it into the **"URL/ID mercato"** field and click
   **Carica** (Load) — or press Enter.
4. The market title and the **two options with prices** appear at the top.

> You can also try **"Trova mercato attivo"** (Find active market) or the
> **"AUTO-apri"** checkbox, but pasting the URL is the most reliable.

### 3.2 Vote and buy

**If the market is NOT voted yet:**
1. Pick the row: Option 1 or 2, amount (a fixed button or the free field).
2. Type the **percentage** (the "wheel" value, e.g. 77) in the % field.
3. Click **Buy** → the bot **votes** with that % and **buys** right away.

**If the market is ALREADY voted:**
1. Pick option + amount.
2. Leave the **% empty**.
3. Click **Buy** → the bot **just buys** (skips the vote).

**Free amount:** below the fixed buttons there's a row where you **type any
amount** you want, with its own % and Buy.

### 3.3 Check the result

In the **Log** box at the bottom you should see:
```
VOTO ok (xx ms)
ACQUISTO ok (xx ms)  signature: ...
```
The `signature` confirms the order went through. Also check on the site that the
vote/position shows up.

> 💡 On your **first try**, start with a small amount (e.g. $25) to confirm
> everything works, then move to your normal amounts.

---

## 4. Customize (amounts, defaults, etc.)

Open `dashboard.py` in a text editor (Notepad is fine). At the top of the file
you'll find:

```python
# ---- I TUOI DEFAULT (cambiali qui) ----   # <- YOUR DEFAULTS (change here)
IMPORTI = [25, 50, 100, 300, 500]   # fixed-button amounts (USDC)
DEFAULT_SLIPPAGE_BPS = 10000        # slippage tolerance (10000 = 100%)
BUY_MAX_PRICE_PCT = 100.0           # max buy price (100 = same as the site)
PREZZO_REFRESH_SEC = 2.0            # how often to refresh shown prices
AUTO_OPEN_DEFAULT = False           # auto-open the market from the page
```

- **Change the button amounts:** edit the `IMPORTI = [...]` line.
  Examples: `IMPORTI = [10, 50, 200, 1000]` or `IMPORTI = [100, 500]`.
- After any change, **save and restart** the dashboard.

---

## 5. Files in the folder

| File | Purpose | Needed? |
|------|---------|---------|
| `login.py` | One-time login (phone + SMS), saves the session | ✅ yes |
| `dashboard.py` | The button window: what you use to trade | ✅ yes |
| `bot.py` | Command-line version (alternative, you type commands) | optional |
| `recon.py` | Records the site's calls (diagnostics only) | only if needed |
| `README.md` / `README.en.md` | This guide (IT / EN) | reference |
| `browser_profile/` | Your saved session (created automatically) | don't touch |

To trade you only need **`login.py` + `dashboard.py`**.

---

## 6. Troubleshooting

- **Error on start / "No module named playwright"** → run
  `pip install playwright` and `playwright install chromium`.
- **It asks you to log in** → run `python login.py` again.
- **The dashboard can't find the market** → use the **"URL/ID mercato" →
  Carica** field and paste the market URL.
- **"Mercato NON votato: inserisci la percentuale"** (market not voted: enter
  the percentage) → type the % and click Buy again.
- **The Log shows a status other than 200** → copy the message and ask for
  help: the session may have expired or the site may have changed.
