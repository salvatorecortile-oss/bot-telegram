//+------------------------------------------------------------------+
//|                                                  RSI_M1_Bot.mq5  |
//|  Expert Advisor per MT5. Serve un conto HEDGING.                 |
//|                                                                  |
//|  - Timeframe di lavoro M15, RSI 14.                              |
//|  - Filtro trend H1: prezzo sopra EMA 200 H1 -> solo BUY,         |
//|    sotto -> solo SELL.                                           |
//|  - BUY  quando una candela M15 CHIUDE con RSI sotto 30, 25, 20   |
//|    dopo averlo toccato dall'alto (la candela prima era sopra).   |
//|  - SELL quando una candela M15 CHIUDE con RSI sopra 70, 75, 80   |
//|    dopo averlo toccato dal basso.                                |
//|  - Ogni livello apre UNA sola operazione per ciclo; lotti 1x,    |
//|    2x, 3x. Le aggiunte si aprono solo se il trend e' confermato. |
//|  - Uscita: BUY chiusi al tocco di InpBuyExitRsi, SELL al tocco   |
//|    di InpSellExitRsi (in tempo reale).                           |
//|  - Opzioni: stop ATR comune a tutto il ciclo, lotto calcolato    |
//|    in % del capitale, stop in denaro per simbolo.                |
//+------------------------------------------------------------------+
#property copyright "Salvatore Cortile"
#property version   "7.00"
#property description "RSI 14 M15 + trend EMA 200 H1. Uscite BUY/SELL separate, stop ATR, lotto in % del capitale."

#include <Trade/Trade.mqh>

input group "RSI"
input int                InpRsiPeriod  = 14;            // Periodo RSI
input ENUM_APPLIED_PRICE InpRsiPrice   = PRICE_CLOSE;   // Prezzo RSI
input string             InpBuyLevels  = "30,25,20";      // Livelli BUY (tocco dall'alto, conferma a candela chiusa)
input string             InpSellLevels = "70,75,80";      // Livelli SELL (tocco dal basso, conferma a candela chiusa)
input double             InpBuyExitRsi  = 50.0;         // Uscita BUY: chiude tutto quando l'RSI sale a questo livello
input double             InpSellExitRsi = 50.0;         // Uscita SELL: chiude tutto quando l'RSI scende a questo livello
input ENUM_TIMEFRAMES    InpTimeframe  = PERIOD_M15;    // Timeframe di lavoro

input group "Filtro trend"
input bool               InpUseTrendFilter = true;       // Usa il filtro trend
input ENUM_TIMEFRAMES    InpTrendTimeframe = PERIOD_H1;  // Timeframe del trend
input int                InpTrendMaPeriod  = 200;        // Periodo EMA del trend

input group "Lotti e stop"
input double             InpBaseLot      = 0.01;  // Lotto della prima operazione (se rischio % = 0)
input double             InpLotStep      = 0.01;  // Lotto aggiunto a ogni nuova operazione (se rischio % = 0)
input double             InpRiskPercent  = 0.0;   // Rischio del ciclo in % del capitale (0 = lotti fissi; richiede stop ATR)
input double             InpMaxLossMoney = 50.0;  // Stop su questo simbolo: perdita del ciclo per chiudere tutto (0 = nessuno)
input bool               InpCloseOldAtBE = false; // Chiudi in pari le operazioni vecchie (false = tutte al tocco del 50)

input group "Stop ATR"
input bool               InpUseAtrStop      = false; // Stop loss basato sull'ATR, comune a tutto il ciclo
input int                InpAtrPeriod       = 14;    // Periodo ATR (sul timeframe di lavoro)
input double             InpAtrMultiplier   = 3.0;   // Distanza dello stop = ATR x moltiplicatore dal primo ingresso

input group "Ordini"
input int                InpMaxSpreadPoints      = 0;        // Spread massimo per aprire, in points (0 = nessun filtro)
input int                InpSlippagePoints       = 10;       // Slippage massimo in points
input ulong              InpMagic                = 26100201; // Magic number
input string             InpComment              = "RSI M1 Bot";

input group "Orari nuovi cicli (ora del server)"
input int                InpStartHour = 0;   // Ora inizio (0-23)
input int                InpEndHour   = 24;  // Ora fine (1-24, esclusa)

#define MAX_LEVELS 8

CTrade   trade;
int      rsiHandle  = INVALID_HANDLE;
int      maHandle   = INVALID_HANDLE;
int      atrHandle  = INVALID_HANDLE;
datetime currentBar = 0;
int      trendDir   = 0;       // +1 rialzista, -1 ribassista, 0 non disponibile
double   lastRsi    = 0.0;     // RSI in tempo reale (candela in corso)

double   buyLevels[], sellLevels[];

// Stato del ciclo (salvato nelle variabili globali del terminale)
double   cycleRealized = 0.0;   // risultato delle operazioni gia' chiuse nel ciclo
int      cycleOpened   = 0;     // operazioni aperte finora nel ciclo
int      usedMask      = 0;     // livelli gia' usati nel ciclo (bit = indice livello)
double   cycleStop     = 0.0;   // prezzo dello stop ATR del ciclo (0 = nessuno)
double   cycleUnitLot  = 0.0;   // lotto unitario del ciclo in modalita' rischio %

// Livelli confermati sulla candela appena chiusa, da aprire su questa candela
int      pendingMask = 0;

string   gvRealized, gvOpened, gvMask, gvStop, gvUnit;

struct Basket
  {
   int      count;
   int      dir;          // +1 BUY, -1 SELL, 0 vuoto
   double   floating;     // profitto + swap delle posizioni aperte
   ulong    newestTicket; // l'ultima operazione aperta
  };

//+------------------------------------------------------------------+
int OnInit()
  {
   if(!ParseLevels(InpBuyLevels, buyLevels) || !ParseLevels(InpSellLevels, sellLevels))
     {
      PrintFormat("Livelli non validi: servono da 1 a %d numeri separati da virgola.", MAX_LEVELS);
      return(INIT_PARAMETERS_INCORRECT);
     }
   for(int i = 0; i < ArraySize(buyLevels); i++)
      if(buyLevels[i] >= InpBuyExitRsi)
        {
         Print("I livelli BUY devono essere sotto il livello di uscita BUY.");
         return(INIT_PARAMETERS_INCORRECT);
        }
   for(int i = 0; i < ArraySize(sellLevels); i++)
      if(sellLevels[i] <= InpSellExitRsi)
        {
         Print("I livelli SELL devono essere sopra il livello di uscita SELL.");
         return(INIT_PARAMETERS_INCORRECT);
        }
   if(InpRiskPercent > 0 && !InpUseAtrStop)
     {
      Print("Il lotto in % del capitale richiede lo stop ATR (InpUseAtrStop = true).");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(InpRsiPeriod < 2 || InpBaseLot <= 0 || InpLotStep < 0 || InpRiskPercent < 0 ||
      (InpUseAtrStop && (InpAtrPeriod < 1 || InpAtrMultiplier <= 0)) ||
      InpStartHour < 0 || InpStartHour > 23 || InpEndHour < 1 || InpEndHour > 24)
     {
      Print("Parametri non validi: controlla periodo RSI, lotti e orari.");
      return(INIT_PARAMETERS_INCORRECT);
     }

   if((ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
     {
      Print("Questo bot richiede un conto HEDGING (piu' posizioni aperte sullo stesso simbolo).");
      return(INIT_FAILED);
     }

   rsiHandle = iRSI(_Symbol, InpTimeframe, InpRsiPeriod, InpRsiPrice);
   if(rsiHandle == INVALID_HANDLE)
     {
      Print("Impossibile creare l'indicatore RSI: ", GetLastError());
      return(INIT_FAILED);
     }

   if(InpUseTrendFilter)
     {
      maHandle = iMA(_Symbol, InpTrendTimeframe, InpTrendMaPeriod, 0, MODE_EMA, PRICE_CLOSE);
      if(maHandle == INVALID_HANDLE)
        {
         Print("Impossibile creare la media mobile del trend: ", GetLastError());
         return(INIT_FAILED);
        }
     }

   if(InpUseAtrStop)
     {
      atrHandle = iATR(_Symbol, InpTimeframe, InpAtrPeriod);
      if(atrHandle == INVALID_HANDLE)
        {
         Print("Impossibile creare l'ATR: ", GetLastError());
         return(INIT_FAILED);
        }
     }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   gvRealized = StringFormat("RSIBOT_%s_%I64u_real", _Symbol, InpMagic);
   gvOpened   = StringFormat("RSIBOT_%s_%I64u_open", _Symbol, InpMagic);
   gvMask     = StringFormat("RSIBOT_%s_%I64u_mask", _Symbol, InpMagic);
   gvStop     = StringFormat("RSIBOT_%s_%I64u_stop", _Symbol, InpMagic);
   gvUnit     = StringFormat("RSIBOT_%s_%I64u_unit", _Symbol, InpMagic);

   Basket b;
   GetBasket(b);
   if(b.count == 0)
      ResetCycle();
   else
     {
      cycleRealized = GlobalVariableCheck(gvRealized) ? GlobalVariableGet(gvRealized) : 0.0;
      cycleOpened   = GlobalVariableCheck(gvOpened) ? (int)GlobalVariableGet(gvOpened) : b.count;
      usedMask      = GlobalVariableCheck(gvMask) ? (int)GlobalVariableGet(gvMask) : 0;
      cycleStop     = GlobalVariableCheck(gvStop) ? GlobalVariableGet(gvStop) : 0.0;
      cycleUnitLot  = GlobalVariableCheck(gvUnit) ? GlobalVariableGet(gvUnit) : 0.0;
      PrintFormat("Ripreso ciclo esistente: %d posizioni aperte, %d operazioni nel ciclo, realizzato %.2f",
                  b.count, cycleOpened, cycleRealized);
     }

   EventSetTimer(1);
   PrintFormat("RSI_M1_Bot avviato su %s %s | RSI %d | BUY %s esce a %.0f | SELL %s esce a %.0f | stop ATR %s x%.1f | rischio %.2f%% | stop denaro %.2f",
               _Symbol, EnumToString(InpTimeframe), InpRsiPeriod, InpBuyLevels, InpBuyExitRsi,
               InpSellLevels, InpSellExitRsi, InpUseAtrStop ? "si" : "no", InpAtrMultiplier,
               InpRiskPercent, InpMaxLossMoney);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   if(rsiHandle != INVALID_HANDLE)
      IndicatorRelease(rsiHandle);
   if(maHandle != INVALID_HANDLE)
      IndicatorRelease(maHandle);
   if(atrHandle != INVALID_HANDLE)
      IndicatorRelease(atrHandle);
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   // Chiusura al tocco del 50 in tempo reale.
   double rsi;
   if(ReadRsi(0, rsi))
     {
      lastRsi = rsi;
      CheckMidTouch();
     }

   ManageBasket();

   datetime bar0 = iTime(_Symbol, InpTimeframe, 0);
   if(bar0 != 0 && bar0 != currentBar)
     {
      currentBar = bar0;
      OnNewBar();
     }

   TryOpenPending();
   UpdatePanel();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   ManageBasket();
   UpdatePanel();
  }

//+------------------------------------------------------------------+
//| RSI tocca 50: chiude subito tutto il ciclo.                      |
//+------------------------------------------------------------------+
void CheckMidTouch()
  {
   Basket b;
   GetBasket(b);
   if(b.count == 0)
      return;
   double exitLevel  = (b.dir == 1) ? InpBuyExitRsi : InpSellExitRsi;
   bool   touchedMid = (b.dir == 1) ? (lastRsi >= exitLevel) : (lastRsi <= exitLevel);
   if(touchedMid)
     {
      PrintFormat("RSI %.2f ha toccato %.0f: chiudo tutte le operazioni.", lastRsi, exitLevel);
      CloseAll();
     }
  }

//+------------------------------------------------------------------+
//| Primo tick di una nuova candela: cerca i livelli toccati e       |
//| confermati dalla candela appena chiusa.                          |
//+------------------------------------------------------------------+
void OnNewBar()
  {
   pendingMask = 0;
   UpdateTrend();

   double cur, prev;
   if(!ReadRsi(1, cur) || !ReadRsi(2, prev))
      return;

   Basket b;
   GetBasket(b);

   // Nuovo ciclo: solo negli orari consentiti. Ciclo aperto: aggiunge solo nella sua direzione.
   if(b.count == 0 && !InTradingHours())
      return;

   // BUY: candela chiusa sotto il livello, quella prima sopra (tocco dall'alto + conferma).
   if((b.count == 0 || b.dir == 1) && TrendAllows(1))
      for(int i = 0; i < ArraySize(buyLevels); i++)
         if(prev > buyLevels[i] && cur <= buyLevels[i] && (usedMask & (1 << i)) == 0)
            pendingMask |= (1 << i);

   // SELL: candela chiusa sopra il livello, quella prima sotto.
   if((b.count == 0 || b.dir == -1) && TrendAllows(-1))
      for(int i = 0; i < ArraySize(sellLevels); i++)
         if(prev < sellLevels[i] && cur >= sellLevels[i] && (usedMask & (1 << (i + MAX_LEVELS))) == 0)
            pendingMask |= (1 << (i + MAX_LEVELS));
  }

//+------------------------------------------------------------------+
//| Trend dalla chiusura dell'ultima candela H1 chiusa rispetto alla |
//| EMA 200 della stessa candela.                                    |
//+------------------------------------------------------------------+
void UpdateTrend()
  {
   trendDir = 0;
   if(!InpUseTrendFilter)
      return;
   double ma[];
   if(CopyBuffer(maHandle, 0, 1, 1, ma) != 1)
      return;
   double closeH1 = iClose(_Symbol, InpTrendTimeframe, 1);
   if(closeH1 <= 0)
      return;
   if(closeH1 > ma[0])
      trendDir = 1;
   else
      if(closeH1 < ma[0])
         trendDir = -1;
  }

//+------------------------------------------------------------------+
bool TrendAllows(int dir)
  {
   return(!InpUseTrendFilter || trendDir == dir);
  }

//+------------------------------------------------------------------+
//| Controlli continui: stop del simbolo e chiusure in pari.         |
//+------------------------------------------------------------------+
void ManageBasket()
  {
   Basket b;
   GetBasket(b);
   if(b.count == 0)
     {
      if(cycleOpened > 0)
         ResetCycle();
      return;
     }

   double total = cycleRealized + b.floating;
   if(InpMaxLossMoney > 0 && total <= -InpMaxLossMoney)
     {
      PrintFormat("STOP %s: totale ciclo %.2f <= -%.2f. Chiudo tutto su %s.",
                  _Symbol, total, InpMaxLossMoney, _Symbol);
      CloseAll();
      return;
     }

   if(!InpCloseOldAtBE || b.count < 2)
      return;

   // Le operazioni aperte prima dell'ultima si chiudono in pari al ritorno sul loro ingresso.
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || ticket == b.newestTicket || !IsMine())
         continue;

      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      bool   isBuy     = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      bool   atEntry   = isBuy ? (tick.bid >= openPrice) : (tick.ask <= openPrice);
      if(atEntry)
        {
         double lots = PositionGetDouble(POSITION_VOLUME);
         if(ClosePosition(ticket))
            PrintFormat("Chiusa in pari %s %.2f (ingresso %s)", isBuy ? "BUY" : "SELL",
                        lots, DoubleToString(openPrice, _Digits));
        }
     }
  }

//+------------------------------------------------------------------+
//| Apre subito un'operazione per ogni livello toccato.              |
//+------------------------------------------------------------------+
void TryOpenPending()
  {
   if(pendingMask == 0)
      return;

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
     {
      Print("Trading automatico disattivato: abilita 'Algo Trading'.");
      pendingMask = 0;
      return;
     }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;
   double spreadPts = (tick.ask - tick.bid) / _Point;
   if(InpMaxSpreadPoints > 0 && spreadPts > InpMaxSpreadPoints)
      return;   // riprova ai tick successivi della stessa candela

   // Livelli BUY dal piu' alto (30) al piu' basso, SELL dal piu' basso (70) al piu' alto.
   for(int pass = 0; pass < 2; pass++)
     {
      int dir = (pass == 0) ? 1 : -1;
      int n   = (dir == 1) ? ArraySize(buyLevels) : ArraySize(sellLevels);
      for(int i = 0; i < n; i++)
        {
         int bit = (dir == 1) ? i : i + MAX_LEVELS;
         if((pendingMask & (1 << bit)) == 0)
            continue;
         pendingMask &= ~(1 << bit);

         double level = (dir == 1) ? buyLevels[i] : sellLevels[i];

         // Primo ingresso del ciclo: fissa stop ATR e lotto unitario per tutto il ciclo.
         if(cycleOpened == 0 && !PrepareCycle(dir, tick))
           {
            pendingMask = 0;
            return;
           }

         double lots = NextLot();
         if(lots <= 0)
           {
            pendingMask = 0;
            return;
           }
         bool ok = (dir == 1) ? trade.Buy(lots, _Symbol, 0.0, cycleStop, 0.0, InpComment)
                              : trade.Sell(lots, _Symbol, 0.0, cycleStop, 0.0, InpComment);
         if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
           {
            cycleOpened++;
            usedMask |= (1 << bit);
            SaveCycle();
            PrintFormat("Aperto %s %.2f a %s | tocco RSI %.0f (RSI=%.2f) | operazione n. %d del ciclo",
                        dir == 1 ? "BUY" : "SELL", lots, DoubleToString(trade.ResultPrice(), _Digits),
                        level, lastRsi, cycleOpened);
           }
         else
            PrintFormat("Apertura %s %.2f al livello %.0f fallita: %u %s", dir == 1 ? "BUY" : "SELL",
                        lots, level, trade.ResultRetcode(), trade.ResultRetcodeDescription());
        }
     }
  }

//+------------------------------------------------------------------+
//| Inizio ciclo: calcola il prezzo dello stop ATR e, in modalita'   |
//| rischio %, il lotto unitario. false = non aprire il ciclo.       |
//+------------------------------------------------------------------+
bool PrepareCycle(int dir, const MqlTick &tick)
  {
   cycleStop    = 0.0;
   cycleUnitLot = 0.0;
   if(!InpUseAtrStop)
      return(true);

   double atr[];
   if(CopyBuffer(atrHandle, 0, 1, 1, atr) != 1 || atr[0] <= 0)
     {
      Print("ATR non disponibile: ciclo non aperto.");
      return(false);
     }
   double entry    = (dir == 1) ? tick.ask : tick.bid;
   double distance = atr[0] * InpAtrMultiplier;
   cycleStop = NormalizeDouble(dir == 1 ? entry - distance : entry + distance, _Digits);

   if(InpRiskPercent > 0)
     {
      // Perdita di 1 lotto se il prezzo va dall'ingresso allo stop.
      double lossPerLot = 0.0;
      ENUM_ORDER_TYPE type = (dir == 1) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      if(!OrderCalcProfit(type, _Symbol, 1.0, entry, cycleStop, lossPerLot) || lossPerLot >= 0)
        {
         Print("Impossibile calcolare il valore dello stop: ciclo non aperto.");
         return(false);
        }
      // Caso peggiore: tutti i livelli aperti (1x + 2x + 3x ...) con lo stop colpito.
      int    n         = (dir == 1) ? ArraySize(buyLevels) : ArraySize(sellLevels);
      double units     = n * (n + 1) / 2.0;
      double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0;
      double unit      = riskMoney / (units * MathAbs(lossPerLot));
      double minLot    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double stepLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      if(stepLot > 0)
         unit = MathFloor(unit / stepLot + 1e-9) * stepLot;
      if(unit < minLot)
        {
         PrintFormat("Capitale troppo piccolo per rischiare il %.2f%% con questo stop (servirebbe %.3f lotti, minimo %.2f): ciclo non aperto.",
                     InpRiskPercent, unit, minLot);
         cycleStop = 0.0;
         return(false);
        }
      cycleUnitLot = unit;
     }
   SaveCycle();
   return(true);
  }

//+------------------------------------------------------------------+
//| Lotto della prossima operazione del ciclo.                       |
//+------------------------------------------------------------------+
double NextLot()
  {
   if(InpRiskPercent > 0)
      return(cycleUnitLot > 0 ? NormalizeLots(cycleUnitLot * (cycleOpened + 1)) : 0.0);
   return(NormalizeLots(InpBaseLot + InpLotStep * cycleOpened));
  }

//+------------------------------------------------------------------+
bool IsMine()
  {
   return(PositionGetString(POSITION_SYMBOL) == _Symbol &&
          (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic);
  }

//+------------------------------------------------------------------+
void GetBasket(Basket &b)
  {
   b.count        = 0;
   b.dir          = 0;
   b.floating     = 0.0;
   b.newestTicket = 0;
   long newestTime = -1;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsMine())
         continue;
      b.count++;
      b.dir       = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      b.floating += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      long t = PositionGetInteger(POSITION_TIME_MSC);
      if(t > newestTime || (t == newestTime && ticket > b.newestTicket))
        {
         newestTime     = t;
         b.newestTicket = ticket;
        }
     }
  }

//+------------------------------------------------------------------+
//| Chiude una posizione e aggiunge il suo risultato al ciclo.       |
//+------------------------------------------------------------------+
bool ClosePosition(ulong ticket)
  {
   if(!PositionSelectByTicket(ticket))
      return(false);
   double estimate = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);

   if(!trade.PositionClose(ticket, InpSlippagePoints))
     {
      PrintFormat("Chiusura #%I64u fallita: %u %s", ticket,
                  trade.ResultRetcode(), trade.ResultRetcodeDescription());
      return(false);
     }

   double result = estimate;
   ulong  deal   = trade.ResultDeal();
   if(deal > 0 && HistoryDealSelect(deal))
      result = HistoryDealGetDouble(deal, DEAL_PROFIT) + HistoryDealGetDouble(deal, DEAL_SWAP) +
               HistoryDealGetDouble(deal, DEAL_COMMISSION);
   cycleRealized += result;
   SaveCycle();
   return(true);
  }

//+------------------------------------------------------------------+
bool CloseAll()
  {
   bool allClosed = true;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsMine())
         continue;
      if(!ClosePosition(ticket))
         allClosed = false;
     }
   if(allClosed)
     {
      PrintFormat("Ciclo chiuso con risultato %.2f", cycleRealized);
      ResetCycle();
     }
   return(allClosed);
  }

//+------------------------------------------------------------------+
void ResetCycle()
  {
   cycleRealized = 0.0;
   cycleOpened   = 0;
   usedMask      = 0;
   cycleStop     = 0.0;
   cycleUnitLot  = 0.0;
   SaveCycle();
  }

//+------------------------------------------------------------------+
void SaveCycle()
  {
   GlobalVariableSet(gvRealized, cycleRealized);
   GlobalVariableSet(gvOpened, cycleOpened);
   GlobalVariableSet(gvMask, usedMask);
   GlobalVariableSet(gvStop, cycleStop);
   GlobalVariableSet(gvUnit, cycleUnitLot);
  }

//+------------------------------------------------------------------+
//| RSI della candela indicata (0 = in corso, 1 = ultima chiusa...). |
//+------------------------------------------------------------------+
bool ReadRsi(int shift, double &value)
  {
   if(BarsCalculated(rsiHandle) < InpRsiPeriod + 3)
      return(false);
   double rsi[];
   if(CopyBuffer(rsiHandle, 0, shift, 1, rsi) != 1)
      return(false);
   value = rsi[0];
   return(true);
  }

//+------------------------------------------------------------------+
bool ParseLevels(string text, double &levels[])
  {
   string parts[];
   int n = StringSplit(text, ',', parts);
   if(n < 1 || n > MAX_LEVELS)
      return(false);
   ArrayResize(levels, n);
   for(int i = 0; i < n; i++)
     {
      StringTrimLeft(parts[i]);
      StringTrimRight(parts[i]);
      levels[i] = StringToDouble(parts[i]);
      if(levels[i] <= 0 || levels[i] >= 100)
         return(false);
     }
   return(true);
  }

//+------------------------------------------------------------------+
bool InTradingHours()
  {
   MqlDateTime t;
   TimeToStruct(TimeTradeServer(), t);
   if(InpStartHour < InpEndHour)
      return(t.hour >= InpStartHour && t.hour < InpEndHour);
   return(t.hour >= InpStartHour || t.hour < InpEndHour);
  }

//+------------------------------------------------------------------+
double NormalizeLots(double lots)
  {
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double stepLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(stepLot > 0)
      lots = MathRound(lots / stepLot) * stepLot;
   return(MathMax(minLot, MathMin(maxLot, lots)));
  }

//+------------------------------------------------------------------+
string UsedLevelsText(int dir)
  {
   string text = "";
   int    n    = (dir == 1) ? ArraySize(buyLevels) : ArraySize(sellLevels);
   for(int i = 0; i < n; i++)
     {
      int bit = (dir == 1) ? i : i + MAX_LEVELS;
      if((usedMask & (1 << bit)) != 0)
         text += (text == "" ? "" : ", ") + DoubleToString(dir == 1 ? buyLevels[i] : sellLevels[i], 0);
     }
   return(text == "" ? "-" : text);
  }

//+------------------------------------------------------------------+
void UpdatePanel()
  {
   Basket b;
   GetBasket(b);
   string trend = !InpUseTrendFilter ? "filtro spento" : (trendDir == 1 ? "RIALZO (solo BUY)" : (trendDir == -1 ? "RIBASSO (solo SELL)" : "n.d."));
   string state = StringFormat("in attesa del tocco di %s (BUY) o %s (SELL)", InpBuyLevels, InpSellLevels);
   if(b.count > 0)
      state = StringFormat("ciclo %s, livelli usati: %s, chiude a RSI %.0f%s",
                           b.dir == 1 ? "BUY" : "SELL", UsedLevelsText(b.dir),
                           b.dir == 1 ? InpBuyExitRsi : InpSellExitRsi,
                           cycleStop > 0 ? ", stop ATR " + DoubleToString(cycleStop, _Digits) : "");

   Comment(StringFormat("RSI Bot  |  %s %s\nRSI(%d) in tempo reale = %.2f\nTrend %s: %s\nStato: %s\n"
                        "Posizioni aperte: %d  |  operazioni nel ciclo: %d\n"
                        "Totale ciclo %s: %.2f  (stop -%.2f)",
                        _Symbol, EnumToString(InpTimeframe), InpRsiPeriod, lastRsi,
                        EnumToString(InpTrendTimeframe), trend, state,
                        b.count, cycleOpened, _Symbol, cycleRealized + b.floating, InpMaxLossMoney));
  }
//+------------------------------------------------------------------+
