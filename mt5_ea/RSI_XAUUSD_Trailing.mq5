//+------------------------------------------------------------------+
//|                                        RSI_XAUUSD_Trailing.mq5   |
//|  EA RSI su XAUUSD con stop loss e take profit fissi (in points)  |
//+------------------------------------------------------------------+
#property version   "2.00"
#property description "RSI(14) M1: >=60 SELL, <=25 BUY. SL e TP fissi in points, nessun trailing."

#include <Trade\Trade.mqh>

enum ENUM_SIGNAL_MODE
  {
   SIGNAL_CROSS_IN  = 0, // Entra quando l'RSI ENTRA in zona (sale al livello SELL / scende al livello BUY)
   SIGNAL_CROSS_OUT = 1  // Entra quando l'RSI ESCE dalla zona (rientra sotto il livello SELL / sopra il livello BUY)
  };

//--- Trading
input double           InpLots          = 0.01;            // Lotto
input ulong            InpMagic         = 20261006;        // Magic number
input bool             InpOnePosition   = true;            // Una sola posizione alla volta

//--- RSI
input ENUM_TIMEFRAMES  InpRsiTimeframe  = PERIOD_M1;       // Timeframe RSI
input int              InpRsiPeriod     = 14;              // Periodo RSI
input ENUM_APPLIED_PRICE InpRsiPrice    = PRICE_CLOSE;     // Prezzo RSI
input double           InpRsiSellLevel  = 60.0;            // Livello SELL
input double           InpRsiBuyLevel   = 25.0;            // Livello BUY
input ENUM_SIGNAL_MODE InpSignalMode    = SIGNAL_CROSS_IN; // Modalita' segnale

//--- Slippage
input double           InpSimSlipPerLot = 15.0;            // Slippage simulato nel tester ($ per lotto, 0 = off)
input bool             InpSimSlipOnClose= false;           // Applica lo slippage simulato anche in chiusura

//--- Filtro spread
input int              InpMaxSpreadPts  = 50;              // Opera solo se lo spread e' inferiore a (points, 0 = off)

//--- Stop loss e take profit (points: 1 point = 0.01 di prezzo = 0.01 $ a 0.01 lotti)
input int              InpStopLossPts   = 200;             // Stop loss (points, 0 = nessuno SL)
input int              InpTakeProfitPts = 200;             // Take profit (points, 0 = nessun TP)

#define NO_SLIPPAGE_LIMIT 100000   // points: in pratica nessun limite allo slippage

CTrade   trade;
int      rsiHandle   = INVALID_HANDLE;
datetime lastBarTime = 0;
double   simSlipTotal = 0.0;   // totale slippage simulato addebitato nel tester ($)
int      simSlipCount = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("ATTENZIONE: l'EA e' pensato per XAUUSD, simbolo attuale: ", _Symbol);

   rsiHandle = iRSI(_Symbol, InpRsiTimeframe, InpRsiPeriod, InpRsiPrice);
   if(rsiHandle == INVALID_HANDLE)
     {
      Print("Impossibile creare l'indicatore RSI, errore ", GetLastError());
      return(INIT_FAILED);
     }

   trade.SetExpertMagicNumber(InpMagic);
   // Nessun limite di slippage: l'ordine viene eseguito a qualunque prezzo disponibile.
   trade.SetDeviationInPoints(NO_SLIPPAGE_LIMIT);
   trade.SetTypeFillingBySymbol(_Symbol);

   PrintFormat("EA avviato su %s | SL = %d points | TP = %d points",
               _Symbol, InpStopLossPts, InpTakeProfitPts);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(rsiHandle != INVALID_HANDLE)
      IndicatorRelease(rsiHandle);
   if(simSlipCount > 0)
      PrintFormat("Slippage simulato totale: %.2f $ su %d deal", simSlipTotal, simSlipCount);
  }

//+------------------------------------------------------------------+
//| Slippage simulato: solo nello Strategy Tester, per ogni deal     |
//| dell'EA scala dal saldo InpSimSlipPerLot $ per lotto eseguito    |
//| (0.01 lotti -> 0.15 $ con il valore di default).                 |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(InpSimSlipPerLot <= 0.0 || !MQLInfoInteger(MQL_TESTER))
      return;
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
   if(!HistoryDealSelect(trans.deal))
      return;
   if(HistoryDealGetString(trans.deal, DEAL_SYMBOL) != _Symbol)
      return;
   if((ulong)HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic)
      return;

   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   bool isOpen  = (entry == DEAL_ENTRY_IN);
   bool isClose = (entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY || entry == DEAL_ENTRY_INOUT);
   if(!isOpen && !(isClose && InpSimSlipOnClose))
      return;

   double cost = NormalizeDouble(InpSimSlipPerLot * HistoryDealGetDouble(trans.deal, DEAL_VOLUME), 2);
   if(cost <= 0.0)
      return;
   if(TesterWithdrawal(cost))
     {
      simSlipTotal += cost;
      simSlipCount++;
      PrintFormat("Slippage simulato: -%.2f $ (deal #%I64u, %s)", cost, trans.deal, isOpen ? "apertura" : "chiusura");
     }
   else
      PrintFormat("TesterWithdrawal fallito (%.2f $), errore %d", cost, GetLastError());
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   // I segnali RSI si valutano solo alla chiusura di ogni candela del timeframe RSI.
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

   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   long   spread = (long)MathRound((SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / point);
   if(InpMaxSpreadPts > 0 && spread >= InpMaxSpreadPts)
     {
      PrintFormat("Segnale %s ignorato (RSI %.2f): spread %I64d points >= %d",
                  sellSignal ? "SELL" : "BUY", last, spread, InpMaxSpreadPts);
      return;
     }

   double lots = NormalizeLots(InpLots);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);

   if(buySignal)
     {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl  = (InpStopLossPts   > 0) ? NormalizeDouble(ask - InpStopLossPts   * point, digits) : 0.0;
      double tp  = (InpTakeProfitPts > 0) ? NormalizeDouble(ask + InpTakeProfitPts * point, digits) : 0.0;
      if(trade.Buy(lots, _Symbol, ask, sl, tp, "RSI BUY"))
         PrintFormat("BUY aperto: RSI %.2f, prezzo %.2f, SL %.2f, TP %.2f", last, ask, sl, tp);
      else
         PrintFormat("BUY fallito: %d %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }
   else if(sellSignal)
     {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double sl  = (InpStopLossPts   > 0) ? NormalizeDouble(bid + InpStopLossPts   * point, digits) : 0.0;
      double tp  = (InpTakeProfitPts > 0) ? NormalizeDouble(bid - InpTakeProfitPts * point, digits) : 0.0;
      if(trade.Sell(lots, _Symbol, bid, sl, tp, "RSI SELL"))
         PrintFormat("SELL aperto: RSI %.2f, prezzo %.2f, SL %.2f, TP %.2f", last, bid, sl, tp);
      else
         PrintFormat("SELL fallito: %d %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }
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
