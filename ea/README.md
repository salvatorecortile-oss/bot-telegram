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

# FiboRetraceM1 — EA MT5 ritracciamento di Fibonacci

Lavora su M1 (pensato per XAUUSD, 0,01 lotti). Entra nella direzione dell'impulso quando il prezzo ritraccia sui livelli 0,382, 0,5 e 0,618.

## Come lavora

- **Impulso:** trova l'ultimo swing low e l'ultimo swing high confermati (frattali con `InpSwingDepth` candele per lato).
  - Se il più recente è il massimo, l'impulso è rialzista: Fibonacci dallo swing low allo swing high, cerca BUY.
  - Se il più recente è il minimo, l'impulso è ribassista: Fibonacci dallo swing high allo swing low, cerca SELL.
  - L'impulso deve essere almeno `InpMinLegATR` × ATR M1.
  - Lo disegna sul grafico.
- **Filtro trend** (`InpTrendFilter`):
  - 0 = nessuno;
  - 1 = EMA 50 in salita per i buy, in discesa per i sell;
  - 2 = struttura: massimi e minimi crescenti per i buy, decrescenti per i sell.
- **Ingresso** (`InpEntryMode`):
  - 0 = ordini **limit** sui livelli attivi;
  - 1 = **mercato** appena il prezzo tocca il livello;
  - 2 = mercato dopo una **pin bar** nella zona;
  - 3 = mercato dopo un'**engulfing** nella zona;
  - 4 = mercato dopo **pin bar o engulfing**.
- **Livelli** (`InpLvl382`, `InpLvl500`, `InpLvl618`):
  - un solo livello attivo = un ingresso;
  - più livelli attivi = ingressi **scalati**, uno per livello.
  - Con la candela di conferma apre un trade per conferma, sul livello più profondo raggiunto.
- **SL** sul livello **1.1** di Fibonacci, cioè oltre lo swing low o high di partenza.
- **TP** (`InpTPMode`):
  - rischio/rendimento 1:1, 1:1,5, 1:2 o 1:3;
  - ritorno allo swing (livello 0);
  - estensione −0,272 o −0,618;
  - ATR × `InpTPATRMult`.
- **Annullamento:**
  - se il prezzo fa un nuovo massimo oltre lo swing (o minimo nei sell), aspetta lo swing successivo;
  - se chiude oltre l'inizio dell'impulso o tocca il livello SL, l'impulso non vale più;
  - dopo `InpMaxLegBars` candele l'impulso scade.

  In tutti questi casi i limit non eseguiti vengono cancellati.
- **Orari** (`InpSessMode`, ora di MT5 = italiana + 1):
  - 0 = tutto il giorno;
  - 1 = 10–13 (9–12 italiane);
  - 2 = 15–19 (14–18 italiane);
  - 3 = entrambe le fasce.
- Nessun filtro spread e nessun limite di trade.

## Set

- `FiboRetraceM1_XAU_ottimizza.set`: tutte le combinazioni in un solo file, circa 34.000. Impostazioni:
  - "Algoritmo genetico veloce";
  - criterio **Custom max** (profitto / drawdown; scarta i passaggi con meno di 30 trade);
  - tick reali;
  - forward 1/3.
- `FiboRetraceM1_XAU.set`: impostazione singola, dove copiare il passaggio migliore.

---

# KairosFibo_M1_XAU — Kairos + Fibonacci in un solo bot

Due strategie nello stesso EA, su XAUUSD M1:

| | Fibonacci (mattina) | Kairos RSI (pomeriggio) |
|---|---|---|
| Entrate (ora MT5) | 10:00–13:00 (9–12 italiane) | 13:00–20:00 (12–19 italiane) |
| Logica | pin bar sul ritracciamento 0,5 / 0,618, SL a 1.1, TP RR 1:2, filtro EMA | RSI(28) al rientro da 30/70, TP BUY a RSI 65 e SELL a RSI 50, SL 2,5 × ATR, filtro ATR, chiusura prima del weekend |
| Magic number | 61800 | 54001 |

- Ogni strategia ha il suo magic number e gestisce solo le sue posizioni, esattamente come se fossero due bot separati. Nel report puoi distinguerle dal commento: `FIB500`/`FIB618` per il Fibonacci, `RSI M1` per il Kairos.
- `InpFbOn` e `InpRsOn` accendono o spengono ciascuna strategia.
- Set: `KairosFibo_M1_XAU.set`, con il set 28 per il Fibonacci e il set definitivo per il Kairos. La parte Fibonacci verrà aggiornata con il risultato della fase 2.
- Serve un conto **hedging**.
