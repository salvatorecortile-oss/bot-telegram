# Gold MO Bot

Bot Telegram -> MetaTrader 5 per il canale **Gold MO**. Stessa architettura
del bot esistente in questo repository (Telethon + MetaTrader5 + sqlite),
adattata al formato dei segnali di questo provider e con supporto opzionale
a un secondo conto MT5 in parallelo.

## Canali

- Sorgente: `-1002495224665`
- Destinazione: `-1004456671842`

## Regole trading

Il segnale e' composto da **2 messaggi**:

1. `Gold buy now 4379.8 - 4376` (o `Gold sell now ...`)
   Apre **immediatamente** a mercato (BUY -> ASK, SELL -> BID). La zona di
   prezzo indicata e' solo di riferimento: NON viene usata per aspettare o
   validare il prezzo di ingresso.

2. Messaggio successivo con SL e take profit multipli:
   ```
   SL: 4372

   TP: 4382
   TP: 4384
   TP. 4386
   TP: 4388
   TP: open
   ```
   Applica subito lo SL alla posizione aperta al punto 1. I TP vengono letti
   in ordine di comparsa (TP1, TP2, TP3, TP4); **TP3 e' l'unico take profit
   impostato realmente su MT5**. TP1/TP2/TP4/"open" restano informativi e
   vengono mostrati nel messaggio copiato nel canale destinazione.

3. Quando il prezzo live raggiunge **TP1**, il bot sposta lo Stop Loss al
   prezzo di apertura (**Break Even**). Il messaggio nel canale destinazione
   viene aggiornato in automatico ad ogni passaggio (SL/TP applicati, BE,
   chiusura).

4. La chiusura (a TP3 o a SL) viene rilevata leggendo lo storico MT5 e
   riportata nel messaggio destinazione.

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
4. Login Telegram (una tantum, via QR code):
   ```bat
   python telegram_login.py
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
