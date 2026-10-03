//+------------------------------------------------------------------+
//|                                               Donchian_Trend.mq5 |
//|  Trend following con canale di Donchian, multi-simbolo.          |
//|                                                                  |
//|  Un solo grafico gestisce tutte le coppie di InpSymbols          |
//|  (vuoto = solo il simbolo del grafico).                          |
//|                                                                  |
//|  - BUY  quando la candela chiude sopra il massimo delle          |
//|    InpEntryPeriod candele precedenti; SELL sotto il minimo.      |
//|  - Stop iniziale a ATR x InpAtrStopMult, messo sull'ordine.      |
//|  - Uscita a inseguimento: lo stop segue il minimo (BUY) o il     |
//|    massimo (SELL) delle ultime InpExitPeriod candele, e la       |
//|    posizione si chiude quando la candela chiude oltre quel       |
//|    livello. Nessun take profit.                                  |
//|  - Lotto calcolato per rischiare InpRiskPercent del capitale.    |
//|  - Massimo InpMaxPositions posizioni aperte insieme.             |
//|  Le decisioni si prendono sulla candela chiusa.                  |
//+------------------------------------------------------------------+
#property copyright "Salvatore Cortile"
#property version   "1.00"
#property description "Trend following Donchian multi-simbolo: rottura del canale, stop ATR, uscita a inseguimento, rischio in % del capitale."

#include <Trade/Trade.mqh>

input group "Simboli"
input string          InpSymbols = "EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,NZDUSD,USDCAD,EURGBP,EURJPY,EURCHF,EURAUD,EURNZD,EURCAD,GBPJPY,GBPCHF,GBPAUD,GBPNZD,GBPCAD,AUDJPY,AUDCHF,AUDNZD,AUDCAD,NZDJPY,NZDCHF,NZDCAD,CADJPY,CADCHF,CHFJPY"; // Coppie (vuoto = solo il grafico)
input string          InpSuffix  = "-P";       // Suffisso del broker aggiunto a ogni coppia

input group "Segnale"
input ENUM_TIMEFRAMES InpTimeframe    = PERIOD_D1; // Timeframe di lavoro
input int             InpEntryPeriod  = 20;        // Canale di ingresso (candele)
input int             InpExitPeriod   = 10;        // Canale di uscita (candele)
input bool            InpUseTrendMa   = false;     // Filtro: BUY solo sopra la SMA, SELL solo sotto
input int             InpTrendMaPeriod = 200;      // Periodo SMA del filtro
input bool            InpAllowLong    = true;      // Abilita i BUY
input bool            InpAllowShort   = true;      // Abilita i SELL

input group "Rischio"
input double          InpRiskPercent    = 0.5;  // Rischio per operazione in % del capitale
input double          InpAtrStopMult    = 2.5;  // Stop iniziale = ATR x moltiplicatore
input int             InpAtrPeriod      = 20;   // Periodo ATR
input double          InpMaxRiskMinLot  = 2.0;  // Se il lotto calcolato e' sotto il minimo: usa il minimo solo se rischia al massimo questa % (0 = salta)
input int             InpMaxPositions   = 6;    // Posizioni aperte al massimo insieme

input group "Ordini"
input int             InpSlippagePoints = 30;       // Slippage massimo in points
input ulong           InpMagic          = 26100401; // Magic number
input string          InpComment        = "Donchian Trend";

struct SymbolState
  {
   string   name;
   int      atrHandle;
   int      maHandle;
   datetime lastBar;
  };

CTrade      trade;
SymbolState syms[];

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpEntryPeriod < 2 || InpExitPeriod < 2 || InpRiskPercent <= 0 || InpAtrStopMult <= 0 ||
      InpAtrPeriod < 1 || InpMaxPositions < 1 || InpMaxRiskMinLot < 0 || (!InpAllowLong && !InpAllowShort))
     {
      Print("Parametri non validi.");
      return(INIT_PARAMETERS_INCORRECT);
     }

   string list[];
   if(StringLen(InpSymbols) == 0)
     {
      ArrayResize(list, 1);
      list[0] = _Symbol;
     }
   else
     {
      int n = StringSplit(InpSymbols, ',', list);
      for(int i = 0; i < n; i++)
        {
         StringTrimLeft(list[i]);
         StringTrimRight(list[i]);
         list[i] = list[i] + InpSuffix;
        }
     }

   ArrayResize(syms, 0);
   for(int i = 0; i < ArraySize(list); i++)
     {
      string s = list[i];
      if(s == "" || !SymbolSelect(s, true))
        {
         PrintFormat("Simbolo %s non trovato: saltato.", s);
         continue;
        }
      SymbolState st;
      st.name      = s;
      st.lastBar   = 0;
      st.atrHandle = iATR(s, InpTimeframe, InpAtrPeriod);
      st.maHandle  = InpUseTrendMa ? iMA(s, InpTimeframe, InpTrendMaPeriod, 0, MODE_SMA, PRICE_CLOSE) : INVALID_HANDLE;
      if(st.atrHandle == INVALID_HANDLE || (InpUseTrendMa && st.maHandle == INVALID_HANDLE))
        {
         PrintFormat("Indicatori non disponibili per %s: saltato.", s);
         continue;
        }
      int k = ArraySize(syms);
      ArrayResize(syms, k + 1);
      syms[k] = st;
     }

   if(ArraySize(syms) == 0)
     {
      Print("Nessun simbolo valido.");
      return(INIT_FAILED);
     }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePoints);

   EventSetTimer(30);
   PrintFormat("Donchian_Trend avviato su %d simboli | %s | ingresso %d, uscita %d | stop ATR(%d) x%.1f | rischio %.2f%% | max %d posizioni",
               ArraySize(syms), EnumToString(InpTimeframe), InpEntryPeriod, InpExitPeriod,
               InpAtrPeriod, InpAtrStopMult, InpRiskPercent, InpMaxPositions);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   for(int i = 0; i < ArraySize(syms); i++)
     {
      IndicatorRelease(syms[i].atrHandle);
      if(syms[i].maHandle != INVALID_HANDLE)
         IndicatorRelease(syms[i].maHandle);
     }
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()  { ProcessAll(); }
void OnTimer() { ProcessAll(); }

//+------------------------------------------------------------------+
void ProcessAll()
  {
   for(int i = 0; i < ArraySize(syms); i++)
      ProcessSymbol(syms[i]);
   UpdatePanel();
  }

//+------------------------------------------------------------------+
//| Una volta per candela: gestisce la posizione o cerca l'ingresso. |
//+------------------------------------------------------------------+
void ProcessSymbol(SymbolState &st)
  {
   string s    = st.name;
   datetime b0 = iTime(s, InpTimeframe, 0);
   if(b0 == 0 || b0 == st.lastBar)
      return;
   if(iBars(s, InpTimeframe) < MathMax(InpEntryPeriod, InpExitPeriod) + 5)
      return;

   double close1 = iClose(s, InpTimeframe, 1);
   int    hiEnt  = iHighest(s, InpTimeframe, MODE_HIGH, InpEntryPeriod, 2);
   int    loEnt  = iLowest(s, InpTimeframe, MODE_LOW, InpEntryPeriod, 2);
   int    hiExit = iHighest(s, InpTimeframe, MODE_HIGH, InpExitPeriod, 1);
   int    loExit = iLowest(s, InpTimeframe, MODE_LOW, InpExitPeriod, 1);
   if(close1 <= 0 || hiEnt < 0 || loEnt < 0 || hiExit < 0 || loExit < 0)
      return;   // dati non pronti: riprova piu' tardi

   double entryHigh = iHigh(s, InpTimeframe, hiEnt);
   double entryLow  = iLow(s, InpTimeframe, loEnt);
   double exitLow   = iLow(s, InpTimeframe, loExit);    // minimo delle ultime N candele chiuse
   double exitHigh  = iHigh(s, InpTimeframe, hiExit);   // massimo delle ultime N candele chiuse
   int    digits    = (int)SymbolInfoInteger(s, SYMBOL_DIGITS);

   st.lastBar = b0;

   ulong ticket;
   int   dir = PositionDir(s, ticket);

   // --- Posizione aperta: uscita e stop a inseguimento ---
   if(dir != 0)
     {
      // Uscita: la candela ha chiuso oltre il canale di uscita (ultime N candele prima di lei).
      int    loPrev = iLowest(s, InpTimeframe, MODE_LOW, InpExitPeriod, 2);
      int    hiPrev = iHighest(s, InpTimeframe, MODE_HIGH, InpExitPeriod, 2);
      bool   exitNow = (dir == 1 && loPrev >= 0 && close1 < iLow(s, InpTimeframe, loPrev)) ||
                       (dir == -1 && hiPrev >= 0 && close1 > iHigh(s, InpTimeframe, hiPrev));
      if(exitNow)
        {
         if(trade.PositionClose(ticket, InpSlippagePoints))
            PrintFormat("%s: chiusa posizione #%I64u (rottura del canale di uscita %d)", s, ticket, InpExitPeriod);
         else
            PrintFormat("%s: chiusura #%I64u fallita: %u %s", s, ticket, trade.ResultRetcode(), trade.ResultRetcodeDescription());
         return;
        }

      // Lo stop sale (BUY) o scende (SELL) seguendo il canale di uscita, mai indietro.
      double curSl = PositionGetDouble(POSITION_SL);
      double curTp = PositionGetDouble(POSITION_TP);
      double newSl = NormalizeDouble(dir == 1 ? exitLow : exitHigh, digits);
      MqlTick tick;
      if(!SymbolInfoTick(s, tick))
         return;
      double minDist = SymbolInfoInteger(s, SYMBOL_TRADE_STOPS_LEVEL) * SymbolInfoDouble(s, SYMBOL_POINT);
      bool better = (dir == 1) ? (curSl == 0 || newSl > curSl) : (curSl == 0 || newSl < curSl);
      bool valid  = (dir == 1) ? (tick.bid - newSl > minDist) : (newSl - tick.ask > minDist);
      if(better && valid && !trade.PositionModify(ticket, newSl, curTp))
         PrintFormat("%s: spostamento stop fallito: %u %s", s, trade.ResultRetcode(), trade.ResultRetcodeDescription());
      return;
     }

   // --- Nessuna posizione: cerca la rottura del canale di ingresso ---
   int signal = 0;
   if(InpAllowLong && close1 > entryHigh)
      signal = 1;
   else
      if(InpAllowShort && close1 < entryLow)
         signal = -1;
   if(signal == 0)
      return;

   if(InpUseTrendMa)
     {
      double ma[];
      if(CopyBuffer(st.maHandle, 0, 1, 1, ma) != 1)
         return;
      if((signal == 1 && close1 <= ma[0]) || (signal == -1 && close1 >= ma[0]))
         return;
     }

   if(CountPositions() >= InpMaxPositions)
     {
      PrintFormat("%s: segnale %s ignorato, gia' %d posizioni aperte.", s, signal == 1 ? "BUY" : "SELL", InpMaxPositions);
      return;
     }

   OpenTrade(st, signal, digits);
  }

//+------------------------------------------------------------------+
void OpenTrade(SymbolState &st, int dir, int digits)
  {
   string s = st.name;
   double atr[];
   if(CopyBuffer(st.atrHandle, 0, 1, 1, atr) != 1 || atr[0] <= 0)
      return;

   MqlTick tick;
   if(!SymbolInfoTick(s, tick))
      return;
   double entry = (dir == 1) ? tick.ask : tick.bid;
   double sl    = NormalizeDouble(dir == 1 ? entry - atr[0] * InpAtrStopMult : entry + atr[0] * InpAtrStopMult, digits);

   double lots = CalcLots(s, dir, entry, sl);
   if(lots <= 0)
      return;

   trade.SetTypeFillingBySymbol(s);
   bool ok = (dir == 1) ? trade.Buy(lots, s, 0.0, sl, 0.0, InpComment)
                        : trade.Sell(lots, s, 0.0, sl, 0.0, InpComment);
   if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
      PrintFormat("%s: aperto %s %.2f a %s, stop %s", s, dir == 1 ? "BUY" : "SELL", lots,
                  DoubleToString(trade.ResultPrice(), digits), DoubleToString(sl, digits));
   else
      PrintFormat("%s: apertura fallita: %u %s", s, trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
//| Lotto per rischiare InpRiskPercent fino allo stop.               |
//+------------------------------------------------------------------+
double CalcLots(string s, int dir, double entry, double sl)
  {
   double lossPerLot = 0.0;
   if(!OrderCalcProfit(dir == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, s, 1.0, entry, sl, lossPerLot) || lossPerLot >= 0)
     {
      PrintFormat("%s: impossibile calcolare il valore dello stop.", s);
      return(0.0);
     }
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double minLot  = SymbolInfoDouble(s, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(s, SYMBOL_VOLUME_MAX);
   double stepLot = SymbolInfoDouble(s, SYMBOL_VOLUME_STEP);

   double lots = balance * InpRiskPercent / 100.0 / MathAbs(lossPerLot);
   if(stepLot > 0)
      lots = MathFloor(lots / stepLot + 1e-9) * stepLot;

   if(lots < minLot)
     {
      double minRisk = minLot * MathAbs(lossPerLot) / balance * 100.0;
      if(InpMaxRiskMinLot > 0 && minRisk <= InpMaxRiskMinLot)
        {
         PrintFormat("%s: lotto calcolato sotto il minimo, uso %.2f (rischio %.2f%%).", s, minLot, minRisk);
         return(minLot);
        }
      PrintFormat("%s: operazione saltata, il lotto minimo rischierebbe il %.2f%% del capitale.", s, minRisk);
      return(0.0);
     }
   return(MathMin(maxLot, lots));
  }

//+------------------------------------------------------------------+
int PositionDir(string s, ulong &ticket)
  {
   ticket = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == s && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
        {
         ticket = t;
         return(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1);
        }
     }
   return(0);
  }

//+------------------------------------------------------------------+
int CountPositions()
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t != 0 && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         n++;
     }
   return(n);
  }

//+------------------------------------------------------------------+
void UpdatePanel()
  {
   string open = "";
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      open += StringFormat("\n  %s %s %.2f  P/L %.2f", PositionGetString(POSITION_SYMBOL),
                           PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "BUY" : "SELL",
                           PositionGetDouble(POSITION_VOLUME),
                           PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP));
     }
   Comment(StringFormat("Donchian Trend  |  %d simboli  |  %s  |  rischio %.2f%%\nPosizioni aperte: %d / %d%s",
                        ArraySize(syms), EnumToString(InpTimeframe), InpRiskPercent,
                        CountPositions(), InpMaxPositions, open));
  }
//+------------------------------------------------------------------+
