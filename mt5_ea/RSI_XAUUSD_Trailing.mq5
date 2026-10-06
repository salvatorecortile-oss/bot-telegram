//+------------------------------------------------------------------+
//|                                        RSI_XAUUSD_Trailing.mq5   |
//|  EA RSI M5 su XAUUSD con SL fisso, senza TP e trailing a gradini |
//+------------------------------------------------------------------+
#property version   "1.00"
#property description "RSI(14) M5: >=70 SELL, <=30 BUY. SL 100 pips, nessun TP."
#property description "Trailing: ogni 20 pips di profitto lo SL sale di 20 (+20 -> pareggio, +40 -> +20, ...)."

#include <Trade\Trade.mqh>

enum ENUM_SIGNAL_MODE
  {
   SIGNAL_CROSS_IN  = 0, // Entra quando l'RSI ENTRA in zona (sale sopra 70 / scende sotto 30)
   SIGNAL_CROSS_OUT = 1  // Entra quando l'RSI ESCE dalla zona (rientra sotto 70 / sopra 30)
  };

//--- Trading
input double           InpLots          = 0.01;            // Lotto
input ulong            InpMagic         = 20261006;        // Magic number
input int              InpDeviation     = 30;              // Slippage massimo (points)
input bool             InpOnePosition   = true;            // Una sola posizione alla volta

//--- RSI
input ENUM_TIMEFRAMES  InpRsiTimeframe  = PERIOD_M5;       // Timeframe RSI
input int              InpRsiPeriod     = 14;              // Periodo RSI
input ENUM_APPLIED_PRICE InpRsiPrice    = PRICE_CLOSE;     // Prezzo RSI
input double           InpRsiSellLevel  = 70.0;            // Livello SELL
input double           InpRsiBuyLevel   = 30.0;            // Livello BUY
input ENUM_SIGNAL_MODE InpSignalMode    = SIGNAL_CROSS_IN; // Modalita' segnale

//--- Stop loss (nessun take profit)
input double           InpStopLossPips  = 100.0;           // Stop loss (pips)
input double           InpPointsPerPip  = 10.0;            // Points per 1 pip (XAUUSD 2 decimali: 10 -> 1 pip = 0.10)

//--- Trailing a gradini: ogni 20 pips di profitto lo SL sale di 20 pips
input double           InpTrailStart    = 20.0;            // Profitto minimo per attivare il trailing (pips)
input double           InpTrailStep     = 20.0;            // Ogni quanti pips di profitto si sposta lo SL
input double           InpTrailDistance = 20.0;            // Distanza dello SL dal gradino raggiunto (pips)

CTrade   trade;
int      rsiHandle   = INVALID_HANDLE;
datetime lastBarTime = 0;
double   pipSize     = 0.0;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("ATTENZIONE: l'EA e' pensato per XAUUSD, simbolo attuale: ", _Symbol);

   pipSize = SymbolInfoDouble(_Symbol, SYMBOL_POINT) * InpPointsPerPip;
   if(pipSize <= 0.0)
     {
      Print("Pip size non valida");
      return(INIT_FAILED);
     }

   rsiHandle = iRSI(_Symbol, InpRsiTimeframe, InpRsiPeriod, InpRsiPrice);
   if(rsiHandle == INVALID_HANDLE)
     {
      Print("Impossibile creare l'indicatore RSI, errore ", GetLastError());
      return(INIT_FAILED);
     }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpDeviation);
   trade.SetTypeFillingBySymbol(_Symbol);

   PrintFormat("EA avviato su %s | pip = %.5f | SL = %.1f pips (%.2f di prezzo)",
               _Symbol, pipSize, InpStopLossPips, InpStopLossPips * pipSize);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(rsiHandle != INVALID_HANDLE)
      IndicatorRelease(rsiHandle);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   // Il trailing va controllato a ogni tick.
   ManageTrailing();

   // I segnali RSI si valutano solo alla chiusura di una candela M5.
   datetime barTime = iTime(_Symbol, InpRsiTimeframe, 0);
   if(barTime == 0 || barTime == lastBarTime)
      return;
   lastBarTime = barTime;

   CheckSignal();
  }

//+------------------------------------------------------------------+
void CheckSignal()
  {
   double rsi[];
   ArraySetAsSeries(rsi, true);
   // rsi[0] = ultima candela chiusa, rsi[1] = quella precedente
   if(CopyBuffer(rsiHandle, 0, 1, 2, rsi) != 2)
     {
      Print("CopyBuffer RSI fallito, errore ", GetLastError());
      return;
     }

   double last = rsi[0];
   double prev = rsi[1];
   bool sellSignal = false;
   bool buySignal  = false;

   if(InpSignalMode == SIGNAL_CROSS_IN)
     {
      sellSignal = (prev < InpRsiSellLevel && last >= InpRsiSellLevel);
      buySignal  = (prev > InpRsiBuyLevel  && last <= InpRsiBuyLevel);
     }
   else
     {
      sellSignal = (prev >= InpRsiSellLevel && last < InpRsiSellLevel);
      buySignal  = (prev <= InpRsiBuyLevel  && last > InpRsiBuyLevel);
     }

   if(!sellSignal && !buySignal)
      return;

   if(InpOnePosition && CountMyPositions() > 0)
     {
      PrintFormat("Segnale %s ignorato (RSI %.2f): posizione gia' aperta",
                  sellSignal ? "SELL" : "BUY", last);
      return;
     }

   double lots = NormalizeLots(InpLots);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   if(buySignal)
     {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl  = NormalizeDouble(ask - InpStopLossPips * pipSize, digits);
      if(trade.Buy(lots, _Symbol, ask, sl, 0.0, "RSI BUY"))
         PrintFormat("BUY aperto: RSI %.2f, prezzo %.2f, SL %.2f", last, ask, sl);
      else
         PrintFormat("BUY fallito: %d %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }
   else if(sellSignal)
     {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double sl  = NormalizeDouble(bid + InpStopLossPips * pipSize, digits);
      if(trade.Sell(lots, _Symbol, bid, sl, 0.0, "RSI SELL"))
         PrintFormat("SELL aperto: RSI %.2f, prezzo %.2f, SL %.2f", last, bid, sl);
      else
         PrintFormat("SELL fallito: %d %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }
  }

//+------------------------------------------------------------------+
//| Trailing a gradini: lo SL si sposta solo in avanti, mai indietro |
//+------------------------------------------------------------------+
void ManageTrailing()
  {
   int    digits     = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double point      = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   long   stopsLevel = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long   freeze     = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double minDist    = (double)MathMax(stopsLevel, freeze) * point;
   double bid        = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask        = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      long   type      = PositionGetInteger(POSITION_TYPE);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double curSL     = PositionGetDouble(POSITION_SL);
      double curTP     = PositionGetDouble(POSITION_TP);

      double profitPips = (type == POSITION_TYPE_BUY)
                          ? (bid - openPrice) / pipSize
                          : (openPrice - ask) / pipSize;

      double lockPips = LockForProfit(profitPips);
      if(lockPips < 0.0)
         continue; // nessun gradino raggiunto

      if(type == POSITION_TYPE_BUY)
        {
         double newSL = NormalizeDouble(openPrice + lockPips * pipSize, digits);
         if(curSL > 0.0 && newSL <= curSL + point / 2.0)
            continue;               // SL gia' a questo livello o migliore
         if(bid - newSL < minDist)
            continue;               // troppo vicino al prezzo per il broker
         if(trade.PositionModify(ticket, newSL, curTP))
            PrintFormat("Trailing BUY #%I64u: profitto %.1f pips -> SL a +%.0f pips (%.2f)",
                        ticket, profitPips, lockPips, newSL);
         else
            PrintFormat("Modifica SL fallita #%I64u: %d %s", ticket,
                        trade.ResultRetcode(), trade.ResultRetcodeDescription());
        }
      else
        {
         double newSL = NormalizeDouble(openPrice - lockPips * pipSize, digits);
         if(curSL > 0.0 && newSL >= curSL - point / 2.0)
            continue;
         if(newSL - ask < minDist)
            continue;
         if(trade.PositionModify(ticket, newSL, curTP))
            PrintFormat("Trailing SELL #%I64u: profitto %.1f pips -> SL a +%.0f pips (%.2f)",
                        ticket, profitPips, lockPips, newSL);
         else
            PrintFormat("Modifica SL fallita #%I64u: %d %s", ticket,
                        trade.ResultRetcode(), trade.ResultRetcodeDescription());
        }
     }
  }

//+------------------------------------------------------------------+
//| Restituisce i pips da bloccare per il profitto attuale (-1=none) |
//| Es. step 20, distanza 20: +20 -> SL a 0 (pareggio), +40 -> +20,  |
//| +60 -> +40, +80 -> +60 ... senza limite                          |
//+------------------------------------------------------------------+
double LockForProfit(double profitPips)
  {
   if(InpTrailStep <= 0.0 || profitPips < InpTrailStart)
      return(-1.0);
   double reached = MathFloor(profitPips / InpTrailStep) * InpTrailStep;
   return(reached - InpTrailDistance);
  }

//+------------------------------------------------------------------+
int CountMyPositions()
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
