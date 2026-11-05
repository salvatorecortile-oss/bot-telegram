# Sistema licenze FactMachine — Guida venditore

Serve a vendere il bot a licenza: il bot funziona **solo** se la chiave del
cliente è valida e non scaduta, e **solo sul PC** su cui è stata attivata. Tu
crei/revochi le chiavi e decidi la durata (giorno/settimana/mese).

## Come funziona (in breve)

```
  BOT del cliente  ──(chiave + impronta PC)──►  TUO SERVER (VPS)
                   ◄──(valida/scaduta/altro PC, firmato)──
```
- La logica vera sta sul **tuo server** (sulla VPS), non nel file del cliente.
- Ogni chiave si lega al **primo PC** che la attiva (machine-lock): se il cliente
  passa il file a un altro, la stessa chiave **non funziona** sul secondo PC.
- La durata parte dalla **prima attivazione** (es. mensile = 30 giorni da quando
  il cliente la usa la prima volta).

---

## PARTE 1 — Preparare il server (una volta sola, sulla VPS)

### 1. Imposta i due segreti

Apri `server.py` e cambia **questi due valori** (in cima al file) con due
stringhe lunghe e casuali tue:

```python
ADMIN_TOKEN    = "..."   # la tua password per creare/revocare chiavi
SIGNING_SECRET = "..."   # segreto per firmare le risposte
```

> ⚠️ Il **SIGNING_SECRET** deve essere **identico** a quello che metti nel bot
> (`factmachine/license_client.py`). L'**ADMIN_TOKEN** invece resta solo sul
> server e nel tuo pannello admin — non va mai nel bot dei clienti.

### 2. Avvia il server

Sulla VPS, nella cartella `license_server`, apri il CMD e lancia:

```
python server.py
```

Deve stampare `Server licenze FactMachine su http://0.0.0.0:8000`. Lascialo
aperto (o avvialo come servizio, vedi sotto).

### 3. Apri la porta nel firewall della VPS

La porta **8000** deve essere raggiungibile da internet. Su Windows Server, nel
CMD come amministratore:

```
netsh advfirewall firewall add rule name="FactMachine Licenze" dir=in action=allow protocol=TCP localport=8000
```

L'indirizzo del tuo server sarà `http://IP-DELLA-VPS:8000` (sostituisci con l'IP
pubblico della VPS).

### 4. (Consigliato) Tenerlo sempre acceso

Il modo più semplice su Windows: crea un file `avvia_server.bat` con dentro
`python server.py` e mettilo tra i programmi all'avvio, oppure usa l'Utilità di
pianificazione per lanciarlo all'accensione.

---

## PARTE 2 — Creare e gestire le chiavi (pannello admin)

Usa `admin.py` (sulla VPS, o dal tuo PC impostando `FM_SERVER_URL`). Prima
imposta in cima ad `admin.py` lo stesso `ADMIN_TOKEN` del server (e, se lo usi
dal tuo PC, `SERVER_URL = "http://IP-DELLA-VPS:8000"`).

```
# licenza mensile (30 giorni)
python admin.py create --days 30 --note "cliente Mario"

# licenza settimanale
python admin.py create --days 7

# licenza giornaliera
python admin.py create --days 1

# 5 licenze mensili in blocco
python admin.py create --days 30 --count 5

# elenca tutte le licenze e lo stato
python admin.py list

# revoca (blocca subito) una licenza
python admin.py revoke FM-ABCD-EFGH-JKLM

# sblocca il PC legato a una chiave (il cliente ha cambiato computer)
python admin.py reset FM-ABCD-EFGH-JKLM
```

La chiave creata (es. `FM-ABCD-EFGH-JKLM`) è quella che dai al cliente.

---

## PARTE 3 — Preparare il bot per il cliente

### 1. Metti l'indirizzo del server e il segreto nel bot

Apri `factmachine/license_client.py` e imposta:

```python
SERVER_URL     = "http://IP-DELLA-VPS:8000"   # il tuo server
SIGNING_SECRET = "..."                         # LO STESSO del server.py
```

### 2. Compila il bot in .exe (così il cliente non vede/modifica il codice)

Sul PC dove sviluppi, nella cartella `factmachine`:

```
pip install pyinstaller
pyinstaller --onefile --noconsole --name FactMachine dashboard.py
```

Trovi l'eseguibile in `factmachine/dist/FactMachine.exe`. Dai al cliente:
- `FactMachine.exe`
- (il cliente dovrà fare il primo **login** una volta; se usi anche `login.py`,
  compila pure quello, oppure includi le istruzioni)

> Nota: PyInstaller include Playwright, ma il **browser** Chromium va installato
> sul PC del cliente una volta (`playwright install chromium`). In alternativa si
> può preparare un pacchetto che lo include — chiedi se ti serve.

### 3. Come attiva il cliente

- Il cliente avvia il bot. Alla prima apertura chiede la **chiave di licenza**:
  incolla quella che gli hai dato.
- Il bot la salva in `license.key` e la verifica col tuo server ad ogni avvio.
- Se la licenza scade o la revochi, il bot **smette di funzionare**.

---

## Note di sicurezza (onestà)

- Nessun software è inviolabile al 100%. Questo sistema tiene fuori i clienti
  normali e chi condivide i file: la logica è sul tuo server, c'è il blocco per
  PC, la firma anti-manomissione e la scadenza lato server.
- Per alzare ancora la sicurezza puoi mettere il server dietro **HTTPS** (con un
  dominio e un certificato) invece di HTTP. Chiedi se vuoi farlo.
- Non condividere mai `ADMIN_TOKEN` e `SIGNING_SECRET`. Se li cambi, aggiorna
  sia `server.py` sia `license_client.py` (per il SIGNING_SECRET).
