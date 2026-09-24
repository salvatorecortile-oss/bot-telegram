# Gold MO Bot

Bot Telegram -> MetaTrader 5 per il canale **Gold MO**. Stessa architettura
del bot esistente in questo repository (Telethon + MetaTrader5 + sqlite),
adattata al formato dei segnali di questo provider e con supporto opzionale
a un secondo conto MT5 in parallelo.

## Canali

- Sorgente: `-1002495224665`
- Destinazione: `-1004456671842`

## Regole trading

Il segnale arriva in un **unico messaggio**:

```
Gold buy now 4379.8 - 4376
SL: 4372
TP: 4382
TP: 4384
TP. 4386
TP: 4388
TP: open
```

1. Il bot apre **immediatamente** a mercato (BUY -> ASK, SELL -> BID) **con
   SL e TP3 gia' impostati nello stesso ordine**: la zona di prezzo indicata
   ("4379.8 - 4376") e' solo di riferimento, NON viene usata per
   aspettare o validare il prezzo di ingresso — l'entry reale e' sempre
   il prezzo live MT5 al momento dell'apertura.
   I TP vengono letti in ordine di comparsa (TP1, TP2, TP3, TP4);
   **TP3 e' l'UNICO take profit impostato realmente su MT5**. TP1 resta
   memorizzato solo per il trigger interno del Break Even (punto 3),
   TP2/TP4/"open" sono ignorati.

2. Solo ora, con l'operazione gia' aperta su MT5, il bot pubblica **un
   messaggio** nel canale destinazione con entry reale, SL e un **unico
   TP** (quello operativo, cioe' TP3) — non compare la lista TP1-TP4.

3. Quando il prezzo live raggiunge **TP1**, il bot sposta lo Stop Loss al
   prezzo di apertura (**Break Even**) e aggiorna il messaggio nel canale.

4. La chiusura (a TP3 o a SL) viene rilevata leggendo lo storico MT5 e
   riportata nel messaggio destinazione.

Per robustezza il bot accetta anche gli stessi dati divisi in due
messaggi separati (apertura senza parametri, poi SL/TP in un messaggio
successivo): in quel caso il flusso e' identico ma il messaggio nel
canale parte solo quando arrivano SL/TP.

## Comandi remoti (da "Messaggi Salvati")

Scrivendo a te stesso su Telegram (chat "Messaggi Salvati") con l'account
usato dal bot, sono disponibili questi comandi (prefisso configurabile,
default `bot5_`):

- `bot5_play` — il bot riparte al 100%
- `bot5_stop` — chiude tutte le posizioni (entrambi i conti) e ferma
  completamente il bot (niente ascolto ne' messaggi nel canale)
- `bot5_riavvio` — come `bot5_stop` e subito dopo come `bot5_play`
- `bot5_pausa` — non copia ne' apre nuovi trade, ma i trade gia' aperti
  restano gestiti normalmente (BE/chiusura continuano)
- `bot5_status` — stato attuale + posizioni aperte con il profitto
  flottante
- `bot5_report` / `bot5_reportw` / `bot5_reportm` — invia subito il
  report giornaliero / settimanale / mensile
- `bot5_comandi` — mostra l'elenco comandi

## Automatismi giornalieri (orario Europe/Rome)

- ☀️ 06:00 (lun-ven): messaggio di buongiorno
- 🔒 22:45 (lun-ven): chiusura a mercato di tutte le posizioni aperte
  (entrambi i conti)
- 📊 23:00 (lun-ven): report giornaliero (letto direttamente dallo storico
  MT5 del conto principale)
- 📅 Sabato 10:00: report settimanale
- 🗓️ Ultimo giorno del mese, 23:59: report mensile

Orari personalizzabili nel `.env` (`DAILY_CLOSE_HOUR`, `DAILY_REPORT_HOUR`,
`GOOD_MORNING_HOUR`, `WEEKLY_REPORT_HOUR`, ecc.).

## Recovery automatico all'avvio

Se il bot si riavvia mentre una posizione e' aperta sul conto principale,
al successivo avvio la ritrova sempre: se manca la riga nel database (es.
crash tra apertura e scrittura), la "adotta" e pubblica un nuovo messaggio
nel canale, riprendendo la gestione (BE/chiusura) da li'.

## Secondo conto MT5 (opzionale)

Il bot puo' aprire la stessa operazione anche su un secondo conto MT5, in
parallelo al conto principale, con lo stesso lotto configurato
(`LOT_SIZE`). Per attivarlo:

1. Installa un secondo terminale MetaTrader 5 sulla stessa macchina, in un
   percorso diverso da quello del conto principale.
2. Nel `.env`, imposta `SECOND_ACCOUNT_ENABLED=true` e compila
   `MT5_PATH_2`, `MT5_LOGIN_2`, `MT5_PASSWORD_2`, `MT5_SERVER_2`.

Il secondo conto gira in un processo separato (il modulo Python di MT5
regge una sola connessione attiva per processo): se non e' raggiungibile o
non e' configurato, il bot continua a funzionare normalmente sul solo
conto principale, senza bloccarsi.

## Prima esecuzione

1. Installa Python 3.13.
2. Installa i requisiti:
   ```bat
   pip install -r requirements.txt
   ```
3. Copia `.env.example` in `.env` e compila i valori (API Telegram, MT5
   conto principale, eventualmente secondo conto).
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
