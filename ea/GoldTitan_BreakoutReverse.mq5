//+------------------------------------------------------------------+
//|                                    GoldTitan_BreakoutReverse.mq5 |
//|  Solo la strategia ROTTURA di GoldTitan Trio, INVERTITA:         |
//|   - stesso segnale (chiusura M15 fuori dal canale di 24 candele, |
//|     filtro trend H1 e ADX) ma si entra nella direzione opposta:  |
//|     rottura al rialzo -> SELL, rottura al ribasso -> BUY         |
//|   - SL e TP scambiati: SL 300 pips, TP 200 pips                  |
//|  Filtri identici a GoldTitan Trio 1.12 (ATR giornaliero, spread, |
//|  notizie USD, pausa dopo una serie di stop).                     |
//|  Magic number diverso, per confrontarlo con la versione attuale. |
//|  Con InpReverse = false si comporta come la Rottura originale.   |
//+------------------------------------------------------------------+
#property version   "1.00"
#property description "GoldTitan Breakout Reverse - rottura del canale M15 su XAUUSD invertita (SELL sulla rottura in alto, BUY su quella in basso), SL e TP scambiati."

#include <Trade\Trade.mqh>

//--- Lotto
input double InpLots          = 0.01;      // Lotto
input double InpBalancePerLot = 0.0;       // Lotto progressivo: un lotto ogni X $ di saldo (0 = lotto fisso)

//--- Inversione e stop (1 pip = 0.10 di prezzo = 10 points)
input bool   InpReverse       = true;      // INVERTI: entra contro la rottura (false = rottura originale)
input int    InpSlPips        = 300;       // Stop loss (pips) - era il TP della Rottura
input int    InpTpPips        = 200;       // Take profit (pips) - era lo SL della Rottura

//--- Filtri
input double InpAdxMin        = 30.0;      // Opera solo se ADX M15 e' sopra questo valore (0 = filtro spento)
input double InpMinAtrUsd     = 60.0;      // Opera solo se l'ATR giornaliero e' sopra X $ (0 = filtro spento)
input int    InpMaxSpreadPts  = 70;        // Opera solo se lo spread e' inferiore a (points, 0 = off)

//--- Protezioni per i periodi di volatilita' estrema
input int    InpPauseLosses   = 4;         // Pausa dopo N stop loss consecutivi (0 = off)
input int    InpPauseHours    = 24;        // Durata della pausa (ore)

//--- Tester e identificativi
input double InpSimSlipPerLot = 10.0;      // Slippage simulato nel tester ($ per lotto, 0 = off)
input ulong  InpMagic         = 20261009;  // Magic number (diverso da quelli di GoldTitan Trio)

//--- Filtro notizie (USD)
input bool   InpNewsFilter    = true;      // NOTIZIE: niente nuove operazioni vicino alle notizie USD
input int    InpNewsBeforeMin = 0;         // NOTIZIE: minuti prima della notizia
input int    InpNewsAfterMin  = 90;        // NOTIZIE: minuti dopo la notizia
input bool   InpNewsMedium    = false;     // NOTIZIE: includi anche quelle di media importanza
input bool   InpNewsClose     = false;     // NOTIZIE: chiudi la posizione aperta durante la finestra

//--- Pannello sul grafico (solo informativo, non cambia il trading)
input bool   InpShowPanel     = true;      // PANNELLO: mostra il pannello sul grafico

//--- Valori fissi, uguali a GoldTitan Trio
#define BRK_TF            PERIOD_M15   // timeframe della rottura
#define CHANNEL_BARS      24           // candele del canale
#define ADX_PERIOD        14
#define ATR_PERIOD        14           // giorni
#define EMA_FAST_PERIOD   50
#define EMA_SLOW_PERIOD   200
#define PIP_SIZE          0.10         // valore di 1 pip in prezzo
#define NO_SLIPPAGE_LIMIT 100000       // points: in pratica nessun limite allo slippage

CTrade   trade;
int      h1FastHandle  = INVALID_HANDLE;   // EMA su H1
int      h1SlowHandle  = INVALID_HANDLE;
int      adxHandle     = INVALID_HANDLE;   // ADX sul timeframe della rottura
int      atrHandle     = INVALID_HANDLE;   // ATR giornaliero
double   atrSum        = 0.0;
int      atrCount      = 0;
datetime atrWarnDay    = 0;
datetime brkLastBar    = 0;
datetime lastWarnBar   = 0;
double   slipSim       = 0.0;              // slippage simulato accumulato ($)
int      consLosses    = 0;                // stop consecutivi
datetime pauseUntil    = 0;                // fine della pausa in corso
int      pauseCount    = 0;
double   atrMaxSeen    = 0.0;
string   lastSignal    = "";               // ultimo segnale, per il pannello

#define  NEWS_FILE "GoldTitan_news.csv"
datetime newsTimes[];
int      newsCount     = 0;
int      newsPtr       = 0;
datetime newsLoadedAt  = 0;
int      newsSkips     = 0;
int      newsCloses    = 0;

//--- pannello
bool     panelOn        = false;
bool     panelHistDirty = true;
datetime panelHistAt    = 0;
int      panelLines     = 0;

double   hsTodayNet = 0, hsMonthNet = 0, hsAllNet = 0, hsGrossWin = 0, hsGrossLoss = 0;
int      hsTodayN = 0, hsTodayW = 0, hsMonthN = 0, hsMonthW = 0, hsAllN = 0, hsAllW = 0;
datetime hsFirst = 0;

color    PNL_TXT  = clrWhite;
color    PNL_DIM  = C'150,150,150';
color    PNL_HEAD = C'212,175,55';
color    PNL_OK   = C'60,200,90';
color    PNL_WARN = C'255,170,40';
color    PNL_BAD  = C'240,80,80';

//+------------------------------------------------------------------+
int OnInit()
  {
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("ATTENZIONE: l'EA e' pensato per XAUUSD, simbolo attuale: ", _Symbol);

   if(InpLots <= 0.0 || InpBalancePerLot < 0.0 || InpAdxMin < 0.0 || InpMinAtrUsd < 0.0 ||
      InpPauseLosses < 0 || InpPauseHours < 1)
     {
      Print("Parametri di lotto o dei filtri non validi");
      return(INIT_PARAMETERS_INCORRECT);
     }

   double point   = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(InpSlPips <= 0 || InpTpPips <= 0 ||
      InpSlPips * PIP_SIZE < minDist || InpTpPips * PIP_SIZE < minDist)
     {
      Print("SL/TP non validi o sotto lo stop level del broker");
      return(INIT_PARAMETERS_INCORRECT);
     }

   h1FastHandle = iMA(_Symbol, PERIOD_H1, EMA_FAST_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
   h1SlowHandle = iMA(_Symbol, PERIOD_H1, EMA_SLOW_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
   adxHandle    = iADX(_Symbol, BRK_TF, ADX_PERIOD);
   atrHandle    = iATR(_Symbol, PERIOD_D1, ATR_PERIOD);
   if(h1FastHandle == INVALID_HANDLE || h1SlowHandle == INVALID_HANDLE ||
      adxHandle == INVALID_HANDLE || atrHandle == INVALID_HANDLE)
     {
      Print("Impossibile creare gli indicatori, errore ", GetLastError());
      return(INIT_FAILED);
     }

   trade.SetDeviationInPoints(NO_SLIPPAGE_LIMIT);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetExpertMagicNumber(InpMagic);

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

   PrintFormat("GoldTitan Breakout Reverse 1.00 avviato su %s | %s | SL %d TP %d | ADX min %.0f | ATR min %.0f $ | lotto %.2f, progressivo %.0f $",
               _Symbol, InpReverse ? "INVERTITA" : "ORIGINALE", InpSlPips, InpTpPips,
               InpAdxMin, InpMinAtrUsd, InpLots, InpBalancePerLot);
   PanelInit();
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(h1FastHandle != INVALID_HANDLE) IndicatorRelease(h1FastHandle);
   if(h1SlowHandle != INVALID_HANDLE) IndicatorRelease(h1SlowHandle);
   if(adxHandle    != INVALID_HANDLE) IndicatorRelease(adxHandle);
   if(atrHandle    != INVALID_HANDLE) IndicatorRelease(atrHandle);
   PanelDeinit();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   PanelUpdate();
  }

//+------------------------------------------------------------------+
//| Risultato del test al netto dello slippage simulato (criterio    |
//| "Custom max").                                                   |
//+------------------------------------------------------------------+
double OnTester()
  {
   double prof = 0.0;
   int    n = 0, win = 0;

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
         if((ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != InpMagic)
            continue;
         double p = HistoryDealGetDouble(deal, DEAL_PROFIT) +
                    HistoryDealGetDouble(deal, DEAL_SWAP) +
                    HistoryDealGetDouble(deal, DEAL_COMMISSION);
         prof += p;
         n++;
         if(p > 0.0) win++;
        }
     }

   PrintFormat("ROTTURA %s: %d trade, %d vinti, netto %.2f $ (slippage %.2f $)",
               InpReverse ? "INVERTITA" : "ORIGINALE", n, win, prof - slipSim, slipSim);
   PrintFormat("ATR giornaliero medio alle aperture: %.2f $ (%d letture)",
               atrCount > 0 ? atrSum / atrCount : 0.0, atrCount);
   PrintFormat("ATR giornaliero massimo a un segnale: %.2f $ | pause scattate: %d", atrMaxSeen, pauseCount);
   if(InpNewsFilter)
      PrintFormat("NOTIZIE : %d notizie caricate | finestra -%d / +%d min | segnali scartati %d | posizioni chiuse %d",
                  newsCount, InpNewsBeforeMin, InpNewsAfterMin, newsSkips, newsCloses);
   double realNet = TesterStatistics(STAT_PROFIT) - slipSim;
   PrintFormat("TOTALE  : netto reale %.2f $", realNet);
   return(NormalizeDouble(realNet, 2));
  }

//+------------------------------------------------------------------+
//| Conta gli stop consecutivi (pausa) e, solo nel tester, lo        |
//| slippage simulato a ogni apertura.                               |
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
   if((ulong)HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic)
      return;
   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);

   if(entry == DEAL_ENTRY_OUT)
     {
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
   slipSim += NormalizeDouble(InpSimSlipPerLot * HistoryDealGetDouble(trans.deal, DEAL_VOLUME), 2);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   if(InpNewsFilter)
     {
      if(!MQLInfoInteger(MQL_TESTER) && TimeCurrent() - newsLoadedAt > (newsCount > 0 ? 3600 : 60))
         LoadNews();
      if(InpNewsClose && NewsBlocked(TimeCurrent()))
         CloseAllForNews();
     }

   // Il segnale si valuta alla chiusura di ogni candela M15.
   // La candela e' segnata come valutata solo se i dati erano pronti (altrimenti si riprova).
   datetime brkBar = iTime(_Symbol, BRK_TF, 0);
   if(brkBar != 0 && brkBar != brkLastBar)
     {
      if(CheckBreakout(brkBar))
         brkLastBar = brkBar;
     }
  }

//+------------------------------------------------------------------+
//| Segnale identico alla Rottura di GoldTitan Trio: l'ultima        |
//| candela M15 chiude sopra il massimo (rottura in alto) o sotto il |
//| minimo (rottura in basso) delle 24 candele precedenti, a favore  |
//| del trend H1 e con ADX sopra il minimo.                          |
//| Con InpReverse si entra nella direzione opposta alla rottura.    |
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

   bool breakUp   = (cl[0] > upper);
   bool breakDown = (cl[0] < lower);
   if(!breakUp && !breakDown)
      return(true);

   // I filtri guardano la direzione della rottura, come nella versione originale.
   bool ready = true;
   if(!H1TrendOk(breakUp, ready))
      return(ready ? true : NotReady(barTime, "EMA H1"));

   if(InpAdxMin > 0.0)
     {
      double adx[];
      if(BarsCalculated(adxHandle) < 2 * ADX_PERIOD + 2 ||
         CopyBuffer(adxHandle, 0, 1, 1, adx) != 1 ||
         adx[0] == EMPTY_VALUE)
         return(NotReady(barTime, "ADX"));
      if(adx[0] < InpAdxMin)
         return(true);
     }

   bool isBuy = InpReverse ? breakDown : breakUp;
   lastSignal = StringFormat("%s %s (rottura in %s)", TimeToString(barTime, TIME_DATE | TIME_MINUTES),
                             isBuy ? "BUY" : "SELL", breakUp ? "alto" : "basso");
   OpenTrade(isBuy);
   return(true);
  }

//+------------------------------------------------------------------+
//| Filtro trend H1 sull'ultima candela H1 chiusa: rialzo se         |
//| EMA 50 > EMA 200, ribasso se sotto.                              |
//| ready = false se le EMA H1 non sono ancora disponibili.          |
//+------------------------------------------------------------------+
bool H1TrendOk(const bool isUp, bool &ready)
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
   return(isUp ? (h1Fast[0] > h1Slow[0]) : (h1Fast[0] < h1Slow[0]));
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
//| Apre il trade. Al massimo una posizione aperta.                  |
//+------------------------------------------------------------------+
void OpenTrade(const bool isBuy)
  {
   string side = isBuy ? "BUY" : "SELL";
   string tag  = InpReverse ? "ROTINV" : "ROT";

   if(CountPositions() > 0)
      return;
   if(InpNewsFilter && NewsBlocked(TimeCurrent()))
     {
      newsSkips++;
      return;
     }
   if(pauseUntil > 0 && TimeCurrent() < pauseUntil)
      return;

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
      return;
   if(atr > 0.0)
     {
      atrSum += atr;
      atrCount++;
     }

   double lots = InpLots;
   if(InpBalancePerLot > 0.0)
     {
      double steps = MathFloor(AccountInfoDouble(ACCOUNT_BALANCE) / InpBalancePerLot);
      lots = InpLots * MathMax(1.0, steps);
     }
   lots = NormalizeLots(lots);

   double slDist = InpSlPips * PIP_SIZE;
   double tpDist = InpTpPips * PIP_SIZE;
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
int CountPositions()
  {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
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
void CloseAllForNews()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      if(trade.PositionClose(ticket))
         newsCloses++;
      else
         PrintFormat("Chiusura per notizia fallita: %d %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }
  }
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| PANNELLO INFORMATIVO                                             |
//| Solo lettura: mostra stato, risultati e condizioni di mercato.   |
//+------------------------------------------------------------------+
#define PNL_PFX   "GTBR_"
#define PNL_W     410
#define PNL_LINEH 15
#define PNL_MAXL  30

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
//| Rilegge lo storico (solo deal di questo bot su questo simbolo).  |
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

   if(!HistorySelect(0, now + 86400))
      return;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
     {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0 || HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol)
         continue;
      if((ulong)HistoryDealGetInteger(d, DEAL_MAGIC) != InpMagic)
         continue;
      datetime dt = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
      double p = HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) +
                 HistoryDealGetDouble(d, DEAL_COMMISSION);
      long entry = HistoryDealGetInteger(d, DEAL_ENTRY);
      if(hsFirst == 0 || dt < hsFirst)
         hsFirst = dt;
      hsAllNet += p;
      if(dt >= monthStart) hsMonthNet += p;
      if(dt >= dayStart)   hsTodayNet += p;
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY)
         continue;
      bool win = (p > 0);
      hsAllN++;
      if(win) { hsAllW++; hsGrossWin += p; }
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
   PanelLine(i++, "GoldTitan Breakout Reverse 1.00   " + _Symbol, PNL_HEAD);
   PanelLine(i++, StringFormat("Modo %s   SL %d  TP %d pips", InpReverse ? "INVERTITO" : "ORIGINALE",
                               InpSlPips, InpTpPips), PNL_DIM);
   string st; color sc;
   bool algoOk = TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && MQLInfoInteger(MQL_TRADE_ALLOWED);
   if(!algoOk)
     { st = "FERMO: Algo Trading disattivato"; sc = PNL_BAD; }
   else if(pauseUntil > 0 && now < pauseUntil)
     { st = "IN PAUSA fino alle " + TimeToString(pauseUntil, TIME_DATE | TIME_MINUTES) + " (stop di fila)"; sc = PNL_WARN; }
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
   PanelLine(i++, "", PNL_TXT);

   //--- posizione aperta
   PanelLine(i++, "POSIZIONE", PNL_DIM);
   int open = 0;
   for(int p = PositionsTotal() - 1; p >= 0; p--)
     {
      ulong tk = PositionGetTicket(p);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      double pr = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      open++;
      bool buy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      PanelLine(i++, StringFormat("  %-4s %.2f @ %.2f  %s", buy ? "BUY" : "SELL",
                                  PositionGetDouble(POSITION_VOLUME), PositionGetDouble(POSITION_PRICE_OPEN), Money(pr)),
                pr >= 0 ? PNL_OK : PNL_BAD);
     }
   if(open == 0)
      PanelLine(i++, "  nessuna", PNL_TXT);
   PanelLine(i++, "Ultimo segnale: " + (lastSignal == "" ? "-" : lastSignal), PNL_TXT);
   PanelLine(i++, StringFormat("Saldo %.2f   Equity %.2f %s", AccountInfoDouble(ACCOUNT_BALANCE),
                               AccountInfoDouble(ACCOUNT_EQUITY), AccountInfoString(ACCOUNT_CURRENCY)), PNL_TXT);
   PanelLine(i++, StringFormat("Stop di fila %d / %d (poi pausa %d ore)", consLosses, InpPauseLosses, InpPauseHours),
             consLosses >= InpPauseLosses - 1 && InpPauseLosses > 0 ? PNL_WARN : PNL_TXT);
   PanelLine(i++, "", PNL_TXT);

   //--- mercato e filtri
   PanelLine(i++, "MERCATO", PNL_DIM);
   PanelLine(i++, StringFormat("ATR giornaliero %6.1f $  (min %.0f)  %s", atr, InpMinAtrUsd,
                               atr >= InpMinAtrUsd ? "OK" : "NO"), atr >= InpMinAtrUsd ? PNL_OK : PNL_WARN);
   PanelLine(i++, StringFormat("Spread %I64d points   (max %d)  %s", spread, InpMaxSpreadPts,
                               (InpMaxSpreadPts <= 0 || spread < InpMaxSpreadPts) ? "OK" : "NO"),
             (InpMaxSpreadPts <= 0 || spread < InpMaxSpreadPts) ? PNL_OK : PNL_WARN);
   string trend = "-";
   if(h1f >= 0 && h1s >= 0)
     {
      if(InpReverse)
         trend = h1f > h1s ? "RIALZO (solo SELL su rottura in alto)" : "RIBASSO (solo BUY su rottura in basso)";
      else
         trend = h1f > h1s ? "RIALZO (solo BUY)" : "RIBASSO (solo SELL)";
     }
   PanelLine(i++, "Trend H1 " + trend, PNL_TXT);
   PanelLine(i++, StringFormat("ADX M15 %5.1f  (min %.0f)  %s", adx, InpAdxMin,
                               adx >= InpAdxMin ? "OK" : "NO"), adx >= InpAdxMin ? PNL_OK : PNL_TXT);

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

   for(int j = i; j < panelLines; j++)
      ObjectDelete(0, PNL_PFX + "l" + IntegerToString(j));
   panelLines = i;
   ObjectSetInteger(0, PNL_PFX + "bg", OBJPROP_YSIZE, 16 + i * PNL_LINEH);
   ChartRedraw();
  }
//+------------------------------------------------------------------+
