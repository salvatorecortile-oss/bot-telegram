//+------------------------------------------------------------------+
//|                                              GoldTitan_Final.mq5 |
//|  GoldTitan Final 3.00: versione definitiva su XAUUSD, 4          |
//|  strategie con i valori migliori dei test (pass 47 delle 64      |
//|  combinazioni, gen-ott 2026) gia' impostati come default.        |
//|  Non serve nessun file set.                                      |
//|   1) RSI + EMA (M5)  : ritracciamento nel trend, SL 150 TP 220   |
//|   2) Rottura (M15)   : rottura del canale 24 candele, ADX >= 30, |
//|                        SL 200 TP 300                             |
//|   3) Range asiatico  : range 01-09 (server), ingressi fino alle  |
//|      (M5)              14, SL 350 TP 250                          |
//|   4) Fibonacci (M1)  : ritracciamento 0.5 / 0.618 con pin bar,   |
//|                        10:00-12:00 (server), SL 1.1, TP 1:3      |
//|  Ogni strategia ha il suo magic number. Lotto 0.01 per tutte.    |
//|  RSI, Rottura e Asia: filtro trend H1, ATR giornaliero >= 60 $,  |
//|  spread < 70 points, notizie USD (+90 min), pausa 24 ore dopo    |
//|  4 stop di fila. Fibonacci: logica di Kairos Fibonacci (vers. C).|
//|  Serve un conto HEDGING.                                         |
//+------------------------------------------------------------------+
#property version   "3.00"
#property description "GoldTitan Final 3.00 - RSI+EMA (M5), Rottura (M15), Range asiatico (M5) e Fibonacci (M1) su XAUUSD, valori migliori gia' impostati."

#include <Trade\Trade.mqh>

enum EntryMode
  {
   ENTRY_LIMIT      = 0, // Ordini limit sui livelli
   ENTRY_MARKET     = 1, // Mercato al tocco del livello
   ENTRY_PINBAR     = 2, // Mercato dopo pin bar nella zona
   ENTRY_ENGULF     = 3, // Mercato dopo engulfing nella zona
   ENTRY_PIN_OR_ENG = 4  // Mercato dopo pin bar o engulfing
  };

enum TPMode
  {
   TP_RR1    = 0, // Rischio/rendimento 1:1
   TP_RR15   = 1, // Rischio/rendimento 1:1.5
   TP_RR2    = 2, // Rischio/rendimento 1:2
   TP_RR3    = 3, // Rischio/rendimento 1:3
   TP_SWING  = 4, // Livello 0 (torna allo swing high/low)
   TP_EXT272 = 5, // Estensione -0.272
   TP_EXT618 = 6, // Estensione -0.618
   TP_ATR    = 7  // ATR M1 x InpFbTPATRMult
  };

enum TrendFilter
  {
   TREND_NONE   = 0, // Nessuno: basta la direzione dell'impulso
   TREND_EMA    = 1, // EMA in salita (buy) / in discesa (sell)
   TREND_STRUCT = 2  // Struttura: massimi e minimi crescenti (buy) / decrescenti (sell)
  };

//--- Strategie attive
input bool   InpUseRsi        = true;      // RSI + EMA: attiva la strategia
input bool   InpUseBrk        = true;      // ROTTURA: attiva la strategia
input bool   InpUseAsia       = true;      // RANGE ASIATICO: attiva la strategia
input bool   InpUseFib        = true;      // FIBONACCI: attiva la strategia

//--- Lotto
input double InpLots          = 0.01;      // Lotto (uguale per tutte le strategie)
input double InpBalancePerLot = 0.0;       // Lotto progressivo: un lotto ogni X $ di saldo (0 = lotto fisso)

//--- Stop loss e take profit (1 pip = 0.10 di prezzo = 10 points)
input int    InpRsiSlPips     = 150;       // RSI: stop loss (pips) (migliore dai test)
input int    InpRsiTpPips     = 220;       // RSI: take profit (pips) (migliore dai test)
input int    InpBrkSlPips     = 200;       // ROTTURA: stop loss (pips)
input int    InpBrkTpPips     = 300;       // ROTTURA: take profit (pips)
input int    InpAsiaSlPips    = 350;       // RANGE ASIATICO: stop loss (pips) (migliore dai test)
input int    InpAsiaTpPips    = 250;       // RANGE ASIATICO: take profit (pips) (migliore dai test)

//--- RSI + EMA: segnale e filtri
input int    InpRsiPeriod     = 14;        // RSI: periodo (M5)
input double InpRsiLevel      = 70.0;      // RSI: livello SELL (il BUY e' 100 - livello, 70 -> 30)
input bool   InpRsiEmaFilter  = true;      // RSI: filtro EMA 50/200 su M5
input bool   InpRsiH1Filter   = true;      // RSI: filtro trend H1 (EMA 50/200)

//--- Range asiatico: orari e filtri (ore del server)
input int    InpAsiaStartHour = 1;         // RANGE ASIATICO: inizio del range (ora)
input int    InpAsiaEndHour   = 9;         // RANGE ASIATICO: fine del range, da qui cerca la rottura (ora)
input int    InpAsiaLastHour  = 14;        // RANGE ASIATICO: dopo quest'ora non entra piu' (ora) (migliore dai test)
input bool   InpAsiaH1Filter  = false;     // RANGE ASIATICO: entra solo a favore del trend H1 (EMA 50/200)
input double InpAsiaMinRange  = 0.0;       // RANGE ASIATICO: salta il giorno se il range e' piu' stretto di X $ (0 = off)
input double InpAsiaMaxRange  = 0.0;       // RANGE ASIATICO: salta il giorno se il range e' piu' largo di X $ (0 = off)

//--- Filtri (RSI, Rottura, Range asiatico)
input double InpBrkAdxMin     = 30.0;      // ROTTURA: opera solo se ADX e' sopra questo valore (0 = filtro spento)
input double InpMinAtrUsd     = 60.0;      // Opera solo se l'ATR giornaliero e' sopra X $ (0 = filtro spento)
input int    InpMaxSpreadPts  = 70;        // Opera solo se lo spread e' inferiore a (points, 0 = off)

//--- Protezioni per i periodi di volatilita' estrema (RSI, Rottura, Range asiatico)
input int    InpPauseLosses   = 4;         // Pausa dopo N stop loss consecutivi (0 = off)
input int    InpPauseHours    = 24;        // Durata della pausa (ore)

//--- Fibonacci (valori del set Kairos_Fibonacci_M1_XAU, versione C)
input int         InpFbHourStart  = 1000;          // FIBONACCI: entra dalle (HHMM, ora del server FPG su MT5)
input int         InpFbHourEnd    = 1200;          // FIBONACCI: entra fino alle (HHMM, ora del server FPG su MT5)
input EntryMode   InpFbEntryMode  = ENTRY_PINBAR;  // FIBONACCI: tipo di ingresso
input bool        InpFbLvl382     = false;         // FIBONACCI: entra a 0.382
input bool        InpFbLvl500     = true;          // FIBONACCI: entra a 0.5
input bool        InpFbLvl618     = true;          // FIBONACCI: entra a 0.618
input double      InpFbTouchTol   = 0.06;          // FIBONACCI: mercato, entra solo entro questa frazione dello swing oltre il livello
input double      InpFbPinWick    = 0.6;           // FIBONACCI: pin bar, coda almeno questa frazione della candela
input double      InpFbSLFib      = 1.1;           // FIBONACCI: SL sul livello di Fibonacci (1.1 = oltre lo swing)
input TPMode      InpFbTPMode     = TP_RR3;        // FIBONACCI: take profit
input double      InpFbTPATRMult  = 2.0;           // FIBONACCI: TP ATR, multiplo dell'ATR M1
input int         InpFbSwingDepth = 3;             // FIBONACCI: candele a sinistra e a destra per confermare uno swing
input int         InpFbLookback   = 300;           // FIBONACCI: candele M1 analizzate
input double      InpFbMinLegATR  = 4.0;           // FIBONACCI: impulso minimo = ATR M1 x questo
input int         InpFbMinLegPts  = 0;             // FIBONACCI: impulso minimo in punti (0 = off)
input int         InpFbMaxLegBars = 60;            // FIBONACCI: ignora l'impulso dopo X candele dalla fine
input TrendFilter InpFbTrend      = TREND_EMA;     // FIBONACCI: filtro trend
input int         InpFbEMAPeriod  = 50;            // FIBONACCI: periodo EMA del filtro trend
input bool        InpFbWeekend    = true;          // FIBONACCI: venerdi' sera chiude le posizioni prima del weekend
input int         InpFbFriClose   = 2245;          // FIBONACCI: venerdi', chiude alle (HHMM)
input bool        InpFbNews       = false;         // FIBONACCI: rispetta anche il filtro notizie (false = come il bot originale)


//--- Tester e identificativi
input double InpSimSlipPerLot = 10.0;      // Slippage simulato nel tester ($ per lotto, 0 = off)
input ulong  InpRsiMagic      = 20261006;  // RSI: magic number
input ulong  InpBrkMagic      = 20261007;  // ROTTURA: magic number
input ulong  InpAsiaMagic     = 20261008;  // RANGE ASIATICO: magic number
input ulong  InpFbMagic       = 61800;     // FIBONACCI: magic number

//--- Filtro notizie (USD)
input bool   InpNewsFilter    = true;      // NOTIZIE: niente nuove operazioni vicino alle notizie USD
input int    InpNewsBeforeMin = 0;         // NOTIZIE: minuti prima della notizia
input int    InpNewsAfterMin  = 90;        // NOTIZIE: minuti dopo la notizia
input bool   InpNewsMedium    = false;     // NOTIZIE: includi anche quelle di media importanza
input bool   InpNewsClose     = false;     // NOTIZIE: chiudi le posizioni aperte durante la finestra

//--- Pannello sul grafico (solo informativo, non cambia il trading)
input bool   InpShowPanel     = true;      // PANNELLO: mostra il pannello sul grafico

//--- Valori fissi, scelti con i test (non piu' modificabili dagli Inputs)
#define RSI_TF            PERIOD_M5    // timeframe di RSI ed EMA
#define BRK_TF            PERIOD_M15   // timeframe della rottura
#define CHANNEL_BARS      24           // candele del canale
#define ADX_PERIOD        14
#define ASIA_TF           PERIOD_M5    // timeframe del range asiatico
#define ATR_PERIOD        14           // giorni
#define EMA_FAST_PERIOD   50
#define EMA_SLOW_PERIOD   200
#define PIP_SIZE          0.10         // valore di 1 pip in prezzo
#define NO_SLIPPAGE_LIMIT 100000       // points: in pratica nessun limite allo slippage
#define FB_DEVIATION      50           // points: slippage massimo del Fibonacci (come il bot originale)
#define NSTRAT            4            // 0 = RSI, 1 = Rottura, 2 = Asia, 3 = Fibonacci
#define OPT_FILE          "GoldTitan_Final_ottimizzazione.csv"

CTrade   trade;
int      rsiHandle     = INVALID_HANDLE;
int      emaFastHandle = INVALID_HANDLE;   // EMA sul timeframe dell'RSI
int      emaSlowHandle = INVALID_HANDLE;
int      h1FastHandle  = INVALID_HANDLE;   // EMA su H1
int      h1SlowHandle  = INVALID_HANDLE;
int      adxHandle     = INVALID_HANDLE;   // ADX sul timeframe della rottura
int      atrHandle     = INVALID_HANDLE;   // ATR giornaliero
double   atrSum        = 0.0;              // somma degli ATR letti alle aperture (per la media nel Journal)
int      atrCount      = 0;
datetime atrWarnDay    = 0;
datetime rsiLastBar    = 0;
datetime brkLastBar    = 0;
datetime asiaLastBar   = 0;
datetime asiaDay       = 0;                // giorno in cui il range asiatico ha gia' dato il segnale
datetime lastWarnBar   = 0;
double   slip[NSTRAT]  = {0.0, 0.0, 0.0, 0.0};   // slippage simulato accumulato, per strategia ($)
int      consLosses    = 0;                // stop consecutivi di RSI, Rottura e Asia insieme
datetime pauseUntil    = 0;                // fine della pausa in corso
int      pauseCount    = 0;                // numero di pause scattate (per il Journal)
double   atrMaxSeen    = 0.0;              // ATR giornaliero piu' alto visto a un segnale

#define  NEWS_FILE "GoldTitan_news.csv"
datetime newsTimes[];                       // orari (server) delle notizie filtrate, in ordine
int      newsCount     = 0;
int      newsPtr       = 0;                 // prima notizia la cui finestra non e' ancora finita
datetime newsLoadedAt  = 0;
int      newsSkips     = 0;                 // segnali scartati per notizia (per il Journal)
int      newsCloses    = 0;                 // posizioni chiuse per notizia

//--- ottimizzazione: file del confronto tra le combinazioni
int      optFile = INVALID_HANDLE;
int      optRows = 0;
string   optNames[];                        // parametri che variano nell'ottimizzazione (colonne del CSV)

//--- pannello
bool     panelOn        = false;
bool     panelHistDirty = true;
datetime panelHistAt    = 0;
int      panelLines     = 0;

// statistiche dallo storico (solo operazioni del bot)
double   hsTodayNet = 0, hsMonthNet = 0, hsAllNet = 0, hsGrossWin = 0, hsGrossLoss = 0;
int      hsTodayN = 0, hsTodayW = 0, hsMonthN = 0, hsMonthW = 0, hsAllN = 0, hsAllW = 0;
int      hsN[NSTRAT], hsW[NSTRAT];
double   hsNet[NSTRAT];
datetime hsFirst = 0;

color    PNL_TXT  = clrWhite;
color    PNL_DIM  = C'150,150,150';
color    PNL_HEAD = C'212,175,55';
color    PNL_OK   = C'60,200,90';
color    PNL_WARN = C'255,170,40';
color    PNL_BAD  = C'240,80,80';

//--- Fibonacci: log e disegni
bool     g_quiet = false;   // in ottimizzazione: niente log del Fibonacci
bool     g_draw  = false;   // Fibonacci sul grafico

//--- valori di RSI e Asia usati dal bot (copiati dagli Inputs all'avvio)
bool     gUseRsi, gRsiEmaFilter, gRsiH1Filter;
int      gRsiSlPips, gRsiTpPips, gRsiPeriod;
double   gRsiLevel;
bool     gUseAsia, gAsiaH1Filter;
int      gAsiaSlPips, gAsiaTpPips, gAsiaStartHour, gAsiaEndHour, gAsiaLastHour;
double   gAsiaMinRange, gAsiaMaxRange;

//+------------------------------------------------------------------+
//| Copia i valori degli Inputs nelle variabili usate dal bot.       |
//+------------------------------------------------------------------+
void LoadSettings()
  {
   gUseRsi = InpUseRsi;  gRsiSlPips = InpRsiSlPips;  gRsiTpPips = InpRsiTpPips;
   gRsiPeriod = InpRsiPeriod;  gRsiLevel = InpRsiLevel;
   gRsiEmaFilter = InpRsiEmaFilter;  gRsiH1Filter = InpRsiH1Filter;

   gUseAsia = InpUseAsia;  gAsiaSlPips = InpAsiaSlPips;  gAsiaTpPips = InpAsiaTpPips;
   gAsiaStartHour = InpAsiaStartHour;  gAsiaEndHour = InpAsiaEndHour;  gAsiaLastHour = InpAsiaLastHour;
   gAsiaH1Filter = InpAsiaH1Filter;  gAsiaMinRange = InpAsiaMinRange;  gAsiaMaxRange = InpAsiaMaxRange;
  }

//+------------------------------------------------------------------+
int StratIdx(const ulong m)
  {
   if(m == InpRsiMagic)  return(0);
   if(m == InpBrkMagic)  return(1);
   if(m == InpAsiaMagic) return(2);
   if(m == InpFbMagic)   return(3);
   return(-1);
  }

string StratName(const int k)
  {
   return(k == 0 ? "RSI" : (k == 1 ? "ROTTURA" : (k == 2 ? "ASIA" : "FIBO")));
  }

bool StratOn(const int k)
  {
   return(k == 0 ? gUseRsi : (k == 1 ? InpUseBrk : (k == 2 ? gUseAsia : InpUseFib)));
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   LoadSettings();
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("ATTENZIONE: l'EA e' pensato per XAUUSD, simbolo attuale: ", _Symbol);

   if(InpRsiMagic == InpBrkMagic || InpAsiaMagic == InpRsiMagic || InpAsiaMagic == InpBrkMagic ||
      InpFbMagic == InpRsiMagic || InpFbMagic == InpBrkMagic || InpFbMagic == InpAsiaMagic)
     {
      Print("I magic number devono essere diversi tra loro");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(InpLots <= 0.0 || InpBalancePerLot < 0.0 || InpBrkAdxMin < 0.0 || InpMinAtrUsd < 0.0 ||
      InpPauseLosses < 0 || InpPauseHours < 1)
     {
      Print("Parametri di lotto o dei filtri non validi");
      return(INIT_PARAMETERS_INCORRECT);
     }

   int active = 0;
   for(int k = 0; k < NSTRAT; k++)
      if(StratOn(k))
         active++;
   if(active == 0)
      Print("Nessuna strategia attiva: il bot non aprira' operazioni");
   // strategie diverse possono stare in direzioni opposte: su un conto netting si annullerebbero
   if(active > 1 && AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
     {
      Print("Con piu' strategie attive serve un conto HEDGING (oppure attivane una sola)");
      return(INIT_FAILED);
     }

   double point   = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(gRsiSlPips <= 0 || gRsiTpPips <= 0 || InpBrkSlPips <= 0 || InpBrkTpPips <= 0 ||
      gRsiSlPips * PIP_SIZE < minDist || gRsiTpPips * PIP_SIZE < minDist ||
      InpBrkSlPips * PIP_SIZE < minDist || InpBrkTpPips * PIP_SIZE < minDist ||
      gAsiaSlPips <= 0 || gAsiaTpPips <= 0 ||
      gAsiaSlPips * PIP_SIZE < minDist || gAsiaTpPips * PIP_SIZE < minDist)
     {
      Print("SL/TP non validi o sotto lo stop level del broker");
      return(INIT_PARAMETERS_INCORRECT);
     }

   if(gRsiPeriod < 2 || gRsiLevel <= 50.0 || gRsiLevel >= 100.0 ||
      gAsiaStartHour < 0 || gAsiaStartHour >= gAsiaEndHour || gAsiaEndHour >= gAsiaLastHour ||
      gAsiaLastHour > 24 || gAsiaMinRange < 0.0 || gAsiaMaxRange < 0.0 ||
      (gAsiaMaxRange > 0.0 && gAsiaMaxRange <= gAsiaMinRange))
     {
      Print("Parametri di RSI o del range asiatico non validi");
      return(INIT_PARAMETERS_INCORRECT);
     }

   rsiHandle     = iRSI(_Symbol, RSI_TF, gRsiPeriod, PRICE_CLOSE);
   emaFastHandle = iMA(_Symbol, RSI_TF, EMA_FAST_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
   emaSlowHandle = iMA(_Symbol, RSI_TF, EMA_SLOW_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
   h1FastHandle  = iMA(_Symbol, PERIOD_H1, EMA_FAST_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
   h1SlowHandle  = iMA(_Symbol, PERIOD_H1, EMA_SLOW_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
   adxHandle     = iADX(_Symbol, BRK_TF, ADX_PERIOD);
   atrHandle     = iATR(_Symbol, PERIOD_D1, ATR_PERIOD);
   if(rsiHandle == INVALID_HANDLE || emaFastHandle == INVALID_HANDLE || emaSlowHandle == INVALID_HANDLE ||
      h1FastHandle == INVALID_HANDLE || h1SlowHandle == INVALID_HANDLE ||
      adxHandle == INVALID_HANDLE || atrHandle == INVALID_HANDLE)
     {
      Print("Impossibile creare gli indicatori, errore ", GetLastError());
      return(INIT_FAILED);
     }

   // Nessun limite di slippage: l'ordine viene eseguito a qualunque prezzo disponibile.
   trade.SetDeviationInPoints(NO_SLIPPAGE_LIMIT);
   trade.SetTypeFillingBySymbol(_Symbol);

   g_quiet = (bool)MQLInfoInteger(MQL_OPTIMIZATION);
   g_draw  = !(bool)MQLInfoInteger(MQL_TESTER) || (bool)MQLInfoInteger(MQL_VISUAL_MODE);
   if(InpUseFib)
     {
      int r = FbInit();
      if(r != INIT_SUCCEEDED)
         return(r);
     }

   if(InpNewsFilter)
     {
      if(InpNewsBeforeMin < 0 || InpNewsAfterMin < 0)
        {
         Print("Minuti del filtro notizie non validi");
         return(INIT_PARAMETERS_INCORRECT);
        }
      if(!LoadNews())
        {
         if(MQLInfoInteger(MQL_TESTER))
           {
            Print("Filtro notizie: file ", NEWS_FILE, " non trovato in Common\\Files. Esegui prima lo script GoldTitan_ExportNews.");
            return(INIT_FAILED);
           }
         Print("Filtro notizie: calendario non ancora disponibile, riprovo tra poco");
        }
     }

   PrintFormat("GoldTitan Final 3.00 avviato su %s | RSI %s | Rottura %s | Asia %s | Fibonacci %s (%04d-%04d) | lotto %.2f, progressivo %.0f $",
               _Symbol, gUseRsi ? "ON" : "OFF", InpUseBrk ? "ON" : "OFF", gUseAsia ? "ON" : "OFF",
               InpUseFib ? "ON" : "OFF", InpFbHourStart, InpFbHourEnd, InpLots, InpBalancePerLot);
   PrintFormat("RSI SL %d TP %d | Rottura SL %d TP %d ADX %.0f | Asia SL %d TP %d, range %d-%d, fino alle %d | ATR min %.0f $",
               gRsiSlPips, gRsiTpPips, InpBrkSlPips, InpBrkTpPips, InpBrkAdxMin,
               gAsiaSlPips, gAsiaTpPips, gAsiaStartHour, gAsiaEndHour, gAsiaLastHour, InpMinAtrUsd);
   PanelInit();
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(rsiHandle     != INVALID_HANDLE) IndicatorRelease(rsiHandle);
   if(emaFastHandle != INVALID_HANDLE) IndicatorRelease(emaFastHandle);
   if(emaSlowHandle != INVALID_HANDLE) IndicatorRelease(emaSlowHandle);
   if(h1FastHandle  != INVALID_HANDLE) IndicatorRelease(h1FastHandle);
   if(h1SlowHandle  != INVALID_HANDLE) IndicatorRelease(h1SlowHandle);
   if(adxHandle     != INVALID_HANDLE) IndicatorRelease(adxHandle);
   if(atrHandle     != INVALID_HANDLE) IndicatorRelease(atrHandle);
   FbDeinit();
   PanelDeinit();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   PanelUpdate();
  }

//+------------------------------------------------------------------+
//| Risultato del test al netto dello slippage simulato (criterio    |
//| "Custom max"). Nel Journal stampa anche il dettaglio per         |
//| strategia: numero di trade, trade vinti e netto.                 |
//| In ottimizzazione manda i risultati al terminale (frame) per il  |
//| file CSV delle combinazioni.                                     |
//+------------------------------------------------------------------+
double OnTester()
  {
   double prof[NSTRAT] = {0.0, 0.0, 0.0, 0.0};
   int    n[NSTRAT]    = {0, 0, 0, 0};
   int    win[NSTRAT]  = {0, 0, 0, 0};

   if(HistorySelect(0, TimeCurrent()))
     {
      int total = HistoryDealsTotal();
      for(int i = 0; i < total; i++)
        {
         ulong deal = HistoryDealGetTicket(i);
         if(deal == 0)
            continue;
         long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
         if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY && entry != DEAL_ENTRY_INOUT)
            continue;
         int k = StratIdx((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC));
         if(k < 0)
            continue;
         double p = HistoryDealGetDouble(deal, DEAL_PROFIT) +
                    HistoryDealGetDouble(deal, DEAL_SWAP) +
                    HistoryDealGetDouble(deal, DEAL_COMMISSION);
         prof[k] += p;
         n[k]++;
         if(p > 0.0) win[k]++;
        }
     }

   double slipTot = 0.0;
   for(int k = 0; k < NSTRAT; k++)
     {
      PrintFormat("%-8s: %s | %d trade, %d vinti, netto %.2f $ (slippage %.2f $)",
                  StratName(k), StratOn(k) ? "ON " : "OFF", n[k], win[k], prof[k] - slip[k], slip[k]);
      slipTot += slip[k];
     }
   PrintFormat("ATR giornaliero medio alle aperture: %.2f $ (%d letture)",
               atrCount > 0 ? atrSum / atrCount : 0.0, atrCount);
   PrintFormat("ATR giornaliero massimo a un segnale: %.2f $ | pause scattate: %d", atrMaxSeen, pauseCount);
   double realNet = TesterStatistics(STAT_PROFIT) - slipTot;
   if(InpNewsFilter)
      PrintFormat("NOTIZIE : %d notizie caricate | finestra -%d / +%d min | segnali scartati %d | posizioni chiuse %d",
                  newsCount, InpNewsBeforeMin, InpNewsAfterMin, newsSkips, newsCloses);
   PrintFormat("TOTALE  : netto reale %.2f $", realNet);

   double data[NSTRAT * 4 + 4];
   for(int k = 0; k < NSTRAT; k++)
     {
      data[k * 4 + 0] = n[k];
      data[k * 4 + 1] = win[k];
      data[k * 4 + 2] = prof[k] - slip[k];
      data[k * 4 + 3] = StratOn(k) ? 1.0 : 0.0;
     }
   data[NSTRAT * 4 + 0] = TesterStatistics(STAT_PROFIT_FACTOR);
   data[NSTRAT * 4 + 1] = TesterStatistics(STAT_EQUITY_DD);
   data[NSTRAT * 4 + 2] = TesterStatistics(STAT_EQUITYDD_PERCENT);
   data[NSTRAT * 4 + 3] = TesterStatistics(STAT_TRADES);
   FrameAdd("q", 0, realNet, data);
   return(NormalizeDouble(realNet, 2));
  }

//+------------------------------------------------------------------+
//| Ottimizzazione: apre il CSV delle combinazioni.                  |
//+------------------------------------------------------------------+
void OnTesterInit()
  {
   optRows = 0;
   optFile = FileOpen(OPT_FILE, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(optFile == INVALID_HANDLE)
     {
      Print("Impossibile creare ", OPT_FILE, ", errore ", GetLastError());
      return;
     }
   // annota quali parametri variano: diventano colonne del CSV (interi e bool con la versione long, i double con quella double)
   string cand[] = {"InpRsiSlPips", "InpRsiTpPips", "InpRsiPeriod", "InpRsiLevel", "InpRsiEmaFilter", "InpRsiH1Filter",
                    "InpBrkSlPips", "InpBrkTpPips", "InpBrkAdxMin",
                    "InpAsiaSlPips", "InpAsiaTpPips", "InpAsiaStartHour", "InpAsiaEndHour", "InpAsiaLastHour",
                    "InpAsiaH1Filter", "InpAsiaMinRange", "InpAsiaMaxRange",
                    "InpMinAtrUsd", "InpMaxSpreadPts", "InpPauseLosses", "InpPauseHours", "InpNewsAfterMin"};
   ArrayResize(optNames, 0);
   for(int i = 0; i < ArraySize(cand); i++)
     {
      bool   enable = false;
      long   lv, lstart, lstep, lstop;
      double dv, dstart, dstep, dstop;
      bool   found = ParameterGetRange(cand[i], enable, lv, lstart, lstep, lstop);
      if(!found)
         found = ParameterGetRange(cand[i], enable, dv, dstart, dstep, dstop);
      if(found && enable)
        {
         int n = ArraySize(optNames);
         ArrayResize(optNames, n + 1);
         optNames[n] = cand[i];
        }
     }

   string head = "Passaggio;RSI;ROTTURA;ASIA;FIBO;Strategie attive";
   for(int i = 0; i < ArraySize(optNames); i++)
      head += ";" + optNames[i];
   for(int k = 0; k < NSTRAT; k++)
      head += ";" + StratName(k) + " trade;" + StratName(k) + " vinti;" + StratName(k) + " % vinti;" + StratName(k) + " netto";
   head += ";Trade totali;Netto totale;Profit factor;DD equity $;DD equity %;Netto / DD";
   FileWriteString(optFile, head + "\r\n");
  }

//+------------------------------------------------------------------+
//| Numero con la virgola decimale (Excel in italiano).              |
//+------------------------------------------------------------------+
string Num(const double v, const int digits)
  {
   string s = DoubleToString(v, digits);
   StringReplace(s, ".", ",");
   return(s);
  }

//+------------------------------------------------------------------+
//| Ottimizzazione: una riga del CSV per ogni combinazione finita.   |
//+------------------------------------------------------------------+
void OnTesterPass()
  {
   ulong  pass;
   string name;
   long   id;
   double value;
   double data[];
   while(FrameNext(pass, name, id, value, data))
     {
      if(name != "q" || ArraySize(data) < NSTRAT * 4 + 4 || optFile == INVALID_HANDLE)
         continue;

      string params[];
      uint   pcount = 0;
      string on[NSTRAT] = {"?", "?", "?", "?"};
      string pv[];
      ArrayResize(pv, ArraySize(optNames));
      if(FrameInputs(pass, params, pcount))
         for(uint j = 0; j < pcount; j++)
           {
            for(int i = 0; i < ArraySize(optNames); i++)
               if(StringFind(params[j], optNames[i] + "=") == 0)
                 {
                  pv[i] = StringSubstr(params[j], StringLen(optNames[i]) + 1);
                  StringReplace(pv[i], ".", ",");
                 }
           }

      for(int k = 0; k < NSTRAT; k++)
         on[k] = data[k * 4 + 3] > 0.5 ? "SI" : "no";

      string list = "";
      for(int k = 0; k < NSTRAT; k++)
         if(on[k] == "SI")
            list += (list == "" ? "" : " + ") + StratName(k);
      if(list == "")
         list = "nessuna";

      string line = IntegerToString((long)pass);
      for(int k = 0; k < NSTRAT; k++)
         line += ";" + on[k];
      line += ";" + list;
      for(int i = 0; i < ArraySize(optNames); i++)
         line += ";" + pv[i];
      for(int k = 0; k < NSTRAT; k++)
        {
         double nk = data[k * 4 + 0], wk = data[k * 4 + 1];
         line += ";" + Num(nk, 0) + ";" + Num(wk, 0) + ";" + Num(nk > 0 ? 100.0 * wk / nk : 0.0, 1) +
                 ";" + Num(data[k * 4 + 2], 2);
        }
      double dd = data[NSTRAT * 4 + 1];
      line += ";" + Num(data[NSTRAT * 4 + 3], 0) + ";" + Num(value, 2) + ";" + Num(data[NSTRAT * 4 + 0], 2) +
              ";" + Num(dd, 2) + ";" + Num(data[NSTRAT * 4 + 2], 2) + ";" + Num(dd > 0 ? value / dd : 0.0, 2);
      FileWriteString(optFile, line + "\r\n");
      FileFlush(optFile);
      optRows++;
     }
  }

//+------------------------------------------------------------------+
void OnTesterDeinit()
  {
   OnTesterPass();   // eventuali frame rimasti
   if(optFile != INVALID_HANDLE)
     {
      FileClose(optFile);
      optFile = INVALID_HANDLE;
     }
   PrintFormat("Combinazioni salvate: %d righe in %s\\Files\\%s",
               optRows, TerminalInfoString(TERMINAL_COMMONDATA_PATH), OPT_FILE);
  }

//+------------------------------------------------------------------+
//| Pausa (solo RSI, Rottura e Asia) e slippage simulato: solo nello |
//| Strategy Tester, a ogni apertura conteggia InpSimSlipPerLot $    |
//| per lotto (0.01 lotti -> 0.10 $), per tutte e quattro.           |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
   panelHistDirty = true;
   if(!HistoryDealSelect(trans.deal))
      return;
   if(HistoryDealGetString(trans.deal, DEAL_SYMBOL) != _Symbol)
      return;
   int k = StratIdx((ulong)HistoryDealGetInteger(trans.deal, DEAL_MAGIC));
   if(k < 0)
      return;
   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);

   // Chiusura: conta gli stop consecutivi (il Fibonacci non conta) e, se serve, fa partire la pausa.
   if(entry == DEAL_ENTRY_OUT)
     {
      if(k == 3)
         return;   // il Fibonacci non conta per la pausa
      double p = HistoryDealGetDouble(trans.deal, DEAL_PROFIT) +
                 HistoryDealGetDouble(trans.deal, DEAL_SWAP) +
                 HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
      if(p < 0.0)
        {
         consLosses++;
         if(InpPauseLosses > 0 && consLosses >= InpPauseLosses)
           {
            pauseUntil = TimeCurrent() + (datetime)(InpPauseHours * 3600);
            consLosses = 0;
            pauseCount++;
            PrintFormat("Pausa di %d ore dopo %d stop consecutivi", InpPauseHours, InpPauseLosses);
           }
        }
      else
         consLosses = 0;
      return;
     }

   if(entry != DEAL_ENTRY_IN)
      return;
   if(InpSimSlipPerLot <= 0.0 || !MQLInfoInteger(MQL_TESTER))
      return;
   slip[k] += NormalizeDouble(InpSimSlipPerLot * HistoryDealGetDouble(trans.deal, DEAL_VOLUME), 2);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   // Filtro notizie: dal vivo ricarica il calendario ogni ora; chiusura facoltativa nella finestra.
   if(InpNewsFilter)
     {
      // ricarica ogni ora; se il calendario non era disponibile riprova ogni minuto
      if(!MQLInfoInteger(MQL_TESTER) && TimeCurrent() - newsLoadedAt > (newsCount > 0 ? 3600 : 60))
         LoadNews();
      if(InpNewsClose && NewsBlocked(TimeCurrent()))
         CloseAllForNews();
     }

   // Ogni strategia valuta il segnale alla chiusura di una candela del proprio timeframe.
   // La candela e' segnata come valutata solo se i dati erano pronti (altrimenti si riprova).
   if(gUseRsi)
     {
      datetime rsiBar = iTime(_Symbol, RSI_TF, 0);
      if(rsiBar != 0 && rsiBar != rsiLastBar)
        {
         if(CheckRsi(rsiBar))
            rsiLastBar = rsiBar;
        }
     }

   if(InpUseBrk)
     {
      datetime brkBar = iTime(_Symbol, BRK_TF, 0);
      if(brkBar != 0 && brkBar != brkLastBar)
        {
         if(CheckBreakout(brkBar))
            brkLastBar = brkBar;
        }
     }

   if(gUseAsia)
     {
      datetime asiaBar = iTime(_Symbol, ASIA_TF, 0);
      if(asiaBar != 0 && asiaBar != asiaLastBar)
        {
         if(CheckAsia(asiaBar))
            asiaLastBar = asiaBar;
        }
     }

   if(InpUseFib)
      FbOnTick();
  }

//+------------------------------------------------------------------+
//| Strategia 3: range asiatico. Massimo e minimo tra le 01:00 e le  |
//| 09:00 (ora del server); entra alla prima candela M5 che chiude   |
//| fuori dal range, entro le 13:00. Un solo segnale al giorno.      |
//| Ritorna false solo se i dati non sono pronti.                    |
//+------------------------------------------------------------------+
bool CheckAsia(const datetime barTime)
  {
   datetime dayStart = iTime(_Symbol, PERIOD_D1, 0);
   if(dayStart == 0)
      return(false);
   if(asiaDay == dayStart)
      return(true);

   MqlDateTime t;
   TimeToStruct(barTime, t);
   if(t.hour < gAsiaEndHour || t.hour >= gAsiaLastHour)
      return(true);

   double hi[], lo[], cl[];
   datetime from = dayStart + (datetime)(gAsiaStartHour * 3600);
   datetime to   = dayStart + (datetime)(gAsiaEndHour * 3600 - 1);
   int nh = CopyHigh(_Symbol, ASIA_TF, from, to, hi);
   int nl = CopyLow(_Symbol, ASIA_TF, from, to, lo);
   if(nh < 2 || nl < 2 || CopyClose(_Symbol, ASIA_TF, 1, 1, cl) != 1)
      return(true);

   double upper = hi[ArrayMaximum(hi)];
   double lower = lo[ArrayMinimum(lo)];

   // Range troppo stretto o troppo largo: niente segnale per tutto il giorno.
   double width = upper - lower;
   if((gAsiaMinRange > 0.0 && width < gAsiaMinRange) || (gAsiaMaxRange > 0.0 && width > gAsiaMaxRange))
     {
      asiaDay = dayStart;
      return(true);
     }

   bool buySignal  = (cl[0] > upper);
   bool sellSignal = (cl[0] < lower);
   if(!buySignal && !sellSignal)
      return(true);

   // Filtro trend H1: una rottura contro il trend non conta, si aspetta quella a favore.
   if(gAsiaH1Filter)
     {
      bool ready = true;
      if(!H1TrendOk(buySignal, ready))
         return(ready ? true : NotReady(barTime, "EMA H1"));
     }

   asiaDay = dayStart;   // un solo segnale al giorno, anche se i filtri lo scartano
   OpenTrade(buySignal, gAsiaSlPips, gAsiaTpPips, InpAsiaMagic, "ASIA");
   return(true);
  }

//+------------------------------------------------------------------+
//| Strategia 1: l'RSI esce dalla zona (rientra sotto 70 o sopra 30) |
//| nella direzione delle EMA 50/200 su M5 e su H1.                  |
//| Ritorna false solo se i dati non sono pronti.                    |
//+------------------------------------------------------------------+
bool CheckRsi(const datetime barTime)
  {
   double rsi[];
   ArraySetAsSeries(rsi, true);
   // rsi[0] = ultima candela chiusa, rsi[1] = quella precedente
   if(BarsCalculated(rsiHandle) < gRsiPeriod + 3 ||
      CopyBuffer(rsiHandle, 0, 1, 2, rsi) != 2 ||
      rsi[0] == EMPTY_VALUE || rsi[1] == EMPTY_VALUE)
      return(NotReady(barTime, "RSI"));

   double sellLevel = gRsiLevel;
   double buyLevel  = 100.0 - gRsiLevel;
   bool sellSignal = (rsi[1] >= sellLevel && rsi[0] < sellLevel);
   bool buySignal  = (rsi[1] <= buyLevel  && rsi[0] > buyLevel);
   if(!sellSignal && !buySignal)
      return(true);

   // Filtro EMA sul timeframe dell'RSI: si opera solo a favore di trend.
   if(gRsiEmaFilter)
     {
      double emaFast[], emaSlow[];
      if(BarsCalculated(emaFastHandle) < EMA_SLOW_PERIOD + 2 ||
         BarsCalculated(emaSlowHandle) < EMA_SLOW_PERIOD + 2 ||
         CopyBuffer(emaFastHandle, 0, 1, 1, emaFast) != 1 ||
         CopyBuffer(emaSlowHandle, 0, 1, 1, emaSlow) != 1 ||
         emaFast[0] == EMPTY_VALUE || emaSlow[0] == EMPTY_VALUE)
         return(NotReady(barTime, "EMA"));

      bool emaOk = buySignal ? (emaFast[0] > emaSlow[0]) : (emaFast[0] < emaSlow[0]);
      if(!emaOk)
         return(true);
     }

   if(gRsiH1Filter)
     {
      bool ready = true;
      if(!H1TrendOk(buySignal, ready))
         return(ready ? true : NotReady(barTime, "EMA H1"));
     }

   OpenTrade(buySignal, gRsiSlPips, gRsiTpPips, InpRsiMagic, "RSI");
   return(true);
  }

//+------------------------------------------------------------------+
//| Strategia 2: l'ultima candela M15 chiude sopra il massimo (BUY)  |
//| o sotto il minimo (SELL) delle 24 candele precedenti, a favore   |
//| del trend H1 e solo se l'ADX indica un trend abbastanza forte.   |
//| Ritorna false solo se i dati non sono pronti.                    |
//+------------------------------------------------------------------+
bool CheckBreakout(const datetime barTime)
  {
   double hi[], lo[], cl[];
   int n = CHANNEL_BARS;
   if(CopyHigh(_Symbol, BRK_TF, 2, n, hi) != n ||
      CopyLow(_Symbol, BRK_TF, 2, n, lo) != n ||
      CopyClose(_Symbol, BRK_TF, 1, 1, cl) != 1)
      return(NotReady(barTime, "canale"));

   double upper = hi[ArrayMaximum(hi)];
   double lower = lo[ArrayMinimum(lo)];

   bool buySignal  = (cl[0] > upper);
   bool sellSignal = (cl[0] < lower);
   if(!buySignal && !sellSignal)
      return(true);

   bool ready = true;
   if(!H1TrendOk(buySignal, ready))
      return(ready ? true : NotReady(barTime, "EMA H1"));

   // Filtro ADX sull'ultima candela chiusa.
   if(InpBrkAdxMin > 0.0)
     {
      double adx[];
      if(BarsCalculated(adxHandle) < 2 * ADX_PERIOD + 2 ||
         CopyBuffer(adxHandle, 0, 1, 1, adx) != 1 ||
         adx[0] == EMPTY_VALUE)
         return(NotReady(barTime, "ADX"));
      if(adx[0] < InpBrkAdxMin)
         return(true);
     }

   OpenTrade(buySignal, InpBrkSlPips, InpBrkTpPips, InpBrkMagic, "ROT");
   return(true);
  }

//+------------------------------------------------------------------+
//| Filtro trend H1 sull'ultima candela H1 chiusa: BUY solo se       |
//| EMA 50 > EMA 200, SELL solo se sotto.                            |
//| ready = false se le EMA H1 non sono ancora disponibili.          |
//+------------------------------------------------------------------+
bool H1TrendOk(const bool isBuy, bool &ready)
  {
   ready = true;
   double h1Fast[], h1Slow[];
   if(BarsCalculated(h1FastHandle) < EMA_SLOW_PERIOD + 2 ||
      BarsCalculated(h1SlowHandle) < EMA_SLOW_PERIOD + 2 ||
      CopyBuffer(h1FastHandle, 0, 1, 1, h1Fast) != 1 ||
      CopyBuffer(h1SlowHandle, 0, 1, 1, h1Slow) != 1 ||
      h1Fast[0] == EMPTY_VALUE || h1Slow[0] == EMPTY_VALUE)
     {
      ready = false;
      return(false);
     }
   return(isBuy ? (h1Fast[0] > h1Slow[0]) : (h1Fast[0] < h1Slow[0]));
  }

//+------------------------------------------------------------------+
bool NotReady(const datetime barTime, const string what)
  {
   if(lastWarnBar != barTime)
     {
      lastWarnBar = barTime;
      Print(what, " non ancora disponibile, riprovo al prossimo tick");
     }
   return(false);
  }

//+------------------------------------------------------------------+
//| Lotto fisso, oppure progressivo: lotto x (saldo / X), per        |
//| difetto, minimo un lotto. Uguale per tutte le strategie.         |
//+------------------------------------------------------------------+
double CalcLots()
  {
   double lots = InpLots;
   if(InpBalancePerLot > 0.0)
     {
      double steps = MathFloor(AccountInfoDouble(ACCOUNT_BALANCE) / InpBalancePerLot);
      lots = InpLots * MathMax(1.0, steps);
     }
   return(NormalizeLots(lots));
  }

//+------------------------------------------------------------------+
//| Apre un trade per la strategia indicata dal magic number         |
//| (RSI, Rottura, Asia). Ogni strategia tiene al massimo una        |
//| posizione aperta.                                                |
//+------------------------------------------------------------------+
void OpenTrade(const bool isBuy, const int slPips, const int tpPips,
               const ulong magic, const string tag)
  {
   string side = isBuy ? "BUY" : "SELL";

   if(CountPositions(magic) > 0)
      return;   // ogni strategia tiene al massimo una posizione aperta
   if(InpNewsFilter && NewsBlocked(TimeCurrent()))
     {
      newsSkips++;
      return;   // vicino a una notizia
     }
   if(pauseUntil > 0 && TimeCurrent() < pauseUntil)
      return;   // pausa dopo una serie di stop

   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   long spread = (long)MathRound((ask - bid) / point);
   if(InpMaxSpreadPts > 0 && spread >= InpMaxSpreadPts)
     {
      PrintFormat("%s %s ignorato: spread %I64d points >= %d", tag, side, spread, InpMaxSpreadPts);
      return;
     }

   // ATR giornaliero dell'ultimo giorno chiuso (in $ di prezzo).
   double atrBuf[];
   double atr = 0.0;
   if(BarsCalculated(atrHandle) >= ATR_PERIOD + 2 &&
      CopyBuffer(atrHandle, 0, 1, 1, atrBuf) == 1 && atrBuf[0] != EMPTY_VALUE)
      atr = atrBuf[0];
   if(atr <= 0.0 && InpMinAtrUsd > 0.0)
     {
      datetime day = iTime(_Symbol, PERIOD_D1, 0);
      if(atrWarnDay != day)
        {
         atrWarnDay = day;
         Print("ATR giornaliero non ancora disponibile: segnale ignorato");
        }
      return;
     }
   if(atr > atrMaxSeen)
      atrMaxSeen = atr;
   if(InpMinAtrUsd > 0.0 && atr < InpMinAtrUsd)
      return;   // mercato troppo fermo rispetto ai costi
   if(atr > 0.0)
     {
      atrSum += atr;
      atrCount++;
     }

   double lots = CalcLots();

   double slDist = slPips * PIP_SIZE;
   double tpDist = tpPips * PIP_SIZE;
   double sl = 0.0, tp = 0.0;
   if(isBuy)
     {
      sl = NormalizeDouble(ask - slDist, digits);
      tp = NormalizeDouble(ask + tpDist, digits);
     }
   else
     {
      sl = NormalizeDouble(bid + slDist, digits);
      tp = NormalizeDouble(bid - tpDist, digits);
     }

   if(!StopsAllowed(isBuy, ask, bid, sl, tp, point))
     {
      PrintFormat("%s %s ignorato: SL/TP sotto lo stop level del broker", tag, side);
      return;
     }

   trade.SetExpertMagicNumber(magic);
   string comment = tag + " " + side;
   bool ok = isBuy ? trade.Buy(lots, _Symbol, ask, sl, tp, comment)
                   : trade.Sell(lots, _Symbol, bid, sl, tp, comment);
   if(!ok)
      PrintFormat("%s %s fallito: %d %s", tag, side, trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
//| Verifica la distanza minima degli stop richiesta dal broker.     |
//| BUY:  SL e TP si misurano dal Bid.  SELL: SL e TP dall'Ask.      |
//+------------------------------------------------------------------+
bool StopsAllowed(const bool isBuy, const double ask, const double bid,
                  const double sl, const double tp, const double point)
  {
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(minDist <= 0.0)
      return(true);

   double eps = point * 0.5;
   if(isBuy)
     {
      if((bid - sl) < minDist - eps) return(false);
      if((tp - bid) < minDist - eps) return(false);
     }
   else
     {
      if((sl - ask) < minDist - eps) return(false);
      if((ask - tp) < minDist - eps) return(false);
     }
   return(true);
  }

//+------------------------------------------------------------------+
int CountPositions(const ulong magic)
  {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == magic)
         count++;
     }
   return(count);
  }

//+------------------------------------------------------------------+
double NormalizeLots(double lots)
  {
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step > 0.0)
      lots = MathFloor(lots / step + 1e-9) * step;
   lots = MathMax(minLot, MathMin(maxLot, lots));
   return(NormalizeDouble(lots, 2));
  }
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| Carica le notizie USD. Nel tester dal file in Common\Files       |
//| (creato dallo script GoldTitan_ExportNews), dal vivo dal         |
//| calendario di MT5 (da ieri a 7 giorni avanti).                   |
//+------------------------------------------------------------------+
bool LoadNews()
  {
   newsLoadedAt = TimeCurrent();
   datetime tmp[];
   int n = 0;

   if(MQLInfoInteger(MQL_TESTER))
     {
      int h = FileOpen(NEWS_FILE, FILE_READ | FILE_SHARE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON, ';');
      if(h == INVALID_HANDLE)
         return(false);
      while(!FileIsEnding(h))
        {
         string ts  = FileReadString(h);
         if(FileIsEnding(h) && ts == "")
            break;
         string imp = FileReadString(h);
         while(!FileIsLineEnding(h) && !FileIsEnding(h))
            FileReadString(h);   // nome della notizia: non serve
         long t = StringToInteger(ts);
         int  i = (int)StringToInteger(imp);
         if(t <= 0)
            continue;
         if(i == (int)CALENDAR_IMPORTANCE_HIGH || (InpNewsMedium && i == (int)CALENDAR_IMPORTANCE_MODERATE))
           {
            ArrayResize(tmp, n + 1, 1000);
            tmp[n++] = (datetime)t;
           }
        }
      FileClose(h);
     }
   else
     {
      MqlCalendarValue values[];
      datetime from = TimeTradeServer() - 86400;
      datetime to   = TimeTradeServer() + 7 * 86400;
      if(CalendarValueHistory(values, from, to, NULL, "USD") <= 0)
         return(false);
      for(int k = 0; k < ArraySize(values); k++)
        {
         MqlCalendarEvent ev;
         if(!CalendarEventById(values[k].event_id, ev))
            continue;
         if(ev.importance == CALENDAR_IMPORTANCE_HIGH || (InpNewsMedium && ev.importance == CALENDAR_IMPORTANCE_MODERATE))
           {
            ArrayResize(tmp, n + 1, 100);
            tmp[n++] = values[k].time;
           }
        }
     }

   ArraySort(tmp);
   ArrayResize(newsTimes, n);
   for(int k = 0; k < n; k++)
      newsTimes[k] = tmp[k];
   newsCount = n;
   newsPtr   = 0;
   if(MQLInfoInteger(MQL_TESTER))
      PrintFormat("Filtro notizie: %d notizie caricate dal file", n);
   else
      PrintFormat("Filtro notizie: %d notizie USD importanti nei prossimi 7 giorni (finestra -%d / +%d min)",
                  n, InpNewsBeforeMin, InpNewsAfterMin);
   return(true);
  }

//+------------------------------------------------------------------+
//| true se 'now' e' dentro la finestra di una notizia.              |
//+------------------------------------------------------------------+
bool NewsBlocked(const datetime now)
  {
   if(newsCount == 0)
      return(false);
   int after  = InpNewsAfterMin * 60;
   int before = InpNewsBeforeMin * 60;
   while(newsPtr < newsCount && newsTimes[newsPtr] + after < now)
      newsPtr++;
   if(newsPtr >= newsCount)
      return(false);
   return(now >= newsTimes[newsPtr] - before);
  }

//+------------------------------------------------------------------+
//| Chiude le posizioni nella finestra delle notizie: RSI, Rottura,  |
//| Asia e, solo se InpFbNews, anche il Fibonacci.                   |
//+------------------------------------------------------------------+
void CloseAllForNews()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      int k = StratIdx((ulong)PositionGetInteger(POSITION_MAGIC));
      if(k < 0 || (k == 3 && !InpFbNews))
         continue;
      if(trade.PositionClose(ticket))
         newsCloses++;
      else
         PrintFormat("Chiusura per notizia fallita: %d %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }
  }
//+------------------------------------------------------------------+

//+==================================================================+
//|  FIBONACCI (da Kairos_Fibonacci_M1_XAU, logica invariata)         |
//+==================================================================+
#define MAX_SWINGS 40

CTrade   g_fbTrade;
int      g_fbATR = INVALID_HANDLE;
int      g_fbEMA = INVALID_HANDLE;
datetime g_fbLastBar = 0;

bool     g_fbLegOk   = false;  // c'e' un impulso
bool     g_fbLegDead = true;   // impulso non piu' tradabile
int      g_fbDir     = 0;      // +1 impulso in salita (cerca buy), -1 in discesa (cerca sell)
double   g_fbH = 0, g_fbL = 0;
datetime g_fbTH = 0, g_fbTL = 0;
double   g_fbAtr = 0;
double   g_fbExtreme = 0;      // punto piu' profondo del ritracciamento finora
string   g_fbStatus = "avvio";

double   g_fbLv[3] = {0.382, 0.5, 0.618};
bool     g_fbUsed[3];          // livello gia' usato su questo impulso
ulong    g_fbPend[3];          // ticket del limit per livello

void Log(string s)
  {
   if(!g_quiet) Print(s);
  }

int HHMM(datetime t)
  {
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return dt.hour * 100 + dt.min;
  }

bool IsFriday(datetime t)
  {
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return dt.day_of_week == 5;
  }

double Norm(double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0)
      return NormalizeDouble(p, _Digits);
   return NormalizeDouble(MathRound(p / ts) * ts, _Digits);
  }

int FbInit()
  {
   if(!InpFbLvl382 && !InpFbLvl500 && !InpFbLvl618)
     {
      Print("Fibonacci: nessun livello attivo");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpFbSwingDepth < 1 || InpFbLookback < 4 * InpFbSwingDepth + 10 || InpFbSLFib <= 1.0)
      return INIT_PARAMETERS_INCORRECT;

   g_fbTrade.SetExpertMagicNumber(InpFbMagic);
   g_fbTrade.SetTypeFillingBySymbol(_Symbol);
   g_fbTrade.SetDeviationInPoints(FB_DEVIATION);

   g_fbATR = iATR(_Symbol, PERIOD_M1, 14);
   g_fbEMA = iMA(_Symbol, PERIOD_M1, InpFbEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   if(g_fbATR == INVALID_HANDLE || g_fbEMA == INVALID_HANDLE)
     {
      Print("Fibonacci: errore creazione indicatori ", GetLastError());
      return INIT_FAILED;
     }
   ArrayInitialize(g_fbUsed, false);
   ArrayInitialize(g_fbPend, 0);
   FbDeleteStrayOrders();
   return INIT_SUCCEEDED;
  }

void FbDeinit()
  {
   if(!InpUseFib)
      return;
   FbCancelPendings();
   if(g_fbATR != INVALID_HANDLE) IndicatorRelease(g_fbATR);
   if(g_fbEMA != INVALID_HANDLE) IndicatorRelease(g_fbEMA);
   ObjectsDeleteAll(0, "FIBM1_");
  }

bool FbInSession()
  {
   int hm = HHMM(TimeCurrent());
   return hm >= InpFbHourStart && hm < InpFbHourEnd;
  }

void FbOnTick()
  {
   // weekend: il venerdi' sera chiude, cosi' nessun trade resta aperto sul gap del lunedi'
   if(InpFbWeekend && IsFriday(TimeCurrent()) && HHMM(TimeCurrent()) >= InpFbFriClose)
      FbCloseAll();

   datetime bt = iTime(_Symbol, PERIOD_M1, 0);
   bool newBar = (bt != g_fbLastBar && bt != 0);
   if(newBar)
     {
      g_fbLastBar = bt;
      FbUpdateLeg();
     }

   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk))
      return;

   if(g_fbLegOk && !g_fbLegDead)
     {
      double slLevel = FbPrice(InpFbSLFib);
      if(g_fbDir > 0)
        {
         g_fbExtreme = MathMin(g_fbExtreme, tk.bid);
         if(tk.bid > g_fbH)           FbKill("nuovo massimo oltre lo swing, attendo il prossimo");
         else if(tk.bid <= slLevel)   FbKill("prezzo oltre il livello SL, impulso annullato");
        }
      else
        {
         g_fbExtreme = MathMax(g_fbExtreme, tk.bid);
         if(tk.bid < g_fbL)           FbKill("nuovo minimo oltre lo swing, attendo il prossimo");
         else if(tk.bid >= slLevel)   FbKill("prezzo oltre il livello SL, impulso annullato");
        }
     }

   if(!g_fbLegOk || g_fbLegDead)
     {
      FbCancelPendings();
      return;
     }
   if(!FbInSession())
     {
      FbCancelPendings();
      g_fbStatus = "fuori orario";
      return;
     }
   // filtro notizie solo se richiesto (il bot originale non lo aveva)
   if(InpFbNews && InpNewsFilter && NewsBlocked(TimeCurrent()))
     {
      FbCancelPendings();
      return;
     }

   switch(InpFbEntryMode)
     {
      case ENTRY_LIMIT:  FbManageLimits(tk); break;
      case ENTRY_MARKET: FbCheckTouch(tk);   break;
      default:           if(newBar) FbCheckConfirm(tk); break;
     }
  }

//--- impulso: ultimo swing low/high confermati con i frattali -------
bool FbIsSwingHigh(const double &hi[], int i, int n)
  {
   for(int k = 1; k <= n; k++)
      if(hi[i + k] > hi[i] || hi[i - k] >= hi[i])
         return false;
   return true;
  }

bool FbIsSwingLow(const double &lo[], int i, int n)
  {
   for(int k = 1; k <= n; k++)
      if(lo[i + k] < lo[i] || lo[i - k] <= lo[i])
         return false;
   return true;
  }

int ArgMax(const double &v[], int from, int to)
  {
   int best = from;
   for(int i = from; i <= to; i++)
      if(v[i] > v[best]) best = i;
   return best;
  }

int ArgMin(const double &v[], int from, int to)
  {
   int best = from;
   for(int i = from; i <= to; i++)
      if(v[i] < v[best]) best = i;
   return best;
  }

void FbUpdateLeg()
  {
   int n = InpFbLookback, N = InpFbSwingDepth;
   double hi[], lo[], cl[];
   datetime tm[];
   ArraySetAsSeries(hi, true);
   ArraySetAsSeries(lo, true);
   ArraySetAsSeries(cl, true);
   ArraySetAsSeries(tm, true);
   if(CopyHigh(_Symbol, PERIOD_M1, 0, n, hi) < n || CopyLow(_Symbol, PERIOD_M1, 0, n, lo) < n ||
      CopyClose(_Symbol, PERIOD_M1, 0, n, cl) < n || CopyTime(_Symbol, PERIOD_M1, 0, n, tm) < n)
      return;

   double a[];
   if(CopyBuffer(g_fbATR, 0, 1, 1, a) == 1)
      g_fbAtr = a[0];

   // swing dal piu' recente al piu' vecchio
   int sh[MAX_SWINGS], sl[MAX_SWINGS];
   int nsh = 0, nsl = 0;
   for(int i = N + 1; i < n - N && (nsh < MAX_SWINGS || nsl < MAX_SWINGS); i++)
     {
      if(nsh < MAX_SWINGS && FbIsSwingHigh(hi, i, N)) sh[nsh++] = i;
      if(nsl < MAX_SWINGS && FbIsSwingLow(lo, i, N))  sl[nsl++] = i;
     }
   if(nsh == 0 || nsl == 0 || sh[0] == sl[0])
     {
      FbNoLeg("nessuno swing chiaro");
      return;
     }

   int dir = (sl[0] > sh[0]) ? 1 : -1;
   int e, s;   // e = fine dell'impulso (indice), s = inizio
   double H, L;
   if(dir > 0)
     {
      e = ArgMax(hi, sh[0], sl[0]);
      s = ArgMin(lo, e, sl[0]);
      H = hi[e];
      L = lo[s];
     }
   else
     {
      e = ArgMin(lo, sl[0], sh[0]);
      s = ArgMax(hi, e, sh[0]);
      L = lo[e];
      H = hi[s];
     }
   datetime tH = (dir > 0) ? tm[e] : tm[s];
   datetime tL = (dir > 0) ? tm[s] : tm[e];

   bool same = g_fbLegOk && dir == g_fbDir && tH == g_fbTH && tL == g_fbTL;
   if(!same)
     {
      FbCancelPendings();
      g_fbLegOk   = true;
      g_fbLegDead = false;
      g_fbDir     = dir;
      g_fbH = H; g_fbL = L; g_fbTH = tH; g_fbTL = tL;
      ArrayInitialize(g_fbUsed, false);
      ArrayInitialize(g_fbPend, 0);
      g_fbStatus = StringFormat("impulso %s %s -> %s", dir > 0 ? "rialzista" : "ribassista",
                                DoubleToString(dir > 0 ? L : H, _Digits), DoubleToString(dir > 0 ? H : L, _Digits));

      FbDraw();
      string why = "";
      if(!FbLegValid(dir, s, hi, lo, sh, nsh, sl, nsl, why))
         FbKill(why);   // impulso scartato: il disegno diventa grigio
     }
   if(g_fbLegDead)
      return;

   // cosa e' successo dopo la fine dell'impulso
   g_fbExtreme = (dir > 0) ? H : L;
   for(int i = 1; i < e; i++)
     {
      if(dir > 0)
        {
         if(hi[i] > H) { FbKill("nuovo massimo oltre lo swing, attendo il prossimo"); return; }
         if(cl[i] < L) { FbKill("chiusura sotto lo swing low, impulso annullato"); return; }
         g_fbExtreme = MathMin(g_fbExtreme, lo[i]);
        }
      else
        {
         if(lo[i] < L) { FbKill("nuovo minimo oltre lo swing, attendo il prossimo"); return; }
         if(cl[i] > H) { FbKill("chiusura sopra lo swing high, impulso annullato"); return; }
         g_fbExtreme = MathMax(g_fbExtreme, hi[i]);
        }
     }
   if(e > InpFbMaxLegBars)
      FbKill("impulso troppo vecchio");
  }

bool FbLegValid(int dir, int s, const double &hi[], const double &lo[],
                const int &sh[], int nsh, const int &sl[], int nsl, string &why)
  {
   double R = g_fbH - g_fbL;
   if(R <= 0 || R < InpFbMinLegATR * g_fbAtr || R < InpFbMinLegPts * _Point)
     {
      why = "impulso troppo piccolo";
      return false;
     }

   if(InpFbTrend == TREND_EMA)
     {
      double e1[], es[];
      if(CopyBuffer(g_fbEMA, 0, 1, 1, e1) != 1 || CopyBuffer(g_fbEMA, 0, s, 1, es) != 1)
        {
         why = "EMA non disponibile";
         return false;
        }
      if((dir > 0 && e1[0] <= es[0]) || (dir < 0 && e1[0] >= es[0]))
        {
         why = "EMA contro l'impulso";
         return false;
        }
     }
   else if(InpFbTrend == TREND_STRUCT)
     {
      // swing precedenti, piu' vecchi dell'inizio dell'impulso
      int ph = -1, pl = -1;
      for(int i = 0; i < nsh; i++) if(sh[i] > s) { ph = sh[i]; break; }
      for(int i = 0; i < nsl; i++) if(sl[i] > s) { pl = sl[i]; break; }
      if(ph < 0 || pl < 0)
        {
         why = "struttura non disponibile";
         return false;
        }
      bool ok = (dir > 0) ? (g_fbH > hi[ph] && g_fbL > lo[pl]) : (g_fbL < lo[pl] && g_fbH < hi[ph]);
      if(!ok)
        {
         why = (dir > 0) ? "niente massimi e minimi crescenti" : "niente massimi e minimi decrescenti";
         return false;
        }
     }
   return true;
  }

void FbNoLeg(string why)
  {
   FbCancelPendings();
   g_fbLegOk   = false;
   g_fbLegDead = true;
   g_fbStatus  = why;
  }

void FbKill(string why)
  {
   bool wasAlive = !g_fbLegDead;
   g_fbLegDead = true;
   g_fbStatus  = why;
   FbCancelPendings();
   if(wasAlive)
      FbDrawDead();
  }

//--- livelli, SL e TP -----------------------------------------------
// 0 = fine dell'impulso, 1 = inizio, 1.1 = oltre l'inizio, -0.272 = estensione
double FbPrice(double f)
  {
   double R = g_fbH - g_fbL;
   return (g_fbDir > 0) ? g_fbH - f * R : g_fbL + f * R;
  }

bool FbLevelOn(int k)
  {
   return (k == 0) ? InpFbLvl382 : (k == 1) ? InpFbLvl500 : InpFbLvl618;
  }

string FbLevelCmt(int k)
  {
   return (k == 0) ? "FIB382" : (k == 1) ? "FIB500" : "FIB618";
  }

bool FbCalcSLTP(double entry, double &sl, double &tp)
  {
   int dir = g_fbDir;
   sl = FbPrice(InpFbSLFib);
   double risk = MathAbs(entry - sl);
   if(risk <= 0 || (dir > 0 && sl >= entry) || (dir < 0 && sl <= entry))
      return false;

   switch(InpFbTPMode)
     {
      case TP_RR1:    tp = entry + dir * 1.0 * risk; break;
      case TP_RR15:   tp = entry + dir * 1.5 * risk; break;
      case TP_RR2:    tp = entry + dir * 2.0 * risk; break;
      case TP_RR3:    tp = entry + dir * 3.0 * risk; break;
      case TP_SWING:  tp = FbPrice(0.0);    break;
      case TP_EXT272: tp = FbPrice(-0.272); break;
      case TP_EXT618: tp = FbPrice(-0.618); break;
      default:        tp = entry + dir * InpFbTPATRMult * g_fbAtr; break;
     }
   if((dir > 0 && tp <= entry) || (dir < 0 && tp >= entry))
      return false;

   double minD = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(MathAbs(entry - sl) < minD || MathAbs(tp - entry) < minD)
      return false;

   sl = Norm(sl);
   tp = Norm(tp);
   return true;
  }

//--- ingresso con ordini limit --------------------------------------
void FbManageLimits(const MqlTick &tk)
  {
   double minD = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   for(int k = 0; k < 3; k++)
     {
      if(!FbLevelOn(k) || g_fbUsed[k])
         continue;
      if(g_fbPend[k] != 0)
        {
         if(OrderSelect(g_fbPend[k]))
            continue;           // ancora in attesa
         g_fbUsed[k] = true;    // eseguito (o tolto a mano): non lo rimette
         g_fbPend[k] = 0;
         continue;
        }

      double px = Norm(FbPrice(g_fbLv[k]));
      // il prezzo e' gia' sul livello o oltre: il limit non si puo' piu' mettere
      if((g_fbDir > 0 && tk.ask <= px + minD) || (g_fbDir < 0 && tk.bid >= px - minD))
        {
         g_fbUsed[k] = true;
         continue;
        }
      double sl, tp;
      if(!FbCalcSLTP(px, sl, tp))
        {
         g_fbUsed[k] = true;
         continue;
        }
      double lots = CalcLots();
      bool ok = (g_fbDir > 0)
                ? g_fbTrade.BuyLimit(lots, px, _Symbol, sl, tp, ORDER_TIME_GTC, 0, FbLevelCmt(k))
                : g_fbTrade.SellLimit(lots, px, _Symbol, sl, tp, ORDER_TIME_GTC, 0, FbLevelCmt(k));
      if(ok && g_fbTrade.ResultOrder() > 0)
         g_fbPend[k] = g_fbTrade.ResultOrder();
      else
        {
         g_fbUsed[k] = true;
         Log(StringFormat("Fibonacci: limit %s rifiutato: %d %s", FbLevelCmt(k), g_fbTrade.ResultRetcode(), g_fbTrade.ResultRetcodeDescription()));
        }
     }
  }

void FbCancelPendings()
  {
   for(int k = 0; k < 3; k++)
     {
      if(g_fbPend[k] == 0)
         continue;
      ulong t = g_fbPend[k];
      g_fbPend[k] = 0;
      if(OrderSelect(t))
         g_fbTrade.OrderDelete(t);
      else
         g_fbUsed[k] = true;   // nel frattempo e' stato eseguito
     }
  }

void FbCloseAll()
  {
   for(int k = PositionsTotal() - 1; k >= 0; k--)
     {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpFbMagic) continue;
      if(g_fbTrade.PositionClose(tk))
         Log("Fibonacci: posizione chiusa prima del weekend");
     }
  }

void FbDeleteStrayOrders()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t > 0 && (ulong)OrderGetInteger(ORDER_MAGIC) == InpFbMagic && OrderGetString(ORDER_SYMBOL) == _Symbol)
         g_fbTrade.OrderDelete(t);
     }
  }

//--- ingresso a mercato al tocco del livello ------------------------
void FbCheckTouch(const MqlTick &tk)
  {
   double tol = InpFbTouchTol * (g_fbH - g_fbL);
   for(int k = 0; k < 3; k++)
     {
      if(!FbLevelOn(k) || g_fbUsed[k])
         continue;
      double px = FbPrice(g_fbLv[k]);
      if(g_fbDir > 0)
        {
         if(tk.bid > px) continue;                                 // non ancora arrivato
         if(tk.bid < px - tol) { g_fbUsed[k] = true; continue; }   // gia' troppo oltre: perso
        }
      else
        {
         if(tk.bid < px) continue;
         if(tk.bid > px + tol) { g_fbUsed[k] = true; continue; }
        }
      FbOpenMarket(k, tk);
     }
  }

//--- ingresso a mercato dopo pin bar / engulfing nella zona ---------
void FbCheckConfirm(const MqlTick &tk)
  {
   bool bull = (g_fbDir > 0);
   bool pat  = false;
   if(InpFbEntryMode == ENTRY_PINBAR || InpFbEntryMode == ENTRY_PIN_OR_ENG) pat = pat || FbIsPinBar(bull);
   if(InpFbEntryMode == ENTRY_ENGULF || InpFbEntryMode == ENTRY_PIN_OR_ENG) pat = pat || FbIsEngulfing(bull);
   if(!pat)
      return;

   // la candela di conferma deve stare nella zona di ritracciamento
   double zone = FbPrice(0.382);
   if(bull ? iLow(_Symbol, PERIOD_M1, 1) > zone : iHigh(_Symbol, PERIOD_M1, 1) < zone)
      return;

   // un solo trade per conferma, sul livello piu' profondo raggiunto e non ancora usato
   int pick = -1;
   for(int k = 0; k < 3; k++)
     {
      if(!FbLevelOn(k))
         continue;
      double px = FbPrice(g_fbLv[k]);
      bool reached = bull ? (g_fbExtreme <= px) : (g_fbExtreme >= px);
      if(reached)
         pick = k;
     }
   if(pick < 0 || g_fbUsed[pick])
      return;
   for(int k = 0; k <= pick; k++)
      g_fbUsed[k] = true;
   FbOpenMarket(pick, tk);
  }

bool FbIsPinBar(bool bull)
  {
   double o = iOpen(_Symbol, PERIOD_M1, 1), h = iHigh(_Symbol, PERIOD_M1, 1);
   double l = iLow(_Symbol, PERIOD_M1, 1),  c = iClose(_Symbol, PERIOD_M1, 1);
   double range = h - l;
   if(range <= 0)
      return false;
   double body  = MathAbs(c - o);
   double lower = MathMin(o, c) - l;
   double upper = h - MathMax(o, c);
   if(bull)
      return lower >= InpFbPinWick * range && lower >= 2.0 * body;
   return upper >= InpFbPinWick * range && upper >= 2.0 * body;
  }

bool FbIsEngulfing(bool bull)
  {
   double o1 = iOpen(_Symbol, PERIOD_M1, 1), c1 = iClose(_Symbol, PERIOD_M1, 1);
   double o2 = iOpen(_Symbol, PERIOD_M1, 2), c2 = iClose(_Symbol, PERIOD_M1, 2);
   if(MathAbs(c1 - o1) <= MathAbs(c2 - o2))
      return false;
   if(bull)
      return c1 > o1 && c2 < o2 && c1 >= o2 && o1 <= c2;
   return c1 < o1 && c2 > o2 && c1 <= o2 && o1 >= c2;
  }

void FbOpenMarket(int k, const MqlTick &tk)
  {
   g_fbUsed[k] = true;   // un tentativo per livello: niente raffiche di ordini se il broker rifiuta
   double entry = (g_fbDir > 0) ? tk.ask : tk.bid;
   double sl, tp;
   if(!FbCalcSLTP(entry, sl, tp))
      return;
   double lots = CalcLots();
   bool ok = (g_fbDir > 0)
             ? g_fbTrade.Buy(lots, _Symbol, 0, sl, tp, FbLevelCmt(k))
             : g_fbTrade.Sell(lots, _Symbol, 0, sl, tp, FbLevelCmt(k));
   if(!ok)
     {
      Log(StringFormat("Fibonacci: ordine %s rifiutato: %d %s", FbLevelCmt(k), g_fbTrade.ResultRetcode(), g_fbTrade.ResultRetcodeDescription()));
      return;
     }
   double px = g_fbTrade.ResultPrice() > 0 ? g_fbTrade.ResultPrice() : entry;
   Log(StringFormat("Fibonacci %s %s: entrata %s SL %s TP %s (impulso %s -> %s)", FbLevelCmt(k), g_fbDir > 0 ? "BUY" : "SELL",
                    DoubleToString(px, _Digits), DoubleToString(sl, _Digits), DoubleToString(tp, _Digits),
                    DoubleToString(g_fbDir > 0 ? g_fbL : g_fbH, _Digits), DoubleToString(g_fbDir > 0 ? g_fbH : g_fbL, _Digits)));
   FbDrawTrade(k, px, sl, tp);
  }

//--- grafico --------------------------------------------------------
// Fibonacci dell'impulso corrente: si aggiorna a ogni impulso nuovo
void FbDraw()
  {
   if(!g_draw)
      return;
   FbDrawFibo("FIBM1_leg", true, g_fbDir > 0 ? clrDodgerBlue : clrOrangeRed, false);
   ChartRedraw();
  }

// impulso annullato: il disegno resta ma diventa grigio
void FbDrawDead()
  {
   if(!g_draw || ObjectFind(0, "FIBM1_leg") < 0)
      return;
   FbDrawFibo("FIBM1_leg", true, clrDimGray, true);
   ChartRedraw();
  }

void FbDrawFibo(string nm, bool rayRight, color legColor, bool dim)
  {
   ObjectDelete(0, nm);
   // primo punto = inizio dell'impulso (livello 1), secondo = fine (livello 0)
   datetime t1 = (g_fbDir > 0) ? g_fbTL : g_fbTH;
   double   p1 = (g_fbDir > 0) ? g_fbL  : g_fbH;
   datetime t2 = (g_fbDir > 0) ? g_fbTH : g_fbTL;
   double   p2 = (g_fbDir > 0) ? g_fbH  : g_fbL;
   if(!ObjectCreate(0, nm, OBJ_FIBO, 0, t1, p1, t2, p2))
      return;
   double lv[] = {0.0, 0.382, 0.5, 0.618, 1.0, 0.0, -0.272, -0.618};
   lv[5] = InpFbSLFib;
   int cnt = ArraySize(lv);
   ObjectSetInteger(0, nm, OBJPROP_LEVELS, cnt);
   for(int i = 0; i < cnt; i++)
     {
      color c = dim ? clrDimGray : (i == 5 ? clrRed : (lv[i] > 0.3 && lv[i] < 0.7) ? clrGold : clrSilver);
      ObjectSetDouble(0, nm, OBJPROP_LEVELVALUE, i, lv[i]);
      ObjectSetString(0, nm, OBJPROP_LEVELTEXT, i, (dim && i == 0 ? "ANNULLATO " : "") + (i == 5 ? "SL " : "") + DoubleToString(lv[i], 3) + "  %$");
      ObjectSetInteger(0, nm, OBJPROP_LEVELCOLOR, i, c);
     }
   ObjectSetInteger(0, nm, OBJPROP_COLOR, legColor);
   ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, rayRight);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, true);
  }

// a ogni trade Fibonacci lascia sul grafico il suo schema fisso: Fibonacci dell'impulso,
// freccia sull'entrata e scritta con livello, entrata, SL e TP (restano anche dopo la chiusura)
void FbDrawTrade(int k, double entry, double sl, double tp)
  {
   if(!g_draw)
      return;
   datetime now = TimeCurrent();
   string id = "FIBT_" + IntegerToString((long)now) + "_" + IntegerToString(k);
   bool buy = (g_fbDir > 0);
   color c = buy ? clrDodgerBlue : clrOrangeRed;

   FbDrawFibo(id + "_fib", false, c, false);

   string ar = id + "_arrow";
   if(ObjectCreate(0, ar, buy ? OBJ_ARROW_BUY : OBJ_ARROW_SELL, 0, now, entry))
     {
      ObjectSetInteger(0, ar, OBJPROP_COLOR, c);
      ObjectSetInteger(0, ar, OBJPROP_WIDTH, 3);
     }

   string tx = id + "_txt";
   if(ObjectCreate(0, tx, OBJ_TEXT, 0, now, sl))
     {
      ObjectSetString(0, tx, OBJPROP_TEXT, StringFormat("%s %s %s  SL %s  TP %s", FbLevelCmt(k), buy ? "BUY" : "SELL",
                      DoubleToString(entry, _Digits), DoubleToString(sl, _Digits), DoubleToString(tp, _Digits)));
      ObjectSetInteger(0, tx, OBJPROP_COLOR, c);
      ObjectSetInteger(0, tx, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, tx, OBJPROP_ANCHOR, buy ? ANCHOR_LEFT_UPPER : ANCHOR_LEFT_LOWER);
     }
   ChartRedraw();
  }


//+------------------------------------------------------------------+
//| PANNELLO INFORMATIVO                                             |
//| Solo lettura: mostra stato, risultati e condizioni di mercato.   |
//| Non apre, non chiude e non modifica operazioni.                  |
//+------------------------------------------------------------------+
#define PNL_PFX   "GTF_"
#define PNL_W     430
#define PNL_LINEH 15
#define PNL_MAXL  44

//+------------------------------------------------------------------+
void PanelInit()
  {
   panelOn = InpShowPanel && (!MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_VISUAL_MODE))
             && !MQLInfoInteger(MQL_OPTIMIZATION);
   if(!panelOn)
      return;
   string bg = PNL_PFX + "bg";
   if(ObjectFind(0, bg) < 0)
      ObjectCreate(0, bg, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, bg, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, bg, OBJPROP_XDISTANCE, 8);
   ObjectSetInteger(0, bg, OBJPROP_YDISTANCE, 22);
   ObjectSetInteger(0, bg, OBJPROP_XSIZE, PNL_W);
   ObjectSetInteger(0, bg, OBJPROP_YSIZE, 100);
   ObjectSetInteger(0, bg, OBJPROP_BGCOLOR, C'18,18,22');
   ObjectSetInteger(0, bg, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, bg, OBJPROP_COLOR, C'70,70,80');
   ObjectSetInteger(0, bg, OBJPROP_BACK, false);
   ObjectSetInteger(0, bg, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, bg, OBJPROP_HIDDEN, true);
   EventSetTimer(1);
   panelHistDirty = true;
   PanelUpdate();
  }

//+------------------------------------------------------------------+
void PanelDeinit()
  {
   if(!panelOn)
      return;
   EventKillTimer();
   ObjectsDeleteAll(0, PNL_PFX);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
void PanelLine(const int i, const string text, const color clr)
  {
   if(i >= PNL_MAXL)
      return;
   string name = PNL_PFX + "l" + IntegerToString(i);
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 18);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
     }
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, 30 + i * PNL_LINEH);
   ObjectSetString(0, name, OBJPROP_TEXT, text == "" ? " " : text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
  }

//+------------------------------------------------------------------+
//| Rilegge lo storico (solo deal del bot su questo simbolo).        |
//+------------------------------------------------------------------+
void PanelReadHistory()
  {
   datetime now = TimeCurrent();
   MqlDateTime t;
   TimeToStruct(now, t);
   datetime dayStart = now - (now % 86400);
   t.day = 1; t.hour = 0; t.min = 0; t.sec = 0;
   datetime monthStart = StructToTime(t);

   hsTodayNet = hsMonthNet = hsAllNet = hsGrossWin = hsGrossLoss = 0;
   hsTodayN = hsTodayW = hsMonthN = hsMonthW = hsAllN = hsAllW = 0;
   hsFirst = 0;
   for(int k = 0; k < NSTRAT; k++) { hsN[k] = 0; hsW[k] = 0; hsNet[k] = 0; }

   if(!HistorySelect(0, now + 86400))
      return;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
     {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0 || HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol)
         continue;
      int k = StratIdx((ulong)HistoryDealGetInteger(d, DEAL_MAGIC));
      if(k < 0)
         continue;
      datetime dt = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
      double p = HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) +
                 HistoryDealGetDouble(d, DEAL_COMMISSION);
      long entry = HistoryDealGetInteger(d, DEAL_ENTRY);
      if(hsFirst == 0 || dt < hsFirst)
         hsFirst = dt;
      hsAllNet += p;
      hsNet[k] += p;
      if(dt >= monthStart) hsMonthNet += p;
      if(dt >= dayStart)   hsTodayNet += p;
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY)
         continue;
      bool win = (p > 0);
      hsAllN++; hsN[k]++;
      if(win) { hsAllW++; hsW[k]++; hsGrossWin += p; }
      else    hsGrossLoss -= p;
      if(dt >= monthStart) { hsMonthN++; if(win) hsMonthW++; }
      if(dt >= dayStart)   { hsTodayN++; if(win) hsTodayW++; }
     }
   panelHistAt    = now;
   panelHistDirty = false;
  }

//+------------------------------------------------------------------+
string Money(const double v)
  {
   return(StringFormat("%+.2f %s", v, AccountInfoString(ACCOUNT_CURRENCY)));
  }

string Pct(const int w, const int n)
  {
   return(n > 0 ? StringFormat("%.0f%%", 100.0 * w / n) : "-");
  }

double ReadBuf(const int handle, const int buffer)
  {
   double b[];
   if(handle == INVALID_HANDLE || CopyBuffer(handle, buffer, 1, 1, b) != 1 || b[0] == EMPTY_VALUE)
      return(-1);
   return(b[0]);
  }

//+------------------------------------------------------------------+
void PanelUpdate()
  {
   if(!panelOn)
      return;
   datetime now = TimeCurrent();
   if(panelHistDirty || now - panelHistAt >= 60)
      PanelReadHistory();

   int    i = 0;
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   long   spread = (point > 0) ? (long)MathRound((ask - bid) / point) : 0;
   double atr    = ReadBuf(atrHandle, 0);
   double adx    = ReadBuf(adxHandle, 0);
   double h1f    = ReadBuf(h1FastHandle, 0);
   double h1s    = ReadBuf(h1SlowHandle, 0);
   bool   newsNow = InpNewsFilter && NewsBlocked(now);

   //--- intestazione e stato
   PanelLine(i++, "GoldTitan Final 3.00   " + _Symbol, PNL_HEAD);
   string onList = "";
   for(int k = 0; k < NSTRAT; k++)
      onList += StringFormat("%s %s  ", StratName(k), StratOn(k) ? "ON" : "off");
   PanelLine(i++, onList, PNL_DIM);
   string st; color sc;
   bool algoOk = TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && MQLInfoInteger(MQL_TRADE_ALLOWED);
   if(!algoOk)
     { st = "FERMO: Algo Trading disattivato"; sc = PNL_BAD; }
   else if(pauseUntil > 0 && now < pauseUntil)
     { st = "IN PAUSA (RSI/Rottura/Asia) fino alle " + TimeToString(pauseUntil, TIME_DATE | TIME_MINUTES); sc = PNL_WARN; }
   else if(newsNow && newsPtr < newsCount)
     { st = "NOTIZIA: niente nuove entrate fino alle " + TimeToString(newsTimes[newsPtr] + InpNewsAfterMin * 60, TIME_MINUTES); sc = PNL_WARN; }
   else if(InpMinAtrUsd > 0 && atr >= 0 && atr < InpMinAtrUsd)
     { st = StringFormat("FERMO: volatilita' bassa (ATR %.0f < %.0f)", atr, InpMinAtrUsd); sc = PNL_WARN; }
   else if(InpMaxSpreadPts > 0 && spread >= InpMaxSpreadPts)
     { st = StringFormat("ATTESA: spread alto (%I64d >= %d)", spread, InpMaxSpreadPts); sc = PNL_WARN; }
   else
     { st = "ATTIVO: in attesa di segnali"; sc = PNL_OK; }
   PanelLine(i++, st, sc);
   PanelLine(i++, "", PNL_TXT);

   //--- risultati
   PanelLine(i++, "OGGI", PNL_DIM);
   PanelLine(i++, StringFormat("%-14s Trade %d  Vinti %s", Money(hsTodayNet), hsTodayN, Pct(hsTodayW, hsTodayN)),
             hsTodayNet >= 0 ? PNL_OK : PNL_BAD);
   PanelLine(i++, "MESE", PNL_DIM);
   PanelLine(i++, StringFormat("%-14s Trade %d  Vinti %s", Money(hsMonthNet), hsMonthN, Pct(hsMonthW, hsMonthN)),
             hsMonthNet >= 0 ? PNL_OK : PNL_BAD);
   PanelLine(i++, "TOTALE" + (hsFirst > 0 ? " dal " + TimeToString(hsFirst, TIME_DATE) : ""), PNL_DIM);
   string pf = hsGrossLoss > 0 ? StringFormat("%.2f", hsGrossWin / hsGrossLoss) : "-";
   PanelLine(i++, StringFormat("%-14s Trade %d  Vinti %s  PF %s", Money(hsAllNet), hsAllN, Pct(hsAllW, hsAllN), pf),
             hsAllNet >= 0 ? PNL_OK : PNL_BAD);
   for(int k = 0; k < NSTRAT; k++)
      PanelLine(i++, StringFormat("  %-8s %3d trade  vinti %4s  %s", StratName(k), hsN[k], Pct(hsW[k], hsN[k]), Money(hsNet[k])),
                hsNet[k] >= 0 ? PNL_TXT : PNL_BAD);
   PanelLine(i++, "", PNL_TXT);

   //--- posizioni aperte
   PanelLine(i++, "POSIZIONI", PNL_DIM);
   int open = 0;
   double floating = 0;
   for(int p = PositionsTotal() - 1; p >= 0; p--)
     {
      ulong tk = PositionGetTicket(p);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      int k = StratIdx((ulong)PositionGetInteger(POSITION_MAGIC));
      if(k < 0)
         continue;
      double pr = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      floating += pr;
      open++;
      bool buy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      PanelLine(i++, StringFormat("  %-8s %-4s %.2f @ %.2f  %s", StratName(k), buy ? "BUY" : "SELL",
                                  PositionGetDouble(POSITION_VOLUME), PositionGetDouble(POSITION_PRICE_OPEN), Money(pr)),
                pr >= 0 ? PNL_OK : PNL_BAD);
     }
   if(open == 0)
      PanelLine(i++, "  nessuna", PNL_TXT);
   else
      PanelLine(i++, "  In corso " + Money(floating), floating >= 0 ? PNL_OK : PNL_BAD);
   PanelLine(i++, StringFormat("Saldo %.2f   Equity %.2f %s", AccountInfoDouble(ACCOUNT_BALANCE),
                               AccountInfoDouble(ACCOUNT_EQUITY), AccountInfoString(ACCOUNT_CURRENCY)), PNL_TXT);
   PanelLine(i++, StringFormat("Stop di fila %d / %d (poi pausa %d ore, Fibonacci escluso)", consLosses, InpPauseLosses, InpPauseHours),
             consLosses >= InpPauseLosses - 1 && InpPauseLosses > 0 ? PNL_WARN : PNL_TXT);
   PanelLine(i++, "", PNL_TXT);

   //--- mercato e filtri
   PanelLine(i++, "MERCATO", PNL_DIM);
   PanelLine(i++, StringFormat("ATR giornaliero %6.1f $  (min %.0f)  %s", atr, InpMinAtrUsd,
                               atr >= InpMinAtrUsd ? "OK" : "NO"), atr >= InpMinAtrUsd ? PNL_OK : PNL_WARN);
   PanelLine(i++, StringFormat("Spread %I64d points   (max %d)  %s", spread, InpMaxSpreadPts,
                               (InpMaxSpreadPts <= 0 || spread < InpMaxSpreadPts) ? "OK" : "NO"),
             (InpMaxSpreadPts <= 0 || spread < InpMaxSpreadPts) ? PNL_OK : PNL_WARN);
   string trend = (h1f < 0 || h1s < 0) ? "-" : (h1f > h1s ? "RIALZO (solo BUY)" : "RIBASSO (solo SELL)");
   PanelLine(i++, "Trend H1 " + trend + "  [RSI, Rottura]", PNL_TXT);
   PanelLine(i++, StringFormat("ADX M15 %5.1f  (min %.0f per la Rottura)  %s", adx, InpBrkAdxMin,
                               adx >= InpBrkAdxMin ? "OK" : "NO"), adx >= InpBrkAdxMin ? PNL_OK : PNL_TXT);

   //--- range asiatico di oggi
   MqlDateTime t;
   TimeToStruct(now, t);
   datetime dayStart = iTime(_Symbol, PERIOD_D1, 0);
   string asia;
   if(!gUseAsia)
      asia = "Asia: strategia spenta";
   else if(t.hour < gAsiaEndHour)
      asia = StringFormat("Asia: range in formazione (%02d-%02d)", gAsiaStartHour, gAsiaEndHour);
   else
     {
      double hi[], lo[];
      datetime from = dayStart + (datetime)(gAsiaStartHour * 3600);
      datetime to   = dayStart + (datetime)(gAsiaEndHour * 3600 - 1);
      string range = "";
      if(CopyHigh(_Symbol, ASIA_TF, from, to, hi) > 1 && CopyLow(_Symbol, ASIA_TF, from, to, lo) > 1)
         range = StringFormat(" %.2f-%.2f", lo[ArrayMinimum(lo)], hi[ArrayMaximum(hi)]);
      if(asiaDay == dayStart)
         asia = "Asia:" + range + "  segnale di oggi gia' dato";
      else if(t.hour < gAsiaLastHour)
         asia = "Asia:" + range + StringFormat("  attesa rottura fino alle %02d", gAsiaLastHour);
      else
         asia = "Asia:" + range + "  finestra chiusa";
     }
   PanelLine(i++, asia, PNL_TXT);

   //--- Fibonacci
   string fib = "Fibo: strategia spenta";
   if(InpUseFib)
      fib = StringFormat("Fibo %04d-%04d: %s%s", InpFbHourStart, InpFbHourEnd,
                         g_fbLegDead ? "in attesa, " : "attivo, ", g_fbStatus);
   PanelLine(i++, fib, PNL_TXT);


   //--- prossima notizia
   string nx = "Notizie: filtro spento";
   if(InpNewsFilter)
     {
      nx = "Prossima notizia USD: nessuna nei prossimi giorni";
      for(int n = newsPtr; n < newsCount; n++)
         if(newsTimes[n] >= now)
           {
            nx = "Prossima notizia USD: " + TimeToString(newsTimes[n], TIME_DATE | TIME_MINUTES);
            break;
           }
     }
   PanelLine(i++, nx, PNL_TXT);
   PanelLine(i++, "Orari = ora del server", PNL_DIM);

   //--- pulizia righe in eccesso e dimensione dello sfondo
   for(int j = i; j < panelLines; j++)
      ObjectDelete(0, PNL_PFX + "l" + IntegerToString(j));
   panelLines = i;
   ObjectSetInteger(0, PNL_PFX + "bg", OBJPROP_YSIZE, 16 + i * PNL_LINEH);
   ChartRedraw();
  }
//+------------------------------------------------------------------+
