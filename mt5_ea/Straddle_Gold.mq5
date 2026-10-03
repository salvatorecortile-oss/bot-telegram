//+------------------------------------------------------------------+
//|                                                Straddle_Gold.mq5 |
//|  Rottura "a forbice" sull'oro (XAUUSD), tick per tick.           |
//|                                                                  |
//|  Modalita' (InpMode):                                            |
//|  - 0 = forbice fissa: BUY STOP a +InpDistance e SELL STOP a      |
//|        -InpDistance dal prezzo (ricentrata dopo InpRecenter).    |
//|  - 1 = rottura del range: se le ultime InpRangeBars candele M1   |
//|        stanno in un range non piu' largo di InpMaxRangeWidth,    |
//|        BUY STOP sopra il massimo e SELL STOP sotto il minimo     |
//|        (+/- InpRangeBuffer).                                     |
//|  Comune: stop loss InpStopLoss, l'altro ordine viene cancellato  |
//|  quando uno scatta, trailing senza take profit.                  |
//|                                                                  |
//|  Filtri: orari, due fasce orarie bloccate, spread massimo,       |
//|  stop giornaliero, volatilita' minima (ATR giornaliero in % del  |
//|  prezzo) e ordini stop limit per limitare lo slippage.           |
//|  Tutte le distanze sono in prezzo (1.00 = 1 dollaro sull'oro).   |
//+------------------------------------------------------------------+
#property copyright "Salvatore Cortile"
#property version   "2.00"
#property description "Oro: forbice fissa o rottura del range, stop stretto e trailing. Filtri di orario, fasce bloccate, spread, volatilita' e stop limit."

#include <Trade/Trade.mqh>

input group "Modalita'"
input int    InpMode          = 0;     // 0 = forbice fissa, 1 = rottura del range

input group "Forbice fissa (modalita' 0)"
input double InpDistance      = 1.20;  // Distanza dei BUY STOP / SELL STOP dal prezzo
input double InpRecenter      = 50.0;  // Ricentra la forbice se il prezzo si sposta di questo (valore alto = mai)

input group "Rottura del range (modalita' 1)"
input int    InpRangeBars     = 15;    // Candele M1 che formano il range
input double InpMaxRangeWidth = 3.00;  // Larghezza massima del range per operare
input double InpRangeBuffer   = 0.20;  // Margine oltre il massimo / minimo del range

input group "Gestione"
input double InpStopLoss      = 1.00;  // Stop loss dall'ingresso
input double InpTrailStart    = 0.50;  // Profitto oltre il quale parte il trailing
input double InpTrailDistance = 3.00;  // Distanza del trailing dal prezzo
input double InpTrailStep     = 2.00;  // Sposta lo stop solo se migliora almeno di questo

input group "Filtri e rischio"
input double InpLots            = 0.01;  // Lotto
input int    InpStartHour       = 10;    // Ora inizio (ora del server, 0-23)
input int    InpEndHour         = 19;    // Ora fine (esclusa, 1-24)
input string InpBlock1          = "";    // Fascia bloccata 1, es. "15:00-16:00" (vuoto = nessuna)
input string InpBlock2          = "";    // Fascia bloccata 2, es. "16:55-17:10" (vuoto = nessuna)
input int    InpMaxSpreadPoints = 35;    // Spread massimo per mettere gli ordini, in points (0 = nessun filtro)
input double InpDailyLossLimit  = 30.0;  // Stop giornaliero (0 = spento)
input double InpMinAtrPercent   = 0.0;   // Volatilita' minima: ATR giornaliero in % del prezzo (0 = filtro spento)
input int    InpAtrPeriod       = 14;    // Periodo dell'ATR giornaliero

input group "Ordini"
input bool   InpUseStopLimit   = false;    // Usa ordini stop limit per limitare lo slippage
input double InpMaxSlippage    = 0.30;     // Stop limit: prezzo d'ingresso al massimo peggiore di questo
input int    InpSlippagePoints = 30;       // Slippage massimo in points (ordini a mercato)
input ulong  InpMagic          = 26100601; // Magic number
input string InpComment        = "Straddle Gold";

CTrade   trade;
double   dayPnl     = 0.0;
datetime pnlChecked = 0;
int      atrHandle  = INVALID_HANDLE;
int      block1Start = -1, block1End = -1, block2Start = -1, block2End = -1;
double   lastRangeHigh = 0.0, lastRangeLow = 0.0;   // range su cui sono stati messi gli ordini (modalita' 1)

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpMode < 0 || InpMode > 1 || InpDistance <= 0 || InpStopLoss <= 0 || InpTrailDistance <= 0 ||
      InpTrailStart < 0 || InpTrailStep < 0 || InpRecenter <= 0 || InpLots <= 0 || InpDailyLossLimit < 0 ||
      InpRangeBars < 2 || InpMaxRangeWidth <= 0 || InpRangeBuffer < 0 || InpMinAtrPercent < 0 ||
      InpAtrPeriod < 1 || InpMaxSlippage <= 0 ||
      InpStartHour < 0 || InpStartHour > 23 || InpEndHour < 1 || InpEndHour > 24)
     {
      Print("Parametri non validi.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!ParseWindow(InpBlock1, block1Start, block1End) || !ParseWindow(InpBlock2, block2Start, block2End))
     {
      Print("Fascia bloccata non valida: usa il formato \"HH:MM-HH:MM\".");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(InpMinAtrPercent > 0)
     {
      atrHandle = iATR(_Symbol, PERIOD_D1, InpAtrPeriod);
      if(atrHandle == INVALID_HANDLE)
        {
         Print("Impossibile creare l'ATR giornaliero: ", GetLastError());
         return(INIT_FAILED);
        }
     }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   PrintFormat("Straddle_Gold avviato su %s | modalita' %s | stop %.2f | trailing %.2f/%.2f | orari %d-%d | fasce bloccate [%s] [%s] | ATR min %.2f%% | stop limit %s",
               _Symbol, InpMode == 0 ? "forbice fissa" : "rottura del range", InpStopLoss, InpTrailDistance, InpTrailStep,
               InpStartHour, InpEndHour, InpBlock1, InpBlock2, InpMinAtrPercent, InpUseStopLimit ? "si" : "no");
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(atrHandle != INVALID_HANDLE)
      IndicatorRelease(atrHandle);
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   string state;
   ulong  pos = PositionTicket();
   if(pos != 0)
     {
      // Una posizione e' aperta: niente ordini pendenti, solo trailing.
      DeletePendings();
      ManageTrailing(pos, tick);
      state = "posizione aperta (trailing)";
     }
   else
      state = ManagePendings(tick);

   UpdatePanel(state, tick);
  }

//+------------------------------------------------------------------+
//| Controlla i filtri e mette / aggiorna / toglie gli ordini.       |
//+------------------------------------------------------------------+
string ManagePendings(const MqlTick &tick)
  {
   UpdateDayPnl();
   if(InpDailyLossLimit > 0 && dayPnl <= -InpDailyLossLimit)
     {
      DeletePendings();
      return(StringFormat("fermo: perdita del giorno %.2f", dayPnl));
     }
   if(!InTradingHours())
     {
      DeletePendings();
      return("fuori orario");
     }
   if(InBlockedWindow())
     {
      DeletePendings();
      return("fascia oraria bloccata");
     }
   double spreadPts = (tick.ask - tick.bid) / _Point;
   if(InpMaxSpreadPoints > 0 && spreadPts > InpMaxSpreadPoints)
     {
      DeletePendings();
      return(StringFormat("spread troppo alto (%.0f points)", spreadPts));
     }
   double atrPct;
   if(!VolatilityOk(atrPct))
     {
      DeletePendings();
      return(StringFormat("volatilita' bassa (ATR %.2f%% < %.2f%%)", atrPct, InpMinAtrPercent));
     }

   // Livelli voluti per BUY e SELL.
   double wantBuy, wantSell, high = 0, low = 0;
   if(InpMode == 1)
     {
      int hi = iHighest(_Symbol, PERIOD_M1, MODE_HIGH, InpRangeBars, 1);
      int lo = iLowest(_Symbol, PERIOD_M1, MODE_LOW, InpRangeBars, 1);
      if(hi < 0 || lo < 0)
         return("dati M1 non pronti");
      high = iHigh(_Symbol, PERIOD_M1, hi);
      low  = iLow(_Symbol, PERIOD_M1, lo);
      if(high - low > InpMaxRangeWidth)
        {
         DeletePendings();
         return(StringFormat("range troppo largo (%.2f)", high - low));
        }
      wantBuy  = NormalizeDouble(MathMax(high + InpRangeBuffer, tick.ask + 0.10), _Digits);
      wantSell = NormalizeDouble(MathMin(low - InpRangeBuffer, tick.bid - 0.10), _Digits);
     }
   else
     {
      wantBuy  = NormalizeDouble(tick.ask + InpDistance, _Digits);
      wantSell = NormalizeDouble(tick.bid - InpDistance, _Digits);
     }

   // Ordini attuali.
   ulong  buyT = 0, sellT = 0;
   double buyP = 0, sellP = 0;
   int    count = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t == 0 || OrderGetString(ORDER_SYMBOL) != _Symbol || (ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic)
         continue;
      count++;
      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(type == ORDER_TYPE_BUY_STOP || type == ORDER_TYPE_BUY_STOP_LIMIT)
        {
         buyT = t;
         buyP = OrderGetDouble(ORDER_PRICE_OPEN);
        }
      else
         if(type == ORDER_TYPE_SELL_STOP || type == ORDER_TYPE_SELL_STOP_LIMIT)
           {
            sellT = t;
            sellP = OrderGetDouble(ORDER_PRICE_OPEN);
           }
     }

   // Coppia incompleta (o uno stop limit scattato ma non eseguito): si rifa' da capo.
   if(buyT == 0 || sellT == 0 || count != 2)
     {
      DeletePendings();
      PlaceOrder(true, wantBuy);
      PlaceOrder(false, wantSell);
      lastRangeHigh = high;
      lastRangeLow  = low;
      return(InpMode == 1 ? "ordini sul range piazzati" : "forbice piazzata");
     }

   // Aggiornamento dei livelli.
   bool move = false;
   if(InpMode == 1)
      move = (high != lastRangeHigh || low != lastRangeLow);   // il range e' cambiato (nuova candela)
   else
      move = (MathAbs((tick.ask + tick.bid) / 2.0 - (buyP + sellP) / 2.0) >= InpRecenter);
   if(move)
     {
      ModifyOrder(buyT, true, wantBuy);
      ModifyOrder(sellT, false, wantSell);
      lastRangeHigh = high;
      lastRangeLow  = low;
      return(InpMode == 1 ? "ordini spostati sul nuovo range" : "forbice ricentrata");
     }
   return(InpMode == 1 ? "in attesa della rottura del range" : "forbice in attesa");
  }

//+------------------------------------------------------------------+
void PlaceOrder(bool isBuy, double price)
  {
   double sl = NormalizeDouble(isBuy ? price - InpStopLoss : price + InpStopLoss, _Digits);
   bool   ok;
   if(InpUseStopLimit)
     {
      double limit = NormalizeDouble(isBuy ? price + InpMaxSlippage : price - InpMaxSlippage, _Digits);
      ok = trade.OrderOpen(_Symbol, isBuy ? ORDER_TYPE_BUY_STOP_LIMIT : ORDER_TYPE_SELL_STOP_LIMIT,
                           InpLots, limit, price, sl, 0.0, ORDER_TIME_GTC, 0, InpComment);
     }
   else
      ok = isBuy ? trade.BuyStop(InpLots, price, _Symbol, sl, 0.0, ORDER_TIME_GTC, 0, InpComment)
                 : trade.SellStop(InpLots, price, _Symbol, sl, 0.0, ORDER_TIME_GTC, 0, InpComment);
   if(!ok)
      PrintFormat("%s fallito: %u %s", isBuy ? "BUY STOP" : "SELL STOP", trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
void ModifyOrder(ulong ticket, bool isBuy, double price)
  {
   double sl    = NormalizeDouble(isBuy ? price - InpStopLoss : price + InpStopLoss, _Digits);
   double limit = InpUseStopLimit ? NormalizeDouble(isBuy ? price + InpMaxSlippage : price - InpMaxSlippage, _Digits) : 0.0;
   trade.OrderModify(ticket, price, sl, 0.0, ORDER_TIME_GTC, 0, limit);
  }

//+------------------------------------------------------------------+
//| Lo stop segue il prezzo una volta superato InpTrailStart.        |
//+------------------------------------------------------------------+
void ManageTrailing(ulong ticket, const MqlTick &tick)
  {
   if(!PositionSelectByTicket(ticket))
      return;
   bool   isBuy     = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
   double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
   double curSl     = PositionGetDouble(POSITION_SL);
   double profit    = isBuy ? tick.bid - openPrice : openPrice - tick.ask;
   if(profit < InpTrailStart)
      return;

   double newSl  = NormalizeDouble(isBuy ? tick.bid - InpTrailDistance : tick.ask + InpTrailDistance, _Digits);
   bool   better = isBuy ? (curSl == 0 || newSl >= curSl + InpTrailStep) : (curSl == 0 || newSl <= curSl - InpTrailStep);
   if(!better)
      return;

   double minDist = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(isBuy ? (tick.bid - newSl <= minDist) : (newSl - tick.ask <= minDist))
      return;
   trade.PositionModify(ticket, newSl, PositionGetDouble(POSITION_TP));
  }

//+------------------------------------------------------------------+
//| ATR giornaliero (ultimo giorno chiuso) in % del prezzo.          |
//+------------------------------------------------------------------+
bool VolatilityOk(double &atrPct)
  {
   atrPct = 0.0;
   if(InpMinAtrPercent <= 0)
      return(true);
   double atr[];
   double close = iClose(_Symbol, PERIOD_D1, 1);
   if(CopyBuffer(atrHandle, 0, 1, 1, atr) != 1 || close <= 0)
      return(false);
   atrPct = atr[0] / close * 100.0;
   return(atrPct >= InpMinAtrPercent);
  }

//+------------------------------------------------------------------+
void DeletePendings()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t != 0 && OrderGetString(ORDER_SYMBOL) == _Symbol && (ulong)OrderGetInteger(ORDER_MAGIC) == InpMagic)
         trade.OrderDelete(t);
     }
  }

//+------------------------------------------------------------------+
ulong PositionTicket()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t != 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return(t);
     }
   return(0);
  }

//+------------------------------------------------------------------+
//| Risultato delle operazioni chiuse oggi (ricalcolato ogni 5 s).   |
//+------------------------------------------------------------------+
void UpdateDayPnl()
  {
   datetime now = TimeCurrent();
   if(now - pnlChecked < 5)
      return;
   pnlChecked = now;

   datetime dayStart = now - (now % 86400);
   dayPnl = 0.0;
   if(!HistorySelect(dayStart, now + 60))
      return;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0 || HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol || (ulong)HistoryDealGetInteger(d, DEAL_MAGIC) != InpMagic)
         continue;
      if(HistoryDealGetInteger(d, DEAL_ENTRY) != DEAL_ENTRY_OUT)
         continue;
      dayPnl += HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) + HistoryDealGetDouble(d, DEAL_COMMISSION);
     }
  }

//+------------------------------------------------------------------+
bool InTradingHours()
  {
   MqlDateTime t;
   TimeToStruct(TimeCurrent(), t);
   if(InpStartHour < InpEndHour)
      return(t.hour >= InpStartHour && t.hour < InpEndHour);
   return(t.hour >= InpStartHour || t.hour < InpEndHour);
  }

//+------------------------------------------------------------------+
//| "HH:MM-HH:MM" -> minuti dall'inizio del giorno. Vuoto = nessuna. |
//+------------------------------------------------------------------+
bool ParseWindow(string text, int &startMin, int &endMin)
  {
   startMin = -1;
   endMin   = -1;
   StringTrimLeft(text);
   StringTrimRight(text);
   if(text == "")
      return(true);
   string parts[];
   if(StringSplit(text, '-', parts) != 2)
      return(false);
   startMin = ToMinutes(parts[0]);
   endMin   = ToMinutes(parts[1]);
   return(startMin >= 0 && endMin >= 0);
  }

//+------------------------------------------------------------------+
int ToMinutes(string hhmm)
  {
   StringTrimLeft(hhmm);
   StringTrimRight(hhmm);
   string p[];
   if(StringSplit(hhmm, ':', p) != 2)
      return(-1);
   int h = (int)StringToInteger(p[0]), m = (int)StringToInteger(p[1]);
   if(h < 0 || h > 24 || m < 0 || m > 59)
      return(-1);
   return(h * 60 + m);
  }

//+------------------------------------------------------------------+
bool InWindow(int nowMin, int startMin, int endMin)
  {
   if(startMin < 0)
      return(false);
   if(startMin <= endMin)
      return(nowMin >= startMin && nowMin < endMin);
   return(nowMin >= startMin || nowMin < endMin);
  }

//+------------------------------------------------------------------+
bool InBlockedWindow()
  {
   MqlDateTime t;
   TimeToStruct(TimeCurrent(), t);
   int nowMin = t.hour * 60 + t.min;
   return(InWindow(nowMin, block1Start, block1End) || InWindow(nowMin, block2Start, block2End));
  }

//+------------------------------------------------------------------+
void UpdatePanel(string state, const MqlTick &tick)
  {
   Comment(StringFormat("Straddle Gold  |  %s  |  %s  |  lotto %.2f\nOrari %02d:00-%02d:00  |  spread %.0f points\nStato: %s\nRisultato di oggi: %.2f  (stop giornaliero -%.2f)",
                        _Symbol, InpMode == 0 ? "forbice fissa" : "rottura del range", InpLots,
                        InpStartHour, InpEndHour, (tick.ask - tick.bid) / _Point, state, dayPnl, InpDailyLossLimit));
  }
//+------------------------------------------------------------------+
