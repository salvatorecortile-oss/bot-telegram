# FactMachine Bot — Guida (Italiano)

Bot che, su `alpha.factmachine.com`, **vota** l'opzione che scegli tu e **apre
subito l'operazione** (acquisto), così entri a un prezzo migliore prima che il
prezzo si muova. Gira sul **tuo PC**, avviato da te, usando il **tuo** account.

> ⚠️ Controlla i Termini di servizio del sito: alcune piattaforme vietano i bot
> e potrebbero bloccare l'account. Lo usi sotto tua responsabilità.

---

## 1. Cosa ti serve (una volta sola)

1. **Python 3** installato (su Windows: da python.org; durante l'installazione
   spunta "Add Python to PATH").
2. Apri il **Prompt dei comandi (CMD)** nella cartella del bot e installa
   Playwright:
   ```
   pip install playwright
   playwright install chromium
   ```
   (Tkinter, l'interfaccia a finestra, è già incluso in Python su Windows.)

I file del bot (`login.py`, `dashboard.py`, ecc.) devono stare **tutti nella
stessa cartella**.

---

## 2. Primo accesso — login (una volta sola)

```
python login.py
```

- Si apre un browser: fai il **login a mano** con numero di telefono + codice
  che ricevi via **SMS**.
- Quando sei dentro e vedi la tua dashboard del sito, torna al CMD e premi
  **INVIO**.
- La sessione viene salvata nella cartella `browser_profile/`, così **non ti
  chiede più il codice SMS** ad ogni avvio.

> Non cancellare `browser_profile/` e non condividerla con nessuno: è la tua
> sessione. Se un giorno ti chiede di nuovo il login, rilancia `python login.py`.

---

## 3. Uso quotidiano — la dashboard a bottoni

```
python dashboard.py
```

Si aprono due cose:
- il **browser già loggato**;
- la **finestra con i bottoni** (Opzione 1 e Opzione 2, con importi e campi %).

### 3.1 Caricare il mercato (metodo sicuro: incolla URL)

1. Nel browser, entra nel mercato su cui vuoi operare.
2. **Copia l'URL** dalla barra indirizzi (tipo
   `https://alpha.factmachine.com/market/xxxxxxxx`).
3. Nella dashboard, incollalo nel campo **"URL/ID mercato"** e clicca
   **Carica** (o premi Invio).
4. In alto compaiono il titolo del mercato e le **due opzioni con i prezzi**.

> In alternativa puoi provare **"Trova mercato attivo"** o la casella
> **"AUTO-apri"**, ma il metodo "incolla URL" è il più affidabile.

### 3.2 Votare e comprare

**Se il mercato NON è ancora votato:**
1. Scegli la riga: Opzione 1 o 2, importo (bottone fisso o campo libero).
2. Scrivi la **percentuale** (il valore della "rotellina", es. 77) nel campo %.
3. Clicca **Buy** → il bot **vota** con quella % e **compra** subito.

**Se il mercato è GIÀ votato:**
1. Scegli opzione + importo.
2. Lascia la **% vuota**.
3. Clicca **Buy** → il bot **compra e basta** (salta il voto).

**Importo libero:** sotto i bottoni fissi c'è una riga dove **scrivi tu
l'importo** che vuoi, con la sua % e il suo Buy.

### 3.3 Controlla il risultato

Nel riquadro **Log** in basso devi vedere:
```
VOTO ok (xx ms)
ACQUISTO ok (xx ms)  signature: ...
```
La `signature` conferma che l'operazione è partita. Controlla anche sul sito
che il voto/la posizione risultino.

> 💡 Alla **prima prova** parti con un importo piccolo (es. 25$) per verificare
> che tutto funzioni, poi passa agli importi normali.

---

## 4. Personalizzare (importi, percentuali, ecc.)

Apri `dashboard.py` con un editor di testo (anche Blocco note) e, in cima al
file, trovi:

```python
# ---- I TUOI DEFAULT (cambiali qui) ----
IMPORTI = [25, 50, 100, 300, 500]   # importi dei bottoni fissi (USDC)
DEFAULT_SLIPPAGE_BPS = 10000        # tolleranza slippage (10000 = 100%)
BUY_MAX_PRICE_PCT = 100.0           # prezzo max dell'acquisto (100 = come il sito)
PREZZO_REFRESH_SEC = 2.0            # ogni quanto aggiornare i prezzi mostrati
AUTO_OPEN_DEFAULT = False           # auto-apri il mercato dalla pagina
```

- **Cambiare gli importi dei bottoni:** modifica la riga `IMPORTI = [...]`.
  Esempi: `IMPORTI = [10, 50, 200, 1000]` oppure `IMPORTI = [100, 500]`.
- Dopo ogni modifica, **salva e riavvia** la dashboard.

---

## 5. I file della cartella

| File | A cosa serve | Serve? |
|------|--------------|--------|
| `login.py` | Login una volta sola (numero + SMS), salva la sessione | ✅ sì |
| `dashboard.py` | La finestra a bottoni: è quella che usi per operare | ✅ sì |
| `bot.py` | Versione a riga di comando (alternativa, si scrivono i comandi) | opzionale |
| `recon.py` | Registra le chiamate del sito (solo per diagnosi) | solo se serve |
| `README.md` / `README.en.md` | Questa guida (IT / EN) | riferimento |
| `browser_profile/` | La tua sessione salvata (si crea da sola) | non toccare |

Per operare ti bastano **`login.py` + `dashboard.py`**.

---

## 6. Problemi frequenti

- **Errore all'avvio / "No module named playwright"** → esegui
  `pip install playwright` e `playwright install chromium`.
- **Ti richiede il login** → rilancia `python login.py`.
- **La dashboard non trova il mercato** → usa il campo **"URL/ID mercato" →
  Carica** incollando l'URL del mercato.
- **"Mercato NON votato: inserisci la percentuale"** → scrivi la % nel campo e
  riclicca Buy.
- **Il Log mostra uno status diverso da 200** → copia il messaggio e chiedi
  aiuto: può essere la sessione scaduta o un cambiamento del sito.
