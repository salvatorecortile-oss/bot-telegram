# ScalperM1 — EA MT5 (v3)

Scalper continuo su M1. Funziona su qualsiasi simbolo (XAU, Forex, indici) e si regola da solo: lo attacchi al grafico e parte.

## Come lavora

- **Ingresso:** se la candela M1 in corso sale (scende) e il prezzo sta ancora salendo (scendendo) negli ultimi 3 secondi, apre un BUY (SELL). Lo fa anche più volte nella stessa candela.
- **Direzione favorita (bias):** EMA 9/21 su M1 e conteggio delle candele verdi/rosse sulle ultime 10. Non blocca nulla: rende solo più facile entrare nella direzione favorita e più difficile entrare contro.
- **Stop loss automatico:** 0,5 × la dimensione media delle candele M1 (ATR), minimo 3 × lo spread. Su XAU è circa 0,5 $.
- **Uscita senza TP:**
  - a metà dello SL di profitto va a break-even;
  - poi il trailing chiude appena il prezzo torna indietro;
  - quando il movimento è molto esteso il trailing si stringe.
- **TP fisso:** con `InpExitMode = TP fisso` il TP è uguale allo SL.
- **Spread e slippage automatici:** il bot impara lo spread normale del simbolo e si mette in pausa solo quando è più del doppio (news, rollover).
- **Posizioni multiple:** fino a 3 per direzione. Una nuova si apre solo se le altre della stessa direzione sono già a break-even.
- **Buy e sell insieme** (solo conti hedging): mentre un buy segue la candela, se la candela si è estesa (≥ 0,6 × ATR) e torna indietro dal massimo (≥ 0,2 × ATR, minimo 2 × spread) apre subito un sell, e viceversa. Così quando la candela finisce il sell è già partito. Si spegne con `InpReversal = false`.
- Usa ordini a mercato lanciati dal bot al livello giusto, non ordini pendenti: è più veloce e non lascia ordini dimenticati sul conto.

Tutte le distanze in punti hanno 0 = automatico. Metti un numero solo se vuoi forzarle.

## Dashboard

- Stato: ATTIVO, IN PAUSA (con il motivo) o FERMO.
- P/L netto di oggi, commissioni incluse.
- Trade, vinti, persi e win rate.
- Vincita media e perdita media.
- Posizioni aperte, profitto in corso e saldo.
- Direzione favorita.
- Pulsanti: Start / Start One / Finish / Stop+Close.

## Installazione

1. Copia `ScalperM1_XAU.mq5` in *MQL5/Experts* e compila con F7.
2. Trascinalo sul grafico M1 del simbolo e attiva Algo Trading.
3. Parte da solo.

Prima del conto reale fai un backtest con "Every tick based on real ticks".

---

# StraddleM1 — EA MT5 a ordini pendenti

Replica la logica del bot del video: ordini **BUY STOP** e **SELL STOP** sempre attivi sopra e sotto il prezzo.

- Tiene un **BUY STOP sopra** e un **SELL STOP sotto** il prezzo, a distanza D, ognuno con il suo SL e senza TP.
- **I pendenti inseguono il prezzo:**
  - se il prezzo scende, il BUY STOP scende con lui;
  - se il prezzo sale, il SELL STOP sale;
  - non si spostano mai quando è il prezzo ad andare verso di loro.

  Così scatta solo il lato in cui parte un movimento veloce.
- **Distanze automatiche** dall'ATR M1, cioè dalla dimensione media delle candele:
  - pendenti a 0,50 × ATR (minimo 3 × spread);
  - SL a 0,50 × ATR (minimo 3 × spread), misurato dal prezzo che lo fa scattare, quindi spread escluso;
  - break-even da +0,25 × ATR;
  - trailing a 0,30 × ATR, attivo da +0,40 × ATR.
- **Pendente opposto oltre lo SL:** mentre un BUY è aperto, il SELL STOP sta sotto lo SL del buy, con mezza distanza D di margine. Scatta solo se il buy è già chiuso e il prezzo continua a scendere: niente buy e sell persi insieme sulla stessa oscillazione.
- **Filtro laterale** (`InpBigOnly`), ricalcolato a ogni tick. Servono due condizioni insieme:
  1. **Direzionalità** (Efficiency Ratio di Kaufman sulle ultime 6 candele M1): spostamento netto diviso la somma di tutti i movimenti. In laterale vale circa 0–0,3, in un candelone o in una discesa circa 0,5–1. Serve almeno 0,40.
  2. **Candela grande**: la candela in corso o l'ultima chiusa deve essere almeno 0,8 × la candela media e almeno 6 × spread.

  Se ne manca una, cancella i pendenti e aspetta. Con `InpTrendSide` tiene solo il pendente nella direzione del movimento: in discesa solo SELL STOP, in salita solo BUY STOP.
- **Modalità laterale con i limit** (`InpRangeMode`): quando la direzionalità è sotto 0,25 e il range delle ultime 15 candele è largo almeno 8 × spread, mette un **SELL LIMIT sul massimo** e un **BUY LIMIT sul minimo** del range, con SL appena fuori. Anche questi trade hanno break-even e trailing come quelli con gli stop. Il TP a metà range è opzionale (`InpRangeUseTP`, spento di default). Quando torna il movimento cancella i limit e torna agli STOP. Le posizioni laterali hanno magic + 1 e nel CSV sono segnate "RANGE".
- **Dashboard in primo piano:** il grafico viene messo dietro agli oggetti, così candele e frecce dei trade non coprono più le scritte.
- **2ª posizione nella stessa direzione** (`InpMaxPerDir = 2`): solo quando la prima è già a break-even, così nelle candele lunghe guadagna di più senza rischiare di più.
- **Uscita breakout fallito:** se dopo 20 s il trade non è mai arrivato nemmeno a metà del break-even ed è in perdita, lo chiude subito invece di aspettare lo stop pieno.
- **Filtro orario** (spento di default): due fasce orarie, nell'ora di MT5.
- **Registro CSV:** ogni trade chiuso finisce in `MQL5/Files/StraddleM1_trades.csv` con entrata, uscita, profitto, durata, massimo a favore e contro, e motivo della chiusura.
- **Spread:** con spread anomalo cancella i pendenti e li rimette quando lo spread torna normale.
- **Uscita dal grafico:** se togli l'EA dal grafico cancella i suoi pendenti.

## v9 — conti con spread alto (48 punti)

- **`InpMinATRSpr`**: lavora solo quando la candela media (ATR 30) è almeno *spread × questo valore*. Con spread 48 e valore 6 serve un ATR di almeno 288 punti, così lo spread pesa poco sul movimento. Lo stesso set funziona anche su un conto a 18: la soglia scende da sola a 108.
- **`InpEquityFloor`**: se il capitale scende a questo valore il bot chiude tutto e si ferma, anche dopo un riavvio, finché non premi Start. Non è una garanzia al centesimo: gap e slippage possono portarlo un po' sotto.
- **`InpTestExtraSpread`** (solo nello Strategy Tester): simula punti di spread in più sui tick reali. Ad esempio con 30 i tick Demo2 a 18 diventano un conto a 48. Il bot si comporta come con lo spread largo: entrata, break-even e filtri. Il costo in più però non compare nel report standard: lo trovi nel risultato **Custom** e nella riga `RISULTATO` del journal.
- **Risultato Custom** (ottimizzazione con "Custom max"): profitto meno lo spread simulato, più il rebate stimato (`InpRebatePerLot` × lotti). Un passaggio che tocca il minimo di capitale viene scartato.
- Set: `StraddleM1_XAU_spread48.set` (dal vivo) e `StraddleM1_XAU_spread48_ottimizza.set` (ottimizzazione).

---

# BuySellGrid — griglia buy + sell (ricostruzione di Buysell 2.0)

Ricostruito dai parametri di `buysell2.set` e dagli ordini del report dell'originale. Il file `.ex5` non è stato decompilato. I parametri hanno gli stessi nomi dell'originale, quindi anche il suo `.set` si carica direttamente.

## Come lavora

- **Inizio ciclo:** con nessuna posizione aperta e dentro la finestra oraria, apre un **BUY e un SELL insieme** con `Lots`.
- **Griglia:** un solo buy e un solo sell per livello. Apre un lato quando non ha già una posizione dello stesso tipo a meno di un passo dal prezzo (`MinStep` punti, oppure `MinStepPerc` % con `SType = 1`). Quando il buy chiude in profitto un passo più su, riapre buy e sell insieme, come negli ordini dell'originale. Con `TradingMode = 1` apre solo nella direzione dell'ultimo passo: se sale un buy, se scende un sell.
- **Chiusura singola:** ogni posizione che arriva a `+MinPosProfit` (valuta del conto, swap compreso) si chiude. Con 0,01 lotti sull'oro, 200 punti di passo = 2 $ = `MinPosProfit`.
- **Chiusura del ciclo:** quando la somma di tutte le posizioni arriva a `+MinPosProfit` chiude tutto, perdenti comprese, e riparte subito con una nuova coppia (`ProfitCalcMode`: 0 = solo singole, 1 = solo ciclo, 2 = tutte e due).
- **Stoploss:** perdita del ciclo, in valuta del conto, che chiude tutto. Con `0` non c'è nessuno stop, come nell'originale.
- **Finestra oraria:** da `StartHour` per `time` minuti (1140 = 00:00–19:00, ora del server). Con `CloseOutsideWindow = true` a fine finestra **chiude tutto com'è, anche in perdita**, e riparte il giorno dopo. Sono i gradini in discesa del grafico dell'originale, dove nessuna posizione dura più di 17:36. Con `false` fuori finestra non apre niente ma continua a gestire le posizioni.
- **Lotto** (`LotCalcMode`):
  - 0 = fisso;
  - 1 = `Lots` + `LotsizeIncrement` ogni `LotsizeIncrementMultiple` posizioni già aperte nella stessa direzione;
  - 2 = come 1, con `Lots` per ogni 1.000 di saldo.
  Il limite è `MaxLotsize` (0 = nessun limite).
- **Altro:** `MaxSpread` e `MaxSlippage` in punti, `newBarOnly` apre solo a inizio candela di `Timeframe`. `ExportHistory` salva i deal in `MQL5/Files/BuySellGrid_<simbolo>.csv`.
- **Conto:** funziona solo su conti **hedging**.

`BuySellGrid.set` usa gli stessi valori dell'originale, con lotto fisso (`LotCalcMode = 0`).
