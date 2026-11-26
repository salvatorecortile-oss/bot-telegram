# Kronos – previsioni sulle candele (XAUUSD da MT5)

Servizio **indipendente** dagli altri bot. Legge le ultime candele da MetaTrader 5,
le passa a **Kronos** (modello AI open source addestrato su 12 miliardi di candele,
[GitHub shiyu-coder/Kronos](https://github.com/shiyu-coder/Kronos), licenza MIT)
e restituisce una **previsione delle prossime candele**.

**Non apre ordini.** Restituisce solo numeri e un testo. Collegarlo a un bot che opera
è un passo successivo, da fare solo dopo averlo verificato su conto demo.

## Cosa calcola

Kronos genera tanti **scenari** possibili per le prossime candele (di default 20 scenari
per 12 candele). Da questi scenari ricava:

| Campo | Significato |
|---|---|
| `upside_probability` | % di scenari che chiudono **sopra** l'ultimo prezzo |
| `volatility_up_probability` | % di scenari con volatilità **più alta** delle ultime candele |
| `mean_final_close` | prezzo medio previsto alla fine |
| `p10_final_close` / `p90_final_close` | intervallo "probabile" (10% – 90%) |
| `bias` | `RIALZO` se rialzo ≥ 65%, `RIBASSO` se ≤ 35%, altrimenti `NEUTRO` |

Il calcolo si rifà solo quando chiude una nuova candela. Fino ad allora il servizio
risponde subito con l'ultimo risultato (`"cached": true`).

## Quando fa le previsioni

- **`python main.py --once`**: una sola previsione, poi si chiude.
- **`python main.py`** (o `avvia_kronos.bat`): servizio sempre acceso. Ogni 30 secondi controlla
  se è chiusa una nuova candela del timeframe scelto (M15 di default). Quando succede, fa
  **da solo** la previsione e la salva nel **registro di verifica**. Con M15 sono circa 4
  previsioni all'ora, 96 al giorno. Nel weekend, a mercato chiuso, non fa nulla.
  Si spegne con `KRONOS_AUTO=false` nel `.env`.
- Gli altri bot possono comunque chiedere una previsione quando vogliono (vedi sotto).

## Registro di verifica

Ogni previsione automatica viene salvata in `data/kronos.db`. Quando sono passate le
candele previste (12 candele = 3 ore su M15), il servizio legge il prezzo vero da MT5
e controlla se Kronos ci aveva preso. Le candele si contano una per una, quindi il weekend
non falsa il conto.

Per vedere i risultati:
```
python report.py
python report.py --giorni 7
```
oppure nel browser: `http://127.0.0.1:8765/stats`

| Riga del report | Come leggerla |
|---|---|
| RIALZO / RIBASSO x/y corretti | quante volte, quando ha dato quel segnale, il prezzo è andato davvero in quella direzione |
| Direzione della maggioranza | precisione su tutte le previsioni; **50% = come tirare una moneta** |
| Dentro il range 10-90% | quante volte il prezzo vero è finito nell'intervallo previsto (ideale circa 80%) |
| Errore medio | distanza media in $ tra il prezzo medio previsto e il prezzo vero |
| Brier | qualità delle probabilità: più basso è meglio, 0.25 = moneta |

Servono **almeno 100-200 previsioni verificate** (2-3 giorni di mercato su M15) prima di
trarre conclusioni.

## Backtest (verifica sul passato)

Per non aspettare giorni, `backtest.py` usa le candele passate di MT5. In tanti
momenti del passato fa fare a Kronos la previsione usando **solo** le candele fino a
quel momento, e la confronta subito con quello che è successo dopo. Non apre ordini.

```
python backtest.py                 (300 prove, una ogni ora su M15)
python backtest.py --prove 100     (prova veloce)
python backtest.py --prove 1000    (più affidabile, più lento)
```

Opzioni: `--passo` (ogni quante candele fare una prova, default 4), `--scenari` (default 10),
`--candele-future` (default 12), `--symbol`, `--timeframe`.

Alla fine stampa lo stesso report del registro, più due confronti:
- la regola semplice "continua come le ultime 12 candele": Kronos deve fare **meglio** di questa;
- quante volte l'oro è salito nel periodo: se è molto lontano dal 50%, il periodo era in forte
  tendenza e i numeri vanno presi con cautela.

Salva anche tutte le prove, una per una, in `data/backtest_....csv`, da aprire con Excel.

## Installazione (una volta sola, nel CMD di Windows)

> **Sulla VPS** segui la guida completa: [`GUIDA_VPS.md`](GUIDA_VPS.md).

```
cd C:\percorso\bot-telegram\kronos
pip install -r requirements.txt
git clone https://github.com/shiyu-coder/Kronos.git Kronos
copy .env.example .env
```

Al primo avvio i pesi del modello (alcune centinaia di MB) vengono scaricati da
HuggingFace e poi restano salvati sul PC.

## Uso

Con MetaTrader 5 aperto:

```
python main.py --once
```
stampa una sola previsione e chiude. Fai questo per la prima prova.

```
python main.py
```
avvia il **servizio** (lascia la finestra aperta). In alternativa fai doppio clic su
`avvia_kronos.bat`, che lo riavvia da solo se si ferma. Gli altri bot del PC lo interrogano a:

- `http://127.0.0.1:8765/forecast?symbol=XAUUSD&timeframe=M15` → risposta JSON
- `http://127.0.0.1:8765/forecast?symbol=XAUUSD&timeframe=M15&format=text` → testo pronto per Telegram
- `http://127.0.0.1:8765/stats` → risultati del registro di verifica
- `http://127.0.0.1:8765/health` → controlla che sia acceso

Parametri facoltativi: `pred_len` (candele future, 1-120), `samples` (scenari, 1-100),
`force=1` (ricalcola anche se la candela non è cambiata).
Timeframe accettati: M1, M5, M15, M30, H1, H4, D1.

Come leggerlo da un altro programma Python: vedi `client_example.py`.

Il servizio ascolta **solo sul tuo PC** (127.0.0.1). Non è raggiungibile da internet.

## Impostazioni (`.env`)

Vedi `.env.example`. Le più utili:
- `KRONOS_TIMEFRAME` (default M15), `KRONOS_PRED_LEN` (12), `KRONOS_SAMPLES` (20)
- `KRONOS_MODEL`: `NeoQuasar/Kronos-small` (default) o `NeoQuasar/Kronos-base` (più lento)
- `KRONOS_BULLISH_THRESHOLD` / `KRONOS_BEARISH_THRESHOLD`: soglie per RIALZO/RIBASSO

Senza scheda video NVIDIA il calcolo gira sul processore e può richiedere da qualche
secondo a un minuto. Se è troppo lento, abbassa `KRONOS_SAMPLES`.

## Test (senza MT5 e senza modello)

```
python tests/test_forecast.py
```

## Avvertenze

- È una **previsione statistica**: Kronos non "sa" dove andrà l'oro. Nei test degli
  autori è buono soprattutto su volatilità e andamento generale, non sulla singola candela.
- Il modello è addestrato soprattutto su azioni e cripto. Su XAUUSD va verificato con i
  tuoi dati prima di fidarsi.
