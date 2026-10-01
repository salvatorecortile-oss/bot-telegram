# Backtest V-Formation su dati MT5

Backtester in Python della strategia V-Formation. Usa **la stessa logica** dello script TradingView
([`tradingview/v_formation`](../tradingview/v_formation/README.md)), ma gira su **anni di dati** del tuo MT5
e su più coppie in un colpo solo.

> Lo script **scarica solo dati storici**: non invia ordini e non tocca il conto.

## 1. Installazione (una volta sola, sul PC con MT5)

Dalla cartella del bot:

```bat
pip install -r backtest\requirements.txt
```

In MetaTrader 5: **Strumenti → Opzioni → Grafici → "Max barre nel grafico" = Illimitato**.
Altrimenti MT5 restituisce solo le ultime barre. Poi riavvia MT5.

Lo script si collega con le credenziali del file `.env` del bot (`MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`, `MT5_PATH`).
Se non sono impostate, usa il terminale MT5 già aperto.

## 2. Comandi

**Primo test consigliato**: 4 coppie, M5, dal 2021, con il confronto di tutte le varianti e la divisione
in-sample/out-of-sample:

```bat
python backtest\run_vformation.py --symbols EURUSD GBPUSD USDCHF EURGBP --timeframe M5 --from 2021-01-01 --compare --split 2024-01-01
```

> Se il tuo broker usa un suffisso nei simboli (es. `XAUUSD-P`), scrivi i nomi esatti: `--symbols EURUSD-P GBPUSD-P …`

Altri esempi:

```bat
:: solo la configurazione base
python backtest\run_vformation.py --symbols EURUSD

:: cambiare i parametri della base
python backtest\run_vformation.py --symbols EURUSD --set bias_mode=ema htf=1D min_rank=S

:: spread fisso invece di quello storico + slippage sugli stop
python backtest\run_vformation.py --symbols EURUSD --set spread_pips=0.8 slippage_pips=0.3

:: riscaricare i dati (la prima volta vengono salvati in backtest\data_cache)
python backtest\run_vformation.py --symbols EURUSD --refresh
```

| Opzione | Significato |
|---|---|
| `--symbols` | simboli MT5 |
| `--timeframe` | M1, M5, M15, M30, H1, H4 (default M5) |
| `--from` / `--to` | periodo (default dal 2021-01-01 a oggi) |
| `--compare` | confronta le varianti predefinite (vedi sotto) |
| `--split DATA` | risultati separati prima e dopo la data (in-sample / out-of-sample) |
| `--set chiave=valore` | cambia i parametri; elenco in `vformation_engine.py` → `Params` |
| `--server-tz` | fuso orario del server del broker (default `Europe/Athens` = GMT+2/+3, il più comune) |
| `--csv FILE` | usa un CSV (time, open, high, low, close[, spread]) invece di MT5 |

### Varianti di `--compare`

| Nome | Cosa cambia rispetto alla base |
|---|---|
| `base` | default dello script TradingView: bias struttura H1, sessione 9–17, TP1 = massimo V (50%), TP2 = massimo impulso |
| `config_tradingview` | la tua configurazione su TradingView: bias EMA D1, TP1 1R, TP2 2R, gamba destra 23 barre |
| `bias_off` / `bias_ema_D1` / `bias_struttura_H4` | quanto contribuisce il bias |
| `solo_rango_S` | solo V con gamba destra più alta |
| `sweep_asia_o_giorno_prec` | V che prende la liquidità di Asia o del giorno precedente |
| `entry_0.618` | entry più profonda |
| `tp_1R_2R` / `tutto_a_2R` | gestione delle uscite |
| `senza_sessione` | opera a qualsiasi ora |

## 3. Come leggere i risultati

Tutto è espresso in **R**: 1R = il rischio del trade. Un trade che prende lo stop vale −1R,
uno che arriva a un target a 2R vale +2R. Così i risultati non dipendono dal lotto.

| Colonna | Significato |
|---|---|
| `setup` | numero di trade (setup interi, non chiusure parziali come su TradingView) |
| `win %` / `BE %` / `loss %` | trade in profitto, a break-even, in perdita |
| `R medio` | **la metrica principale**: guadagno medio per trade. Sopra +0,15R con i costi reali è interessante |
| `profit factor` | guadagni / perdite. Sopra 1,3 è buono, sotto 1,1 il vantaggio non c'è |
| `max DD R` | massima perdita dal picco, in R |
| `rendimento %` / `max DD %` | simulazione con rischio 1% per trade (0,5% sul rango A) |
| `IS …` / `OOS …` | prima e dopo la data di `--split`. **L'OOS deve restare positivo** |

Sono stampati anche:
- la **diagnostica**, con la stessa logica del pannello di TradingView;
- il dettaglio della prima variante **per simbolo, anno, lato e rango**.

Tutti i file (riepilogo, trade per variante, diagnostica) finiscono in `backtest\results\<data_ora>\`.

**Regole d'oro**
- Una variante è credibile solo se è positiva **su più coppie e su più anni**, non solo in totale.
- Se una variante va bene in-sample ma male out-of-sample, è **overfitting**.
- Servono almeno 100–200 setup per trarre conclusioni.

## 4. Differenze rispetto a TradingView

- **Spread reale**: le barre MT5 sono prezzi BID. I long entrano all'ASK (BID + spread storico della barra)
  e gli short escono all'ASK. TradingView invece ignora lo spread.
- Le **chiusure parziali** sono contate dentro lo stesso setup: un trade = un setup.
- Dentro la barra il prezzo segue lo stesso percorso ipotizzato da TradingView (prima l'estremo più vicino all'apertura).
- Se sono pendenti un long e uno short, quando uno entra l'altro non può più entrare (niente inversioni).

## 5. Test

```bat
python backtest\test_vformation.py
```

Verificano su prezzi costruiti a mano: entry al 50%, TP1/TP2, simmetria long/short, V non confermata,
effetto dello spread e filtro di bias.
