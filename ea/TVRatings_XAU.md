# TVRatings_XAU — EA MT5 (v4 finale)

Replica le **Technical Ratings** di TradingView (il widget "Analisi tecnica": Forte acquisto / Acquisto / Neutrale / Vendita / Forte vendita) e le usa per aprire e chiudere i trade su XAUUSD.

## Versione finale v4: risultati dei backtest e scelte

### Risultati dei test (XAUUSD-P, 2026.01.01 – 2026.10.27, tick reali 99%, 0,01 lotti)

| Test | Netto | Profit factor | DD equity | Trade | Lotti | Netto + rebate 35 |
|---|---|---|---|---|---|---|
| V1 a favore (H1) | −111 | 0,97 | 922 | 218 | 2,2 | −35 |
| V1 contraria (H1) | −171 | 0,96 | 1 180 | 218 | 2,2 | −95 |
| V2 a favore (M5) | −23 499 | 0,21 | 23 504 | 46 998 | 470 | −7 050 |
| V2 contraria (M5) | −16 616 | 0,18 | 16 619 | 29 212 | 292 | −6 392 |
| V3 hedge (M5) | −22 370 | 0,21 | 22 370 | 42 888 | 429 | −7 359 |
| **GoldTitan equivalente (M5)** | **+506** | **2,63** | **198** | 1 256 | 12,6 | **+946** |

### Cosa dicono i numeri

- **V2 e V3 (farm in laterale) perdono per motivi strutturali.**
  - Il TP vale in media +0,13 $; la chiusura sul segnale opposto in media −9 $ (V2) e −12,7 $ (V3).
  - Con questi valori servirebbe una percentuale di vincita sopra il 96%; ne fanno il 85%.
  - Neanche con il rebate di 35 $/lotto tornano in positivo.
  - Spostare le soglie non cambia la struttura: in laterale il rating si gira continuamente.
- **V1 (stop and reverse su H1) è in pari** in entrambe le direzioni (profit factor 0,96–0,97). Da solo il rating H1 non dà un vantaggio.
- **La logica GoldTitan funziona.** Insieme portano il risultato:
  - si entra solo con ADX ≥ 50 e nella direzione di H4;
  - TP piccolo;
  - quando va contro, la griglia (3 livelli a 300 punti) recupera e il paniere chiude appena è a +1 $.

  Il dettaglio:
  - **ogni mese** da gennaio a ottobre è positivo, e anche ogni ora e ogni giorno della settimana;
  - Buy e Sell rendono uguale;
  - sono 195 panieri chiusi, tutti in profitto; la perdita massima del paniere (300 $) non è mai scattata;
  - una sola chiusura su tutto il periodo è negativa (−0,16 $).

### Cosa cambia nella v4

- **Valori di default = configurazione GoldTitan.** L'EA appena caricato lavora già con la logica migliore.
- **Funziona su tutti i timeframe in due modi:**
  - TP e passo della griglia **in ATR** (`InpStopMode = ATR`, `InpTPATR`, `InpGridStepATR`), così la stessa impostazione si adatta da M1 a H4;
  - oppure in punti, con un file .set per ogni timeframe e range già scalati.
- **Filtro di direzione automatico** (`InpFilterAuto`): M1→H1, M5→H4, M15→H4, M30→D1, H1→D1, H4→W1.
- **Commissione simulata** (`InpCommPerLot`): nei test la commissione era 0. Se il tuo conto reale ne paga una, inseriscila qui e il risultato Custom la sottrae.
- **Criterio Custom di default:** (profitto + rebate − commissione) / drawdown, con rebate 35 $/lotto.

### File .set della versione finale

| File | Timeframe | TP (punti) | Passo griglia (punti) |
|---|---|---|---|
| `TVRatings_Finale_M1.set` | M1 | 10–40 | 100–400 |
| `TVRatings_Finale_M5.set` | M5 | 20–60 | 200–600 |
| `TVRatings_Finale_M15.set` | M15 | 30–100 | 300–1000 |
| `TVRatings_Finale_M30.set` | M30 | 50–200 | 500–1500 |
| `TVRatings_Finale_H1.set` | H1 | 50–300 | 600–2400 |
| `TVRatings_Finale_H4.set` | H4 | 100–600 | 1000–5000 |
| `TVRatings_Finale_ATR_tuttiTF.set` | da M1 a H4 (si ottimizza anche il TF) | 0,05–0,3 × ATR | 0,5–2 × ATR |

In tutti i file si ottimizzano anche:
- ADX minimo (25–60);
- profitto del paniere (0,5–3 $);
- livelli della griglia (2–5);
- filtro di direzione acceso o spento;
- pausa dopo troppe inversioni.

### Attenzione prima del conto reale

- **Un solo periodo:** 10 mesi di un anno con trend forti sull'oro. Ripeti il test migliore anche sul 2024 e sul 2025.
- **Nessuno SL:** il rischio vero è la perdita massima del paniere. Su un conto da 1 000 $ con 0,01 lotti, 300 $ sono il 30% del conto. Valuta di ridurla o di attivare `InpMaxDDPercent`.
- **Drawdown sul tuo saldo:** 198 $ sono lo 0,2% di 100 000 $, ma il 20% di 1 000 $. Ragiona sul drawdown in valuta.

## Come calcola il rating

- Calcola sulle **candele chiuse** del timeframe del segnale (H1 di default). Ricalcola a ogni nuova candela.
- Gli indicatori sono scritti nel codice con le formule di TradingView, non con quelli standard di MT5:
  - RSI, ATR e DMI/ADX usano la media di Wilder (RMA);
  - EMA e RMA partono da una SMA;
  - l'ADX non usa iADX, che in MT5 ha un'altra formula.
- Ogni componente vota +1, −1 oppure 0. Una componente vale 0 anche quando la sua regola non è soddisfatta. Se mancano i dati, la componente viene esclusa dalla media, come fa TradingView.

### Medie mobili (15 componenti)

- SMA ed EMA a 10, 20, 30, 50, 100 e 200 periodi, Hull MA 9 e VWMA 20: votano acquisto se la media è sotto la chiusura, vendita se è sopra.
- Ichimoku (9, 26, 52): vota acquisto se valgono tutte e quattro le condizioni:
  - Span A sopra Span B;
  - Kijun sopra Span A;
  - Tenkan sopra Kijun;
  - prezzo sopra Tenkan.

  Vendita se valgono tutte al contrario.
- **Nota sull'Ichimoku:** si usa la nuvola che sta sotto la candela corrente, cioè quella calcolata 25 candele prima (`InpIchiShift`, come il displacement 26 di TradingView). Con la nuvola non spostata la regola non scatterebbe mai: se Tenkan è sopra Kijun, Span A, che è la loro media, sta per forza sopra Kijun.

### Oscillatori (11 componenti)

- Le regole sono quelle della richiesta.
- Per Stochastic RSI e Bull Bear Power il trend è la chiusura sopra o sotto la **SMA 50** (`InpTrendLen` e `InpTrendEMA`). Dovrebbe corrispondere allo script pubblico di TradingView, ma non l'ho verificato riga per riga.
- Il CCI usa la chiusura come sorgente. Con `InpCCITypical = true` usa il prezzo tipico.
- Il volume della VWMA è il volume tick, perché sull'oro CFD il volume reale di solito è 0.

### Rating

| Rating | Calcolo |
|---|---|
| Medie | media dei voti validi delle medie mobili |
| Oscillatori | media dei voti validi degli oscillatori |
| Totale | (medie + oscillatori) / 2, va da −1 a +1 |

| Fascia | Valore |
|---|---|
| Forte vendita | sotto −0,5 |
| Vendita | da −0,5 a −0,1 |
| Neutrale | da −0,1 a +0,1 |
| Acquisto | da +0,1 a +0,5 |
| Forte acquisto | sopra +0,5 |

Il pannello sul grafico mostra, per il TF del segnale e per il TF del filtro:
- i tre rating con la fascia;
- quante componenti votano acquisto e quante vendita;
- la posizione aperta e lo stato dell'EA.

## Logica di trading

- **Ingresso:**
  - `ENTRY_CROSS`: BUY quando il rating scelto passa sopra `InpBuyLevel`, SELL quando passa sotto `InpSellLevel`;
  - `ENTRY_LEVEL`: entra a ogni candela in cui il rating è oltre la soglia e non ci sono posizioni aperte.
- **Filtro:** usa il rating dell'ultima candela chiusa del secondo TF (D1). Non guarda mai la candela in corso.
  - BUY solo se il filtro è sopra `InpFilterLevel`, SELL solo se è sotto −`InpFilterLevel`;
  - con 0,1 il filtro deve essere almeno "Acquisto";
  - con −0,1 basta che non sia contrario.
- **Una sola posizione alla volta**, riconosciuta da simbolo e magic number. Fanno eccezione la griglia e la versione 3 (hedge), descritte sotto.
- **Filtro orario e filtro spread:** si applicano solo agli ingressi. Se all'apertura della candela lo spread è alto o si è fuori orario, il segnale resta valido fino alla fine di quella candela e l'EA riprova a ogni tick.
- **Lotto:**
  - fisso;
  - oppure % del saldo rischiata sullo SL, calcolata con `OrderCalcProfit` e quindi corretta anche sul valore del tick dell'oro.
- **SL/TP:**
  - in pips (1 pip = 0,01, quindi 500 pips = 5,00 $);
  - oppure in multipli di ATR (RMA 14 sul TF del segnale);
  - 0 significa nessuno SL o nessun TP.
- **Uscita (`InpExitMode`):**
  - `EXIT_SLTP`: solo SL e TP;
  - `EXIT_NEUTRAL`: chiude il BUY quando il rating scende a +0,1 o meno (torna neutro o si gira). Il SELL è speculare;
  - `EXIT_REVERSE`: chiude il BUY solo quando il rating scende sotto −0,1, cioè quando si gira in vendita;
  - la fascia ±0,1 si cambia con `InpNeutralBand`.

## Le strategie da testare (v2)

### Quando si aggiorna il rating

Il rating si ricalcola **alla chiusura di ogni candela** del timeframe scelto in `InpSignalTF`: in M1 ogni minuto, in M5 ogni 5 minuti, in H1 ogni ora. Il filtro (`InpFilterTF`) si ricalcola alla chiusura della sua candela. Fra una chiusura e l'altra il rating non cambia; durante la candela l'EA controlla solo TP, griglia, spread e drawdown.

### Le configurazioni

Per ogni configurazione c'è un file .set pronto: Strategy Tester > Parametri > tasto destro > Carica.

| File .set | Versione | Cosa fa |
|---|---|---|
| `TVRatings_V1_trend_favore.set` | 1 a favore | BUY quando l'indicatore dice acquisto, SELL quando dice vendita. Niente SL e niente TP. Quando l'indicatore diventa opposto chiude e apre subito il trade opposto (stop and reverse). ADX minimo (trend). H1 |
| `TVRatings_V1_trend_contrario.set` | 1 contraria | Come sopra, ma BUY quando l'indicatore dice vendita e SELL quando dice acquisto |
| `TVRatings_V2_farm_favore.set` | 2 a favore | Niente SL, TP a 10 punti. Chiude se l'indicatore diventa opposto. Dopo il TP rientra subito finché il segnale resta valido (per fare volume). ADX massimo (laterale). M5 |
| `TVRatings_V2_farm_contrario.set` | 2 contraria | Come sopra, con la direzione invertita |
| `TVRatings_GoldTitan_equivalente.set` | confronto | Stessa configurazione del tuo GoldTitanFarma.set, per confrontare i due EA |
| `TVRatings_V3_hedge.set` | 3 hedge | Quando il mercato è laterale (ADX sotto `InpADXMax`) tiene aperti un BUY e un SELL insieme, ognuno con TP a 10 punti. Quando uno chiude in TP lo riapre. Se il mercato smette di essere laterale chiude tutto. Serve un conto **hedging** |

### Come le versioni si traducono negli input

- **"Indicatore dice acquisto/vendita":** rating sopra `InpBuyLevel` o sotto `InpSellLevel`. Nei file .set il valore di partenza è ±0,1, cioè le fasce "Acquisto" e "Vendita" di TradingView, e si ottimizza fino a ±0,5. `InpEntryMode = Finche' il rating e' oltre la soglia`.
- **Contraria:** `InpInvert = true`. È lo specchio esatto della versione a favore: anche il filtro D1 e le uscite si leggono sul segnale dell'indicatore, poi si inverte solo la direzione del trade.
- **"Chiude quando l'indicatore diventa opposto":** `InpExitMode = EXIT_OPPOSITE`. Chiude il trade nato da un segnale di acquisto quando il rating scende sotto `InpSellLevel`, e viceversa. Nella stessa candela la logica d'ingresso apre il trade opposto, quindi la versione 1 è sempre nel mercato dopo il primo segnale.
- **Niente SL / TP 10 punti:** `InpStopMode = Punti`, `InpSLPoints = 0`, `InpTPPoints = 0` (versione 1) o `10` (versioni 2 e 3).
  - Con l'oro a 2 decimali 1 punto = 0,01, quindi 10 punti = 0,10 $.
  - Se il broker ha un livello minimo di stop più alto, il TP viene allargato a quel minimo e l'EA lo scrive nel journal.
- **Rientro immediato dopo il TP:** `InpReenterSameBar = true`. Con `false` rientra solo alla candela successiva.

### Filtro ADX

| Input | Funzione |
|---|---|
| `InpADXMin` | apre solo con ADX almeno a questo valore (trend, versione 1). 0 = spento |
| `InpADXMax` | apre solo con ADX al massimo a questo valore (laterale, versioni 2 e 3). 0 = spento. Puoi usare insieme minimo e massimo per una fascia |
| `InpADXSrc` | ADX sul TF del segnale o su quello del filtro |
| `InpADXFiltLen` | periodo dell'ADX del filtro, separato da quello della componente del rating, che resta 14 come TradingView |
| `InpADXCloseOut` | se true, chiude tutto quando l'ADX esce dalla zona |

- **Quando conta:** l'ADX blocca solo i nuovi ingressi. Le posizioni aperte escono con la loro regola, salvo `InpADXCloseOut`.
- **Con e senza filtro:** nei file .set il range di ottimizzazione parte da 0 (spento), così vedi in un'unica ottimizzazione se il filtro ADX migliora la versione.
- **Versione 3:** il mercato è "laterale" quando l'ADX è dentro la zona, quindi va impostato `InpADXMax`.

### Griglia

- **Quando aggiunge:** se il prezzo va contro di `InpGridStepPts` punti rispetto al livello peggiore, apre un altro trade nella stessa direzione.
- **Lotti:** il lotto del nuovo livello è quello dell'ultimo livello × `InpGridLotMult`; con 1 resta costante, con più di 1 è una martingala.
- **Limite:** al massimo `InpGridMaxLevels` livelli per direzione, compreso il primo.
- **TP del cesto:** con 2 o più livelli tutti i trade di quella direzione prendono lo stesso TP, cioè prezzo medio ± `InpGridTPPts`. Con 0 usa lo stesso TP del trade singolo, quindi 10 punti nelle versioni 2 e 3.
- **Versione 1 (senza TP):** il cesto chiude solo quando il segnale diventa opposto.
- **Nella versione 3:** la griglia lavora separatamente sul lato BUY e sul lato SELL.
- **Conto:** serve un conto hedging. Su un conto netting l'EA rifiuta di partire con la griglia accesa.
- **Rischio:** senza SL una griglia può accumulare perdite grandi. `InpMaxDDPercent` chiude tutto quando la perdita aperta supera la % del saldo indicata e blocca gli ingressi fino alla candela successiva.
- **Paniere:** uscita al TP comune o al profitto in valuta, perdita e durata massime, e altre opzioni: vedi "Novità v3" più sotto.

### Impostazioni del tester per le versioni 2 e 3

- **Modellazione "Ogni tick basato su tick reali" obbligatoria:** con un TP di 10 punti "OHLC su M1" non è affidabile, perché inventa i tick dentro il minuto.
- **Spread:** con TP a 10 punti lo spread pesa moltissimo. Usa i tick reali, che portano lo spread storico; nei file .set il filtro spread è spento (`InpMaxSpread = 0`), quindi prova anche 20–40 pips.
- **Commissioni:** assicurati che il simbolo del tester abbia le commissioni del tuo conto, altrimenti i risultati del "farm" sono falsati. Se usi un rebate per lotto, sommalo a parte.
- **Ottimizzazione:** algoritmo genetico. Criterio "Fattore di recupero max" per la versione 1, "Saldo max" o "Complesso criterio max" per le versioni 2 e 3. Forward 1/3.

### Parametri nuovi (v2)

| Parametro | Default | Note |
|---|---|---|
| InpStrategy | Segnale | Segnale (versioni 1 e 2) oppure Hedge (versione 3) |
| InpInvert | false | true = versione contraria |
| InpReenterSameBar | false | true = dopo il TP rientra subito (farm) |
| InpADXSrc / InpADXFiltLen / InpADXMin / InpADXMax / InpADXCloseOut | TF segnale / 14 / 0 / 0 / false | filtro ADX (v3: minimo e massimo al posto di modo + livello) |
| InpExitMode = EXIT_OPPOSITE | — | nuova uscita: segnale opposto |
| InpStopMode = Punti, InpSLPoints, InpTPPoints | — / 0 / 10 | SL e TP in punti |
| InpMaxDDPercent | 0 | stop di sicurezza sulla perdita aperta in % del saldo |
| InpGridOn / InpGridStepPts / InpGridLotMult / InpGridMaxLevels / InpGridTPPts | false / 200 / 1.0 / 5 / 0 | griglia |
| InpHedgeNeutralOnly | false | versione 3: laterale solo se anche il rating è neutro |
| InpHedgeCloseOnTrend | true | versione 3: chiude tutto quando il mercato non è più laterale |

## Novità v3 (idee prese da GoldTitanFarma)

### Cosa ho preso dal tuo bot e cosa ho migliorato

| Funzione | In GoldTitanFarma | In TVRatings v3 |
|---|---|---|
| Uscita del paniere | profitto totale in valuta | a scelta: profitto in valuta (`InpBasketExit = profitto`) oppure TP comune dal prezzo medio, che resta sul server anche se l'EA si ferma |
| Perdita massima e durata massima del paniere | sì | sì (`InpBasketMaxLoss`, `InpBasketMaxHours`); con `InpBasketScale` crescono insieme al lotto |
| Profitto del paniere con l'interesse composto | fisso, non cresce col lotto | cresce col lotto, come la perdita massima |
| Griglia solo col segnale / chiusura del paniere sull'inversione | sì | sì (`InpGridOnlyWithSignal`, `InpGridCloseOnFlip`) |
| Filtro notizie | CSV nel tester, calendario MT5 dal vivo | identico, legge lo stesso `GT_news.csv` |
| ADX minimo e massimo | sì | sì (`InpADXMin`, `InpADXMax`), sul TF del segnale o del filtro |
| ATR H1 massimo | sì | sì (`InpATRMaxPts`, `InpVolBlockGrid`) |
| Pausa dopo troppe inversioni | sì | sì (`InpMaxFlips`, `InpFlipWindowMin`, `InpFlipPauseMin`) |
| Direzione di un TF superiore | H1, H4, M15 o tutti i TF | qualsiasi TF (`InpFilterTF`) oppure tutti i TF da M1 a D1 (`InpFilterAllTF`) |
| Interesse composto | sì | `InpLotMode = Interesse composto`, più lotto fisso e % di rischio |
| Dopo un TP aspetta un segnale nuovo | controlla lo storico dei deal a ogni tick (lento nel tester) | lo legge da `OnTradeTransaction`, senza ricerche nello storico |
| Ritardo di riapertura | 8 valori fissi | secondi liberi (`InpReopenDelaySec`) |
| Risultato Custom del tester con rebate | profitto + rebate, o diviso il drawdown | in più: diviso il drawdown × profit factor (`InpOptCriterion`) |
| Pannello con tutti i TF | M1–D1 | M1–D1, ognuno aggiornato alla chiusura della propria candela |
| Ichimoku | **vale sempre 0** (nuvola non spostata: la regola non può mai scattare) | nuvola spostata come TradingView, la componente funziona |
| Velocità | ricalcolo completo | le serie con finestra (massimi, minimi, WMA, CCI) si calcolano solo sulle ultime 40 candele |
| Stop di sicurezza sul conto | no | `InpMaxDDPercent`: chiude tutto oltre una perdita in % del saldo |

### Confronto diretto con il tuo bot

`TVRatings_GoldTitan_equivalente.set` riproduce il tuo `GoldTitanFarma.set`:
- segnale M5, ±0,1, chiude e si gira quando il rating si inverte;
- TP 30 punti, ADX minimo 50, direzione H4;
- griglia di 3 posizioni a 300 punti, paniere +1 / −300;
- spread 60, rebate 35.

Lancialo sullo stesso periodo del tuo bot e confronta i risultati. Ci saranno due piccole differenze:
- da me l'Ichimoku vota;
- il trend di Stoch RSI e Bull Bear Power è la SMA 50; il tuo bot usa la EMA 50, che puoi attivare con `InpTrendEMA = true`.

**Nota sul tuo .set:** usa ADX minimo 50, cioè lavora solo nei trend molto forti, non nel laterale. Vale la pena confrontarlo con la versione 2 (ADX massimo, laterale) per capire quale delle due idee rende di più.

### File notizie

Per usare il filtro notizie nel tester copia il `GT_news.csv` che crei con il tuo script GT_NewsExport in *MQL5\Files* oppure in *Common\Files*. Dal vivo usa il calendario economico di MT5 e il file non serve.

## Installazione

1. Copia `TVRatings_XAU.mq5` in *MQL5/Experts* e compila con F7.
2. Aprilo su un grafico XAUUSD. Il TF del grafico non conta, conta `InpSignalTF`.
3. Attiva Algo Trading.

## Impostazioni dello Strategy Tester (voce per voce)

### Scheda "Impostazioni"

| Voce | Valore consigliato |
|---|---|
| Expert | `TVRatings_XAU.ex5` |
| Simbolo | XAUUSD (il nome esatto del tuo broker, es. XAUUSD, XAUUSD.m, GOLD) |
| Timeframe | H1, uguale a `InpSignalTF` (serve solo per il grafico visuale) |
| Data | "Periodo personalizzato", es. dal 2022.01.01 al 2025.12.31 |
| Forward | 1/3 durante l'ottimizzazione (es. le ultime 1/3 del periodo come test fuori campione), "No" per un test singolo |
| Ritardi | "Zero latenza, esecuzione ideale" per ottimizzare; "Ritardo casuale" per il controllo finale |
| Modellazione | "OHLC su M1" per ottimizzare (veloce, SL/TP verificati dentro la candela); "Ogni tick basato su tick reali" per la verifica finale (usa anche lo spread reale storico, importante per il filtro spread) |
| Deposito | 10000 USD (o il tuo saldo reale) |
| Leva | quella del tuo conto, es. 1:100 |
| Ottimizzazione | "Disabilitata" per un test singolo; "Algoritmo genetico veloce" per ottimizzare |
| Criterio di ottimizzazione | "Saldo max" oppure "Fattore di recupero max" (più robusto); in alternativa "Complesso criterio max" |
| Visuale | attivo solo se vuoi vedere il pannello e i trade durante il test |

Note:
- **Prezzi di apertura:** "Solo prezzi di apertura" va bene solo con `InpExitMode` diverso da `EXIT_SLTP` e senza SL e TP stretti. In questa modalità SL e TP vengono verificati in modo approssimativo.
- **Spread:** nei modelli diversi da "tick reali" lo spread è fisso. Lo imposti con la voce "Spread" nelle proprietà del simbolo nel tester, oppure usi "Spread corrente".
- **Storico:** l'EA ha bisogno di almeno circa 205 candele del TF del filtro prima dell'inizio del test. Con il filtro su D1 servono quindi circa 10 mesi di storico prima della data di inizio. Se non ci sono, i trade partono dopo.

### Scheda "Parametri" (valori, e range Inizio / Passo / Stop per l'ottimizzazione)

| Parametro | Default | Ottimizza? | Inizio | Passo | Stop |
|---|---|---|---|---|---|
| InpSignalTF | H1 | opzionale | M30 | — | H4 |
| InpSignalSrc | Rating totale | sì | (tutti e 3) | | |
| InpEntryMode | Attraversamento | sì | (entrambi) | | |
| InpBuyLevel | 0.5 | sì | 0.2 | 0.1 | 0.7 |
| InpSellLevel | -0.5 | sì | -0.7 | 0.1 | -0.2 |
| InpDirection | Buy e Sell | opzionale | | | |
| InpUseFilter | true | sì | false | | true |
| InpFilterTF | D1 | opzionale | H4 | — | W1 |
| InpFilterSrc | Rating totale | opzionale | | | |
| InpFilterLevel | 0.1 | sì | -0.1 | 0.1 | 0.5 |
| InpExitMode | Neutro | sì | (tutti e 3) | | |
| InpNeutralBand | 0.1 | opzionale | 0.0 | 0.1 | 0.3 |
| InpLotMode | Fisso | no (usa Fisso per ottimizzare, % per il test finale) | | | |
| InpFixedLots | 0.01 | no | | | |
| InpRiskPercent | 1.0 | no | | | |
| InpStopMode | ATR | sì | (entrambi) | | |
| InpSLPips | 500 | sì (se Pips) | 200 | 100 | 1500 |
| InpTPPips | 1000 | sì (se Pips) | 0 | 250 | 3000 |
| InpATRPeriod | 14 | no | | | |
| InpSLATR | 1.5 | sì (se ATR) | 0.5 | 0.5 | 4.0 |
| InpTPATR | 3.0 | sì (se ATR) | 0 | 0.5 | 6.0 |
| InpPipSize | 0.01 | no (oro a 2 decimali) | | | |
| InpUseHours | false | sì | false | | true |
| InpStartHour | 8 | sì | 0 | 1 | 12 |
| InpEndHour | 20 | sì | 14 | 1 | 23 |
| InpMaxSpread | 50 | opzionale | 20 | 10 | 80 |
| InpMagic | 26102801 | no | | | |
| InpSlippage | 30 | no | | | |
| InpComment | TVRatings | no | | | |
| InpHistoryBars | 400 | no (più alto = più fedele, più lento) | | | |
| InpShowPanel | true | no (in ottimizzazione il pannello è spento in automatico) | | | |
| InpLogRatings | false | no | | | |
| Periodi indicatori (MA, Ichimoku, RSI, Stoch, CCI, ADX, AO, Momentum, MACD, StochRSI, W%R, BBP, UO, Trend) | default TradingView | **no**: cambiandoli non replichi più TradingView; ottimizzali solo se vuoi un rating "tuo" | | | |

Consigli:
- **Non ottimizzare tutto insieme.** Prima segnale e filtro (soglie, sorgente, filtro), poi l'uscita (`InpExitMode`, SL e TP), poi gli orari.
- **Combinazioni inutili.** Con `InpStopMode = Pips` i parametri ATR non contano, e viceversa. Ottimizza solo quelli della modalità scelta, così l'algoritmo genetico non perde tempo su combinazioni identiche.
- **Prima del conto reale:** controlla il risultato del periodo forward e ripeti il test migliore con "Ogni tick basato su tick reali" e "Ritardo casuale".
