//+------------------------------------------------------------------+
//|                                          RSI_Retracement_M15.mq5 |
//|  EA per MT5 Strategy Tester - ritracciamenti con RSI + EMA       |
//|                                                                  |
//|  Regole (tutto valutato a candela chiusa):                       |
//|  - Filtro trend (opzionale, disattivato di default):             |
//|                  EMA50 < EMA200 -> solo BUY                      |
//|                  EMA50 > EMA200 -> solo SELL                     |
//|                  (invertibile con InpInvertTrend)                |
//|  - BUY : RSI incrocia dal basso il livello 30                    |
//|  - SELL: RSI incrocia dall'alto il livello 70                    |
//|  - Una sola operazione aperta alla volta, lotto fisso            |
//|  - SL: ultimo swing low (buy) / swing high (sell) precedente     |
//|        all'apertura +/- 1 x ATR, con distanza minima/massima     |
//|  - BUY : RSI >= 45 -> SL a break-even, RSI >= 50 -> chiusura     |
//|  - SELL: RSI <= 55 -> SL a break-even, RSI <= 50 -> chiusura     |
//|  - Orario (server): nuove operazioni solo dalle 02:00 alle 18:00,|
//|    alle 18:00 chiude tutte le operazioni aperte                  |
//+------------------------------------------------------------------+
#property copyright "RSI Retracement M15"
#property version   "1.20"

#include <Trade\Trade.mqh>

enum ENUM_TRADE_DIRECTION
  {
   DIR_BOTH      = 0, // Buy e Sell
   DIR_BUY_ONLY  = 1, // Solo Buy
   DIR_SELL_ONLY = 2  // Solo Sell
  };

//--- Generali
input ENUM_TIMEFRAMES      InpTimeframe     = PERIOD_M15; // Timeframe di lavoro
input double               InpLots          = 0.01;       // Lotto fisso
input int                  InpSlippage      = 10;         // Slippage (points)
input ulong                InpMagic         = 150030;     // Magic number
input ENUM_TRADE_DIRECTION InpDirection     = DIR_BOTH;   // Direzione operazioni

//--- RSI
input int                  InpRsiPeriod     = 14;         // Periodo RSI
input double               InpBuyEntry      = 30.0;       // BUY: incrocio dal basso
input double               InpSellEntry     = 70.0;       // SELL: incrocio dall'alto
input double               InpBuyBE         = 45.0;       // BUY: livello break-even
input double               InpSellBE        = 55.0;       // SELL: livello break-even
input double               InpBuyTP         = 50.0;       // BUY: livello chiusura (TP)
input double               InpSellTP        = 50.0;       // SELL: livello chiusura (TP)

//--- Filtro trend
input bool                 InpUseTrendFilter= false;      // Usa filtro trend EMA
input int                  InpEmaFast       = 50;         // EMA veloce
input int                  InpEmaSlow       = 200;        // EMA lenta
input bool                 InpInvertTrend   = false;      // Inverti filtro (EMA50>EMA200 -> BUY)

//--- Stop Loss
input int                  InpSwingBars     = 2;          // Candele a sx/dx per swing
input int                  InpSwingLookback = 200;        // Candele massime di ricerca swing
input int                  InpAtrPeriod     = 14;         // Periodo ATR
input double               InpSLAtrMult     = 1.0;        // Distacco SL dallo swing (x ATR)
input double               InpSLMinAtr      = 1.0;        // Distanza minima SL dall'entrata (x ATR, 0=off)
input double               InpSLMaxAtr      = 3.0;        // Distanza massima SL dall'entrata (x ATR, 0=off)

//--- Filtro orario (ora del server)
input bool                 InpUseTimeFilter = true;       // Usa filtro orario
input int                  InpStartHour     = 2;          // Ora inizio apertura operazioni
input int                  InpEndHour       = 18;         // Ora fine operativita'
input bool                 InpCloseAtEnd    = true;       // Chiudi le operazioni all'ora di fine

CTrade   trade;
int      hRsi     = INVALID_HANDLE;
int      hEmaFast = INVALID_HANDLE;
int      hEmaSlow = INVALID_HANDLE;
int      hAtr     = INVALID_HANDLE;
datetime lastBar  = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   hRsi     = iRSI(_Symbol, InpTimeframe, InpRsiPeriod, PRICE_CLOSE);
   hEmaFast = iMA(_Symbol, InpTimeframe, InpEmaFast, 0, MODE_EMA, PRICE_CLOSE);
   hEmaSlow = iMA(_Symbol, InpTimeframe, InpEmaSlow, 0, MODE_EMA, PRICE_CLOSE);
   hAtr     = iATR(_Symbol, InpTimeframe, InpAtrPeriod);
   if(hRsi == INVALID_HANDLE || hEmaFast == INVALID_HANDLE ||
      hEmaSlow == INVALID_HANDLE || hAtr == INVALID_HANDLE)
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
   IndicatorRelease(hAtr);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   //--- lavora solo all'apertura di una nuova candela (= candela precedente chiusa)
   datetime barTime = iTime(_Symbol, InpTimeframe, 0);
   if(barTime == 0 || barTime == lastBar)
      return;

   double rsi[], emaFast[], emaSlow[], atr[];
   ArraySetAsSeries(rsi, true);
   ArraySetAsSeries(emaFast, true);
   ArraySetAsSeries(emaSlow, true);
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(hRsi, 0, 1, 2, rsi) != 2 ||
      CopyBuffer(hEmaFast, 0, 1, 1, emaFast) != 1 ||
      CopyBuffer(hEmaSlow, 0, 1, 1, emaSlow) != 1 ||
      CopyBuffer(hAtr, 0, 1, 1, atr) != 1)
      return; // dati non pronti, riprova al prossimo tick

   lastBar = barTime;

   double rsiLast = rsi[0]; // candela appena chiusa (shift 1)
   double rsiPrev = rsi[1]; // candela prima (shift 2)
   bool   inHours = IsTradingHour();

   //--- gestione posizione aperta
   ulong ticket;
   if(SelectMyPosition(ticket))
     {
      if(InpUseTimeFilter && InpCloseAtEnd && !inHours)
        {
         if(!trade.PositionClose(ticket))
            Print("Chiusura fine orario fallita: ", trade.ResultRetcodeDescription());
         return;
        }
      ManagePosition(ticket, rsiLast);
      return; // una sola operazione alla volta
     }

   if(!inHours)
      return;

   //--- ingressi
   bool upTrend   = emaFast[0] > emaSlow[0];
   bool downTrend = emaFast[0] < emaSlow[0];
   bool trendBuy  = !InpUseTrendFilter || (InpInvertTrend ? upTrend : downTrend);
   bool trendSell = !InpUseTrendFilter || (InpInvertTrend ? downTrend : upTrend);
   bool allowBuy  = InpDirection != DIR_SELL_ONLY;
   bool allowSell = InpDirection != DIR_BUY_ONLY;

   if(allowBuy && trendBuy && rsiPrev < InpBuyEntry && rsiLast >= InpBuyEntry)
      OpenBuy(atr[0]);
   else if(allowSell && trendSell && rsiPrev > InpSellEntry && rsiLast <= InpSellEntry)
      OpenSell(atr[0]);
  }

//+------------------------------------------------------------------+
//| true se l'ora del server e' nella finestra operativa             |
//| [InpStartHour, InpEndHour), anche a cavallo della mezzanotte     |
//+------------------------------------------------------------------+
bool IsTradingHour()
  {
   if(!InpUseTimeFilter)
      return(true);
   MqlDateTime t;
   TimeToStruct(TimeCurrent(), t);
   if(InpStartHour < InpEndHour)
      return(t.hour >= InpStartHour && t.hour < InpEndHour);
   return(t.hour >= InpStartHour || t.hour < InpEndHour);
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
void OpenBuy(const double atr)
  {
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double swing;
   if(!FindSwingLow(ask, swing))
     {
      Print("BUY saltato: nessuno swing low trovato");
      return;
     }
   double dist = ask - (swing - InpSLAtrMult * atr);
   if(InpSLMinAtr > 0.0 && dist < InpSLMinAtr * atr)
      dist = InpSLMinAtr * atr;
   if(InpSLMaxAtr > 0.0 && dist > InpSLMaxAtr * atr)
     {
      Print("BUY saltato: SL oltre ", InpSLMaxAtr, " x ATR");
      return;
     }
   double sl = NormalizeDouble(ask - dist, _Digits);
   if(ask - sl <= StopsDistance())
     {
      Print("BUY saltato: SL troppo vicino al prezzo");
      return;
     }
   if(!trade.Buy(NormalizeLots(InpLots), _Symbol, 0.0, sl, 0.0, "RSI Retr BUY"))
      Print("Apertura BUY fallita: ", trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
void OpenSell(const double atr)
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double swing;
   if(!FindSwingHigh(bid, swing))
     {
      Print("SELL saltato: nessuno swing high trovato");
      return;
     }
   double dist = (swing + InpSLAtrMult * atr) - bid;
   if(InpSLMinAtr > 0.0 && dist < InpSLMinAtr * atr)
      dist = InpSLMinAtr * atr;
   if(InpSLMaxAtr > 0.0 && dist > InpSLMaxAtr * atr)
     {
      Print("SELL saltato: SL oltre ", InpSLMaxAtr, " x ATR");
      return;
     }
   double sl = NormalizeDouble(bid + dist, _Digits);
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
