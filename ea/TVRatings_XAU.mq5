//+------------------------------------------------------------------+
//|                                              TVRatings_XAU.mq5   |
//|  v5 - Replica delle "Technical Ratings" di TradingView           |
//|  v5: secondo filtro di direzione (es. D1), pausa minima tra i    |
//|  livelli della griglia contro i picchi veloci, statistiche ATR   |
//|  H1 a fine test per scegliere il filtro volatilita'.             |
//|  Default = configurazione migliore dei backtest 2026 (GoldTitan): |
//|  M5, ADX >= 50, direzione H4, TP 30 punti, griglia 3 x 300 punti |
//|  con chiusura del paniere a +1. TP e griglia anche in ATR, per   |
//|  usare la stessa logica su tutti i timeframe.                    |
//|  (widget "Analisi tecnica": Forte acquisto ... Forte vendita)    |
//|  - 15 componenti medie mobili + 11 oscillatori, voto +1/-1/0     |
//|  - calcolo alla chiusura di ogni candela del TF scelto           |
//|    (M1 ogni minuto, M5 ogni 5 minuti, ...)                       |
//|  - segnale a favore o contrario all'indicatore (Inverti)         |
//|  - versione 1: stop and reverse senza SL/TP                       |
//|  - versione 2: TP in punti, chiude sul segnale opposto (farm)     |
//|  - versione 3: Buy e Sell insieme quando il mercato e' laterale  |
//|  - griglia a paniere: TP dal prezzo medio o profitto in valuta,  |
//|    perdita massima e durata massima del paniere                  |
//|  - filtri: ADX min/max, ATR H1, notizie, troppe inversioni,      |
//|    direzione di un TF superiore o di tutti i TF                  |
//|  - lotto fisso, % di rischio o interesse composto                |
//|  - criterio Custom del tester con rebate per lotto               |
//|  Tutti gli indicatori sono calcolati nel codice con le formule   |
//|  di TradingView (RMA di Wilder, EMA con seme SMA, ecc.).         |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "5.00"
#property description "Technical Ratings stile TradingView su XAUUSD: segnale, filtri multi-timeframe, ADX, notizie, griglia a paniere, hedge"

#property tester_file "GT_news.csv"

#include <Trade\Trade.mqh>

#define NA EMPTY_VALUE   // valore "non disponibile" (come na in Pine)
#define N_ALLTF 7

enum StrategyMode
  {
   STRAT_SIGNAL = 0, // Segnale: una direzione alla volta (versioni 1 e 2)
   STRAT_HEDGE  = 1  // Hedge: Buy e Sell insieme in laterale (versione 3)
  };

enum RatingSource
  {
   SRC_TOTAL = 0, // Rating totale
   SRC_MA    = 1, // Rating medie mobili
   SRC_OSC   = 2  // Rating oscillatori
  };

enum EntryMode
  {
   ENTRY_CROSS = 0, // Solo quando il rating attraversa la soglia
   ENTRY_LEVEL = 1  // Finche' il rating e' oltre la soglia
  };

enum TradeDir
  {
   DIR_BOTH = 0, // Buy e Sell
   DIR_BUY  = 1, // Solo Buy
   DIR_SELL = 2  // Solo Sell
  };

enum ExitMode
  {
   EXIT_SLTP     = 0, // Solo SL e TP
   EXIT_NEUTRAL  = 1, // Chiude quando il rating torna neutro (o si gira)
   EXIT_REVERSE  = 2, // Chiude quando il rating passa la fascia neutra opposta
   EXIT_OPPOSITE = 3  // Chiude quando il segnale diventa opposto (oltre la soglia opposta)
  };

enum LotMode
  {
   LOT_FIXED    = 0, // Lotto fisso
   LOT_RISK     = 1, // % del saldo rischiata sullo SL
   LOT_COMPOUND = 2  // Interesse composto: lotto fisso ogni X di saldo
  };

enum StopMode
  {
   STOP_PIPS   = 0, // SL e TP in pips
   STOP_ATR    = 1, // SL e TP in multipli di ATR
   STOP_POINTS = 2  // SL e TP in punti (1 punto = _Point)
  };

enum AdxSource
  {
   ADXSRC_SIGNAL = 0, // ADX sul TF del segnale
   ADXSRC_FILTER = 1  // ADX sul TF del filtro
  };

enum BasketExit
  {
   BASKET_TP_PRICE = 0, // TP comune dal prezzo medio (punti)
   BASKET_MONEY    = 1  // Chiude quando il profitto totale arriva a X (valuta conto)
  };

enum OptCriterion
  {
   OPT_PROFIT_REBATE = 0, // Profitto + rebate
   OPT_RATIO_DD      = 1, // (Profitto + rebate) / drawdown di equity
   OPT_RATIO_DD_PF   = 2  // (Profitto + rebate) / drawdown x profit factor
  };

//--- parametri ------------------------------------------------------
input group "Strategia"
input StrategyMode    InpStrategy    = STRAT_SIGNAL; // Strategia
input bool            InpInvert      = false;        // Inverti: BUY quando l'indicatore dice SELL e viceversa

input group "Segnale"
input ENUM_TIMEFRAMES InpSignalTF    = PERIOD_M5;   // Timeframe del segnale
input RatingSource    InpSignalSrc   = SRC_TOTAL;   // Rating usato per il segnale
input EntryMode       InpEntryMode   = ENTRY_LEVEL; // Modalita' di ingresso
input double          InpBuyLevel    = 0.1;         // Soglia segnale BUY dell'indicatore (rating sopra)
input double          InpSellLevel   = -0.1;        // Soglia segnale SELL dell'indicatore (rating sotto)
input TradeDir        InpDirection   = DIR_BOTH;    // Direzioni ammesse (dei trade, dopo l'inversione)
input bool            InpReenterSameBar = false;    // Dopo una chiusura (es. TP) rientra subito, anche nella stessa candela
input bool            InpReopenAfterTP  = true;     // Dopo un TP rientra nella stessa direzione (false = aspetta un segnale nuovo)
input int             InpReopenDelaySec = 0;        // Attesa in secondi dopo una chiusura prima di riaprire (0 = nessuna)

input group "Filtro direzione su altri timeframe"
input bool            InpUseFilter   = true;        // Usa il filtro
input ENUM_TIMEFRAMES InpFilterTF    = PERIOD_H4;   // Timeframe del filtro
input bool            InpFilterAuto  = false;       // TF del filtro automatico: M1>H1, M5>H4, M15>H4, M30>D1, H1>D1, H4>W1, D1>MN1
input RatingSource    InpFilterSrc   = SRC_TOTAL;   // Rating usato per il filtro
input double          InpFilterLevel = 0.1;         // Segnale BUY se filtro > livello, SELL se filtro < -livello (0.1 = almeno Acquisto, -0.1 = non contrario)
input bool            InpUseFilter2  = false;       // Secondo filtro: deve confermare anche questo TF
input ENUM_TIMEFRAMES InpFilter2TF   = PERIOD_D1;   // Timeframe del secondo filtro (stessa sorgente e livello del primo)
input bool            InpFilterAllTF = false;       // Al posto del TF del filtro: devono concordare M1, M5, M15, M30, H1, H4 e D1

input group "Filtri di mercato"
input AdxSource       InpADXSrc      = ADXSRC_SIGNAL; // Timeframe dell'ADX
input int             InpADXFiltLen  = 14;            // Periodo ADX del filtro
input double          InpADXMin      = 50;            // ADX minimo per aprire (0 = off) - trend
input double          InpADXMax      = 0;             // ADX massimo per aprire (0 = off) - laterale
input bool            InpADXCloseOut = false;         // Chiude tutto quando l'ADX esce dalla zona
input int             InpATRMaxPts   = 0;             // Volatilita' massima: ATR(14) H1 in punti oltre cui non apre (0 = off)
input bool            InpVolBlockGrid= false;         // Il filtro volatilita' blocca anche i livelli della griglia
input int             InpMaxFlips    = 0;             // Inversioni massime nella finestra prima della pausa (0 = off)
input int             InpFlipWindowMin = 30;          // Finestra per contare le inversioni (minuti)
input int             InpFlipPauseMin  = 60;          // Pausa dopo troppe inversioni (minuti)

input group "Notizie"
input bool            InpNewsFilter    = false;     // Blocca i nuovi ingressi vicino alle notizie ad alto impatto
input int             InpNewsMinBefore = 30;        // Minuti prima della notizia
input int             InpNewsMinAfter  = 30;        // Minuti dopo la notizia
input string          InpNewsCurrency  = "USD";     // Valuta delle notizie
input bool            InpNewsBlockGrid = true;      // Blocca anche i livelli della griglia

input group "Uscita"
input ExitMode        InpExitMode    = EXIT_OPPOSITE; // Tipo di uscita (strategia Segnale)
input double          InpNeutralBand = 0.1;          // Fascia neutra (+/-): neutro = tra -X e +X

input group "Lotto e stop"
input LotMode         InpLotMode     = LOT_FIXED;   // Calcolo del lotto
input double          InpFixedLots   = 0.01;        // Lotto fisso (con l'interesse composto: lotto per ogni blocco di saldo)
input double          InpRiskPercent = 1.0;         // Rischio % del saldo (solo modalita' %, serve uno SL)
input double          InpBalancePerLot = 1000;      // Interesse composto: un lotto fisso ogni X di saldo
input double          InpMaxLots     = 0;           // Lotto massimo (0 = nessun limite)
input StopMode        InpStopMode    = STOP_POINTS;   // SL/TP in pips, ATR o punti
input double          InpSLPips      = 500;         // SL in pips (0 = nessuno) - 500 pips = 5.00 $
input double          InpTPPips      = 1000;        // TP in pips (0 = nessuno)
input int             InpATRPeriod   = 14;          // Periodo ATR (sul TF del segnale)
input double          InpSLATR       = 0;           // SL = ATR x (0 = nessuno)
input double          InpTPATR       = 0.1;         // TP = ATR x (0 = nessuno)
input double          InpSLPoints    = 0;           // SL in punti (0 = nessuno)
input double          InpTPPoints    = 30;          // TP in punti (0 = nessuno) - oro a 2 decimali: 30 punti = 0.30 $
input double          InpPipSize     = 0.01;        // Valore di 1 pip in prezzo (oro: 0.01)
input double          InpMaxDDPercent= 0;           // Chiude tutto se la perdita aperta supera X% del saldo (0 = off)

input group "Griglia e paniere"
input bool            InpGridOn      = true;        // Griglia: aggiunge posizioni quando il prezzo va contro
input double          InpGridStepPts = 300;         // Distanza tra i livelli in punti
input double          InpGridStepATR = 0;           // Distanza tra i livelli in ATR del TF segnale (0 = usa i punti)
input double          InpGridLotMult = 1.0;         // Moltiplicatore lotto per livello (1 = lotto costante)
input int             InpGridMaxLevels = 3;         // Livelli massimi per direzione (compreso il primo)
input int             InpGridMinMinutes = 0;        // Minuti minimi tra due livelli della griglia (0 = off): contro i picchi veloci
input bool            InpGridOnlyWithSignal = false;// Aggiunge livelli solo se il segnale e' ancora nella direzione del paniere
input BasketExit      InpBasketExit  = BASKET_MONEY; // Uscita del paniere (2+ posizioni)
input double          InpGridTPPts   = 0;           // TP comune dal prezzo medio, in punti (0 = stesso TP del singolo trade)
input double          InpBasketProfit= 1.0;         // Profitto del paniere per chiudere (valuta conto, modalita' profitto)
input double          InpBasketMaxLoss = 300;       // Chiude il paniere se la perdita arriva a X (valuta conto, 0 = off)
input double          InpBasketMaxHours= 0;         // Chiude il paniere aperto da piu' di X ore (0 = off)
input bool            InpBasketScale = true;        // Profitto e perdita del paniere crescono con il lotto (riferimento: lotto fisso)
input bool            InpGridCloseOnFlip = false;   // Con 2+ posizioni chiude anche sul segnale (false = aspetta profitto, perdita max o durata)

input group "Hedge (versione 3)"
input bool            InpHedgeNeutralOnly  = false; // Laterale solo se anche il rating e' neutro
input bool            InpHedgeCloseOnTrend = true;  // Chiude tutto quando il mercato smette di essere laterale

input group "Filtri orario e spread"
input bool            InpUseHours    = false;       // Usa il filtro orario (ora del server)
input int             InpStartHour   = 8;           // Ora di inizio (inclusa)
input int             InpEndHour     = 20;          // Ora di fine (esclusa; se < inizio passa la mezzanotte)
input double          InpMaxSpread   = 60;          // Spread massimo in pips (0 = off; oro: 1 pip = 1 punto)

input group "Ordini"
input long            InpMagic       = 26102801;    // Magic number
input double          InpSlippage    = 30;          // Slippage massimo in pips
input string          InpComment     = "TVRatings"; // Commento ordini

input group "Tester"
input double          InpRebatePerLot = 35;         // Rebate per lotto (solo per il risultato Custom)
input double          InpCommPerLot   = 0;          // Commissione per lotto andata e ritorno da sottrarre nel risultato Custom (se il tester non la applica)
input OptCriterion    InpOptCriterion = OPT_RATIO_DD; // Criterio Custom del tester

input group "Calcolo e grafico"
input int             InpHistoryBars = 300;         // Candele usate per il calcolo (min. circa 260)
input bool            InpShowPanel   = true;        // Mostra i rating sul grafico
input bool            InpPanelAllTF  = true;        // Nel pannello anche il rating di M1, M5, M15, M30, H1, H4, D1
input bool            InpLogRatings  = false;       // Scrive i rating nel journal a ogni candela

input group "Medie mobili (default TradingView)"
input int    InpMA1      = 10;    // SMA/EMA 1
input int    InpMA2      = 20;    // SMA/EMA 2
input int    InpMA3      = 30;    // SMA/EMA 3
input int    InpMA4      = 50;    // SMA/EMA 4
input int    InpMA5      = 100;   // SMA/EMA 5
input int    InpMA6      = 200;   // SMA/EMA 6
input int    InpHullLen  = 9;     // Hull MA
input int    InpVWMALen  = 20;    // VWMA
input int    InpIchiConv = 9;     // Ichimoku Tenkan
input int    InpIchiBase = 26;    // Ichimoku Kijun
input int    InpIchiSpanB= 52;    // Ichimoku Span B
input int    InpIchiShift= 25;    // Ichimoku spostamento nuvola (TradingView: displacement 26 = 25 candele)

input group "Oscillatori (default TradingView)"
input int    InpRSILen   = 14;    // RSI
input int    InpStochK   = 14;    // Stocastico %K
input int    InpStochSm  = 3;     // Stocastico smussamento %K
input int    InpStochD   = 3;     // Stocastico %D
input int    InpCCILen   = 20;    // CCI
input bool   InpCCITypical = false; // CCI su prezzo tipico (false = su chiusura, come TradingView)
input int    InpADXLen   = 14;    // ADX / DI (componente del rating)
input int    InpAOFast   = 5;     // Awesome Oscillator veloce
input int    InpAOSlow   = 34;    // Awesome Oscillator lento
input int    InpMomLen   = 10;    // Momentum
input int    InpMACDFast = 12;    // MACD veloce
input int    InpMACDSlow = 26;    // MACD lento
input int    InpMACDSig  = 9;     // MACD signal
input int    InpSRSIK    = 3;     // Stoch RSI %K
input int    InpSRSID    = 3;     // Stoch RSI %D
input int    InpSRSIRsi  = 14;    // Stoch RSI periodo RSI
input int    InpSRSIStoch= 14;    // Stoch RSI periodo stocastico
input int    InpWPRLen   = 14;    // Williams %R
input int    InpBBPLen   = 13;    // Bull Bear Power
input int    InpUO1      = 7;     // Ultimate Oscillator 1
input int    InpUO2      = 14;    // Ultimate Oscillator 2
input int    InpUO3      = 28;    // Ultimate Oscillator 3
input int    InpTrendLen = 50;    // Trend (Stoch RSI e Bull Bear Power): prezzo sopra/sotto media
input bool   InpTrendEMA = false; // Trend con EMA (false = SMA)

//--- strutture --------------------------------------------------------
struct Series
  {
   double v[];
  };

struct Rating
  {
   double ma, osc, total;
   int    nMA, nOsc;              // componenti valide
   int    bMA, sMA, bOsc, sOsc;   // quanti in acquisto / vendita
   double adx;                    // ADX del filtro (InpADXFiltLen)
   bool   ok;
  };

struct SideInfo
  {
   int      count;
   double   volume;
   double   avgPrice;
   double   worstPrice;    // buy: prezzo di ingresso piu' basso, sell: piu' alto
   double   lastLot;       // lotto dell'ultimo livello aperto
   double   firstLot;      // lotto del primo livello
   datetime oldest;        // apertura della posizione piu' vecchia
   datetime newest;        // apertura dell'ultimo livello
   double   profit;
  };

//--- stato ------------------------------------------------------------
CTrade          g_trade;
ENUM_TIMEFRAMES g_sigTF, g_fltTF;
int             g_maLen[6];
bool            g_needFlt = false;
int             g_from    = 0;   // primo indice calcolato per le serie con finestra

// serie di prezzo e indicatori (indice 0 = candela piu' vecchia)
double g_c[], g_h[], g_l[], g_vol[], g_hl2[], g_cciSrc[];
Series g_sma[6], g_ema[6];
double g_hma[], g_vwma[], g_conv[], g_base[], g_spanB[];
double g_rsi[], g_stK[], g_stD[], g_cci[], g_pdi[], g_mdi[], g_adx[];
double g_ao[], g_mom[], g_macd[], g_macdSig[], g_srK[], g_srD[];
double g_wpr[], g_bull[], g_bear[], g_uo[], g_trend[], g_atr[];
double g_fpdi[], g_fmdi[], g_fadx[];

Rating   g_sigCur, g_sigPrev, g_flt, g_flt2;
datetime g_lastFlt2Bar = 0, g_flt2Closed = 0;
double   g_atrHist[];             // ATR H1 registrato a ogni ora nel tester
int      g_atrN = 0;
datetime g_atrBar = 0;
double   g_sigATR     = NA;
datetime g_lastSigBar = 0;   // candela (in corso) del TF segnale gia' elaborata
datetime g_lastFltBar = 0;
datetime g_sigClosed  = 0;   // orario della candela chiusa usata
datetime g_fltClosed  = 0;

// tutti i timeframe (filtro "tutti concordano" e pannello)
ENUM_TIMEFRAMES a_tf[N_ALLTF] = {PERIOD_M1, PERIOD_M5, PERIOD_M15, PERIOD_M30, PERIOD_H1, PERIOD_H4, PERIOD_D1};
Rating   a_rat[N_ALLTF];
datetime a_bar[N_ALLTF];
datetime a_closed[N_ALLTF];
int      g_allDir   = 0;     // +1 tutti in acquisto, -1 tutti in vendita, 0 discordi
bool     g_needAll  = false;

int      g_desired    = 0;   // direzione del trade voluta in questa candela (1 buy, -1 sell, 0 nessuna)
bool     g_adxOk      = true;
bool     g_lateral    = false;
datetime g_lastEntryBar = 0; // candela dell'ultimo ingresso (strategia Segnale)
datetime g_lastBuyBar   = 0; // candela dell'ultimo buy base (Hedge)
datetime g_lastSellBar  = 0; // candela dell'ultimo sell base (Hedge)
datetime g_ddBlockBar   = 0; // stop per drawdown: niente ingressi fino alla candela successiva
datetime g_lastClose    = 0; // ora dell'ultima chiusura di una posizione di questo EA
int      g_tpBlockDir   = 0; // dopo un TP non riapre in questa direzione finche' il segnale non cambia

// filtri
int      g_hATRH1     = INVALID_HANDLE;
datetime g_flipTimes[];
datetime g_pauseUntil = 0;
datetime g_news[];
int      g_newsN = 0, g_newsPos = 0;
datetime g_newsLoaded = 0;

// statistiche (stampate a fine test)
int      g_flips = 0, g_gridAdds = 0, g_profitCloses = 0, g_lossCloses = 0, g_timeCloses = 0;
int      g_ddStops = 0, g_newsBlocks = 0, g_volBlocks = 0;
double   g_maxLotUsed = 0;

string   g_status     = "avvio";
string   g_pfx        = "TVR_";
bool     g_draw       = true;
bool     g_warnedStops = false;

//+------------------------------------------------------------------+
int OnInit()
  {
   g_sigTF = (InpSignalTF == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : InpSignalTF;
   g_fltTF = (InpFilterTF == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : InpFilterTF;
   if(InpFilterAuto) g_fltTF = AutoFilterTF(g_sigTF);
   g_needFlt = (InpUseFilter && !InpFilterAllTF) || ((InpADXMin > 0 || InpADXMax > 0) && InpADXSrc == ADXSRC_FILTER);

   g_maLen[0] = InpMA1; g_maLen[1] = InpMA2; g_maLen[2] = InpMA3;
   g_maLen[3] = InpMA4; g_maLen[4] = InpMA5; g_maLen[5] = InpMA6;

   if(InpPipSize <= 0 || InpHistoryBars < 100 || InpBuyLevel <= InpSellLevel || InpADXFiltLen < 1)
     {
      Print("Parametri non validi: controlla dimensione pip, candele di calcolo, soglie e periodo ADX");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpADXMin > 0 && InpADXMax > 0 && InpADXMin >= InpADXMax)
     {
      Print("ADX minimo deve essere sotto l'ADX massimo");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpLotMode == LOT_COMPOUND && InpBalancePerLot <= 0)
      return INIT_PARAMETERS_INCORRECT;
   for(int k = 0; k < 6; k++)
      if(g_maLen[k] < 1) return INIT_PARAMETERS_INCORRECT;
   if(InpGridOn && (InpGridStepPts <= 0 || InpGridMaxLevels < 1 || InpGridLotMult <= 0))
     {
      Print("Parametri della griglia non validi");
      return INIT_PARAMETERS_INCORRECT;
     }
   bool hedging = (AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);
   if((InpStrategy == STRAT_HEDGE || InpGridOn) && !hedging)
     {
      Print("Hedge e griglia richiedono un conto hedging (questo conto e' netting)");
      return INIT_FAILED;
     }
   if(InpHistoryBars < MinBars() + 50)
      Print("Attenzione: InpHistoryBars basso, la media a ", MaxMALen(), " periodi non avra' il tempo di stabilizzarsi");

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints((ulong)MathMax(1.0, MathRound(InpSlippage * InpPipSize / _Point)));
   g_trade.SetTypeFillingBySymbol(_Symbol);

   g_draw = InpShowPanel && !MQLInfoInteger(MQL_OPTIMIZATION) &&
            (!MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_VISUAL_MODE));
   g_needAll = (InpUseFilter && InpFilterAllTF) || (g_draw && InpPanelAllTF);
   g_sigCur.ok = false; g_flt.ok = false;
   for(int k = 0; k < N_ALLTF; k++) { a_rat[k].ok = false; a_bar[k] = 0; a_closed[k] = 0; }

   if(InpATRMaxPts > 0 || MQLInfoInteger(MQL_TESTER))
     {
      g_hATRH1 = iATR(_Symbol, PERIOD_H1, 14);
      if(g_hATRH1 == INVALID_HANDLE) { Print("Impossibile creare l'ATR H1"); return INIT_FAILED; }
     }
   if(InpNewsFilter && MQLInfoInteger(MQL_TESTER))
     {
      if(!LoadNewsFile() || g_newsN == 0)
        {
         Print("Filtro notizie: GT_news.csv non trovato o vuoto (MQL5\\Files o Common\\Files)");
         return INIT_FAILED;
        }
      PrintFormat("Filtro notizie: %d notizie %s caricate dal file", g_newsN, InpNewsCurrency);
      g_newsLoaded = 1;
     }
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0, g_pfx);
   if(g_hATRH1 != INVALID_HANDLE) IndicatorRelease(g_hATRH1);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| Chiusure: ora dell'ultima chiusura e blocco dopo il TP            |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic) return;
   if(HistoryDealGetString(trans.deal, DEAL_SYMBOL) != _Symbol) return;
   long e = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(e != DEAL_ENTRY_OUT && e != DEAL_ENTRY_OUT_BY) return;
   g_lastClose = TimeCurrent();
   if(!InpReopenAfterTP && HistoryDealGetInteger(trans.deal, DEAL_REASON) == DEAL_REASON_TP)
      // la chiusura di un BUY e' un deal SELL
      g_tpBlockDir = (HistoryDealGetInteger(trans.deal, DEAL_TYPE) == DEAL_TYPE_SELL) ? 1 : -1;
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   datetime sigBar = iTime(_Symbol, g_sigTF, 0);
   if(sigBar == 0) return;

   UpdateNews();
   if(g_needAll) UpdateAllTF();

   //--- chiusa una candela del TF del segnale: ricalcolo e decisioni.
   //    Il rating si aggiorna solo qui, cioe' alla chiusura di ogni
   //    candela del TF scelto (M1 ogni minuto, M5 ogni 5 minuti, ...)
   if(sigBar != g_lastSigBar)
     {
      Rating cur, prv;
      double atr;
      if(!CalcRatings(g_sigTF, cur, prv, atr, g_sigClosed))
        {
         g_status = "dati " + TFName(g_sigTF) + " non ancora pronti";
         DrawPanel();
         return;                       // riprova al prossimo tick
        }
      g_lastSigBar = sigBar;
      g_sigCur = cur; g_sigPrev = prv; g_sigATR = atr;

      if(g_needFlt) UpdateFilter();
      if(InpUseFilter2) UpdateFilter2();

      if(InpLogRatings)
         PrintFormat("%s %s  MA %+.3f  OSC %+.3f  TOT %+.3f  ADX %.1f  (%s)", TFName(g_sigTF),
                     TimeToString(g_sigClosed), cur.ma, cur.osc, cur.total, cur.adx, RatingText(cur.total));

      g_adxOk = AdxZoneOk();
      if(InpStrategy == STRAT_HEDGE)
         HedgeOnBar();
      else
        {
         int closed = ManageExit();
         g_desired  = NewSignal();
         if(g_tpBlockDir != 0 && g_desired != g_tpBlockDir) g_tpBlockDir = 0;   // segnale cambiato: sblocca
         if(closed != 0 && g_desired == -closed) RegisterFlip();
         g_status = (g_desired == 0) ? "nessun segnale" : (g_desired > 0 ? "segnale BUY" : "segnale SELL");
        }
     }
   else
     {
      if(g_needFlt && iTime(_Symbol, g_fltTF, 0) != g_lastFltBar)
         UpdateFilter();               // filtro non ancora pronto o nuova candela del filtro
      if(InpUseFilter2 && iTime(_Symbol, InpFilter2TF, 0) != g_lastFlt2Bar)
         UpdateFilter2();
     }
   TrackATR();

   CheckDrawdown(sigBar);
   ManageBaskets();

   if(InpStrategy == STRAT_HEDGE) HedgeTick(sigBar);
   else                           SignalTick(sigBar);

   if(InpGridOn) ManageGrid(sigBar);

   DrawPanel();
  }

// TF del filtro scelto in base al TF del segnale (circa 12-48 volte piu' lento)
ENUM_TIMEFRAMES AutoFilterTF(const ENUM_TIMEFRAMES tf)
  {
   if(tf <= PERIOD_M1)  return PERIOD_H1;
   if(tf <= PERIOD_M5)  return PERIOD_H4;
   if(tf <= PERIOD_M15) return PERIOD_H4;
   if(tf <= PERIOD_M30) return PERIOD_D1;
   if(tf <= PERIOD_H1)  return PERIOD_D1;
   if(tf <= PERIOD_H4)  return PERIOD_W1;
   return PERIOD_MN1;
  }

//+------------------------------------------------------------------+
//| Filtro: ricalcolato solo quando chiude una candela del suo TF     |
//+------------------------------------------------------------------+
void UpdateFilter()
  {
   datetime fBar = iTime(_Symbol, g_fltTF, 0);
   if(fBar == 0 || fBar == g_lastFltBar) return;
   Rating cur, prv;
   double atr;
   if(CalcRatings(g_fltTF, cur, prv, atr, g_fltClosed))
     {
      g_flt = cur;
      g_lastFltBar = fBar;
     }
   else
      g_flt.ok = false;
  }

void UpdateFilter2()
  {
   datetime fBar = iTime(_Symbol, InpFilter2TF, 0);
   if(fBar == 0 || fBar == g_lastFlt2Bar) return;
   Rating cur, prv;
   double atr;
   if(CalcRatings(InpFilter2TF, cur, prv, atr, g_flt2Closed))
     {
      g_flt2 = cur;
      g_lastFlt2Bar = fBar;
     }
   else
      g_flt2.ok = false;
  }

// registra l'ATR H1 a ogni nuova ora (statistiche a fine test per scegliere InpATRMaxPts)
void TrackATR()
  {
   if(!MQLInfoInteger(MQL_TESTER) || g_hATRH1 == INVALID_HANDLE) return;
   datetime t = iTime(_Symbol, PERIOD_H1, 0);
   if(t == g_atrBar) return;
   g_atrBar = t;
   double a = ATRH1Pts();
   if(a <= 0) return;
   ArrayResize(g_atrHist, g_atrN + 1, 2000);
   g_atrHist[g_atrN++] = a;
  }

// tutti i TF: ognuno si ricalcola alla chiusura della propria candela
void UpdateAllTF()
  {
   bool changed = false;
   for(int k = 0; k < N_ALLTF; k++)
     {
      datetime t = iTime(_Symbol, a_tf[k], 0);
      if(t == 0 || t == a_bar[k]) continue;
      Rating cur, prv;
      double atr;
      if(CalcRatings(a_tf[k], cur, prv, atr, a_closed[k])) { a_rat[k] = cur; a_bar[k] = t; }
      else a_rat[k].ok = false;
      changed = true;
     }
   if(!changed) return;
   int d = 0;
   for(int k = 0; k < N_ALLTF; k++)
     {
      if(!a_rat[k].ok) { d = 0; break; }
      double v = Pick(a_rat[k], InpFilterSrc);
      int dk = (v > InpFilterLevel) ? 1 : ((v < -InpFilterLevel) ? -1 : 0);
      if(k == 0) d = dk;
      else if(dk != d) d = 0;
      if(d == 0) break;
     }
   g_allDir = d;
  }

//+------------------------------------------------------------------+
//| Segnale dell'indicatore sulla candela appena chiusa:              |
//| +1 = BUY, -1 = SELL, 0 = niente                                   |
//+------------------------------------------------------------------+
int IndicatorSignal()
  {
   if(!g_sigCur.ok) return 0;
   double v = Pick(g_sigCur, InpSignalSrc);
   double p = g_sigPrev.ok ? Pick(g_sigPrev, InpSignalSrc) : NA;
   if(InpEntryMode == ENTRY_CROSS)
     {
      if(p != NA && p <= InpBuyLevel  && v > InpBuyLevel)  return 1;
      if(p != NA && p >= InpSellLevel && v < InpSellLevel) return -1;
      return 0;
     }
   if(v > InpBuyLevel)  return 1;
   if(v < InpSellLevel) return -1;
   return 0;
  }

// direzione del trade: segnale dell'indicatore, invertito se richiesto
int NewSignal()
  {
   int dir = IndicatorSignal();
   if(InpInvert) dir = -dir;
   if(InpDirection == DIR_SELL && dir > 0) dir = 0;
   if(InpDirection == DIR_BUY  && dir < 0) dir = 0;
   return dir;
  }

//+------------------------------------------------------------------+
//| ADX: il mercato e' nella zona voluta (trend o laterale)?          |
//+------------------------------------------------------------------+
double CurrentADX()
  {
   if(InpADXSrc == ADXSRC_FILTER) return g_flt.ok ? g_flt.adx : NA;
   return g_sigCur.ok ? g_sigCur.adx : NA;
  }

bool AdxZoneOk()
  {
   if(InpADXMin <= 0 && InpADXMax <= 0) return true;
   double a = CurrentADX();
   if(a == NA) return false;
   if(InpADXMin > 0 && a < InpADXMin) return false;
   if(InpADXMax > 0 && a > InpADXMax) return false;
   return true;
  }

string AdxZoneText()
  {
   if(InpADXMin > 0 && InpADXMax > 0) return StringFormat("%.0f-%.0f", InpADXMin, InpADXMax);
   if(InpADXMin > 0) return StringFormat(">= %.0f", InpADXMin);
   return StringFormat("<= %.0f", InpADXMax);
  }

//+------------------------------------------------------------------+
//| Filtri ATR, inversioni, notizie                                  |
//+------------------------------------------------------------------+
double ATRH1Pts()
  {
   if(g_hATRH1 == INVALID_HANDLE) return 0;
   double b[];
   if(CopyBuffer(g_hATRH1, 0, 1, 1, b) != 1) return 0;
   return b[0] / _Point;
  }

bool VolTooHigh()
  {
   if(InpATRMaxPts <= 0) return false;
   double a = ATRH1Pts();
   return (a > 0 && a > InpATRMaxPts);
  }

void RegisterFlip()
  {
   g_flips++;
   if(InpMaxFlips <= 0) return;
   datetime now = TimeCurrent();
   int n = ArraySize(g_flipTimes), k = 0;
   ArrayResize(g_flipTimes, n + 1);
   g_flipTimes[n] = now;
   for(int i = 0; i <= n; i++)
      if(now - g_flipTimes[i] <= InpFlipWindowMin * 60) g_flipTimes[k++] = g_flipTimes[i];
   ArrayResize(g_flipTimes, k);
   if(k >= InpMaxFlips)
     {
      g_pauseUntil = now + InpFlipPauseMin * 60;
      ArrayResize(g_flipTimes, 0);
      if(!MQLInfoInteger(MQL_OPTIMIZATION))
         PrintFormat("Troppe inversioni (%d in %d min): pausa fino alle %s", k, InpFlipWindowMin,
                     TimeToString(g_pauseUntil, TIME_DATE | TIME_MINUTES));
     }
  }

// Notizie. Nel tester legge MQL5\Files\GT_news.csv (o Common\Files), righe
// "aaaa.mm.gg hh:mm;VALUTA;...". Dal vivo usa il calendario economico di MT5.
// Gli orari sono in ora del server.
void SortNews()
  {
   for(int i = 1; i < g_newsN; i++)
     {
      datetime v = g_news[i];
      int j = i - 1;
      while(j >= 0 && g_news[j] > v) { g_news[j + 1] = g_news[j]; j--; }
      g_news[j + 1] = v;
     }
  }

bool LoadNewsFile()
  {
   int h = FileOpen("GT_news.csv", FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ);
   if(h == INVALID_HANDLE) h = FileOpen("GT_news.csv", FILE_READ | FILE_TXT | FILE_ANSI | FILE_SHARE_READ | FILE_COMMON);
   if(h == INVALID_HANDLE) return false;
   g_newsN = 0;
   while(!FileIsEnding(h))
     {
      string line = FileReadString(h);
      if(StringLen(line) < 10 || StringGetCharacter(line, 0) == ';') continue;
      string f[];
      if(StringSplit(line, ';', f) < 2) continue;
      if(InpNewsCurrency != "" && f[1] != InpNewsCurrency) continue;
      datetime tm = StringToTime(f[0]);
      if(tm <= 0) continue;
      ArrayResize(g_news, g_newsN + 1, 1000);
      g_news[g_newsN++] = tm;
     }
   FileClose(h);
   SortNews();
   g_newsPos = 0;
   return true;
  }

void LoadNewsCalendar()
  {
   MqlCalendarValue v[];
   datetime now = TimeTradeServer();
   int n = CalendarValueHistory(v, now - 86400, now + 3 * 86400, NULL, InpNewsCurrency);
   g_newsN = 0;
   for(int i = 0; i < n; i++)
     {
      MqlCalendarEvent ev;
      if(!CalendarEventById(v[i].event_id, ev)) continue;
      if(ev.importance != CALENDAR_IMPORTANCE_HIGH) continue;
      ArrayResize(g_news, g_newsN + 1, 100);
      g_news[g_newsN++] = v[i].time;
     }
   SortNews();
   g_newsPos = 0;
  }

void UpdateNews()
  {
   if(!InpNewsFilter || MQLInfoInteger(MQL_TESTER)) return;   // nel tester il file e' caricato in OnInit
   datetime now = TimeCurrent();
   if(g_newsLoaded == 0 || now - g_newsLoaded >= 3600) { LoadNewsCalendar(); g_newsLoaded = now; }
  }

bool NewsBlocked()
  {
   if(!InpNewsFilter || g_newsN == 0) return false;
   datetime now = TimeCurrent();
   while(g_newsPos < g_newsN && g_news[g_newsPos] + InpNewsMinAfter * 60 < now) g_newsPos++;
   if(g_newsPos >= g_newsN) return false;
   return (now >= g_news[g_newsPos] - InpNewsMinBefore * 60);
  }

//+------------------------------------------------------------------+
//| Controlli comuni prima di aprire una posizione base              |
//+------------------------------------------------------------------+
bool CanOpen(const datetime bar)
  {
   if(g_ddBlockBar == bar) { g_status = "stop per drawdown, riparte alla prossima candela"; return false; }
   if(InpMaxFlips > 0 && TimeCurrent() < g_pauseUntil)
     { g_status = "pausa per troppe inversioni fino alle " + TimeToString(g_pauseUntil, TIME_MINUTES); return false; }
   if(InpReopenDelaySec > 0 && TimeCurrent() - g_lastClose < InpReopenDelaySec)
     { g_status = "attesa dopo la chiusura"; return false; }
   if(InpUseHours && !InHours()) { g_status = "fuori orario"; return false; }
   if(NewsBlocked()) { g_newsBlocks++; g_status = "notizia vicina, niente ingressi"; return false; }
   if(VolTooHigh()) { g_volBlocks++; g_status = StringFormat("volatilita' alta (ATR H1 %.0f punti)", ATRH1Pts()); return false; }
   if(!SpreadOk())
     { g_status = StringFormat("spread alto (%.0f pips), in attesa", SpreadPips()); return false; }
   return true;
  }

double SpreadPips() { return (SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / InpPipSize; }
bool   SpreadOk()   { return InpMaxSpread <= 0 || SpreadPips() <= InpMaxSpread; }

// il filtro deve confermare il segnale dell'indicatore (prima dell'inversione):
// cosi' la versione invertita e' lo specchio esatto di quella a favore
bool FilterOk(const int tradeDir)
  {
   if(!InpUseFilter) return true;
   int ind = InpInvert ? -tradeDir : tradeDir;
   if(InpFilterAllTF)
     {
      if(g_allDir == ind) return true;
      g_status = StringFormat("%s bloccato: i TF non concordano", tradeDir > 0 ? "BUY" : "SELL");
      return false;
     }
   if(!g_flt.ok) { g_status = "filtro " + TFName(g_fltTF) + " non disponibile"; return false; }
   double f = Pick(g_flt, InpFilterSrc);
   if(!((ind > 0 && f > InpFilterLevel) || (ind < 0 && f < -InpFilterLevel)))
     {
      g_status = StringFormat("%s bloccato dal filtro %s (%+.2f)", tradeDir > 0 ? "BUY" : "SELL", TFName(g_fltTF), f);
      return false;
     }
   if(!InpUseFilter2) return true;
   if(!g_flt2.ok) { g_status = "filtro " + TFName(InpFilter2TF) + " non disponibile"; return false; }
   double f2 = Pick(g_flt2, InpFilterSrc);
   if((ind > 0 && f2 > InpFilterLevel) || (ind < 0 && f2 < -InpFilterLevel)) return true;
   g_status = StringFormat("%s bloccato dal filtro %s (%+.2f)", tradeDir > 0 ? "BUY" : "SELL", TFName(InpFilter2TF), f2);
   return false;
  }

//+------------------------------------------------------------------+
//| Strategia Segnale (versioni 1 e 2)                               |
//+------------------------------------------------------------------+
void SignalTick(const datetime bar)
  {
   if(g_desired == 0) return;
   if(CountMine() > 0) return;                        // una direzione (o un paniere) alla volta
   if((InpEntryMode == ENTRY_CROSS || !InpReenterSameBar) && g_lastEntryBar == bar) return;
   if(g_tpBlockDir == g_desired) { g_status = "dopo il TP aspetta un segnale nuovo"; return; }
   if(!g_adxOk) { g_status = StringFormat("ADX %.1f fuori zona (%s)", CurrentADX(), AdxZoneText()); return; }
   if(!FilterOk(g_desired)) return;
   if(!CanOpen(bar)) return;
   if(OpenTrade(g_desired > 0, CalcLots(g_desired > 0, BaseSLDist())))
      g_lastEntryBar = bar;
  }

//+------------------------------------------------------------------+
//| Uscita sul rating (a ogni candela chiusa del TF segnale)          |
//| restituisce la direzione chiusa (1 buy, -1 sell, 0 nessuna)       |
//+------------------------------------------------------------------+
int ManageExit()
  {
   if(InpADXCloseOut && !g_adxOk && CountMine() > 0)
     {
      CloseAll(0);
      g_status = StringFormat("chiuso tutto: ADX %.1f fuori zona", CurrentADX());
      Print(g_status);
      return 0;
     }
   if(InpExitMode == EXIT_SLTP || !g_sigCur.ok) return 0;
   double v  = Pick(g_sigCur, InpSignalSrc);
   int    sg = InpInvert ? -1 : 1;
   int    closed = 0;

   for(int side = 1; side >= -1; side -= 2)
     {
      int n = CountSide(side);
      if(n == 0) continue;
      if(n >= 2 && !InpGridCloseOnFlip) continue;     // il paniere esce su profitto, perdita o durata
      // o = direzione dell'indicatore che ha giustificato la posizione
      int  o = sg * side;
      bool close;
      if(InpExitMode == EXIT_NEUTRAL)
         close = (o > 0) ? (v <= InpNeutralBand) : (v >= -InpNeutralBand);
      else if(InpExitMode == EXIT_REVERSE)
         close = (o > 0) ? (v < -InpNeutralBand) : (v > InpNeutralBand);
      else
         close = (o > 0) ? (v < InpSellLevel) : (v > InpBuyLevel);
      if(close)
        {
         CloseAll(side);
         closed = side;
         g_status = StringFormat("chiuso %s: rating %+.2f (%s)", side > 0 ? "BUY" : "SELL", v, RatingText(v));
         if(InpLogRatings) Print(g_status);
        }
     }
   return closed;
  }

//+------------------------------------------------------------------+
//| Strategia Hedge (versione 3): Buy e Sell insieme in laterale      |
//+------------------------------------------------------------------+
void HedgeOnBar()
  {
   bool lat = g_adxOk && g_sigCur.ok;
   if(lat && InpHedgeNeutralOnly)
      lat = MathAbs(Pick(g_sigCur, InpSignalSrc)) <= InpNeutralBand;
   g_lateral = lat;
   if(!lat && InpHedgeCloseOnTrend && CountMine() > 0)
     {
      CloseAll(0);
      g_status = "mercato non piu' laterale: chiuso tutto";
      if(InpLogRatings) Print(g_status);
     }
   else
      g_status = lat ? "laterale: hedge attivo" : "non laterale: in attesa";
  }

void HedgeTick(const datetime bar)
  {
   if(!g_lateral) return;
   for(int side = 1; side >= -1; side -= 2)
     {
      if(CountSide(side) > 0) continue;
      datetime last = (side > 0) ? g_lastBuyBar : g_lastSellBar;
      if(!InpReenterSameBar && last == bar) continue;
      if(!CanOpen(bar)) return;
      if(OpenTrade(side > 0, CalcLots(side > 0, BaseSLDist())))
        {
         if(side > 0) g_lastBuyBar = bar; else g_lastSellBar = bar;
        }
     }
  }

//+------------------------------------------------------------------+
//| Griglia: aggiunge livelli quando il prezzo va contro              |
//+------------------------------------------------------------------+
void ManageGrid(const datetime bar)
  {
   double step = InpGridStepPts * _Point;
   if(InpGridStepATR > 0)
     {
      if(g_sigATR == NA || g_sigATR <= 0) return;
      step = InpGridStepATR * g_sigATR;
     }
   for(int side = 1; side >= -1; side -= 2)
     {
      SideInfo si;
      GetSide(side, si);
      if(si.count == 0 || si.count >= InpGridMaxLevels) continue;
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      bool adverse = (side > 0) ? (ask <= si.worstPrice - step) : (bid >= si.worstPrice + step);
      if(!adverse) continue;
      if(g_ddBlockBar == bar || !SpreadOk()) continue;
      if(InpGridMinMinutes > 0 && TimeCurrent() - si.newest < InpGridMinMinutes * 60) continue;
      if(InpGridOnlyWithSignal && InpStrategy == STRAT_SIGNAL && g_desired != side) continue;
      if(InpNewsBlockGrid && NewsBlocked()) continue;
      if(InpVolBlockGrid && VolTooHigh()) continue;
      double lots = NormLots(si.lastLot * InpGridLotMult);
      if(OpenTrade(side > 0, lots, false))
        {
         g_gridAdds++;
         g_status = StringFormat("griglia %s livello %d", side > 0 ? "BUY" : "SELL", si.count + 1);
         if(InpBasketExit == BASKET_TP_PRICE) SetBasketTP(side);
         else                                 RemoveTPs(side);
        }
     }
  }

// TP comune a tutto il paniere: prezzo medio +/- distanza
void SetBasketTP(const int side)
  {
   SideInfo si;
   GetSide(side, si);
   if(si.count < 2) return;
   double dist = (InpGridTPPts > 0) ? InpGridTPPts * _Point : BaseTPDist();
   if(dist <= 0) return;
   double tp = NormPrice(side > 0 ? si.avgPrice + dist : si.avgPrice - dist);
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsMine() || PosSide() != side) continue;
      if(MathAbs(PositionGetDouble(POSITION_TP) - tp) < ts / 2) continue;
      if(!g_trade.PositionModify(ticket, PositionGetDouble(POSITION_SL), tp))
         Print("TP del paniere non impostato: ", g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
     }
  }

// paniere a profitto in valuta: i TP dei singoli livelli non servono piu'
void RemoveTPs(const int side)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsMine() || PosSide() != side) continue;
      if(PositionGetDouble(POSITION_TP) != 0)
         g_trade.PositionModify(ticket, PositionGetDouble(POSITION_SL), 0);
     }
  }

// profitto, perdita massima e durata massima dei panieri (2+ posizioni)
void ManageBaskets()
  {
   if(!InpGridOn) return;
   for(int side = 1; side >= -1; side -= 2)
     {
      SideInfo si;
      GetSide(side, si);
      if(si.count < 2) continue;
      double scale = (InpBasketScale && InpFixedLots > 0) ? si.firstLot / InpFixedLots : 1.0;
      string name  = side > 0 ? "BUY" : "SELL";
      if(InpBasketExit == BASKET_MONEY && si.profit >= InpBasketProfit * scale)
        {
         CloseAll(side); g_profitCloses++;
         g_status = StringFormat("paniere %s chiuso in profitto %.2f", name, si.profit);
         continue;
        }
      if(InpBasketMaxLoss > 0 && si.profit <= -InpBasketMaxLoss * scale)
        {
         CloseAll(side); g_lossCloses++;
         g_status = StringFormat("paniere %s chiuso per perdita massima %.2f", name, si.profit);
         if(InpLogRatings) Print(g_status);
         continue;
        }
      if(InpBasketMaxHours > 0 && TimeCurrent() - si.oldest >= (long)(InpBasketMaxHours * 3600))
        {
         CloseAll(side); g_timeCloses++;
         g_status = StringFormat("paniere %s chiuso per durata massima (%.2f)", name, si.profit);
        }
     }
  }

//+------------------------------------------------------------------+
//| Stop di sicurezza sulla perdita aperta                           |
//+------------------------------------------------------------------+
void CheckDrawdown(const datetime bar)
  {
   if(InpMaxDDPercent <= 0) return;
   SideInfo b, s;
   GetSide(1, b);
   GetSide(-1, s);
   double floating = b.profit + s.profit;
   double limit = AccountInfoDouble(ACCOUNT_BALANCE) * InpMaxDDPercent / 100.0;
   if(b.count + s.count > 0 && floating < -limit)
     {
      CloseAll(0);
      g_ddBlockBar = bar;
      g_ddStops++;
      g_status = StringFormat("stop drawdown: perdita %.2f oltre %.2f", floating, limit);
      Print(g_status);
     }
  }

//+------------------------------------------------------------------+
//| Apertura                                                         |
//+------------------------------------------------------------------+
double BaseSLDist()
  {
   if(InpStopMode == STOP_PIPS)   return InpSLPips * InpPipSize;
   if(InpStopMode == STOP_POINTS) return InpSLPoints * _Point;
   return (g_sigATR != NA && g_sigATR > 0) ? InpSLATR * g_sigATR : 0;
  }

double BaseTPDist()
  {
   if(InpStopMode == STOP_PIPS)   return InpTPPips * InpPipSize;
   if(InpStopMode == STOP_POINTS) return InpTPPoints * _Point;
   return (g_sigATR != NA && g_sigATR > 0) ? InpTPATR * g_sigATR : 0;
  }

// withTP = false per i livelli della griglia: il TP lo decide il paniere
bool OpenTrade(const bool isBuy, const double lots, const bool withTP = true)
  {
   if(lots <= 0) { g_status = "lotto non calcolabile"; return false; }
   if(InpStopMode == STOP_ATR && (g_sigATR == NA || g_sigATR <= 0) && (InpSLATR > 0 || InpTPATR > 0))
     { g_status = "ATR non disponibile"; return false; }

   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk) || tk.ask <= 0 || tk.bid <= 0) return false;

   double slDist = BaseSLDist(), tpDist = withTP ? BaseTPDist() : 0;
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if((slDist > 0 && slDist < minDist) || (tpDist > 0 && tpDist < minDist))
     {
      if(!g_warnedStops)
         PrintFormat("SL/TP sotto il livello minimo del broker (%.0f punti): uso il minimo", minDist / _Point);
      g_warnedStops = true;
     }
   if(slDist > 0 && slDist < minDist) slDist = minDist;
   if(tpDist > 0 && tpDist < minDist) tpDist = minDist;

   double price = isBuy ? tk.ask : tk.bid;
   double sl = 0, tp = 0;
   if(slDist > 0) sl = NormPrice(isBuy ? price - slDist : price + slDist);
   if(tpDist > 0) tp = NormPrice(isBuy ? price + tpDist : price - tpDist);

   double margin = 0;
   ENUM_ORDER_TYPE type = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(OrderCalcMargin(type, _Symbol, lots, price, margin) &&
      margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE))
     { g_status = "margine insufficiente"; return false; }

   string cmt = withTP ? InpComment : InpComment + " grid";
   bool sent = isBuy ? g_trade.Buy(lots, _Symbol, price, sl, tp, cmt)
                     : g_trade.Sell(lots, _Symbol, price, sl, tp, cmt);
   uint rc = g_trade.ResultRetcode();
   if(sent && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED || rc == TRADE_RETCODE_DONE_PARTIAL))
     {
      if(lots > g_maxLotUsed) g_maxLotUsed = lots;
      g_status = StringFormat("aperto %s %.2f @ %s", isBuy ? "BUY" : "SELL", lots, DoubleToString(price, _Digits));
      if(InpLogRatings)
         PrintFormat("%s %.2f lotti  SL %s  TP %s  rating %+.3f", isBuy ? "BUY" : "SELL", lots,
                     DoubleToString(sl, _Digits), DoubleToString(tp, _Digits), Pick(g_sigCur, InpSignalSrc));
      return true;
     }
   g_status = StringFormat("ordine rifiutato: %u %s", rc, g_trade.ResultRetcodeDescription());
   Print(g_status);
   return false;
  }

//+------------------------------------------------------------------+
//| Posizioni, lotti, prezzi                                         |
//+------------------------------------------------------------------+
bool IsMine()
  {
   return PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagic;
  }

int PosSide()
  {
   return (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
  }

void GetSide(const int side, SideInfo &si)
  {
   si.count = 0; si.volume = 0; si.avgPrice = 0; si.worstPrice = 0;
   si.lastLot = 0; si.firstLot = 0; si.oldest = 0; si.newest = 0; si.profit = 0;
   long lastTime = 0, firstTime = 0;
   double pv = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsMine() || PosSide() != side) continue;
      double p   = PositionGetDouble(POSITION_PRICE_OPEN);
      double vol = PositionGetDouble(POSITION_VOLUME);
      long   t   = PositionGetInteger(POSITION_TIME_MSC);
      if(si.count == 0 || (side > 0 ? p < si.worstPrice : p > si.worstPrice)) si.worstPrice = p;
      if(t >= lastTime) { lastTime = t; si.lastLot = vol; si.newest = (datetime)(t / 1000); }
      if(firstTime == 0 || t < firstTime) { firstTime = t; si.firstLot = vol; si.oldest = (datetime)(t / 1000); }
      si.count++;
      si.volume += vol;
      pv += p * vol;
      si.profit += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
     }
   if(si.volume > 0) si.avgPrice = pv / si.volume;
  }

int CountSide(const int side)
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) > 0 && IsMine() && PosSide() == side) n++;
   return n;
  }

int CountMine() { return CountSide(1) + CountSide(-1); }

// side: 1 = solo buy, -1 = solo sell, 0 = tutto
void CloseAll(const int side)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsMine()) continue;
      if(side != 0 && PosSide() != side) continue;
      if(!g_trade.PositionClose(ticket))
         Print("Chiusura fallita: ", g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
     }
  }

double NormLots(double lots)
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step > 0) lots = MathFloor(lots / step + 1e-9) * step;
   if(lots < vmin) lots = vmin;
   if(lots > vmax) lots = vmax;
   if(InpMaxLots > 0 && lots > InpMaxLots) lots = InpMaxLots;
   return NormalizeDouble(lots, 2);
  }

double CalcLots(const bool isBuy, const double slDist)
  {
   double lots = InpFixedLots;
   if(InpLotMode == LOT_COMPOUND)
      lots = MathMax(1.0, MathFloor(AccountInfoDouble(ACCOUNT_BALANCE) / InpBalancePerLot + 1e-9)) * InpFixedLots;
   else if(InpLotMode == LOT_RISK && slDist > 0)   // senza SL il rischio non e' calcolabile: lotto fisso
     {
      double price = isBuy ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double profit = 0;
      ENUM_ORDER_TYPE type = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      double slPrice = isBuy ? price - slDist : price + slDist;
      if(!OrderCalcProfit(type, _Symbol, 1.0, price, slPrice, profit) || profit >= 0)
         return 0;
      lots = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0 / (-profit);
     }
   return NormLots(lots);
  }

double NormPrice(const double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0) ts = _Point;
   return NormalizeDouble(MathRound(p / ts) * ts, _Digits);
  }

bool InHours()
  {
   MqlDateTime t;
   TimeToStruct(TimeCurrent(), t);
   int h = t.hour;
   if(InpStartHour == InpEndHour) return true;
   if(InpStartHour < InpEndHour) return (h >= InpStartHour && h < InpEndHour);
   return (h >= InpStartHour || h < InpEndHour);   // fascia a cavallo della mezzanotte
  }

double Pick(const Rating &r, const RatingSource s)
  {
   if(s == SRC_MA)  return r.ma;
   if(s == SRC_OSC) return r.osc;
   return r.total;
  }

//+------------------------------------------------------------------+
//| Risultato Custom del tester: profitto + rebate per lotto          |
//+------------------------------------------------------------------+
double OnTester()
  {
   double lots = 0;
   if(HistorySelect(0, TimeCurrent() + 86400))
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
        {
         ulong t = HistoryDealGetTicket(i);
         if(t == 0 || HistoryDealGetInteger(t, DEAL_MAGIC) != InpMagic) continue;
         if(HistoryDealGetInteger(t, DEAL_ENTRY) != DEAL_ENTRY_IN) continue;
         lots += HistoryDealGetDouble(t, DEAL_VOLUME);
        }
   double net    = TesterStatistics(STAT_PROFIT) - lots * InpCommPerLot;
   double rebate = lots * InpRebatePerLot;
   double dd     = TesterStatistics(STAT_EQUITY_DD);
   double pf     = TesterStatistics(STAT_PROFIT_FACTOR);
   PrintFormat("Lotti %.2f | profitto %.2f (commissione simulata %.2f) | rebate %.2f | totale %.2f | DD equity %.2f (%.2f%%) | lotto max %.2f",
               lots, net, lots * InpCommPerLot, rebate, net + rebate, dd, TesterStatistics(STAT_EQUITYDD_PERCENT), g_maxLotUsed);
   PrintFormat("Inversioni %d | livelli griglia %d | panieri chiusi: profitto %d, perdita max %d, durata max %d | stop drawdown %d | blocchi notizie %d, volatilita' %d",
               g_flips, g_gridAdds, g_profitCloses, g_lossCloses, g_timeCloses, g_ddStops, g_newsBlocks, g_volBlocks);
   if(g_atrN > 10)
     {
      double a[];
      ArrayCopy(a, g_atrHist, 0, 0, g_atrN);
      ArraySort(a);
      PrintFormat("ATR(14) H1 in punti nel periodo: min %.0f | 25%% %.0f | mediana %.0f | 75%% %.0f | 90%% %.0f | 95%% %.0f | 99%% %.0f | max %.0f",
                  a[0], a[g_atrN / 4], a[g_atrN / 2], a[g_atrN * 3 / 4], a[g_atrN * 9 / 10], a[g_atrN * 95 / 100], a[g_atrN * 99 / 100], a[g_atrN - 1]);
     }
   if(InpOptCriterion == OPT_RATIO_DD)    return dd > 0 ? (net + rebate) / dd : 0;
   if(InpOptCriterion == OPT_RATIO_DD_PF) return dd > 0 ? (net + rebate) / dd * pf : 0;
   return net + rebate;
  }

//+------------------------------------------------------------------+
//| Fasce di TradingView                                             |
//+------------------------------------------------------------------+
string RatingText(const double v)
  {
   if(v == NA)   return "n.d.";
   if(v > 0.5)   return "FORTE ACQUISTO";
   if(v > 0.1)   return "ACQUISTO";
   if(v >= -0.1) return "NEUTRALE";
   if(v >= -0.5) return "VENDITA";
   return "FORTE VENDITA";
  }

color RatingColor(const double v)
  {
   if(v == NA)   return clrGray;
   if(v > 0.5)   return clrDodgerBlue;
   if(v > 0.1)   return clrDeepSkyBlue;
   if(v >= -0.1) return clrSilver;
   if(v >= -0.5) return clrTomato;
   return clrRed;
  }

//+------------------------------------------------------------------+
//| Calcolo dei rating su un timeframe                               |
//| cur = ultima candela chiusa, prv = quella prima                  |
//+------------------------------------------------------------------+
int MaxMALen()
  {
   int m = 0;
   for(int k = 0; k < 6; k++) m = MathMax(m, g_maLen[k]);
   return m;
  }

int MinBars()
  {
   int m = MaxMALen();
   m = MathMax(m, InpIchiSpanB + InpIchiShift);
   m = MathMax(m, InpMACDSlow + InpMACDSig);
   m = MathMax(m, InpSRSIRsi + InpSRSIStoch + InpSRSIK + InpSRSID);
   m = MathMax(m, InpTrendLen);
   m = MathMax(m, 3 * InpADXLen);
   m = MathMax(m, InpAOSlow + 3);
   m = MathMax(m, InpUO3 + 1);
   return m + 5;
  }

bool CalcRatings(const ENUM_TIMEFRAMES tf, Rating &cur, Rating &prv, double &atr, datetime &closedTime)
  {
   cur.ok = false; prv.ok = false; atr = NA;
   int need  = MinBars();
   int avail = Bars(_Symbol, tf);
   int cnt   = MathMin(InpHistoryBars, avail - 1);
   if(cnt < need) return false;

   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, tf, 1, cnt, r);     // solo candele chiuse
   if(n < need) return false;
   closedTime = r[n - 1].time;
   // le serie con finestra (massimi, minimi, WMA, CCI) servono solo sulle ultime
   // candele: le calcolo da g_from in poi (le medie esponenziali restano complete)
   g_from = MathMax(0, n - 40);

   ArrayResize(g_c, n);   ArrayResize(g_h, n);   ArrayResize(g_l, n);
   ArrayResize(g_vol, n); ArrayResize(g_hl2, n); ArrayResize(g_cciSrc, n);
   for(int i = 0; i < n; i++)
     {
      g_c[i]   = r[i].close;
      g_h[i]   = r[i].high;
      g_l[i]   = r[i].low;
      g_vol[i] = (r[i].real_volume > 0) ? (double)r[i].real_volume : (double)r[i].tick_volume;
      g_hl2[i] = (r[i].high + r[i].low) / 2.0;
      g_cciSrc[i] = InpCCITypical ? (r[i].high + r[i].low + r[i].close) / 3.0 : r[i].close;
     }

   //--- medie mobili
   for(int k = 0; k < 6; k++)
     {
      SMA(g_c, g_maLen[k], g_sma[k].v);
      EMA(g_c, g_maLen[k], g_ema[k].v);
     }
   HMA(g_c, InpHullLen, g_hma);
   VWMA(g_c, g_vol, InpVWMALen, g_vwma);
   Donchian(InpIchiConv, g_conv);
   Donchian(InpIchiBase, g_base);
   Donchian(InpIchiSpanB, g_spanB);

   //--- oscillatori
   RSI(g_c, InpRSILen, g_rsi);
   double raw[];
   Stoch(g_c, g_h, g_l, InpStochK, raw);
   SMA(raw, InpStochSm, g_stK);
   SMA(g_stK, InpStochD, g_stD);
   CCI(g_cciSrc, InpCCILen, g_cci);
   DMI(InpADXLen, g_pdi, g_mdi, g_adx);

   double f[], s[];
   SMA(g_hl2, InpAOFast, f);
   SMA(g_hl2, InpAOSlow, s);
   Diff(f, s, g_ao);

   ArrayResize(g_mom, n);
   for(int i = 0; i < n; i++)
      g_mom[i] = (i >= InpMomLen) ? g_c[i] - g_c[i - InpMomLen] : NA;

   EMA(g_c, InpMACDFast, f);
   EMA(g_c, InpMACDSlow, s);
   Diff(f, s, g_macd);
   EMA(g_macd, InpMACDSig, g_macdSig);

   double rsi2[];
   RSI(g_c, InpSRSIRsi, rsi2);
   Stoch(rsi2, rsi2, rsi2, InpSRSIStoch, raw);
   SMA(raw, InpSRSIK, g_srK);
   SMA(g_srK, InpSRSID, g_srD);

   WPR(InpWPRLen, g_wpr);

   EMA(g_c, InpBBPLen, f);
   ArrayResize(g_bull, n); ArrayResize(g_bear, n);
   for(int i = 0; i < n; i++)
     {
      g_bull[i] = (f[i] != NA) ? g_h[i] - f[i] : NA;
      g_bear[i] = (f[i] != NA) ? g_l[i] - f[i] : NA;
     }

   UO(g_uo);

   if(InpTrendEMA) EMA(g_c, InpTrendLen, g_trend);
   else            SMA(g_c, InpTrendLen, g_trend);

   //--- ATR (RMA del true range, come TradingView)
   double tr[];
   TrueRange(tr);
   RMA(tr, InpATRPeriod, g_atr);
   atr = g_atr[n - 1];

   //--- ADX del filtro (periodo separato da quello della componente del rating)
   DMI(InpADXFiltLen, g_fpdi, g_fmdi, g_fadx);

   Evaluate(n - 1, cur);
   Evaluate(n - 2, prv);
   cur.adx = g_fadx[n - 1];
   prv.adx = g_fadx[n - 2];
   return cur.ok;
  }

//+------------------------------------------------------------------+
//| Voti delle 26 componenti sulla candela i                          |
//+------------------------------------------------------------------+
void Vote(const int v, double &sum, int &cnt, int &nb, int &ns)
  {
   sum += v; cnt++;
   if(v > 0) nb++;
   if(v < 0) ns++;
  }

int MAVote(const double ma, const double price)
  {
   if(ma == NA) return 99;           // non disponibile
   if(ma < price) return 1;
   if(ma > price) return -1;
   return 0;
  }

bool Ok(const double a)                                 { return a != NA; }
bool Ok(const double a, const double b)                 { return a != NA && b != NA; }
bool Ok(const double a, const double b, const double c) { return a != NA && b != NA && c != NA; }

void Evaluate(const int i, Rating &R)
  {
   R.ok = false; R.ma = NA; R.osc = NA; R.total = NA;
   R.nMA = 0; R.nOsc = 0; R.bMA = 0; R.sMA = 0; R.bOsc = 0; R.sOsc = 0;
   if(i < 2) return;

   double c = g_c[i];
   double sM = 0, sO = 0;
   int v;

   //=== medie mobili (15) ============================================
   for(int k = 0; k < 6; k++)
     {
      v = MAVote(g_sma[k].v[i], c); if(v != 99) Vote(v, sM, R.nMA, R.bMA, R.sMA);
      v = MAVote(g_ema[k].v[i], c); if(v != 99) Vote(v, sM, R.nMA, R.bMA, R.sMA);
     }
   v = MAVote(g_hma[i], c);  if(v != 99) Vote(v, sM, R.nMA, R.bMA, R.sMA);
   v = MAVote(g_vwma[i], c); if(v != 99) Vote(v, sM, R.nMA, R.bMA, R.sMA);

   // Ichimoku: Span A > Span B, Kijun > Span A, Tenkan > Kijun, prezzo > Tenkan.
   // La nuvola e' quella disegnata sotto la candela corrente, cioe' calcolata
   // InpIchiShift candele fa (con spostamento 0 la regola non scatta mai,
   // perche' Tenkan > Kijun implica Span A > Kijun).
   int j = i - InpIchiShift;
   if(j >= 0 && Ok(g_conv[i], g_base[i]) && Ok(g_conv[j], g_base[j], g_spanB[j]))
     {
      double tenkan = g_conv[i], kijun = g_base[i];
      double spanA  = (g_conv[j] + g_base[j]) / 2.0, spanB = g_spanB[j];
      v = 0;
      if(spanA > spanB && kijun > spanA && tenkan > kijun && c > tenkan) v = 1;
      else if(spanA < spanB && kijun < spanA && tenkan < kijun && c < tenkan) v = -1;
      Vote(v, sM, R.nMA, R.bMA, R.sMA);
     }

   //=== oscillatori (11) =============================================
   bool up   = Ok(g_trend[i]) && c > g_trend[i];
   bool down = Ok(g_trend[i]) && c < g_trend[i];

   // RSI
   if(Ok(g_rsi[i], g_rsi[i - 1]))
     {
      v = 0;
      if(g_rsi[i] < 30 && g_rsi[i] > g_rsi[i - 1]) v = 1;
      else if(g_rsi[i] > 70 && g_rsi[i] < g_rsi[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Stocastico
   if(Ok(g_stK[i], g_stD[i]))
     {
      double k = g_stK[i], d = g_stD[i];
      v = 0;
      if(k < 20 && d < 20 && k > d) v = 1;
      else if(k > 80 && d > 80 && k < d) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // CCI
   if(Ok(g_cci[i], g_cci[i - 1]))
     {
      v = 0;
      if(g_cci[i] < -100 && g_cci[i] > g_cci[i - 1]) v = 1;
      else if(g_cci[i] > 100 && g_cci[i] < g_cci[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // ADX
   if(Ok(g_adx[i], g_adx[i - 1]) && Ok(g_pdi[i], g_mdi[i]))
     {
      v = 0;
      if(g_pdi[i] > g_mdi[i] && g_adx[i] > 20 && g_adx[i] > g_adx[i - 1]) v = 1;
      else if(g_mdi[i] > g_pdi[i] && g_adx[i] > 20 && g_adx[i] < g_adx[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Awesome Oscillator: incrocio dello zero, oppure "piattino" sopra/sotto zero
   if(Ok(g_ao[i], g_ao[i - 1], g_ao[i - 2]))
     {
      double a0 = g_ao[i], a1 = g_ao[i - 1], a2 = g_ao[i - 2];
      v = 0;
      if((a0 > 0 && a1 <= 0) || (a0 > 0 && a1 > 0 && a0 > a1 && a1 < a2)) v = 1;
      else if((a0 < 0 && a1 >= 0) || (a0 < 0 && a1 < 0 && a0 < a1 && a1 > a2)) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Momentum
   if(Ok(g_mom[i], g_mom[i - 1]))
     {
      v = 0;
      if(g_mom[i] > g_mom[i - 1]) v = 1;
      else if(g_mom[i] < g_mom[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // MACD
   if(Ok(g_macd[i], g_macdSig[i]))
     {
      v = 0;
      if(g_macd[i] > g_macdSig[i]) v = 1;
      else if(g_macd[i] < g_macdSig[i]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Stochastic RSI (con trend)
   if(Ok(g_srK[i], g_srD[i]) && Ok(g_trend[i]))
     {
      double k = g_srK[i], d = g_srD[i];
      v = 0;
      if(down && k < 20 && d < 20 && k > d) v = 1;
      else if(up && k > 80 && d > 80 && k < d) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Williams %R
   if(Ok(g_wpr[i], g_wpr[i - 1]))
     {
      v = 0;
      if(g_wpr[i] < -80 && g_wpr[i] > g_wpr[i - 1]) v = 1;
      else if(g_wpr[i] > -20 && g_wpr[i] < g_wpr[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Bull Bear Power (con trend)
   if(Ok(g_bear[i], g_bear[i - 1]) && Ok(g_bull[i], g_bull[i - 1]) && Ok(g_trend[i]))
     {
      v = 0;
      if(up && g_bear[i] < 0 && g_bear[i] > g_bear[i - 1]) v = 1;
      else if(down && g_bull[i] > 0 && g_bull[i] < g_bull[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Ultimate Oscillator
   if(Ok(g_uo[i]))
     {
      v = 0;
      if(g_uo[i] > 70) v = 1;
      else if(g_uo[i] < 30) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }

   //=== rating ======================================================
   if(R.nMA > 0)  R.ma  = sM / R.nMA;
   if(R.nOsc > 0) R.osc = sO / R.nOsc;
   if(R.nMA > 0 && R.nOsc > 0) R.total = (R.ma + R.osc) / 2.0;
   else if(R.nMA > 0)          R.total = R.ma;
   else if(R.nOsc > 0)         R.total = R.osc;
   R.ok = (R.total != NA);
  }

//+------------------------------------------------------------------+
//| Indicatori con le formule di TradingView (Pine)                   |
//| Tutte le serie: indice 0 = piu' vecchia, NA = non disponibile     |
//+------------------------------------------------------------------+
void SMA(const double &src[], const int len, double &out[])
  {
   int n = ArraySize(src);
   ArrayResize(out, n);
   double sum = 0;
   int bad = 0;
   for(int i = 0; i < n; i++)
     {
      if(src[i] == NA) bad++; else sum += src[i];
      if(i >= len) { if(src[i - len] == NA) bad--; else sum -= src[i - len]; }
      out[i] = (len > 0 && i >= len - 1 && bad == 0) ? sum / len : NA;
     }
  }

// media esponenziale con seme SMA (come ta.ema / ta.rma di Pine)
void ExpMA(const double &src[], const int len, const double alpha, double &out[])
  {
   int n = ArraySize(src);
   ArrayResize(out, n);
   ArrayInitialize(out, NA);
   int f = 0;
   while(f < n && src[f] == NA) f++;
   if(len < 1 || f + len > n) return;
   double sum = 0;
   for(int i = f; i < f + len; i++)
     {
      if(src[i] == NA) return;
      sum += src[i];
     }
   double prev = sum / len;
   out[f + len - 1] = prev;
   for(int i = f + len; i < n; i++)
     {
      if(src[i] == NA) continue;
      prev = alpha * src[i] + (1.0 - alpha) * prev;
      out[i] = prev;
     }
  }

void EMA(const double &src[], const int len, double &out[]) { ExpMA(src, len, 2.0 / (len + 1.0), out); }
void RMA(const double &src[], const int len, double &out[]) { ExpMA(src, len, 1.0 / len, out); }

void WMA(const double &src[], const int len, double &out[])
  {
   int n = ArraySize(src);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      out[i] = NA;
      if(len < 1 || i < len - 1 || i < g_from) continue;
      double s = 0, w = 0;
      bool ok = true;
      for(int k = 0; k < len; k++)
        {
         double x = src[i - k];
         if(x == NA) { ok = false; break; }
         s += x * (len - k);
         w += (len - k);
        }
      if(ok) out[i] = s / w;
     }
  }

void HMA(const double &src[], const int len, double &out[])
  {
   double half[], full[], d[];
   WMA(src, MathMax(1, len / 2), half);
   WMA(src, len, full);
   int n = ArraySize(src);
   ArrayResize(d, n);
   for(int i = 0; i < n; i++)
      d[i] = (half[i] != NA && full[i] != NA) ? 2.0 * half[i] - full[i] : NA;
   WMA(d, MathMax(1, (int)MathFloor(MathSqrt(len))), out);
  }

void VWMA(const double &src[], const double &vol[], const int len, double &out[])
  {
   int n = ArraySize(src);
   double pv[], a[], b[];
   ArrayResize(pv, n);
   for(int i = 0; i < n; i++) pv[i] = src[i] * vol[i];
   SMA(pv, len, a);
   SMA(vol, len, b);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = (a[i] != NA && b[i] != NA && b[i] > 0) ? a[i] / b[i] : NA;
  }

void Highest(const double &src[], const int len, double &out[])
  {
   int n = ArraySize(src);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      out[i] = NA;
      if(len < 1 || i < len - 1 || i < g_from) continue;
      double m = -DBL_MAX;
      bool ok = true;
      for(int k = 0; k < len; k++)
        {
         if(src[i - k] == NA) { ok = false; break; }
         if(src[i - k] > m) m = src[i - k];
        }
      if(ok) out[i] = m;
     }
  }

void Lowest(const double &src[], const int len, double &out[])
  {
   int n = ArraySize(src);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      out[i] = NA;
      if(len < 1 || i < len - 1 || i < g_from) continue;
      double m = DBL_MAX;
      bool ok = true;
      for(int k = 0; k < len; k++)
        {
         if(src[i - k] == NA) { ok = false; break; }
         if(src[i - k] < m) m = src[i - k];
        }
      if(ok) out[i] = m;
     }
  }

void Donchian(const int len, double &out[])
  {
   double hh[], ll[];
   Highest(g_h, len, hh);
   Lowest(g_l, len, ll);
   int n = ArraySize(g_h);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = (hh[i] != NA && ll[i] != NA) ? (hh[i] + ll[i]) / 2.0 : NA;
  }

void Diff(const double &a[], const double &b[], double &out[])
  {
   int n = ArraySize(a);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = (a[i] != NA && b[i] != NA) ? a[i] - b[i] : NA;
  }

void RSI(const double &src[], const int len, double &out[])
  {
   int n = ArraySize(src);
   double u[], d[], ru[], rd[];
   ArrayResize(u, n); ArrayResize(d, n);
   u[0] = NA; d[0] = NA;
   for(int i = 1; i < n; i++)
     {
      double ch = src[i] - src[i - 1];
      u[i] = MathMax(ch, 0.0);
      d[i] = MathMax(-ch, 0.0);
     }
   RMA(u, len, ru);
   RMA(d, len, rd);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      if(ru[i] == NA || rd[i] == NA) { out[i] = NA; continue; }
      if(rd[i] == 0)      out[i] = 100;
      else if(ru[i] == 0) out[i] = 0;
      else                out[i] = 100.0 - 100.0 / (1.0 + ru[i] / rd[i]);
     }
  }

// stocastico grezzo: 100 * (src - minimo) / (massimo - minimo)
void Stoch(const double &src[], const double &hi[], const double &lo[], const int len, double &out[])
  {
   double hh[], ll[];
   Highest(hi, len, hh);
   Lowest(lo, len, ll);
   int n = ArraySize(src);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = (src[i] != NA && hh[i] != NA && ll[i] != NA && hh[i] > ll[i])
               ? 100.0 * (src[i] - ll[i]) / (hh[i] - ll[i]) : NA;
  }

void CCI(const double &src[], const int len, double &out[])
  {
   double ma[];
   SMA(src, len, ma);
   int n = ArraySize(src);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      out[i] = NA;
      if(ma[i] == NA || i < g_from) continue;
      double md = 0;
      for(int k = 0; k < len; k++) md += MathAbs(src[i - k] - ma[i]);
      md /= len;
      out[i] = (md == 0) ? 0 : (src[i] - ma[i]) / (0.015 * md);
     }
  }

void TrueRange(double &out[])
  {
   int n = ArraySize(g_c);
   ArrayResize(out, n);
   out[0] = g_h[0] - g_l[0];
   for(int i = 1; i < n; i++)
      out[i] = MathMax(g_h[i] - g_l[i], MathMax(MathAbs(g_h[i] - g_c[i - 1]), MathAbs(g_l[i] - g_c[i - 1])));
  }

// ta.dmi di Pine: +DI, -DI e ADX con smussamento di Wilder
void DMI(const int len, double &plus[], double &minus[], double &adx[])
  {
   int n = ArraySize(g_c);
   double pdm[], mdm[], tr[], rp[], rm[], rt[], dx[];
   ArrayResize(pdm, n); ArrayResize(mdm, n);
   pdm[0] = NA; mdm[0] = NA;
   for(int i = 1; i < n; i++)
     {
      double up = g_h[i] - g_h[i - 1];
      double dn = g_l[i - 1] - g_l[i];
      pdm[i] = (up > dn && up > 0) ? up : 0;
      mdm[i] = (dn > up && dn > 0) ? dn : 0;
     }
   TrueRange(tr);
   tr[0] = NA;
   RMA(tr, len, rt);
   RMA(pdm, len, rp);
   RMA(mdm, len, rm);
   ArrayResize(plus, n); ArrayResize(minus, n); ArrayResize(dx, n);
   for(int i = 0; i < n; i++)
     {
      if(rt[i] == NA || rp[i] == NA || rm[i] == NA || rt[i] == 0)
        { plus[i] = NA; minus[i] = NA; dx[i] = NA; continue; }
      plus[i]  = 100.0 * rp[i] / rt[i];
      minus[i] = 100.0 * rm[i] / rt[i];
      double sum = plus[i] + minus[i];
      dx[i] = MathAbs(plus[i] - minus[i]) / (sum == 0 ? 1.0 : sum);
     }
   RMA(dx, len, adx);
   for(int i = 0; i < n; i++)
      if(adx[i] != NA) adx[i] *= 100.0;
  }

void WPR(const int len, double &out[])
  {
   double hh[], ll[];
   Highest(g_h, len, hh);
   Lowest(g_l, len, ll);
   int n = ArraySize(g_c);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = (hh[i] != NA && ll[i] != NA && hh[i] > ll[i])
               ? 100.0 * (g_c[i] - hh[i]) / (hh[i] - ll[i]) : NA;
  }

void UO(double &out[])
  {
   int n = ArraySize(g_c);
   double bp[], tr[], b1[], t1[], b2[], t2[], b3[], t3[];
   ArrayResize(bp, n); ArrayResize(tr, n);
   bp[0] = NA; tr[0] = NA;
   for(int i = 1; i < n; i++)
     {
      double lo = MathMin(g_l[i], g_c[i - 1]);
      double hi = MathMax(g_h[i], g_c[i - 1]);
      bp[i] = g_c[i] - lo;
      tr[i] = hi - lo;
     }
   SMA(bp, InpUO1, b1); SMA(tr, InpUO1, t1);
   SMA(bp, InpUO2, b2); SMA(tr, InpUO2, t2);
   SMA(bp, InpUO3, b3); SMA(tr, InpUO3, t3);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      if(b3[i] == NA || t1[i] == NA || t2[i] == NA || t3[i] == NA || t1[i] == 0 || t2[i] == 0 || t3[i] == 0)
        { out[i] = NA; continue; }
      out[i] = 100.0 * (4.0 * b1[i] / t1[i] + 2.0 * b2[i] / t2[i] + b3[i] / t3[i]) / 7.0;
     }
  }

//+------------------------------------------------------------------+
//| Pannello sul grafico                                             |
//+------------------------------------------------------------------+
string TFName(const ENUM_TIMEFRAMES tf)
  {
   string s = EnumToString(tf);
   return StringSubstr(s, 7);        // "PERIOD_H1" -> "H1"
  }

void Label(const int row, const string text, const color clr)
  {
   string name = g_pfx + IntegerToString(row);
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 10);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, 20 + row * 16);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
  }

string Num(const double v) { return (v == NA) ? "  n.d." : StringFormat("%+6.2f", v); }

int RatingRows(int row, const string title, const Rating &r, const datetime t)
  {
   string adx = (r.ok && r.adx != NA) ? StringFormat("  ADX %.1f", r.adx) : "";
   Label(row++, StringFormat("%s  (candela chiusa %s)%s", title, TimeToString(t, TIME_DATE | TIME_MINUTES), adx), clrWhite);
   if(!r.ok) { Label(row++, "  dati non disponibili", clrGray); Label(row++, " ", clrGray); Label(row++, " ", clrGray); return row; }
   Label(row++, StringFormat("  Medie mobili %s  %-15s B %2d  S %2d  su %d", Num(r.ma), RatingText(r.ma), r.bMA, r.sMA, r.nMA), RatingColor(r.ma));
   Label(row++, StringFormat("  Oscillatori  %s  %-15s B %2d  S %2d  su %d", Num(r.osc), RatingText(r.osc), r.bOsc, r.sOsc, r.nOsc), RatingColor(r.osc));
   Label(row++, StringFormat("  TOTALE       %s  %s", Num(r.total), RatingText(r.total)), RatingColor(r.total));
   return row;
  }

void DrawPanel()
  {
   if(!g_draw) return;
   int row = 0;
   string mode = (InpStrategy == STRAT_HEDGE) ? "Hedge (Buy+Sell in laterale)"
                 : (InpInvert ? "Segnale CONTRARIO all'indicatore" : "Segnale A FAVORE dell'indicatore");
   if(InpGridOn) mode += StringFormat(" + griglia %d liv.", InpGridMaxLevels);
   Label(row++, "TV Technical Ratings  " + _Symbol + "  -  " + mode, clrGold);
   row = RatingRows(row, "Segnale " + TFName(g_sigTF), g_sigCur, g_sigClosed);
   if(g_needFlt)
      row = RatingRows(row, "Filtro " + TFName(g_fltTF), g_flt, g_fltClosed);
   if(InpUseFilter2)
      row = RatingRows(row, "Filtro 2 " + TFName(InpFilter2TF), g_flt2, g_flt2Closed);

   if(g_needAll)
     {
      for(int k = 0; k < N_ALLTF; k++)
        {
         if(!a_rat[k].ok) { Label(row++, StringFormat("%-4s  n.d.", TFName(a_tf[k])), clrGray); continue; }
         double v = a_rat[k].total;
         Label(row++, StringFormat("%-4s %s  %-15s  B %2d / S %2d   candela %s", TFName(a_tf[k]), Num(v), RatingText(v),
                                   a_rat[k].bMA + a_rat[k].bOsc, a_rat[k].sMA + a_rat[k].sOsc,
                                   TimeToString(a_closed[k], TIME_DATE | TIME_MINUTES)), RatingColor(v));
        }
      if(InpUseFilter && InpFilterAllTF)
         Label(row++, "Tutti i TF: " + (g_allDir > 0 ? "concordi BUY" : (g_allDir < 0 ? "concordi SELL" : "non concordi")),
               g_allDir != 0 ? clrLime : clrOrange);
     }

   string f = "";
   if(InpADXMin > 0 || InpADXMax > 0)
     {
      double a = CurrentADX();
      f += StringFormat("ADX %s (%s) %s", a == NA ? "n.d." : DoubleToString(a, 1), AdxZoneText(), g_adxOk ? "OK" : "fuori zona");
     }
   if(InpATRMaxPts > 0) f += StringFormat("  |  ATR H1 %.0f / %d", ATRH1Pts(), InpATRMaxPts);
   if(InpNewsFilter)    f += NewsBlocked() ? "  |  NOTIZIA VICINA" : "  |  notizie ok";
   if(InpMaxFlips > 0)  f += (TimeCurrent() < g_pauseUntil) ? "  |  PAUSA inversioni" : "  |  inversioni ok";
   if(f != "") Label(row++, "Filtri: " + f, clrSilver);

   SideInfo b, s;
   GetSide(1, b);
   GetSide(-1, s);
   Label(row++, StringFormat("Buy: %d pos. %.2f lotti  P/L %.2f   Sell: %d pos. %.2f lotti  P/L %.2f",
                             b.count, b.volume, b.profit, s.count, s.volume, s.profit), clrWhite);
   Label(row++, "Stato: " + g_status, clrSilver);
   ChartRedraw();
  }
//+------------------------------------------------------------------+
