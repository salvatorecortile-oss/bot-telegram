//+------------------------------------------------------------------+
//|                                          RSI_Retracement_M15.mq5 |
//|  EA per MT5 Strategy Tester - ritracciamenti con RSI + EMA       |
//|                                                                  |
//|  Regole (tutto valutato a candela chiusa):                       |
//|  - Filtro trend: EMA50 < EMA200 -> solo BUY                      |
//|                  EMA50 > EMA200 -> solo SELL                     |
//|  - BUY : RSI incrocia dal basso il livello 30                    |
//|  - SELL: RSI incrocia dall'alto il livello 70                    |
//|  - Una sola operazione aperta alla volta, lotto fisso            |
//|  - SL: ultimo swing low (buy) / swing high (sell) precedente     |
//|        all'apertura +/- 20 pips di distacco                      |
//|  - BUY : RSI >= 45 -> SL a break-even, RSI >= 50 -> chiusura     |
//|  - SELL: RSI <= 55 -> SL a break-even, RSI <= 50 -> chiusura     |
//+------------------------------------------------------------------+
#property copyright "RSI Retracement M15"
#property version   "1.00"

#include <Trade\Trade.mqh>

//--- Generali
input ENUM_TIMEFRAMES InpTimeframe    = PERIOD_M15; // Timeframe di lavoro
input double          InpLots         = 0.01;       // Lotto fisso
input int             InpSlippage     = 10;         // Slippage (points)
input ulong           InpMagic        = 150030;     // Magic number

//--- RSI
input int             InpRsiPeriod    = 14;         // Periodo RSI
input double          InpBuyEntry     = 30.0;       // BUY: incrocio dal basso
input double          InpSellEntry    = 70.0;       // SELL: incrocio dall'alto
input double          InpBuyBE        = 45.0;       // BUY: livello break-even
input double          InpSellBE       = 55.0;       // SELL: livello break-even
input double          InpBuyTP        = 50.0;       // BUY: livello chiusura (TP)
input double          InpSellTP       = 50.0;       // SELL: livello chiusura (TP)

//--- Filtro trend
input int             InpEmaFast      = 50;         // EMA veloce
input int             InpEmaSlow      = 200;        // EMA lenta

//--- Stop Loss
input int             InpSwingBars    = 2;          // Candele a sx/dx per swing
input int             InpSwingLookback= 200;        // Candele massime di ricerca swing
input double          InpSLBufferPips = 20.0;       // Distacco SL dallo swing (pips)
input int             InpPipPoints    = 10;         // Points per 1 pip

CTrade   trade;
int      hRsi     = INVALID_HANDLE;
int      hEmaFast = INVALID_HANDLE;
int      hEmaSlow = INVALID_HANDLE;
datetime lastBar  = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   hRsi     = iRSI(_Symbol, InpTimeframe, InpRsiPeriod, PRICE_CLOSE);
   hEmaFast = iMA(_Symbol, InpTimeframe, InpEmaFast, 0, MODE_EMA, PRICE_CLOSE);
   hEmaSlow = iMA(_Symbol, InpTimeframe, InpEmaSlow, 0, MODE_EMA, PRICE_CLOSE);
   if(hRsi == INVALID_HANDLE || hEmaFast == INVALID_HANDLE || hEmaSlow == INVALID_HANDLE)
     {
      Print("Errore creazione indicatori: ", GetLastError());
      return(INIT_FAILED);
     }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippage);
   trade.SetTypeFillingBySymbol(_Symbol);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   IndicatorRelease(hRsi);
   IndicatorRelease(hEmaFast);
   IndicatorRelease(hEmaSlow);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   //--- lavora solo all'apertura di una nuova candela (= candela precedente chiusa)
   datetime barTime = iTime(_Symbol, InpTimeframe, 0);
   if(barTime == 0 || barTime == lastBar)
      return;

   double rsi[], emaFast[], emaSlow[];
   ArraySetAsSeries(rsi, true);
   ArraySetAsSeries(emaFast, true);
   ArraySetAsSeries(emaSlow, true);
   if(CopyBuffer(hRsi, 0, 1, 2, rsi) != 2 ||
      CopyBuffer(hEmaFast, 0, 1, 1, emaFast) != 1 ||
      CopyBuffer(hEmaSlow, 0, 1, 1, emaSlow) != 1)
      return; // dati non pronti, riprova al prossimo tick

   lastBar = barTime;

   double rsiLast = rsi[0]; // candela appena chiusa (shift 1)
   double rsiPrev = rsi[1]; // candela prima (shift 2)

   //--- gestione posizione aperta
   ulong ticket;
   if(SelectMyPosition(ticket))
     {
      ManagePosition(ticket, rsiLast);
      return; // una sola operazione alla volta
     }

   //--- ingressi
   bool trendBuy  = emaFast[0] < emaSlow[0];
   bool trendSell = emaFast[0] > emaSlow[0];

   if(trendBuy && rsiPrev < InpBuyEntry && rsiLast >= InpBuyEntry)
      OpenBuy();
   else if(trendSell && rsiPrev > InpSellEntry && rsiLast <= InpSellEntry)
      OpenSell();
  }

//+------------------------------------------------------------------+
//| Trova la posizione dell'EA sul simbolo corrente                  |
//+------------------------------------------------------------------+
bool SelectMyPosition(ulong &ticket)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == (long)InpMagic)
        {
         ticket = t;
         return(true);
        }
     }
   return(false);
  }

//+------------------------------------------------------------------+
//| Break-even e chiusura su livelli RSI                             |
//+------------------------------------------------------------------+
void ManagePosition(const ulong ticket, const double rsiLast)
  {
   if(!PositionSelectByTicket(ticket))
      return;

   long   type      = PositionGetInteger(POSITION_TYPE);
   double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
   double sl        = PositionGetDouble(POSITION_SL);
   double tp        = PositionGetDouble(POSITION_TP);
   double bePrice   = NormalizeDouble(openPrice, _Digits);
   double minDist   = StopsDistance();

   if(type == POSITION_TYPE_BUY)
     {
      if(rsiLast >= InpBuyTP)
        {
         if(!trade.PositionClose(ticket))
            Print("Chiusura BUY fallita: ", trade.ResultRetcodeDescription());
         return;
        }
      if(rsiLast >= InpBuyBE && (sl == 0.0 || sl < bePrice))
        {
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         if(bid - bePrice > minDist)
           {
            if(!trade.PositionModify(ticket, bePrice, tp))
               Print("BE BUY fallito: ", trade.ResultRetcodeDescription());
           }
        }
     }
   else if(type == POSITION_TYPE_SELL)
     {
      if(rsiLast <= InpSellTP)
        {
         if(!trade.PositionClose(ticket))
            Print("Chiusura SELL fallita: ", trade.ResultRetcodeDescription());
         return;
        }
      if(rsiLast <= InpSellBE && (sl == 0.0 || sl > bePrice))
        {
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         if(bePrice - ask > minDist)
           {
            if(!trade.PositionModify(ticket, bePrice, tp))
               Print("BE SELL fallito: ", trade.ResultRetcodeDescription());
           }
        }
     }
  }

//+------------------------------------------------------------------+
void OpenBuy()
  {
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double swing;
   if(!FindSwingLow(ask, swing))
     {
      Print("BUY saltato: nessuno swing low trovato");
      return;
     }
   double sl = NormalizeDouble(swing - InpSLBufferPips * InpPipPoints * _Point, _Digits);
   if(ask - sl <= StopsDistance())
     {
      Print("BUY saltato: SL troppo vicino al prezzo");
      return;
     }
   if(!trade.Buy(NormalizeLots(InpLots), _Symbol, 0.0, sl, 0.0, "RSI Retr BUY"))
      Print("Apertura BUY fallita: ", trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
void OpenSell()
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double swing;
   if(!FindSwingHigh(bid, swing))
     {
      Print("SELL saltato: nessuno swing high trovato");
      return;
     }
   double sl = NormalizeDouble(swing + InpSLBufferPips * InpPipPoints * _Point, _Digits);
   if(sl - bid <= StopsDistance())
     {
      Print("SELL saltato: SL troppo vicino al prezzo");
      return;
     }
   if(!trade.Sell(NormalizeLots(InpLots), _Symbol, 0.0, sl, 0.0, "RSI Retr SELL"))
      Print("Apertura SELL fallita: ", trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
//| Ultimo swing low confermato sotto il prezzo di entrata.          |
//| Uno swing low ha il minimo piu' basso delle N candele a sx e dx. |
//| Se nessuno e' sotto il prezzo, usa il minimo piu' basso del      |
//| periodo di ricerca.                                              |
//+------------------------------------------------------------------+
bool FindSwingLow(const double price, double &swing)
  {
   int n     = InpSwingBars;
   int count = InpSwingLookback + n + 1;
   double low[];
   ArraySetAsSeries(low, true);
   if(CopyLow(_Symbol, InpTimeframe, 0, count, low) != count)
      return(false);

   for(int i = n + 1; i <= InpSwingLookback; i++)
     {
      bool isSwing = true;
      for(int k = 1; k <= n && isSwing; k++)
         if(low[i] >= low[i - k] || low[i] > low[i + k])
            isSwing = false;
      if(isSwing && low[i] < price)
        {
         swing = low[i];
         return(true);
        }
     }

   //--- fallback: minimo piu' basso delle candele chiuse nel lookback
   int idx = ArrayMinimum(low, 1, InpSwingLookback);
   if(idx < 0 || low[idx] >= price)
      return(false);
   swing = low[idx];
   return(true);
  }

//+------------------------------------------------------------------+
bool FindSwingHigh(const double price, double &swing)
  {
   int n     = InpSwingBars;
   int count = InpSwingLookback + n + 1;
   double high[];
   ArraySetAsSeries(high, true);
   if(CopyHigh(_Symbol, InpTimeframe, 0, count, high) != count)
      return(false);

   for(int i = n + 1; i <= InpSwingLookback; i++)
     {
      bool isSwing = true;
      for(int k = 1; k <= n && isSwing; k++)
         if(high[i] <= high[i - k] || high[i] < high[i + k])
            isSwing = false;
      if(isSwing && high[i] > price)
        {
         swing = high[i];
         return(true);
        }
     }

   int idx = ArrayMaximum(high, 1, InpSwingLookback);
   if(idx < 0 || high[idx] <= price)
      return(false);
   swing = high[idx];
   return(true);
  }

//+------------------------------------------------------------------+
double StopsDistance()
  {
   long level = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   return(level * _Point);
  }

//+------------------------------------------------------------------+
double NormalizeLots(const double lots)
  {
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double v = MathFloor(lots / step + 0.5) * step;
   return(MathMax(minLot, MathMin(maxLot, v)));
  }
//+------------------------------------------------------------------+
