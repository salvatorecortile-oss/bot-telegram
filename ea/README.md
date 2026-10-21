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

# LiquiditySweep_XAU — EA MT5 sweep di liquidità (D1 + Asia)

Un solo bot che segue **4 livelli** contemporaneamente:

| Livello | Cos'è | Setup |
|---|---|---|
| `PDL` | minimo di ieri (D1) | BUY |
| `PDH` | massimo di ieri (D1) | SELL |
| `AsiaL` | minimo del range Asia | BUY |
| `AsiaH` | massimo del range Asia | SELL |

Il range Asia va dalle 01:00 alle 08:00 ora di MT5, cioè dalle 00:00 alle 07:00 italiane. Si calcola solo a sessione chiusa, quindi i livelli Asia sono attivi dalle 08:00 di MT5.

## Modalità di entrata (`InpEntryMode`, dalla v2.00)

| Valore | Modalità | Entrata |
|---|---|---|
| 0 | Sweep M5 | logica descritta sotto (chiusura M5 oltre il livello e poi rientro) |
| 1 | RSI M1 + sweep (default) | RSI(28) su M1. **BUY:** l'RSI scende a 30 o sotto e poi una candela M1 chiude con l'RSI di nuovo sopra 30. In quel tratto il prezzo deve aver superato al ribasso un minimo (PDL o AsiaL) e la candela deve chiudere sopra quel livello. **SELL:** stessa logica con 70 e un massimo (PDH o AsiaH). |
| 2 | Solo RSI M1 | come la 1, ma senza bisogno di livelli |

Nelle modalità RSI lo SL va oltre l'estremo del tratto in cui l'RSI è stato oltre 30/70, con lo stesso margine (punti + ATR M5). Valgono gli stessi filtri: sessioni, SL massimo, trade al giorno, spread, trend. Set: `LiquiditySweep_XAU_rsi.set`; per l'ottimizzazione `LiquiditySweep_XAU_rsi_ottimizza.set`.

## Come lavora (esempio BUY sul minimo)

1. **Sweep:** una candela M5 **chiude sotto** il livello. Il bot registra il minimo più basso raggiunto (wick compresi).
2. **Conferma:** entro **12 candele M5** (1 ora) una candela M5 **chiude di nuovo sopra** il livello. Alla chiusura di quella candela il bot apre un **BUY a mercato**.
3. **SL:** sotto il minimo dello sweep, più un margine di 20 punti + 0,3 × ATR M5 (`InpSLBufferATR`). Il margine serve a non farsi prendere dal secondo sweep.
4. **TP:** 2 volte il rischio (RR 1:2).

Per il SELL sul massimo la logica è la stessa, specchiata.

## Nessun trade quando

- lo sweep va troppo oltre il livello: più di 2 × ATR M5 (`InpMaxDepthATR`). È una rottura vera.
- il prezzo resta fuori più di 12 candele M5. Anche questa è una rottura vera: il livello torna valido solo dopo un rientro, e quel rientro non apre trade.
- lo SL risulterebbe più lontano di 4 × ATR M5 (`InpMaxSLATR`). Si può impostare anche un limite in punti (`InpMaxSLPts`).
- il rientro avviene fuori dalle sessioni: Londra 10:00–14:00 e New York 15:30–19:00, ora di MT5.
- c'è già un trade aperto sullo stesso livello, oppure il livello ha già fatto 3 trade oggi.
- due livelli confermano sulla stessa candela nella stessa direzione (per esempio PDL e minimo Asia molto vicini): apre un solo trade.
- lo spread è sopra 60 punti.
- (opzionale, `InpTrendEMA` > 0) il trade va contro il trend D1, cioè contro la posizione della chiusura di ieri rispetto all'EMA D1.

Il break-even è spento (`InpBreakEvenR = 0`). Mettendo per esempio `1.0`, lo SL va a entrata + 10 punti quando il trade è a +1R.

Sul grafico disegna i livelli: D1 con linee rosse continue, Asia con linee blu tratteggiate. In alto a sinistra mostra lo stato di ogni livello.

## Installazione e backtest

1. Copia `LiquiditySweep_XAU.mq5` in *MQL5/Experts* e compila con F7.
2. Trascinalo sul grafico **M5** di XAUUSD e carica `LiquiditySweep_XAU.set`.
3. Fai un backtest con "Every tick based on real ticks" prima del conto reale.
4. Per l'ottimizzazione carica `LiquiditySweep_XAU_ottimizza.set` (algoritmo genetico, forward 1/3).
