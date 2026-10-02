//+------------------------------------------------------------------+
//|                                                  RSI_M1_Bot.mq5  |
//|  Expert Advisor per MT5: si attacca al grafico di QUALSIASI      |
//|  simbolo (EURUSD, GBPUSD, XAUUSD, ...) e opera sul timeframe     |
//|  scelto (default M1). Serve un conto HEDGING.                    |
//|                                                                  |
//|  Regole (RSI calcolato sull'ultima candela CHIUSA):              |
//|  - RSI tra 50 e 70 -> SELL.  RSI tra 30 e 50 -> BUY.             |
//|  - RSI sopra 70 o sotto 30 -> nessuna nuova operazione, ma le    |
//|    operazioni aperte continuano a essere gestite.                |
//|  - Ciclo: apre 0.01. Se alla chiusura della candela e' in        |
//|    profitto chiude e riparte da 0.01. Se e' in perdita apre      |
//|    un'altra operazione con lotto +0.01 (0.02, 0.03, ...) a ogni  |
//|    candela contraria, fino a un massimo di operazioni.           |
//|  - Con piu' operazioni aperte: quelle vecchie si chiudono in     |
//|    pari quando il prezzo torna al loro ingresso; l'ultima resta  |
//|    aperta. Quando la somma del ciclo (chiuse + aperte) arriva    |
//|    al profitto obiettivo chiude tutto e riparte da 0.01.         |
//|  - Stop di emergenza: se la somma arriva alla perdita massima    |
//|    chiude tutto e riparte.                                       |
//|  - Se l'RSI passa nella zona opposta chiude tutto e apre 0.01    |
//|    nella nuova direzione.                                        |
//+------------------------------------------------------------------+
#property copyright "Salvatore Cortile"
#property version   "2.00"
#property description "RSI 28: 50-70 SELL, 30-50 BUY. Recupero con lotti crescenti (+0.01), chiusure in pari e chiusura totale a profitto."

#include <Trade/Trade.mqh>

input group "RSI"
input int                InpRsiPeriod   = 28;           // Periodo RSI
input ENUM_APPLIED_PRICE InpRsiPrice    = PRICE_CLOSE;  // Prezzo RSI
input double             InpRsiUpper    = 70.0;         // Livello alto (sopra = niente nuove operazioni)
input double             InpRsiMid      = 50.0;         // Livello centrale (sopra = SELL, sotto = BUY)
input double             InpRsiLower    = 30.0;         // Livello basso (sotto = niente nuove operazioni)
input ENUM_TIMEFRAMES    InpTimeframe   = PERIOD_M1;    // Timeframe di lavoro

input group "Lotti e ciclo"
input double             InpBaseLot        = 0.01;  // Lotto della prima operazione
input double             InpLotStep        = 0.01;  // Lotto aggiunto a ogni nuova operazione
input int                InpMaxTrades      = 5;     // Operazioni massime per ciclo
input double             InpTargetMoney    = 1.0;   // Profitto totale del ciclo per chiudere tutto (valuta del conto)
input double             InpMaxLossMoney   = 20.0;  // Stop: perdita totale del ciclo per chiudere tutto (0 = nessuno)

input group "Ordini"
input int                InpMaxSpreadPoints      = 0;        // Spread massimo per aprire, in points (0 = nessun filtro)
input int                InpSlippagePoints       = 10;       // Slippage massimo in points
input int                InpMaxEntryDelaySeconds = 10;       // Apri solo nei primi N secondi della candela
input ulong              InpMagic                = 26100201; // Magic number
input string             InpComment              = "RSI M1 Bot";

input group "Orari (ora del server)"
input int                InpStartHour = 0;   // Ora inizio nuove aperture (0-23)
input int                InpEndHour   = 24;  // Ora fine nuove aperture (1-24, esclusa)

CTrade   trade;
int      rsiHandle    = INVALID_HANDLE;
datetime currentBar   = 0;
double   lastRsi      = 0.0;
int      zoneDir      = 0;      // +1 BUY, -1 SELL, 0 nessuna nuova apertura

// Stato del ciclo (salvato nelle variabili globali del terminale)
double   cycleRealized = 0.0;   // profitto gia' realizzato dalle operazioni chiuse del ciclo
int      cycleOpened   = 0;     // operazioni aperte finora nel ciclo

// Apertura da eseguire sulla candela corrente
int      pendingDir   = 0;
double   pendingLot   = 0.0;

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
   if(InpRsiPeriod < 2 || InpMaxTrades < 1 || InpBaseLot <= 0 || InpLotStep < 0 ||
      !(InpRsiLower < InpRsiMid && InpRsiMid < InpRsiUpper) ||
      InpStartHour < 0 || InpStartHour > 23 || InpEndHour < 1 || InpEndHour > 24)
     {
      Print("Parametri non validi: controlla RSI (30 < 50 < 70), lotti, operazioni massime e orari.");
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
   PrintFormat("RSI_M1_Bot avviato su %s %s | RSI %d | lotto %.2f +%.2f | max %d | obiettivo %.2f | stop %.2f",
               _Symbol, EnumToString(InpTimeframe), InpRsiPeriod, InpBaseLot, InpLotStep,
               InpMaxTrades, InpTargetMoney, InpMaxLossMoney);
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
//| Decisioni prese al primo tick di ogni nuova candela.             |
//+------------------------------------------------------------------+
void OnNewBar()
  {
   pendingDir = 0;
   pendingLot = 0.0;

   zoneDir = GetZone(lastRsi);
   if(!InTradingHours())
      zoneDir = 0;

   Basket b;
   GetBasket(b);

   // RSI passato nella zona opposta: chiude tutto e riparte nella nuova direzione.
   if(b.count > 0 && zoneDir != 0 && zoneDir != b.dir)
     {
      Print("RSI passato nella zona opposta: chiudo tutte le operazioni.");
      if(!CloseAll())
         return;
      GetBasket(b);
     }

   // Prima operazione del ciclo in profitto alla chiusura della candela: incassa e riparte.
   if(b.count == 1 && cycleOpened == 1 && b.floating > 0)
     {
      Print("Prima operazione in profitto a fine candela: chiudo e riparto da capo.");
      if(!CloseAll())
         return;
      GetBasket(b);
     }

   if(zoneDir == 0)
      return;   // fuori zona o fuori orario: solo gestione delle aperte

   if(b.count == 0)
     {
      pendingDir = zoneDir;
      pendingLot = InpBaseLot;
      return;
     }

   // Ciclo in corso: aggiunge solo se la candela appena chiusa e' andata contro.
   if(cycleOpened >= InpMaxTrades)
      return;
   bool against = (cycleOpened == 1) ? (b.floating <= 0) : LastCandleAgainst(b.dir);
   if(against)
     {
      pendingDir = b.dir;
      pendingLot = InpBaseLot + InpLotStep * cycleOpened;
     }
  }

//+------------------------------------------------------------------+
//| Controlli continui: obiettivo, stop, chiusure in pari.           |
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

   if(total >= InpTargetMoney)
     {
      PrintFormat("Obiettivo raggiunto: totale ciclo %.2f >= %.2f. Chiudo tutto.", total, InpTargetMoney);
      CloseAll();
      return;
     }
   if(InpMaxLossMoney > 0 && total <= -InpMaxLossMoney)
     {
      PrintFormat("STOP di emergenza: totale ciclo %.2f <= -%.2f. Chiudo tutto.", total, InpMaxLossMoney);
      CloseAll();
      return;
     }

   if(b.count < 2)
      return;

   // Chiude in pari le operazioni vecchie quando il prezzo torna al loro ingresso.
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
      PrintFormat("Aperto %s %.2f a %s | operazione %d/%d | RSI=%.2f | spread=%.0f pts",
                  pendingDir == 1 ? "BUY" : "SELL", lots, DoubleToString(trade.ResultPrice(), _Digits),
                  cycleOpened, InpMaxTrades, lastRsi, spreadPts);
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
//| +1 BUY (RSI tra 30 e 50), -1 SELL (RSI tra 50 e 70), 0 niente.   |
//+------------------------------------------------------------------+
int GetZone(double &rsiValue)
  {
   rsiValue = 0.0;
   if(BarsCalculated(rsiHandle) < InpRsiPeriod + 2)
      return(0);

   double rsi[];
   if(CopyBuffer(rsiHandle, 0, 1, 1, rsi) != 1)
      return(0);
   rsiValue = rsi[0];

   if(rsiValue > InpRsiMid && rsiValue <= InpRsiUpper)
      return(-1);   // tra 50 e 70 -> SELL
   if(rsiValue < InpRsiMid && rsiValue >= InpRsiLower)
      return(1);    // tra 30 e 50 -> BUY
   return(0);
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
   string zone = "NESSUNA (fuori 30-70)";
   if(lastRsi > InpRsiMid && lastRsi <= InpRsiUpper)
      zone = "SELL";
   else
      if(lastRsi < InpRsiMid && lastRsi >= InpRsiLower)
         zone = "BUY";

   Basket b;
   GetBasket(b);
   Comment(StringFormat("RSI M1 Bot  |  %s %s\nRSI(%d) = %.2f  ->  zona %s\n"
                        "Posizioni aperte: %d  |  operazioni nel ciclo: %d/%d\n"
                        "Totale ciclo: %.2f  (obiettivo %.2f, stop -%.2f)",
                        _Symbol, EnumToString(InpTimeframe), InpRsiPeriod, lastRsi, zone,
                        b.count, cycleOpened, InpMaxTrades,
                        cycleRealized + b.floating, InpTargetMoney, InpMaxLossMoney));
  }
//+------------------------------------------------------------------+
