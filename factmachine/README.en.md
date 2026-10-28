# FactMachine Bot — Complete guide (English)

A bot that, on `alpha.factmachine.com`, **votes** the option you choose and
**immediately opens the trade** (buy), so you enter at a better price before it
moves. It runs on **your own PC**, started by you, with **your** account.

> ⚠️ Check the site's Terms of Service: some platforms forbid bots and may ban
> the account. Use it at your own risk.

This guide is for someone who has **never used a bot**. Follow the steps in
order, from first to last. Don't skip any.

---

## ⌨️ Two things to know before you start

**What the "CMD" (Command Prompt) is:** it's a black window where you type
commands. Open it like this:
- Click the Windows **Start** button (bottom-left).
- Type **cmd**
- "Command Prompt" appears: **right-click** it and choose **"Run as
  administrator"**. (If a prompt appears, answer **Yes**.)

**How to paste a command into the CMD:** copy the command from this guide
(select it and press `Ctrl+C`), then go to the black CMD window and **right-click**:
the command pastes by itself. Then press **ENTER** to run it.

> Golden rule: **one command at a time.** Paste, press ENTER, wait for it to
> finish, then move to the next command.

---

## 1. Install Python (all from the CMD)

Python is the "engine" that runs the bot. You install it from the CMD, without
opening any website.

Open the **CMD as administrator** (see above) and first try this command
(copy → right-click to paste → ENTER):

```
winget install -e --id Python.Python.3.12
```

Wait for it to finish (about 1–2 minutes). If it says something like
"Successfully installed", you're good: **go to step 2**.

### If the command above fails ("winget is not recognized")

Use these **two commands**, one at a time (copy the first, paste, ENTER, wait;
then copy the second, paste, ENTER):

```
curl -o python-setup.exe https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe
```

```
python-setup.exe /quiet InstallAllUsers=1 PrependPath=1
```

The first **downloads** Python, the second **installs it automatically**
(including adding it to the "PATH", which lets the CMD find Python). Wait ~1 min.

### Check that Python is installed

**Close the CMD window and open it again** (this refreshes the system). Then
paste this command and press ENTER:

```
python --version
```

If it replies with a number (e.g. `Python 3.12.7`), **Python is installed
correctly**. If it errors, repeat step 1 and make sure you used the exact
commands.

---

## 2. Put the bot files in a folder

1. Create a folder anywhere (e.g. on the Desktop) and name it, for example,
   **`factmachine`**.
2. Put **inside this folder** all the bot files you received:
   `login.py`, `dashboard.py`, `bot.py`, `recon.py`, `README.md`,
   `README.en.md`.

All files must be in the **same folder**.

---

## 3. Open the CMD inside the bot folder

This is the handiest trick:

1. Open the bot folder (the one that contains `dashboard.py`).
2. Click the **address bar** at the top of the window (where the folder path is
   shown).
3. Type **cmd** and press **ENTER**.

A black CMD window opens **already positioned inside your folder**. You'll always
use this one to launch the bot.

---

## 4. Install Playwright (one time)

Playwright is the part that drives the browser. In the CMD opened in the bot
folder, paste these **two commands**, one at a time (copy, ENTER, wait; then the
second):

```
pip install playwright
```

```
playwright install chromium
```

The first installs Playwright, the second downloads the browser it will use.
Wait for them to finish (the second can take a few minutes).

---

## 5. First login (one time)

In the CMD (in the bot folder) paste and press ENTER:

```
python login.py
```

- A **browser** opens. **Log in manually**: enter your phone number, then the
  **code you receive by SMS**.
- Once you're in and see your page on the site, **go back to the black CMD
  window** and press **ENTER**.

Your session is saved in a folder called `browser_profile/` (created
automatically). So it **won't ask for the SMS code** on the next launches.

> Don't delete the `browser_profile/` folder and don't give it to anyone: it's
> your session. If one day the bot asks you to log in again, run
> `python login.py`.

---

## 6. Start the dashboard (every time you want to trade)

In the CMD (in the bot folder) paste and press ENTER:

```
python dashboard.py
```

**Two windows** open:
- the **already-logged-in browser**;
- the **button window** (Option 1 and Option 2, with amounts and % fields).

---

## 7. Load the market (safe method: paste the address)

1. In the **browser**, open the market you want to trade.
2. Click the browser's **address bar** and **copy the address** (it will look
   like `https://alpha.factmachine.com/market/xxxxxxxx`). To copy it: select it
   and press `Ctrl+C`.
3. Go to the **button window**, paste the address (`Ctrl+V`) into the
   **"URL/ID mercato"** field, and click **Carica** (Load) — or press ENTER.
4. The **market title** and the **two options with prices** appear at the top.

> There are also the "Trova mercato attivo" (Find active market) button and the
> "AUTO-apri" checkbox, but pasting the address is the safest: use that.

---

## 8. Vote and buy

**If the market is NOT voted yet:**
1. Pick the row: **Option 1** or **Option 2**, and the **amount** (a fixed
   button, e.g. $100, or the "free amount" row where you type the figure).
2. In the **%** field type the percentage (the "wheel" value, e.g. 77).
3. Click **Buy** → the bot **votes** with that % and **buys** right away.

**If the market is ALREADY voted:**
1. Pick option + amount.
2. Leave the **% empty**.
3. Click **Buy** → the bot **just buys** (skips the vote).

**Free amount:** below the fixed buttons there's a row where you **type any
amount** you want, with its own % and Buy button.

### Check that it went through

In the **Log** box (bottom of the button window) you should see:
```
VOTO ok (xx ms)
ACQUISTO ok (xx ms)  signature: ...
```
The `signature` line confirms the order went through. Also check on the site
that the vote / position shows up.

> 💡 The **first time**, try a small amount (e.g. $25) to confirm everything
> works, then move to your normal amounts.

---

## 9. Change the button amounts

1. Open the `dashboard.py` file with **Notepad** (right-click the file →
   "Open with" → "Notepad").
2. At the top of the file you'll find this part:
   ```python
   # ---- I TUOI DEFAULT (cambiali qui) ----   # YOUR DEFAULTS (change here)
   IMPORTI = [25, 50, 100, 300, 500]   # fixed-button amounts (USDC)
   DEFAULT_SLIPPAGE_BPS = 10000        # slippage tolerance (10000 = 100%)
   BUY_MAX_PRICE_PCT = 100.0           # max buy price
   PREZZO_REFRESH_SEC = 2.0            # how often to refresh prices
   AUTO_OPEN_DEFAULT = False
   ```
3. Edit the **`IMPORTI = [...]`** line with the numbers you want, separated by
   commas. Examples:
   ```python
   IMPORTI = [10, 50, 200, 1000]
   IMPORTI = [100, 500]
   ```
4. **Save** (`Ctrl+S`) and **restart** the dashboard (close the window and run
   `python dashboard.py` again).

---

## 10. Files in the folder

| File | Purpose | Needed? |
|------|---------|---------|
| `login.py` | One-time login (phone + SMS), saves the session | ✅ yes |
| `dashboard.py` | The button window: what you use to trade | ✅ yes |
| `bot.py` | Command-line version (alternative) | optional |
| `recon.py` | Records the site's calls (diagnostics only) | only if needed |
| `README.md` / `README.en.md` | This guide (IT / EN) | reference |
| `browser_profile/` | Your saved session (created automatically) | don't touch |

To trade you only need **`login.py` + `dashboard.py`**.

---

## 11. Troubleshooting

- **`python` or `pip` "not recognized"** → Python isn't installed properly or
  the PATH is missing. Redo **step 1** (and remember to **reopen the CMD**
  afterwards).
- **"No module named playwright"** → redo **step 4**
  (`pip install playwright` and `playwright install chromium`).
- **The bot asks you to log in** → run `python login.py` again (step 5).
- **The dashboard can't find the market** → use the **"URL/ID mercato" →
  Carica** field, pasting the market address (step 7).
- **"Mercato NON votato: inserisci la percentuale"** (market not voted: enter the
  percentage) → type the % in the field and click Buy again.
- **The Log shows a status other than 200** → copy the message: it may be an
  expired session (log in again) or a change on the site.
