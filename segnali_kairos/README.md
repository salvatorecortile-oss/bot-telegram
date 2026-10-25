# Sala segnali Kairos: MT5 → canale Telegram

Bot **a parte**: ha il suo `.env`, la sua sessione Telegram, il suo database (`data/segnali.db`) e i suoi log (`logs/segnali.log`).

Legge le operazioni che il **Kairos Trading Bot** apre su MetaTrader 5 (magic **61800** e **54001**) e le pubblica nel tuo canale. **Non apre, non modifica e non chiude niente**: legge e basta.

## Messaggi nel canale

| Su MT5 | Nel canale |
|---|---|
| Si apre una posizione | `👑 XAUUSD — BUY/SELL` con ENTRY, STOP LOSS e TAKE PROFIT (senza TP: "chiusura a segnale") |
| Cambia il TP | `🎯 TP IMPOSTATO A …` (in reply) |
| Lo SL va all'ingresso o in profitto | `🟢 BE ATTIVATO` (in reply) |
| Cambia lo SL | `🛡️ STOP LOSS IMPOSTATO A …` (in reply) |
| Chiusa al TP | `🟢 TAKE PROFIT RAGGIUNTO` con i pips (in reply) |
| Chiusa allo SL | `🛑 STOP LOSS PRESO` con i pips, oppure `BE PRESO` dopo il BE (in reply) |
| Chiusa dal bot | `✅ OPERAZIONE CHIUSA IN PROFITTO` / `❌ … IN PERDITA` con i pips (in reply) |

- Gli aggiornamenti escono in reply al messaggio di apertura, senza notifica.
- All'avvio le posizioni già aperte vengono pubblicate solo se aperte da meno di 5 minuti (`MAX_OPEN_AGE_SECONDS`). Le altre vengono seguite in silenzio, così dopo un riavvio non escono doppioni.
- Se MT5 per un attimo non risponde, nessuna posizione viene considerata chiusa.
- Con `MAGIC_NUMBERS=` vuoto pubblica **tutte** le operazioni del conto, anche quelle aperte a mano o da altri bot.

I testi si modificano in `messages.py`.

## Messaggi programmati (ora italiana)

| Messaggio | Quando |
|---|---|
| Buongiorno | lunedì–venerdì alle 06:00 |
| Report giornaliero | lunedì–venerdì alle 23:00 (operazioni chiuse oggi) |
| Report settimanale | sabato alle 10:00 (operazioni chiuse da lunedì) |
| Report mensile | ultimo giorno del mese alle 23:00 |

I report contano solo le operazioni pubblicate nel canale. Se il PC era spento all'orario previsto, il messaggio parte appena il bot si riavvia (entro 3 ore). Ogni messaggio parte una sola volta.

## Comandi (scrivili nei tuoi "Messaggi salvati" su Telegram)

| Comando | Cosa fa |
|---|---|
| `segnali_play` | Pubblica di nuovo le operazioni |
| `segnali_pausa` | Smette di pubblicare le nuove operazioni (MT5 lavora normalmente) |
| `segnali_status` | Stato + posizioni aperte con il profitto di ciascuna |
| `segnali_report` / `segnali_reportw` / `segnali_reportm` | Invia subito il report giornaliero / settimanale / mensile |
| `segnali_comandi` | Elenco dei comandi |

## Installazione (Windows, nella cartella `segnali_kairos`)

```bat
cd segnali_kairos
pip install -r requirements.txt
copy .env.example .env
```

Compila `.env`:
1. **`TELEGRAM_API_ID` e `TELEGRAM_API_HASH`** da https://my.telegram.org. Puoi usare gli stessi degli altri bot: la sessione è separata.
2. **`TELEGRAM_DESTINATION_CHAT`**: l'ID della sala segnali. Lo trovi con `python get_chats.py`. Il tuo account deve essere amministratore del canale.
3. **MT5:** il terminale dove gira il Kairos Trading Bot deve essere aperto e loggato. Se c'è un solo MT5 basta `MT5_PATH`.

Primo login Telegram: `python telegram_login.py` (QR code), oppure direttamente `python main.py` (chiede numero e codice).

## Avvio

```bat
python main.py
```

Il PC (o la VPS) con MT5 deve restare acceso, come per il bot.

## Test

```bat
python -m unittest discover -s tests
```
