# TelegramMT5Bot1 — versione finale

Bot per:

1. leggere **tutti** i messaggi dal canale Telegram sorgente;
2. copiarli nel canale destinazione;
3. sincronizzare le modifiche del messaggio originale;
4. riconoscere i segnali XAUUSD/GOLD;
5. aprire l'ordine market su MT5 quando il prezzo entra nel range configurato.

## Regole trading attuali

- Simbolo: `XAUUSD-P`
- Lotto: configurato nel `.env`
- Il segnale è composto da **2 messaggi**.
- Messaggio 1 (`Segnale in arrivo long/short GOLD! ...`): apre **immediatamente** a mercato.
- L'entry del messaggio 1 è **solo indicativa** e non viene usata per aspettare il prezzo.
- BUY: usa `ASK`.
- SELL: usa `BID`.
- Messaggio 2: **non apre un nuovo trade**; applica esclusivamente `SL` e `TP1` alla posizione del messaggio 1.
- TP2 viene ignorato.
- La posizione del messaggio 2 viene associata per direzione + entry indicativa del segnale.
- È previsto solo un breve retry per consentire al DB di registrare la posizione appena aperta; non è un retry di ingresso.
- Un edit Telegram: aggiorna solo la copia Telegram, **NON apre un nuovo trade**.

## Prima esecuzione

1. Installa Python 3.13.
2. Installa i requisiti:

```bat
pip install -r requirements.txt
```

3. Copia `.env.example` in `.env`.
4. Inserisci nel `.env`:
   - API hash Telegram
   - login MT5
   - password MT5
   - server MT5
   - eventualmente il percorso del terminale MT5
5. Avvia:

```bat
python main.py
```

### Telegram

La prima volta Telethon può chiedere il login dell'account. La sessione verrà salvata localmente con il nome configurato in `TELEGRAM_SESSION_NAME`.

**Non condividere mai**:
- `.env`
- `*.session`
- API hash
- password MT5

## Test senza ordini

Parser:

```bat
python tests\test_parser.py
```

Database:

```bat
python tests\test_database.py
```

Logica MT5 (senza connessione/ordine):

```bat
python tests\test_mt5_logic.py
```

## Database

Il database è:

`data\copier.db`

La versione finale usa:
- chiave primaria `(source_chat_id, source_message_id)`;
- inserimento idempotente;
- WAL + busy timeout;
- aggiornamenti parziali che non cancellano ticket/deal esistenti.

## Copia Telegram

La copia usa direttamente `client.forward_messages(..., drop_author=True)`.

Non viene più usato:
- `client.rnd_id()`
- `getrandbits()` per costruire manualmente il forward
- fallback "prendi l'ultimo messaggio del canale"

Questo elimina il problema che aveva causato l'errore `TelegramClient has no attribute rnd_id` e soprattutto evita il rischio di associare al DB un messaggio sbagliato.

## Modifiche Telegram

Quando il messaggio sorgente viene modificato:
- viene cercato il mapping nel database;
- viene modificato il messaggio già presente nella destinazione;
- `MessageNotModifiedError` è trattato come operazione già sincronizzata;
- il parser trading NON viene rilanciato;
- non viene aperto un secondo trade.

## Nota importante sulle credenziali

La cartella distribuita intenzionalmente **non contiene password, API hash o sessioni Telegram**. Questo evita di distribuire credenziali operative in chiaro.

Dopo aver configurato `.env`, puoi usare il bot normalmente.
