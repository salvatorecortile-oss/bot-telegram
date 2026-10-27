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

# GoldTitan — rottura originale e invertita

- `GoldTitan_Trio.mq5`: versione attuale (1.12) con tre strategie: RSI+EMA, Rottura e Range asiatico.
- `GoldTitan_BreakoutReverse.mq5`: contiene solo la Rottura invertita, con SL 300 e TP 200.
- `GoldTitan_BreakoutDuo.mq5`: fa girare **insieme** la Rottura originale e quella invertita, ognuna con il suo magic number (20261010 e 20261011).
  - Il segnale e i filtri sono gli stessi per le due versioni.
  - Pausa e risultati sono separati.
  - Serve un conto **hedging**.
  - Con `InpMirror = true` l'invertita usa SL e TP scambiati rispetto all'originale.
- `GoldTitan_BreakoutDuo_ottimizza.set`: ottimizzazione su SL, TP, ADX minimo e ATR minimo (300 combinazioni) con criterio "Custom max".
  - `InpOptTarget` sceglie cosa massimizzare: totale, solo originale, solo invertita, oppure invertita meno originale.
  - A fine ottimizzazione il confronto di tutte le combinazioni è in `Common\Files\GoldTitan_BreakoutDuo_opt.csv`. Il file è separato da `;` con la virgola come decimale, quindi si apre direttamente con Excel in italiano.
  - Per ogni combinazione mostra trade, vinti, netto, profit factor e drawdown di entrambe le versioni, poi la differenza e quale versione è migliore.

---

# GoldTitan Quattro: Trio + Fibonacci

`GoldTitan_Quattro.mq5` mette nello stesso EA le tre strategie di GoldTitan Trio 1.12 e la strategia Fibonacci di `Kairos_Fibonacci_M1_XAU.mq5`.

**Le quattro strategie**

| Strategia | Timeframe | Magic number |
|---|---|---|
| RSI+EMA | M5 | 20261006 |
| Rottura | M15 | 20261007 |
| Range asiatico | M5 | 20261008 |
| Fibonacci | M1 | 61800 |

- Ognuna si accende o si spegne con il suo input: `InpUseRsi`, `InpUseBrk`, `InpUseAsia`, `InpUseFib`.
- Tutte aprono con lo stesso lotto, `InpLots`, che è 0.01 nei set.

**Logica**

- RSI, Rottura e Asia funzionano esattamente come nel Trio: filtri H1, ADX, ATR giornaliero, spread, notizie USD e pausa dopo 4 stop.
- Il Fibonacci funziona esattamente come nel bot Kairos, versione C. I valori di default sono quelli di `Kairos_Fibonacci_M1_XAU.set`: entra dalle 10:00 alle 12:00 ora del server FPG su MT5.
- Il Fibonacci non conta per la pausa del Trio e non la subisce.
- Il Fibonacci ignora il filtro notizie, a meno che non metti `InpFbNews = true`.
- La parte Kairos RSI del bot Fibonacci, già spenta nel set, non è stata portata.
- Serve un conto **hedging**.

**File set**

- `GoldTitan_Quattro.set`: configurazione di default con le 4 strategie attive.
- `GoldTitan_Quattro_16combinazioni.set`: ottimizzazione con criterio "Custom max" su tutte le combinazioni accese/spente delle 4 strategie, cioè 2 × 2 × 2 × 2 = 16. Alla fine scrive `Common\Files\GoldTitan_Quattro_ottimizzazione.csv`. Per ogni combinazione il file riporta trade, vinti e netto di ogni strategia, poi netto totale, profit factor e drawdown.

**Versione 2.10: parametri di RSI e Asia ottimizzabili**

- Diventano Inputs, con i valori di default uguali a prima:
  - **RSI:** periodo RSI, livello (70 = SELL 70 / BUY 30), filtro EMA su M5, filtro trend H1;
  - **Asia:** ore del range (inizio, fine, ultimo ingresso), filtro trend H1 facoltativo, range minimo e massimo in $.
- `GoldTitan_Quattro_ottimizza_RSI.set`: ottimizza solo l'RSI, con le altre strategie spente. 450 combinazioni:
  - SL 120-240;
  - TP 100-220;
  - periodo 7, 14 o 21;
  - livello 65, 70 o 75;
  - filtro H1 sì o no.
- `GoldTitan_Quattro_ottimizza_ASIA.set`: ottimizza solo il range asiatico, con le altre strategie spente. 450 combinazioni:
  - SL 250-450;
  - TP 200-400;
  - fine del range alle 8, 9 o 10;
  - ultimo ingresso alle 12, 13 o 14;
  - filtro H1 sì o no.
- Il CSV `Common\Files\GoldTitan_Quattro_ottimizzazione.csv` riporta anche i parametri di ogni passaggio.

**Versione 2.20: quinta strategia Kairos RSI**

- La parte RSI del bot Kairos è stata portata nel Quattro con la logica invariata:
  - RSI 28 su M1, ingresso al rientro da 30/70, senza filtro trend;
  - uscita quando l'RSI arriva a 65 (BUY) o a 50 (SELL);
  - SL a 2,5 × ATR M1;
  - ingressi dalle 13:00 alle 20:00 ora del server;
  - filtro ATR in % del prezzo.
- Si attiva con `InpUseKairos`, spento di default. Magic number 54001.
- Usa il lotto comune `InpLots`. Non conta per la pausa del Trio e ignora le notizie, a meno che non metti `InpKrNews = true`.
- `GoldTitan_Quattro_RSI_vs_Kairos.set`: ottimizzazione con 4 passaggi (RSI GoldTitan da solo, Kairos da solo, tutti e due insieme, nessuno). Rottura, Asia e Fibonacci sono spenti. Serve un conto hedging.
