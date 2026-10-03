//+------------------------------------------------------------------+
//|                                                Straddle_Gold.mq5 |
//|  Rottura "a forbice" sull'oro (XAUUSD), tick per tick.           |
//|                                                                  |
//|  - Senza posizioni: BUY STOP a +InpDistance dal prezzo e         |
//|    SELL STOP a -InpDistance, ognuno con stop loss a InpStopLoss. |
//|  - Quando uno scatta, l'altro viene cancellato.                  |
//|  - Trailing: oltre InpTrailStart di profitto lo stop segue il    |
//|    prezzo a InpTrailDistance. Nessun take profit.                |
//|  - Se il prezzo si sposta di InpRecenter senza far scattare      |
//|    niente, la forbice viene ricentrata.                          |
//|  - Opera solo negli orari impostati (ora del server), con filtro |
//|    sullo spread e stop sulla perdita giornaliera.                |
//|  Tutte le distanze sono in prezzo (1.00 = 1 dollaro sull'oro).   |
//+------------------------------------------------------------------+
#property copyright "Salvatore Cortile"
#property version   "1.00"
#property description "Oro: BUY STOP e SELL STOP attorno al prezzo, stop stretto e trailing. Orari, filtro spread e stop giornaliero."

#include <Trade/Trade.mqh>

input group "Forbice"
input double InpDistance      = 1.20;  // Distanza dei BUY STOP / SELL STOP dal prezzo
input double InpStopLoss      = 1.00;  // Stop loss dall'ingresso
input double InpTrailStart    = 0.50;  // Profitto oltre il quale parte il trailing
input double InpTrailDistance = 0.80;  // Distanza del trailing dal prezzo
input double InpTrailStep     = 0.05;  // Sposta lo stop solo se migliora almeno di questo
input double InpRecenter      = 0.50;  // Ricentra la forbice se il prezzo si sposta di questo

input group "Filtri e rischio"
input double InpLots            = 0.01;  // Lotto
input int    InpStartHour       = 9;     // Ora inizio (ora del server, 0-23)
input int    InpEndHour         = 18;    // Ora fine (esclusa, 1-24)
input int    InpMaxSpreadPoints = 35;    // Spread massimo per mettere la forbice, in points (0 = nessun filtro)
input double InpDailyLossLimit  = 30.0;  // Stop giornaliero: si ferma se la perdita del giorno arriva a questo (0 = spento)

input group "Ordini"
input int    InpSlippagePoints = 30;       // Slippage massimo in points
input ulong  InpMagic          = 26100601; // Magic number
input string InpComment        = "Straddle Gold";

CTrade trade;
double dayPnl      = 0.0;
datetime pnlChecked = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpDistance <= 0 || InpStopLoss <= 0 || InpTrailDistance <= 0 || InpTrailStart < 0 || InpTrailStep < 0 ||
      InpRecenter <= 0 || InpLots <= 0 || InpDailyLossLimit < 0 ||
      InpStartHour < 0 || InpStartHour > 23 || InpEndHour < 1 || InpEndHour > 24)
     {
      Print("Parametri non validi.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePoints);
   trade.SetTypeFillingBySymbol(_Symbol);
   PrintFormat("Straddle_Gold avviato su %s | forbice %.2f | stop %.2f | trailing da %.2f a %.2f | orari %d-%d | lotto %.2f | stop giornaliero %.2f",
               _Symbol, InpDistance, InpStopLoss, InpTrailStart, InpTrailDistance, InpStartHour, InpEndHour, InpLots, InpDailyLossLimit);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
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
//| Mette, ricentra o toglie la forbice. Restituisce lo stato.       |
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
   double spreadPts = (tick.ask - tick.bid) / _Point;
   if(InpMaxSpreadPoints > 0 && spreadPts > InpMaxSpreadPoints)
     {
      DeletePendings();
      return(StringFormat("spread troppo alto (%.0f points)", spreadPts));
     }

   ulong buyStop = 0, sellStop = 0;
   double buyPrice = 0, sellPrice = 0;
   int    count = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t == 0 || OrderGetString(ORDER_SYMBOL) != _Symbol || (ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic)
         continue;
      count++;
      ENUM_ORDER_TYPE type = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(type == ORDER_TYPE_BUY_STOP)
        {
         buyStop  = t;
         buyPrice = OrderGetDouble(ORDER_PRICE_OPEN);
        }
      else
         if(type == ORDER_TYPE_SELL_STOP)
           {
            sellStop  = t;
            sellPrice = OrderGetDouble(ORDER_PRICE_OPEN);
           }
     }

   // Forbice incompleta o con ordini estranei: si rifa' da capo.
   if(buyStop == 0 || sellStop == 0 || count != 2)
     {
      DeletePendings();
      PlacePair(tick);
      return("forbice piazzata");
     }

   // Il prezzo si e' spostato: ricentra la forbice attorno al prezzo attuale.
   double center = (buyPrice + sellPrice) / 2.0;
   double mid    = (tick.ask + tick.bid) / 2.0;
   if(MathAbs(mid - center) >= InpRecenter)
     {
      double bp = NormalizeDouble(tick.ask + InpDistance, _Digits);
      double sp = NormalizeDouble(tick.bid - InpDistance, _Digits);
      trade.OrderModify(buyStop, bp, NormalizeDouble(bp - InpStopLoss, _Digits), 0.0, ORDER_TIME_GTC, 0);
      trade.OrderModify(sellStop, sp, NormalizeDouble(sp + InpStopLoss, _Digits), 0.0, ORDER_TIME_GTC, 0);
      return("forbice ricentrata");
     }
   return("forbice in attesa");
  }

//+------------------------------------------------------------------+
void PlacePair(const MqlTick &tick)
  {
   double bp = NormalizeDouble(tick.ask + InpDistance, _Digits);
   double sp = NormalizeDouble(tick.bid - InpDistance, _Digits);
   if(!trade.BuyStop(InpLots, bp, _Symbol, NormalizeDouble(bp - InpStopLoss, _Digits), 0.0, ORDER_TIME_GTC, 0, InpComment))
      PrintFormat("BUY STOP fallito: %u %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
   if(!trade.SellStop(InpLots, sp, _Symbol, NormalizeDouble(sp + InpStopLoss, _Digits), 0.0, ORDER_TIME_GTC, 0, InpComment))
      PrintFormat("SELL STOP fallito: %u %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
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

   double newSl = NormalizeDouble(isBuy ? tick.bid - InpTrailDistance : tick.ask + InpTrailDistance, _Digits);
   bool   better = isBuy ? (curSl == 0 || newSl >= curSl + InpTrailStep) : (curSl == 0 || newSl <= curSl - InpTrailStep);
   if(!better)
      return;

   double minDist = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(isBuy ? (tick.bid - newSl <= minDist) : (newSl - tick.ask <= minDist))
      return;
   trade.PositionModify(ticket, newSl, PositionGetDouble(POSITION_TP));
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
void UpdatePanel(string state, const MqlTick &tick)
  {
   Comment(StringFormat("Straddle Gold  |  %s  |  lotto %.2f\nOrari %02d:00-%02d:00  |  spread %.0f points\nStato: %s\nRisultato di oggi: %.2f  (stop giornaliero -%.2f)",
                        _Symbol, InpLots, InpStartHour, InpEndHour, (tick.ask - tick.bid) / _Point,
                        state, dayPnl, InpDailyLossLimit));
  }
//+------------------------------------------------------------------+
