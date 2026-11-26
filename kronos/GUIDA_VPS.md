# Kronos sulla VPS Windows – guida passo passo

Tutti i comandi vanno scritti nel **Prompt dei comandi (CMD)** della VPS.
Per aprirlo: tasto Start → scrivi `cmd` → Invio.

---

## PARTE 0 – Controlla la VPS (5 minuti)

Kronos fa calcoli pesanti. La VPS deve avere almeno:

| Risorsa | Minimo | Consigliato |
|---|---|---|
| RAM | 4 GB | 8 GB |
| Spazio libero su disco | 5 GB | 10 GB |

Per controllare la RAM: tasto destro sulla barra in basso → **Gestione attività** → scheda **Prestazioni** → **Memoria**.
Per lo spazio: apri **Esplora file** → **Questo PC** → guarda il disco C:.

Se la VPS ha solo 2 GB di RAM, Kronos rischia di bloccarla insieme a MT5 e agli altri bot.

---

## PARTE 1 – Programmi necessari (una volta sola)

### 1. Python

Nel CMD scrivi:
```
python --version
```
- Se risponde `Python 3.10`, `3.11`, `3.12` o `3.13` → è a posto, passa al punto 2.
- Se dà errore o una versione più vecchia → scaricalo da https://www.python.org/downloads/windows/
  (prendi la **3.12**, "Windows installer 64-bit").
  Durante l'installazione **spunta la casella "Add python.exe to PATH"** in basso, poi "Install Now".
  Chiudi e riapri il CMD e riprova `python --version`.

### 2. Git

```
git --version
```
- Se risponde `git version ...` → a posto.
- Se dà errore → scaricalo da https://git-scm.com/download/win ("64-bit Git for Windows Setup"),
  installalo lasciando tutte le opzioni come sono (Next, Next, ... Install). Chiudi e riapri il CMD.

### 3. MetaTrader 5

Deve essere installato sulla VPS, **aperto e collegato al conto**. Se gli altri bot girano già lì, è già a posto.

---

## PARTE 2 – Scarica il codice

### Caso A: il repository `bot-telegram` è GIÀ sulla VPS (ci girano gli altri bot)

```
cd C:\percorso\bot-telegram
git fetch origin claude/brave-cray-6yx1hp
git checkout claude/brave-cray-6yx1hp
```
(sostituisci `C:\percorso\bot-telegram` con la cartella vera, ad esempio `C:\bot\bot-telegram`)

### Caso B: sulla VPS NON c'è ancora niente

```
cd C:\
mkdir bot
cd bot
git clone -b claude/brave-cray-6yx1hp https://github.com/salvatorecortile-oss/bot-telegram.git
cd bot-telegram
```
Il repository è privato: si aprirà una finestra di GitHub per accedere. Scegli **"Sign in with your browser"** e accedi con il tuo account GitHub.

---

## PARTE 3 – Installa Kronos (una volta sola)

### 1. Entra nella cartella kronos
```
cd kronos
```

### 2. Installa le librerie (5-10 minuti, scarica circa 1 GB)
```
pip install -r requirements.txt
```
Alla fine non devono esserci righe rosse con `ERROR`. Gli avvisi gialli (`WARNING`) si possono ignorare.

### 3. Scarica il motore Kronos ufficiale
```
git clone https://github.com/shiyu-coder/Kronos.git Kronos
```
Questo è pubblico, non chiede login.

### 4. Crea le impostazioni
```
copy .env.example .env
```
Se sulla VPS hai **più MetaTrader 5** installati (ad esempio uno per ogni broker), apri `.env` con il Blocco note:
```
notepad .env
```
e nella riga `MT5_PATH=` metti il percorso del terminale da usare, ad esempio:
```
MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
```
Salva e chiudi.

---

## PARTE 4 – Prima prova

Con MetaTrader 5 aperto:
```
python main.py --once
```
La prima volta scarica il modello (qualche centinaio di MB) e ci mette qualche minuto.
Le volte dopo è molto più veloce.

Se funziona vedi qualcosa del genere:
```
🔮 Kronos | XAUUSD M15
Ultima chiusura: 2650.30 (...)
Prossime 12 candele, 20 scenari
🟢 Tendenza: RIALZO
Probabilità rialzo: 70.0%
...
```

---

## PARTE 5 – Lasciarlo sempre acceso

Fai **doppio clic** sul file `avvia_kronos.bat` dentro la cartella `kronos`.
Si apre una finestra nera con scritto `Servizio Kronos attivo su http://127.0.0.1:8765`.

- **Non chiudere quella finestra** (puoi ridurla a icona).
- Se Kronos si blocca, la finestra lo **riavvia da sola** dopo 30 secondi.
- Per controllare che funzioni, apri il browser della VPS su:
  `http://127.0.0.1:8765/forecast?format=text`

### Quando esci dalla VPS
Chiudi la finestra di Desktop remoto con la **X in alto** (questo "disconnette" e i programmi restano accesi).
**Non** fare Start → Disconnetti/Esci ("Sign out"): chiuderebbe tutti i programmi, anche MT5 e i bot.

### Avvio automatico se la VPS si riavvia (facoltativo)
1. Tasto destro su `avvia_kronos.bat` → **Crea collegamento**.
2. Premi `Windows + R`, scrivi `shell:startup`, Invio: si apre la cartella "Esecuzione automatica".
3. Sposta lì dentro il collegamento appena creato.

Così, quando entri nella VPS dopo un riavvio, Kronos parte da solo. Attenzione: parte solo
quando l'utente fa l'accesso, come MT5.

---

## Sicurezza

Il servizio ascolta solo su `127.0.0.1`, cioè **solo dentro la VPS**.
**Non** aprire la porta 8765 nel firewall: non serve, perché i bot che lo usano stanno sulla stessa VPS.

---

## Aggiornare Kronos in futuro

Quando ti dico che c'è una modifica nuova:
```
cd C:\percorso\bot-telegram
git pull
```
Poi chiudi la finestra di `avvia_kronos.bat` e riaprila.

---

## Problemi comuni

| Messaggio | Cosa fare |
|---|---|
| `'python' non è riconosciuto...` | Python non è nel PATH: reinstallalo spuntando "Add python.exe to PATH" (Parte 1) |
| `'git' non è riconosciuto...` | Installa Git (Parte 1) e riapri il CMD |
| `Codice Kronos non trovato` | Manca la Parte 3, punto 3 (`git clone ... Kronos`), oppure l'hai lanciato da un'altra cartella |
| `MT5 initialize fallito` | MetaTrader 5 è chiuso, o `MT5_PATH` nel `.env` è sbagliato |
| `Simbolo ... non trovato` | Il messaggio dice a quale MT5 si è collegato e quali nomi dell'oro ci sono. Se il MT5 è quello giusto, metti uno di quei nomi in `.env` alla riga `KRONOS_SYMBOL=`. Se è quello sbagliato, metti il percorso del MT5 giusto alla riga `MT5_PATH=` |
| VPS lentissima o bloccata | Troppa poca RAM: in `.env` metti `KRONOS_SAMPLES=8` |

Per qualsiasi altro errore, copia il messaggio intero e incollalo a Claude.
