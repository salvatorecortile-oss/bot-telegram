# Bot Gold Empire → canale Telegram + MT5

Bot **indipendente**: ha il suo `.env`, la sua sessione Telegram, il suo database
(`data/goldempire.db`), i suoi log (`logs/bot.log`) e un suo MAGIC NUMBER su MT5.

## Cosa fa

| Messaggio del canale "Gold empire signals room" | Azione del bot |
|---|---|
| `SIGNAL N ⬇️ VENDI XAUUSD` / `⬆️ COMPRA XAUUSD` | Apre **subito a mercato** su MT5 con SL = *Stop* e TP = *Obiettivo* (o *Obiettivo 1* se sono più obiettivi). Pubblica nel tuo canale il segnale riformattato con l'**entry reale**. |
| `✅ OBIETTIVO RAGGIUNTO` | Chiude la posizione (se MT5 non l'ha già chiusa al TP) → "TAKE PROFIT RAGGIUNTO" |
| `⚪ STOP A PAREGGIO` | Sposta lo SL al **tuo** prezzo d'ingresso reale → "BE ATTIVATO" |
| `❌ STOP` | Chiude la posizione (se MT5 non l'ha già chiusa allo SL) → "STOP LOSS PRESO" (o "BE PRESO" se era a pareggio) |
| `🏁 CHIUSA` | Chiude subito a mercato → "OPERAZIONE CHIUSA IN PROFITTO / PERDITA" |

- Gli aggiornamenti vengono collegati al segnale tramite la **reply** di Telegram
  (riserva: ultimo `SIGNAL N` ancora aperto). Nel tuo canale escono in reply al segnale copiato.
- BUY e SELL possono essere aperti **contemporaneamente** (serve un conto MT5 *hedging*).
- Se MT5 chiude da solo (TP/SL raggiunto) il bot se ne accorge e pubblica il messaggio, senza doppioni.
- I pip sono calcolati dai prezzi reali MT5 (1 pip = 0,10 $, come il canale).
- Il segnale non viene aperto se il prezzo ha già superato Stop o Obiettivo, o se il messaggio è più vecchio di `MAX_SIGNAL_AGE_SECONDS`.

## Installazione (Windows, nella cartella `goldempire`)

```bat
cd goldempire
pip install -r requirements.txt
copy .env.example .env
```

Compila `.env`:
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` (da https://my.telegram.org)
- `TELEGRAM_SOURCE_CHAT` (canale Gold Empire) e `TELEGRAM_DESTINATION_CHAT` (tuo canale)
  → per trovare gli ID: `python get_chats.py`
- `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`, `MT5_PATH`, `MT5_SYMBOL` (es. `XAUUSD` o `XAUUSD-P` a seconda del broker)
- `LOT_SIZE`

Se MT5 non si connette (rotellina / timeout): `python diagnose_mt5.py` con MT5 aperto e loggato.

Primo login Telegram: `python telegram_login.py` (QR code) oppure direttamente `python main.py` (chiede numero e codice).

> Se usi **lo stesso conto MT5** degli altri bot va bene: il MAGIC NUMBER diverso tiene separate le posizioni.
> Se usi **un altro conto**, serve un'altra installazione del terminale MT5 e il suo percorso in `MT5_PATH`.

## Avvio

```bat
python main.py
```

### Prova senza aprire ordini
Con `TRADING_ENABLED=false` il bot legge il canale e pubblica tutti i messaggi nel tuo canale
usando i prezzi scritti nei messaggi del canale sorgente, **senza** toccare MT5.
Quando è tutto ok metti `TRADING_ENABLED=true`.

## Messaggi programmati (ora italiana)

| Messaggio | Quando |
|---|---|
| Buongiorno | lunedì–venerdì alle 06:00 |
| Report giornaliero | lunedì–venerdì alle 23:00 (operazioni chiuse oggi) |
| Report settimanale | sabato alle 10:00 (operazioni chiuse da lunedì) |
| Report mensile | ultimo giorno del mese alle 23:00 |

Se il PC era spento all'orario previsto, il messaggio parte appena il bot si riavvia (entro 3 ore). Ogni messaggio parte una sola volta.
I testi si modificano in `messages.py`.

## Comandi (scrivili in "Messaggi salvati" di Telegram; prefisso in `COMMAND_PREFIX` del .env, NON usare `bot2_` che è dell'altro bot)

`bot3_play`, `bot3_pausa`, `bot3_stop` (chiude tutte le posizioni del bot e si ferma), `bot3_riavvio` (chiude tutto e riparte), `bot3_status`,
`bot3_report` / `bot3_reportw` / `bot3_reportm` (invia subito il report giornaliero / settimanale / mensile), `bot3_comandi`.

## Test (senza Telegram né MT5)

```bat
python tests\test_parser.py
python tests\test_flow.py
python tests\test_reports.py
```
