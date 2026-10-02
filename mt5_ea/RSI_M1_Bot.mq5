//+------------------------------------------------------------------+
//|                                                  RSI_M1_Bot.mq5  |
//|  Expert Advisor per MT5 (test su EURUSD M1). Serve un conto      |
//|  HEDGING. Tutti i livelli RSI sono letti sulla candela CHIUSA.   |
//|                                                                  |
//|  - RSI(14) <= 30 -> apre un ciclo BUY  da 0.01.                  |
//|  - RSI(14) >= 70 -> apre un ciclo SELL da 0.01.                  |
//|  - Tra 30 e 70 non apre nuovi cicli.                             |
//|  - Ciclo in corso: a ogni candela chiusa contro la direzione     |
//|    apre un'altra operazione con lotto +0.01 (0.02, 0.03, ...),   |
//|    senza limite di numero.                                       |
//|  - Le operazioni vecchie si chiudono in pari quando il prezzo    |
//|    torna al loro ingresso; l'ultima resta aperta. Quando resta   |
//|    solo l'ultima, le mette lo SL a break even e non aggiunge     |
//|    piu' operazioni.                                              |
//|  - Chiude tutto quando l'RSI tocca 50 (BUY: >= 50, SELL: <= 50). |
//|  - Stop di emergenza: chiude tutto se la perdita totale del      |
//|    ciclo arriva a -InpMaxLossMoney.                              |
//|  - Chiusure e aperture avvengono sul primo tick della candela.   |
//+------------------------------------------------------------------+
#property copyright "Salvatore Cortile"
#property version   "3.00"
#property description "RSI 14: BUY a 30, SELL a 70, lotti +0.01 sulle candele contrarie, chiusure in pari, SL a BE sull'ultima, chiusura a RSI 50, stop -20."

#include <Trade/Trade.mqh>

input group "RSI"
input int                InpRsiPeriod = 14;           // Periodo RSI
input ENUM_APPLIED_PRICE InpRsiPrice  = PRICE_CLOSE;  // Prezzo RSI
input double             InpRsiUpper  = 70.0;         // Tocco = SELL
input double             InpRsiMid    = 50.0;         // Tocco = chiude tutto
input double             InpRsiLower  = 30.0;         // Tocco = BUY
input ENUM_TIMEFRAMES    InpTimeframe = PERIOD_M1;    // Timeframe di lavoro

input group "Lotti e ciclo"
input double             InpBaseLot        = 0.01;  // Lotto della prima operazione
input double             InpLotStep        = 0.01;  // Lotto aggiunto a ogni nuova operazione
input double             InpMaxLossMoney   = 20.0;  // Stop: perdita totale del ciclo per chiudere tutto (0 = nessuno)
input int                InpBeOffsetPoints = 0;     // SL a BE sull'ultima: points oltre l'ingresso (0 = ingresso esatto)

input group "Ordini"
input int                InpMaxSpreadPoints      = 0;        // Spread massimo per aprire, in points (0 = nessun filtro)
input int                InpSlippagePoints       = 10;       // Slippage massimo in points
input int                InpMaxEntryDelaySeconds = 10;       // Apri solo nei primi N secondi della candela
input ulong              InpMagic                = 26100201; // Magic number
input string             InpComment              = "RSI M1 Bot";

input group "Orari nuovi cicli (ora del server)"
input int                InpStartHour = 0;   // Ora inizio (0-23)
input int                InpEndHour   = 24;  // Ora fine (1-24, esclusa)

CTrade   trade;
int      rsiHandle  = INVALID_HANDLE;
datetime currentBar = 0;
double   lastRsi    = 0.0;

// Stato del ciclo (salvato nelle variabili globali del terminale)
double   cycleRealized = 0.0;   // risultato delle operazioni gia' chiuse nel ciclo
int      cycleOpened   = 0;     // operazioni aperte finora nel ciclo

// Apertura da eseguire sulla candela corrente
int      pendingDir = 0;
double   pendingLot = 0.0;

string   gvRealized, gvOpened;

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
   if(InpRsiPeriod < 2 || InpBaseLot <= 0 || InpLotStep < 0 ||
      !(InpRsiLower < InpRsiMid && InpRsiMid < InpRsiUpper) ||
      InpStartHour < 0 || InpStartHour > 23 || InpEndHour < 1 || InpEndHour > 24)
     {
      Print("Parametri non validi: controlla RSI (30 < 50 < 70), lotti e orari.");
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

   Basket b;
   GetBasket(b);
   if(b.count == 0)
      ResetCycle();
   else
     {
      cycleRealized = GlobalVariableCheck(gvRealized) ? GlobalVariableGet(gvRealized) : 0.0;
      cycleOpened   = GlobalVariableCheck(gvOpened) ? (int)GlobalVariableGet(gvOpened) : b.count;
      PrintFormat("Ripreso ciclo esistente: %d posizioni aperte, %d operazioni nel ciclo, realizzato %.2f",
                  b.count, cycleOpened, cycleRealized);
     }

   EventSetTimer(1);
   PrintFormat("RSI_M1_Bot avviato su %s %s | RSI %d (%.0f/%.0f/%.0f) | lotto %.2f +%.2f | stop %.2f",
               _Symbol, EnumToString(InpTimeframe), InpRsiPeriod, InpRsiLower, InpRsiMid, InpRsiUpper,
               InpBaseLot, InpLotStep, InpMaxLossMoney);
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
//| della candela appena chiusa.                                     |
//+------------------------------------------------------------------+
void OnNewBar()
  {
   pendingDir = 0;
   pendingLot = 0.0;

   if(!ReadRsi(lastRsi))
      return;

   Basket b;
   GetBasket(b);

   if(b.count > 0)
     {
      // L'RSI ha toccato 50: chiude tutto il ciclo.
      bool touchedMid = (b.dir == 1) ? (lastRsi >= InpRsiMid) : (lastRsi <= InpRsiMid);
      if(touchedMid)
        {
         PrintFormat("RSI %.2f ha toccato %.0f: chiudo tutte le operazioni.", lastRsi, InpRsiMid);
         if(!CloseAll())
            return;
         GetBasket(b);   // ciclo chiuso: sotto si valuta un eventuale nuovo ciclo
        }
      else
        {
         // Resta solo l'ultima, protetta a BE: nessuna nuova operazione.
         if(IsProtected(b))
            return;
         if(LastCandleAgainst(b.dir))
           {
            pendingDir = b.dir;
            pendingLot = InpBaseLot + InpLotStep * cycleOpened;
           }
         return;
        }
     }

   // Nessun ciclo aperto: ne apre uno nuovo solo al tocco di 30 o 70.
   if(!InTradingHours())
      return;
   if(lastRsi <= InpRsiLower)
      pendingDir = 1;
   else
      if(lastRsi >= InpRsiUpper)
         pendingDir = -1;
   if(pendingDir != 0)
      pendingLot = InpBaseLot;
  }

//+------------------------------------------------------------------+
//| Controlli continui: stop, chiusure in pari, SL a BE sull'ultima. |
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
      PrintFormat("STOP di emergenza: totale ciclo %.2f <= -%.2f. Chiudo tutto.", total, InpMaxLossMoney);
      CloseAll();
      return;
     }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   // Chiude in pari le operazioni vecchie quando il prezzo torna al loro ingresso.
   if(b.count >= 2)
     {
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
      GetBasket(b);
     }

   // Rimasta solo l'ultima dopo le chiusure in pari: SL a break even.
   if(IsProtected(b))
      SetBreakEven(b.newestTicket, tick);
  }

//+------------------------------------------------------------------+
//| true quando le operazioni vecchie sono state chiuse in pari e    |
//| resta solo l'ultima.                                             |
//+------------------------------------------------------------------+
bool IsProtected(const Basket &b)
  {
   return(b.count == 1 && cycleOpened > 1);
  }

//+------------------------------------------------------------------+
void SetBreakEven(ulong ticket, const MqlTick &tick)
  {
   if(!PositionSelectByTicket(ticket))
      return;

   bool   isBuy     = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
   double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
   double curSl     = PositionGetDouble(POSITION_SL);
   double curTp     = PositionGetDouble(POSITION_TP);
   double beSl      = NormalizeDouble(isBuy ? openPrice + InpBeOffsetPoints * _Point
                                            : openPrice - InpBeOffsetPoints * _Point, _Digits);

   // Gia' protetta?
   if(curSl > 0 && (isBuy ? curSl >= beSl : curSl <= beSl))
      return;

   // Il prezzo deve essere oltre lo SL di almeno lo stop level del broker.
   double minDist = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(isBuy ? (tick.bid - beSl <= minDist) : (beSl - tick.ask <= minDist))
      return;

   if(trade.PositionModify(ticket, beSl, curTp))
      PrintFormat("SL a break even sull'ultima operazione #%I64u: %s", ticket, DoubleToString(beSl, _Digits));
   else
      PrintFormat("SL a BE fallito su #%I64u: %u %s", ticket,
                  trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
void TryPendingOpen()
  {
   if(pendingDir == 0)
      return;

   if(TimeTradeServer() - currentBar > InpMaxEntryDelaySeconds)
     {
      Print("Apertura saltata: troppo tardi rispetto all'inizio della candela.");
      pendingDir = 0;
      return;
     }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
     {
      Print("Trading automatico disattivato: abilita 'Algo Trading'.");
      pendingDir = 0;
      return;
     }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;
   double spreadPts = (tick.ask - tick.bid) / _Point;
   if(InpMaxSpreadPoints > 0 && spreadPts > InpMaxSpreadPoints)
      return;   // riprova ai tick successivi finche' resta tempo

   double lots = NormalizeLots(pendingLot);
   bool   ok   = (pendingDir == 1) ? trade.Buy(lots, _Symbol, 0.0, 0.0, 0.0, InpComment)
                                   : trade.Sell(lots, _Symbol, 0.0, 0.0, 0.0, InpComment);

   if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
     {
      cycleOpened++;
      SaveCycle();
      PrintFormat("Aperto %s %.2f a %s | operazione n. %d del ciclo | RSI=%.2f | spread=%.0f pts",
                  pendingDir == 1 ? "BUY" : "SELL", lots, DoubleToString(trade.ResultPrice(), _Digits),
                  cycleOpened, lastRsi, spreadPts);
     }
   else
      PrintFormat("Apertura %s %.2f fallita: %u %s", pendingDir == 1 ? "BUY" : "SELL", lots,
                  trade.ResultRetcode(), trade.ResultRetcodeDescription());

   pendingDir = 0;
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
   SaveCycle();
  }

//+------------------------------------------------------------------+
void SaveCycle()
  {
   GlobalVariableSet(gvRealized, cycleRealized);
   GlobalVariableSet(gvOpened, cycleOpened);
  }

//+------------------------------------------------------------------+
//| RSI della candela appena chiusa.                                 |
//+------------------------------------------------------------------+
bool ReadRsi(double &rsiValue)
  {
   if(BarsCalculated(rsiHandle) < InpRsiPeriod + 2)
      return(false);
   double rsi[];
   if(CopyBuffer(rsiHandle, 0, 1, 1, rsi) != 1)
      return(false);
   rsiValue = rsi[0];
   return(true);
  }

//+------------------------------------------------------------------+
//| true se la candela appena chiusa e' andata contro la direzione.  |
//+------------------------------------------------------------------+
bool LastCandleAgainst(int dir)
  {
   double o = iOpen(_Symbol, InpTimeframe, 1);
   double c = iClose(_Symbol, InpTimeframe, 1);
   if(o == 0 || c == 0)
      return(false);
   return(dir == 1 ? (c < o) : (c > o));
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
void UpdatePanel()
  {
   Basket b;
   GetBasket(b);
   string state = "in attesa del tocco di 30 (BUY) o 70 (SELL)";
   if(b.count > 0)
      state = StringFormat("ciclo %s, chiude a RSI %.0f%s", b.dir == 1 ? "BUY" : "SELL", InpRsiMid,
                           IsProtected(b) ? " (ultima protetta a BE)" : "");

   Comment(StringFormat("RSI M1 Bot  |  %s %s\nRSI(%d) candela chiusa = %.2f\nStato: %s\n"
                        "Posizioni aperte: %d  |  operazioni nel ciclo: %d\n"
                        "Totale ciclo: %.2f  (stop -%.2f)",
                        _Symbol, EnumToString(InpTimeframe), InpRsiPeriod, lastRsi, state,
                        b.count, cycleOpened, cycleRealized + b.floating, InpMaxLossMoney));
  }
//+------------------------------------------------------------------+
