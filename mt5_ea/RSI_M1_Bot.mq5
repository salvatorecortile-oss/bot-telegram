//+------------------------------------------------------------------+
//|                                                  RSI_M1_Bot.mq5  |
//|  Expert Advisor per MT5 (test su EURUSD M1). Serve un conto      |
//|  HEDGING. L'RSI e' letto sulle candele CHIUSE; aperture e        |
//|  chiusure avvengono sul primo tick della candela successiva.     |
//|                                                                  |
//|  - BUY  al tocco dall'alto di 30, 20, 10, 5.                     |
//|  - SELL al tocco dal basso di 70, 80, 90, 95.                    |
//|  - Ogni livello apre UNA sola operazione per ciclo; se una       |
//|    candela attraversa piu' livelli apre un'operazione per        |
//|    livello. I livelli tornano validi solo a ciclo chiuso.        |
//|  - Lotti: 0.01, poi +0.01 a ogni nuova operazione del ciclo.     |
//|  - L'ultima operazione aperta resta aperta fino al tocco del 50; |
//|    quelle aperte prima si chiudono in pari quando il prezzo      |
//|    torna al loro ingresso.                                       |
//|  - RSI tocca 50 -> chiude tutto.                                 |
//|  - Stop per simbolo: se la perdita del ciclo su QUESTO simbolo   |
//|    arriva a -InpMaxLossMoney chiude tutto su questo simbolo.     |
//+------------------------------------------------------------------+
#property copyright "Salvatore Cortile"
#property version   "4.00"
#property description "RSI 14: BUY ai tocchi di 30/20/10/5, SELL ai tocchi di 70/80/90/95, lotti +0.01, chiusure in pari, chiusura a RSI 50, stop per simbolo."

#include <Trade/Trade.mqh>

input group "RSI"
input int                InpRsiPeriod  = 14;            // Periodo RSI
input ENUM_APPLIED_PRICE InpRsiPrice   = PRICE_CLOSE;   // Prezzo RSI
input string             InpBuyLevels  = "30,20,10,5";  // Livelli BUY (tocco dall'alto)
input string             InpSellLevels = "70,80,90,95"; // Livelli SELL (tocco dal basso)
input double             InpRsiMid     = 50.0;          // Tocco = chiude tutto
input ENUM_TIMEFRAMES    InpTimeframe  = PERIOD_M1;     // Timeframe di lavoro

input group "Lotti e stop"
input double             InpBaseLot      = 0.01;  // Lotto della prima operazione
input double             InpLotStep      = 0.01;  // Lotto aggiunto a ogni nuova operazione
input double             InpMaxLossMoney = 20.0;  // Stop su questo simbolo: perdita del ciclo per chiudere tutto (0 = nessuno)

input group "Ordini"
input int                InpMaxSpreadPoints      = 0;        // Spread massimo per aprire, in points (0 = nessun filtro)
input int                InpSlippagePoints       = 10;       // Slippage massimo in points
input int                InpMaxEntryDelaySeconds = 10;       // Apri solo nei primi N secondi della candela
input ulong              InpMagic                = 26100201; // Magic number
input string             InpComment              = "RSI M1 Bot";

input group "Orari nuovi cicli (ora del server)"
input int                InpStartHour = 0;   // Ora inizio (0-23)
input int                InpEndHour   = 24;  // Ora fine (1-24, esclusa)

#define MAX_LEVELS 8

CTrade   trade;
int      rsiHandle  = INVALID_HANDLE;
datetime currentBar = 0;
double   lastRsi    = 0.0;

double   buyLevels[], sellLevels[];

// Stato del ciclo (salvato nelle variabili globali del terminale)
double   cycleRealized = 0.0;   // risultato delle operazioni gia' chiuse nel ciclo
int      cycleOpened   = 0;     // operazioni aperte finora nel ciclo
int      usedMask      = 0;     // livelli gia' usati nel ciclo (bit = indice livello)

// Aperture da eseguire sulla candela corrente (una per livello toccato)
int      pendingDir = 0;
int      pendingLevels[];

string   gvRealized, gvOpened, gvMask;

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
      if(buyLevels[i] >= InpRsiMid)
        {
         Print("I livelli BUY devono essere sotto il livello centrale.");
         return(INIT_PARAMETERS_INCORRECT);
        }
   for(int i = 0; i < ArraySize(sellLevels); i++)
      if(sellLevels[i] <= InpRsiMid)
        {
         Print("I livelli SELL devono essere sopra il livello centrale.");
         return(INIT_PARAMETERS_INCORRECT);
        }
   if(InpRsiPeriod < 2 || InpBaseLot <= 0 || InpLotStep < 0 ||
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

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   gvRealized = StringFormat("RSIBOT_%s_%I64u_real", _Symbol, InpMagic);
   gvOpened   = StringFormat("RSIBOT_%s_%I64u_open", _Symbol, InpMagic);
   gvMask     = StringFormat("RSIBOT_%s_%I64u_mask", _Symbol, InpMagic);

   Basket b;
   GetBasket(b);
   if(b.count == 0)
      ResetCycle();
   else
     {
      cycleRealized = GlobalVariableCheck(gvRealized) ? GlobalVariableGet(gvRealized) : 0.0;
      cycleOpened   = GlobalVariableCheck(gvOpened) ? (int)GlobalVariableGet(gvOpened) : b.count;
      usedMask      = GlobalVariableCheck(gvMask) ? (int)GlobalVariableGet(gvMask) : 0;
      PrintFormat("Ripreso ciclo esistente: %d posizioni aperte, %d operazioni nel ciclo, realizzato %.2f",
                  b.count, cycleOpened, cycleRealized);
     }

   EventSetTimer(1);
   PrintFormat("RSI_M1_Bot avviato su %s %s | RSI %d | BUY %s | SELL %s | chiusura %.0f | lotto %.2f +%.2f | stop %.2f",
               _Symbol, EnumToString(InpTimeframe), InpRsiPeriod, InpBuyLevels, InpSellLevels,
               InpRsiMid, InpBaseLot, InpLotStep, InpMaxLossMoney);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   if(rsiHandle != INVALID_HANDLE)
      IndicatorRelease(rsiHandle);
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   ManageBasket();

   datetime bar0 = iTime(_Symbol, InpTimeframe, 0);
   if(bar0 != 0 && bar0 != currentBar)
     {
      currentBar = bar0;
      OnNewBar();
     }

   TryPendingOpen();
   UpdatePanel();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   ManageBasket();
   UpdatePanel();
  }

//+------------------------------------------------------------------+
//| Decisioni prese al primo tick di ogni nuova candela, con l'RSI   |
//| delle due ultime candele chiuse (prima e dopo il tocco).         |
//+------------------------------------------------------------------+
void OnNewBar()
  {
   pendingDir = 0;
   ArrayResize(pendingLevels, 0);

   double prevRsi;
   if(!ReadRsi(lastRsi, prevRsi))
      return;

   Basket b;
   GetBasket(b);

   // L'RSI ha toccato 50: chiude tutto il ciclo.
   if(b.count > 0)
     {
      bool touchedMid = (b.dir == 1) ? (lastRsi >= InpRsiMid) : (lastRsi <= InpRsiMid);
      if(touchedMid)
        {
         PrintFormat("RSI %.2f ha toccato %.0f: chiudo tutte le operazioni.", lastRsi, InpRsiMid);
         if(!CloseAll())
            return;
         GetBasket(b);
        }
     }

   // Un nuovo ciclo parte solo negli orari consentiti; un ciclo aperto continua sempre.
   if(b.count == 0 && !InTradingHours())
      return;

   // BUY: tocco dall'alto dei livelli 30/20/10/5 non ancora usati.
   if(b.count == 0 || b.dir == 1)
      for(int i = 0; i < ArraySize(buyLevels); i++)
         if(prevRsi > buyLevels[i] && lastRsi <= buyLevels[i] && (usedMask & (1 << i)) == 0)
            AddPending(1, i);

   // SELL: tocco dal basso dei livelli 70/80/90/95 non ancora usati.
   if(pendingDir == 0 && (b.count == 0 || b.dir == -1))
      for(int i = 0; i < ArraySize(sellLevels); i++)
         if(prevRsi < sellLevels[i] && lastRsi >= sellLevels[i] && (usedMask & (1 << (i + MAX_LEVELS))) == 0)
            AddPending(-1, i);
  }

//+------------------------------------------------------------------+
void AddPending(int dir, int levelIndex)
  {
   pendingDir = dir;
   int n = ArraySize(pendingLevels);
   ArrayResize(pendingLevels, n + 1);
   pendingLevels[n] = levelIndex;
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
      if(cycleOpened > 0 && pendingDir == 0)
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

   if(b.count < 2)
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
//| Apre un'operazione per ogni livello toccato in questa candela.   |
//+------------------------------------------------------------------+
void TryPendingOpen()
  {
   if(pendingDir == 0)
      return;

   if(TimeTradeServer() - currentBar > InpMaxEntryDelaySeconds)
     {
      Print("Apertura saltata: troppo tardi rispetto all'inizio della candela.");
      pendingDir = 0;
      ArrayResize(pendingLevels, 0);
      return;
     }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
     {
      Print("Trading automatico disattivato: abilita 'Algo Trading'.");
      pendingDir = 0;
      ArrayResize(pendingLevels, 0);
      return;
     }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;
   double spreadPts = (tick.ask - tick.bid) / _Point;
   if(InpMaxSpreadPoints > 0 && spreadPts > InpMaxSpreadPoints)
      return;   // riprova ai tick successivi finche' resta tempo

   for(int k = 0; k < ArraySize(pendingLevels); k++)
     {
      int    idx   = pendingLevels[k];
      double level = (pendingDir == 1) ? buyLevels[idx] : sellLevels[idx];
      int    bit   = (pendingDir == 1) ? idx : idx + MAX_LEVELS;
      double lots  = NormalizeLots(InpBaseLot + InpLotStep * cycleOpened);

      bool ok = (pendingDir == 1) ? trade.Buy(lots, _Symbol, 0.0, 0.0, 0.0, InpComment)
                                  : trade.Sell(lots, _Symbol, 0.0, 0.0, 0.0, InpComment);
      if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
        {
         cycleOpened++;
         usedMask |= (1 << bit);
         SaveCycle();
         PrintFormat("Aperto %s %.2f a %s | tocco RSI %.0f (RSI=%.2f) | operazione n. %d del ciclo",
                     pendingDir == 1 ? "BUY" : "SELL", lots, DoubleToString(trade.ResultPrice(), _Digits),
                     level, lastRsi, cycleOpened);
        }
      else
         PrintFormat("Apertura %s %.2f al livello %.0f fallita: %u %s", pendingDir == 1 ? "BUY" : "SELL",
                     lots, level, trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }

   pendingDir = 0;
   ArrayResize(pendingLevels, 0);
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
   SaveCycle();
  }

//+------------------------------------------------------------------+
void SaveCycle()
  {
   GlobalVariableSet(gvRealized, cycleRealized);
   GlobalVariableSet(gvOpened, cycleOpened);
   GlobalVariableSet(gvMask, usedMask);
  }

//+------------------------------------------------------------------+
//| RSI dell'ultima candela chiusa (cur) e di quella prima (prev).   |
//+------------------------------------------------------------------+
bool ReadRsi(double &cur, double &prev)
  {
   if(BarsCalculated(rsiHandle) < InpRsiPeriod + 3)
      return(false);
   double rsi[];
   ArraySetAsSeries(rsi, true);
   if(CopyBuffer(rsiHandle, 0, 1, 2, rsi) != 2)
      return(false);
   cur  = rsi[0];
   prev = rsi[1];
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
   string state = StringFormat("in attesa del tocco di %s (BUY) o %s (SELL)", InpBuyLevels, InpSellLevels);
   if(b.count > 0)
      state = StringFormat("ciclo %s, livelli usati: %s, chiude a RSI %.0f",
                           b.dir == 1 ? "BUY" : "SELL", UsedLevelsText(b.dir), InpRsiMid);

   Comment(StringFormat("RSI M1 Bot  |  %s %s\nRSI(%d) candela chiusa = %.2f\nStato: %s\n"
                        "Posizioni aperte: %d  |  operazioni nel ciclo: %d\n"
                        "Totale ciclo %s: %.2f  (stop -%.2f)",
                        _Symbol, EnumToString(InpTimeframe), InpRsiPeriod, lastRsi, state,
                        b.count, cycleOpened, _Symbol, cycleRealized + b.floating, InpMaxLossMoney));
  }
//+------------------------------------------------------------------+
