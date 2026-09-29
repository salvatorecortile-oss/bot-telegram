# Gold MO Bot

Bot Telegram -> MetaTrader 5 per il canale **Gold MO**. Stessa architettura
del bot esistente in questo repository (Telethon + MetaTrader5 + sqlite),
adattata al formato dei segnali di questo provider. Un solo conto MT5.

## Canali

- Sorgente: `-1002495224665`
- Destinazione: `-1004456671842`

## Regole trading

Il segnale arriva in **due messaggi separati**:

1. `Gold buy now 4379.8 - 4376` (o `Gold sell now ...`)
   Il bot apre **immediatamente e silenziosamente** a mercato (BUY -> ASK,
   SELL -> BID): nessun messaggio viene ancora pubblicato nel canale
   destinazione. La zona di prezzo indicata e' solo di riferimento, NON
   viene usata per aspettare o validare il prezzo di ingresso — l'entry
   reale e' sempre il prezzo live MT5 al momento dell'apertura.

2. Un messaggio successivo con SL e i take profit:
   ```
   SL: 4372
   TP: 4382
   TP: 4384
   TP. 4386
   TP: 4388
   TP: open
   ```
   Applica subito SL e **TP3** (l'UNICO take profit impostato realmente su
   MT5) alla posizione aperta al punto 1, e **solo ora** pubblica **un
   messaggio principale** nel canale destinazione con entry reale, SL e
   un **unico TP** (il valore di TP3) — non compare la lista TP1-TP4.
   TP2/TP4/"open" sono ignorati.

   **Importante**: questo secondo messaggio a volte ripete anche la riga
   "Gold buy/sell now ..." insieme a SL/TP (un "rilancio" del segnale
   completo). Il bot lo riconosce comunque come completamento del trade
   gia' aperto al punto 1 — la presenza di SL/TP ha sempre la priorita' e
   NON viene mai aperta una seconda posizione duplicata.

3. La chiusura (a TP3 o a SL) viene rilevata leggendo lo storico MT5 e
   notificata con un **messaggio separato** (in risposta al messaggio
   principale, che non viene mai modificato): **"TAKE PROFIT
   RAGGIUNTO"** o **"STOP LOSS PRESO"** seguito dai **PIPS** realizzati
   (calcolati con il pip_size reale del simbolo letto da MT5) — non
   viene mostrato il prezzo di chiusura.

Nessun Break Even: SL e TP restano esattamente quelli inviati da Gold MO
per tutta la durata del trade, senza alcuna gestione automatica
intermedia.

4. In qualsiasi momento dopo l'apertura, un messaggio del tipo:
   ```
   Move SL to 4149.4
   ```
   sposta lo Stop Loss del trade aperto al prezzo indicato (il TP
   operativo non cambia) e invia un **messaggio separato** di conferma
   ("STOP LOSS SPOSTATO" + nuovo valore), sempre in risposta al
   messaggio principale.

Per ogni trade il canale riceve quindi il messaggio principale
(entry/SL/TP), eventuali messaggi "STOP LOSS SPOSTATO" e infine quello di
chiusura. Nessuno di questi viene mai editato dopo l'invio (l'unica
eccezione e' una correzione dei parametri iniziali arrivata prima della
chiusura del trade).

## Comandi remoti (da "Messaggi Salvati")

Scrivendo a te stesso su Telegram (chat "Messaggi Salvati") con l'account
usato dal bot, sono disponibili questi comandi (prefisso configurabile,
default `bot5_`):

- `bot5_play` — il bot riparte al 100%
- `bot5_stop` — chiude tutte le posizioni e ferma completamente il bot
  (niente ascolto ne' messaggi nel canale)
- `bot5_riavvio` — come `bot5_stop` e subito dopo come `bot5_play`
- `bot5_pausa` — non copia ne' apre nuovi trade, ma i trade gia' aperti
  restano monitorati (la chiusura continua a essere rilevata e notificata)
- `bot5_status` — stato attuale + posizioni aperte con il profitto
  flottante
- `bot5_report` / `bot5_reportw` / `bot5_reportm` — invia subito il
  report giornaliero / settimanale / mensile
- `bot5_comandi` — mostra l'elenco comandi

## Automatismi giornalieri (orario Europe/Rome)

- ☀️ 06:00 (lun-ven): messaggio di buongiorno
- 🔒 22:45 (lun-ven): chiusura a mercato di tutte le posizioni aperte
- 📊 23:00 (lun-ven): report giornaliero (letto direttamente dallo storico
  MT5)
- 📅 Sabato 10:00: report settimanale
- 🗓️ Ultimo giorno del mese, 23:59: report mensile

Orari personalizzabili nel `.env` (`DAILY_CLOSE_HOUR`, `DAILY_REPORT_HOUR`,
`GOOD_MORNING_HOUR`, `WEEKLY_REPORT_HOUR`, ecc.).

## Recovery automatico all'avvio

Se il bot si riavvia mentre una posizione e' aperta, al successivo avvio
la ritrova sempre: se manca la riga nel database (es. crash tra apertura
e scrittura), la "adotta" e pubblica un nuovo messaggio nel canale,
riprendendo il monitoraggio (rilevamento chiusura) da li'.

## Prima esecuzione

1. Installa Python 3.13.
2. Installa i requisiti:
   ```bat
   pip install -r requirements.txt
   ```
3. Copia `.env.example` in `.env` e compila i valori (API Telegram, MT5).
4. Login Telegram (una tantum), via QR code:
   ```bat
   python telegram_login.py
   ```
   oppure, se preferisci numero di telefono + codice:
   ```bat
   python telegram_login_phone.py
   ```
5. Avvia il bot:
   ```bat
   python main.py
   ```

**Non condividere mai** `.env`, `*.session`, API hash, password MT5.

## Test senza ordini

```bat
python test_parser.py
```
