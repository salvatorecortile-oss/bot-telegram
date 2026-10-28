# FactMachine Bot — Guida completa (Italiano)

Bot che, sul sito `alpha.factmachine.com`, **vota** l'opzione che scegli tu e
**apre subito l'operazione** (acquisto), per entrare a un prezzo migliore prima
che il prezzo si muova. Gira sul **tuo PC**, avviato da te, con il **tuo**
account.

> ⚠️ Controlla i Termini di servizio del sito: alcune piattaforme vietano i bot
> e potrebbero bloccare l'account. Lo usi sotto tua responsabilità.

Questa guida è pensata per chi **non ha mai usato un bot**. Segui i passaggi in
ordine, dal primo all'ultimo. Non saltarne nessuno.

---

## ⌨️ Due cose da sapere prima di iniziare

**Cos'è il "CMD" (Prompt dei comandi):** è una finestra nera dove si scrivono
dei comandi. Si apre così:
- Clicca sul pulsante **Start** di Windows (in basso a sinistra).
- Scrivi **cmd**
- Compare "Prompt dei comandi": cliccaci sopra con il **tasto destro** e scegli
  **"Esegui come amministratore"**. (Se compare una domanda, rispondi **Sì**.)

**Come si incolla un comando nel CMD:** copi il comando da questa guida (lo
selezioni e premi `Ctrl+C`), poi vai sulla finestra nera del CMD e fai **click
col tasto destro**: il comando si incolla da solo. Poi premi **INVIO** per
eseguirlo.

> Regola d'oro: **un comando alla volta.** Incolla, premi INVIO, aspetta che
> finisca, poi passa al comando successivo.

---

## 1. Installare Python (tutto dal CMD)

Python è il "motore" che fa girare il bot. Si installa dal CMD, senza aprire
nessun sito.

Apri il **CMD come amministratore** (vedi sopra) e prova prima questo comando
(copia → tasto destro per incollare → INVIO):

```
winget install -e --id Python.Python.3.12
```

Aspetta che finisca (circa 1–2 minuti). Se dice qualcosa tipo "Installazione
riuscita", sei a posto: **vai al passo 2**.

### Se il comando sopra dà errore ("winget non riconosciuto")

Usa questi **due comandi**, uno alla volta (copia il primo, incolla, INVIO,
aspetta; poi copia il secondo, incolla, INVIO):

```
curl -o python-setup.exe https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe
```

```
python-setup.exe /quiet InstallAllUsers=1 PrependPath=1
```

Il primo **scarica** Python, il secondo lo **installa in automatico** (compresa
l'aggiunta al "PATH", che serve a far trovare Python al CMD). Aspetta ~1 minuto.

### Controllo che Python sia installato

**Chiudi la finestra del CMD e riaprila** (serve per aggiornare il sistema).
Poi incolla questo comando e premi INVIO:

```
python --version
```

Se ti risponde con un numero (es. `Python 3.12.7`), **Python è installato
correttamente**. Se invece dà errore, ripeti il passo 1 e assicurati di aver
usato i comandi esatti.

---

## 2. Mettere i file del bot in una cartella

1. Crea una cartella dove vuoi (es. sul Desktop) e chiamala, per esempio,
   **`factmachine`**.
2. Metti **dentro questa cartella** tutti i file del bot che hai ricevuto:
   `login.py`, `dashboard.py`, `bot.py`, `recon.py`, `README.md`,
   `README.en.md`.

Tutti i file devono stare **nella stessa cartella**.

---

## 3. Aprire il CMD dentro la cartella del bot

Questo è il trucco più comodo:

1. Apri la cartella del bot (quella con `dashboard.py` dentro).
2. Clicca sulla **barra dell'indirizzo** in alto nella finestra (quella dove
   c'è scritto il percorso della cartella).
3. Scrivi **cmd** e premi **INVIO**.

Si apre una finestra nera del CMD **già posizionata dentro la tua cartella**.
Userai sempre questa per lanciare il bot.

---

## 4. Installare Playwright (una volta sola)

Playwright è la parte che comanda il browser. Nel CMD aperto nella cartella del
bot, incolla questi **due comandi**, uno alla volta (copia, INVIO, aspetta; poi
il secondo):

```
pip install playwright
```

```
playwright install chromium
```

Il primo installa Playwright, il secondo scarica il browser che userà. Aspetta
che finiscano (il secondo può metterci qualche minuto).

---

## 5. Primo accesso — login (una volta sola)

Nel CMD (nella cartella del bot) incolla e premi INVIO:

```
python login.py
```

- Si apre un **browser**. Fai il **login a mano**: inserisci il numero di
  telefono, poi il **codice che ricevi via SMS**.
- Quando sei entrato e vedi la tua pagina sul sito, **torna alla finestra nera
  del CMD** e premi **INVIO**.

La tua sessione viene salvata in una cartella chiamata `browser_profile/`
(si crea da sola). Così **non ti chiederà più il codice SMS** ai prossimi avvii.

> Non cancellare la cartella `browser_profile/` e non darla a nessuno: è la tua
> sessione. Se un giorno il bot ti richiede il login, rilancia `python login.py`.

---

## 6. Avviare la dashboard (ogni volta che vuoi operare)

Nel CMD (nella cartella del bot) incolla e premi INVIO:

```
python dashboard.py
```

Si aprono **due finestre**:
- il **browser già loggato**;
- la **finestra con i bottoni** (Opzione 1 e Opzione 2, con importi e campi %).

---

## 7. Caricare il mercato (metodo sicuro: incolla l'indirizzo)

1. Nel **browser**, entra nel mercato su cui vuoi operare.
2. Clicca sulla **barra dell'indirizzo** del browser e **copia l'indirizzo**
   (sarà qualcosa tipo `https://alpha.factmachine.com/market/xxxxxxxx`).
   Per copiarlo: selezionalo e premi `Ctrl+C`.
3. Vai sulla **finestra dei bottoni**, nel campo **"URL/ID mercato"** incolla
   l'indirizzo (`Ctrl+V`) e clicca **Carica** (o premi INVIO).
4. In alto compaiono il **titolo del mercato** e le **due opzioni con i prezzi**.

> Esistono anche i pulsanti "Trova mercato attivo" e la casella "AUTO-apri", ma
> il metodo "incolla l'indirizzo" è il più sicuro: usa quello.

---

## 8. Votare e comprare

**Se il mercato NON è ancora votato:**
1. Scegli la riga: **Opzione 1** o **Opzione 2**, e l'**importo** (un bottone
   fisso, es. 100$, oppure la riga "importo libero" dove scrivi la cifra).
2. Nel campo **%** scrivi la percentuale (il valore della "rotellina", es. 77).
3. Clicca **Buy** → il bot **vota** con quella % e **compra** subito.

**Se il mercato è GIÀ votato:**
1. Scegli opzione + importo.
2. Lascia la **% vuota**.
3. Clicca **Buy** → il bot **compra e basta** (salta il voto).

**Importo libero:** sotto i bottoni fissi c'è una riga dove **scrivi tu
l'importo** che vuoi, con la sua % e il suo bottone Buy.

### Controlla che sia andata a buon fine

Nel riquadro **Log** (in basso nella finestra dei bottoni) devi vedere:
```
VOTO ok (xx ms)
ACQUISTO ok (xx ms)  signature: ...
```
La riga `signature` conferma che l'operazione è partita. Controlla anche sul
sito che il voto / la posizione risultino.

> 💡 La **prima volta** prova con un importo piccolo (es. 25$) per verificare che
> tutto funzioni, poi passa agli importi normali.

---

## 9. Cambiare gli importi dei bottoni

1. Apri il file `dashboard.py` con **Blocco note** (tasto destro sul file →
   "Apri con" → "Blocco note").
2. In cima al file trovi questa parte:
   ```python
   # ---- I TUOI DEFAULT (cambiali qui) ----
   IMPORTI = [25, 50, 100, 300, 500]   # importi dei bottoni fissi (USDC)
   DEFAULT_SLIPPAGE_BPS = 10000        # tolleranza slippage (10000 = 100%)
   BUY_MAX_PRICE_PCT = 100.0           # prezzo max dell'acquisto
   PREZZO_REFRESH_SEC = 2.0            # ogni quanto aggiornare i prezzi
   AUTO_OPEN_DEFAULT = False
   ```
3. Modifica la riga **`IMPORTI = [...]`** con i numeri che vuoi, separati da
   virgola. Esempi:
   ```python
   IMPORTI = [10, 50, 200, 1000]
   IMPORTI = [100, 500]
   ```
4. **Salva** (`Ctrl+S`) e **riavvia** la dashboard (chiudi la finestra e rilancia
   `python dashboard.py`).

---

## 10. I file della cartella

| File | A cosa serve | Serve? |
|------|--------------|--------|
| `login.py` | Login una volta sola (numero + SMS), salva la sessione | ✅ sì |
| `dashboard.py` | La finestra a bottoni: è quella che usi per operare | ✅ sì |
| `bot.py` | Versione a riga di comando (alternativa) | opzionale |
| `recon.py` | Registra le chiamate del sito (solo per diagnosi) | solo se serve |
| `README.md` / `README.en.md` | Questa guida (IT / EN) | riferimento |
| `browser_profile/` | La tua sessione salvata (si crea da sola) | non toccare |

Per operare ti bastano **`login.py` + `dashboard.py`**.

---

## 11. Problemi frequenti

- **`python` o `pip` "non riconosciuto"** → Python non è installato bene o manca
  il PATH. Rifai il **passo 1** (e ricordati di **riaprire il CMD** dopo).
- **"No module named playwright"** → rifai il **passo 4**
  (`pip install playwright` e `playwright install chromium`).
- **Il bot ti richiede il login** → rilancia `python login.py` (passo 5).
- **La dashboard non trova il mercato** → usa il campo **"URL/ID mercato" →
  Carica**, incollando l'indirizzo del mercato (passo 7).
- **"Mercato NON votato: inserisci la percentuale"** → scrivi la % nel campo e
  riclicca Buy.
- **Nel Log compare uno status diverso da 200** → copia il messaggio: può essere
  la sessione scaduta (rifai il login) o un cambiamento del sito.
