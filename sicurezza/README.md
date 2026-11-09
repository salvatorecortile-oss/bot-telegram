# Bot Sicurezza → controllo iscritti (sala elite + canale)

Bot **indipendente**: ha il suo `.env`, le sue sessioni Telegram, i suoi report (`report/`) e i suoi log (`logs/`).
Non tocca MetaTrader e non c'entra con gli altri bot.

Ha due parti, si possono usare separatamente:

| Parte | Comando | Cosa fa |
|---|---|---|
| **Report sospetti** (iscritti già dentro) | `python scansione.py` | Legge gli iscritti della sala elite e del canale, dà a ognuno un punteggio di sospetto e salva un file Excel (CSV) in `report/`. **Non elimina nessuno.** |
| **Guardiano** (chi entra da ora in poi) | `python guardiano.py` | Chi chiede di entrare riceve in privato un captcha ("premi la MELA"). Se risponde bene entra, altrimenti la richiesta viene rifiutata. Ti avvisa in privato. |

## 1. Installazione (Windows, nella cartella `sicurezza`)

```bat
cd sicurezza
pip install -r requirements.txt
copy .env.example .env
```

Compila `.env`:
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` (da https://my.telegram.org, vanno bene quelli degli altri bot)
- `TELEGRAM_CHATS`: ID della sala elite e del canale separati da virgola → per trovarli: `python get_chats.py`
  (al primo avvio chiede numero di telefono e codice Telegram; alla fine stampa anche **il tuo ID**)
- `NOMI_PROTETTI`: nomi da proteggere dalle imitazioni, es. `Sala Elite` (il tuo nome è già incluso)

## 2. Report degli iscritti sospetti

```bat
python scansione.py
```

Devi essere **admin** della sala e del canale. Alla fine trovi il file `report\report_AAAAMMGG_HHMM.csv`:
aprilo con Excel (doppio clic). Il file contiene dati personali degli iscritti: non condividerlo.

Se il bot scrive *"Telegram ne ha dati solo una parte"* (succede con i canali grandi), usa la ricerca lettera per lettera, che è più lenta:

```bat
python scansione.py --approfondita
```

### Come leggere il report

Le righe sono già ordinate: in alto i più sospetti, in fondo i conosciuti.

| Livello | Significato |
|---|---|
| **ALTO** (60-100) | Molto sospetto: account eliminato, bot, segnalato da Telegram come truffa/falso, imitazione del tuo nome, profilo vuoto + account nuovo... |
| **MEDIO** (30-59) | Da guardare: es. niente foto e niente username |
| **BASSO** (0-29) | Sembra una persona normale |
| **CONOSCIUTO** | Hai una **chat privata** con questa persona o è nei tuoi **contatti**. Non viene mai segnato come sospetto, anche se non entra su Telegram da tempo. Il punteggio resta visibile. |

Cosa fa salire il punteggio (la colonna *Motivi* dice quali valgono per ogni persona):

| Motivo | Punti |
|---|---|
| Account eliminato / è un bot | +100 |
| Segnalato da Telegram come truffa (scam) o falso (fake) | +80 |
| Possibile imitazione di un nome protetto (es. "Sala Elite Support") | +50 |
| Account limitato da Telegram / link o @ nel nome | +40 |
| Parole da spam nel nome (admin, support, crypto, giveaway, ...) | +25 |
| Nessuna foto profilo | +20 |
| Nome fatto solo di emoji/simboli | +15 |
| Account creato di recente (stima dall'ID) | +15 |
| Non si collega da molto tempo (o lo nasconde) | +15 |
| Nessun username | +10 |
| Profilo vuoto (niente foto e niente username) | +10 |
| Username con tanti numeri | +10 |
| Ultimo accesso nell'ultimo mese | +5 |
| Telegram Premium | −20 |
| Account verificato | −50 |

> Il punteggio è solo un **aiuto**: nessun sistema riconosce al 100% una persona vera.
> Molte persone vere non hanno foto o nascondono l'ultimo accesso. Decidi tu chi rimuovere.
> Per rimuovere qualcuno: apri il profilo dal link nel report → nel canale/sala → *Rimuovi*.

## 3. Guardiano: captcha per chi entra (facoltativo)

Oggi i tuoi link d'invito fanno entrare **subito**: in quel caso nessun bot può fermare chi entra.
Il guardiano funziona solo con un link che ha **"Richiedi approvazione admin"** attivo.

### Una volta sola
1. Su Telegram apri **@BotFather** → `/newbot` → scegli nome e username → copia il **token** in `BOT_TOKEN` nel `.env`.
2. Nel `.env` metti `ADMIN_USER_ID` = il tuo ID (lo stampa `python get_chats.py`).
3. Apri il tuo bot su Telegram e premi **Avvia** (`/start`): così può mandarti gli avvisi.
4. In **sala elite** e **canale** → *Gestisci* → *Amministratori* → *Aggiungi admin* → cerca il tuo bot.
   Lascia attivo almeno **"Invita utenti tramite link"** (o "Aggiungi iscritti"). Gli altri permessi puoi toglierli.
5. Sempre lì → *Link d'invito* → *Crea un nuovo link* → attiva **"Richiedi approvazione admin"** → salva.
   Usa **questo** link per i nuovi iscritti.
6. Facoltativo: **revoca il vecchio link** (chi è già dentro resta dentro). Se non lo revochi, chi usa il vecchio link entra ancora senza captcha.

### Avvio

```bat
python guardiano.py
```

Deve restare aperto (come gli altri bot). Su VPS/PC che resta acceso puoi usare invece
`avvia_guardiano.bat` (doppio clic): se il guardiano si ferma, riparte da solo dopo 10 secondi. Cosa succede:
- La persona clicca il link → *"Richiesta inviata"* → il bot le scrive in privato: *"Premi: MELA"* con 6 pulsanti emoji (testo in italiano e inglese).
- **Pulsante giusto** → la richiesta viene **approvata** e la persona entra. Tu ricevi l'avviso con il punteggio di sospetto.
- **Sbagliato** → può riprovare (`CAPTCHA_TENTATIVI`, default 2). Finiti i tentativi la richiesta viene **rifiutata**.
- **Nessuna risposta** entro `CAPTCHA_TIMEOUT_SECONDS` (default 60 secondi) → **rifiutata**.
- Chi viene rifiutato può riprovare cliccando di nuovo il link.
- Se hai creato il file `benvenuto.txt`, dopo il captcha superato il bot manda in privato **il tuo messaggio di benvenuto** (vedi sotto).
- Se il guardiano è spento, le richieste restano in attesa: le approvi tu a mano dal canale (*Richieste di accesso*).
- Se il bot non riesce a scrivere alla persona, la richiesta resta in attesa e ti avvisa: decidi tu.

### Messaggio di benvenuto personale (facoltativo)

Dopo il captcha superato il bot può mandare in privato un tuo messaggio (regole, link utili, avvisi anti-truffa...).

```bat
copy benvenuto.esempio.txt benvenuto.txt
notepad benvenuto.txt
```

Scrivi il testo come un messaggio normale: a capo, emoji e link funzionano.
- `{nome}` viene sostituito con il nome della persona, `{chat}` con il nome della community.
- Le righe che iniziano con `#` sono note e non vengono mandate.
- Puoi cambiarlo anche con il guardiano acceso: viene riletto ogni volta.
- Se `benvenuto.txt` non c'è o è vuoto, nessun messaggio.
- Il messaggio parte **prima** dell'approvazione: finché la richiesta è aperta Telegram permette al bot di scrivere.
  Non alzare `CAPTCHA_TIMEOUT_SECONDS` sopra 240 (4 minuti): Telegram dà al bot circa 5 minuti per scrivere a chi ha fatto richiesta.

> Il bot può scrivere in privato **solo** a chi chiede di entrare (o a chi gli scrive /start).
> Non può mandare messaggi agli iscritti già presenti: è una regola di Telegram contro lo spam.

Log in `logs\guardiano.log`.

## Test (senza Telegram)

```bat
python tests/test_analisi.py
python tests/test_captcha.py
python tests/test_report.py
python tests/test_benvenuto.py
```
