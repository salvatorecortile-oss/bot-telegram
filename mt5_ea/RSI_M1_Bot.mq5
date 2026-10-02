//+------------------------------------------------------------------+
//|                                                  RSI_M1_Bot.mq5  |
//|  Expert Advisor per MT5: si attacca al grafico di QUALSIASI      |
//|  simbolo (EURUSD, GBPUSD, XAUUSD, ...) e opera sul timeframe      |
//|  scelto (default M1).                                            |
//|                                                                  |
//|  Regole:                                                         |
//|  - RSI (default 28 periodi) calcolato sulla candela CHIUSA.      |
//|  - RSI tra 50 e 70  -> zona BUY  (si aprono solo BUY).           |
//|  - RSI tra 30 e 50  -> zona SELL (si aprono solo SELL).          |
//|  - RSI sopra 70 o sotto 30 -> nessuna operazione.                |
//|  - A OGNI candela (ogni minuto su M1) apre un trade nella         |
//|    direzione della zona, senza aspettare altre condizioni.        |
//|  - L'ordine si apre all'apertura della candela e si chiude        |
//|    prima della fine della stessa candela.                        |
//+------------------------------------------------------------------+
#property copyright "Salvatore Cortile"
#property version   "1.00"
#property description "RSI 28 (70/50/30): tra 50 e 70 BUY, tra 30 e 50 SELL, un trade a ogni candela aperto e chiuso nella stessa candela."

#include <Trade/Trade.mqh>

input group "RSI"
input int                InpRsiPeriod   = 28;           // Periodo RSI
input ENUM_APPLIED_PRICE InpRsiPrice    = PRICE_CLOSE;  // Prezzo RSI
input double             InpRsiUpper    = 70.0;         // Livello alto (sopra = niente trade)
input double             InpRsiMid      = 50.0;         // Livello centrale (sopra = BUY, sotto = SELL)
input double             InpRsiLower    = 30.0;         // Livello basso (sotto = niente trade)

input group "Segnale"
input ENUM_TIMEFRAMES    InpTimeframe          = PERIOD_M1; // Timeframe di lavoro

input group "Ordini"
input double             InpLots                  = 0.01;     // Lotto
input int                InpStopLossPoints        = 0;        // SL di emergenza in points (0 = nessuno)
input int                InpTakeProfitPoints      = 0;        // TP in points (0 = nessuno)
input int                InpMaxSpreadPoints       = 20;       // Spread massimo in points (0 = nessun filtro)
input int                InpSlippagePoints        = 10;       // Slippage massimo in points
input int                InpMaxEntryDelaySeconds  = 10;       // Apri solo nei primi N secondi della candela
input int                InpCloseSecondsBeforeEnd = 2;        // Chiudi N secondi prima della fine della candela
input ulong              InpMagic                 = 26100201; // Magic number
input string             InpComment               = "RSI M1 Bot";

input group "Orari (ora del server)"
input int                InpStartHour = 0;   // Ora inizio (0-23)
input int                InpEndHour   = 24;  // Ora fine (1-24, esclusa)

CTrade   trade;
int      rsiHandle      = INVALID_HANDLE;
datetime lastHandledBar = 0;   // candela su cui il segnale e' gia' stato valutato

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpRsiPeriod < 2 ||
      !(InpRsiLower < InpRsiMid && InpRsiMid < InpRsiUpper) ||
      InpStartHour < 0 || InpStartHour > 23 || InpEndHour < 1 || InpEndHour > 24)
     {
      Print("Parametri non validi: controlla periodo RSI, livelli (30 < 50 < 70) e orari.");
      return(INIT_PARAMETERS_INCORRECT);
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

   // Il timer serve a chiudere in tempo anche se non arrivano tick.
   EventSetTimer(1);
   PrintFormat("RSI_M1_Bot avviato su %s %s | RSI %d (%.0f/%.0f/%.0f)",
               _Symbol, EnumToString(InpTimeframe), InpRsiPeriod,
               InpRsiUpper, InpRsiMid, InpRsiLower);
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
   ManageOpenPositions();
   TryOpenTrade();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   ManageOpenPositions();
  }

//+------------------------------------------------------------------+
//| Chiude le posizioni del bot prima della fine della loro candela, |
//| oppure subito se la candela e' gia' finita.                      |
//+------------------------------------------------------------------+
void ManageOpenPositions()
  {
   int      periodSec = PeriodSeconds(InpTimeframe);
   datetime now       = TimeTradeServer();

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol ||
         (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      datetime barOpen  = openTime - (openTime % periodSec);
      datetime closeAt  = barOpen + periodSec - InpCloseSecondsBeforeEnd;

      if(now >= closeAt)
        {
         if(trade.PositionClose(ticket, InpSlippagePoints))
            PrintFormat("Chiusa posizione #%I64u (fine candela %s)", ticket, TimeToString(barOpen, TIME_MINUTES));
         else
            PrintFormat("Chiusura #%I64u fallita: %u %s", ticket,
                        trade.ResultRetcode(), trade.ResultRetcodeDescription());
        }
     }
  }

//+------------------------------------------------------------------+
bool HasOpenPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return(true);
     }
   return(false);
  }

//+------------------------------------------------------------------+
bool InTradingHours()
  {
   MqlDateTime t;
   TimeToStruct(TimeTradeServer(), t);
   if(InpStartHour < InpEndHour)
      return(t.hour >= InpStartHour && t.hour < InpEndHour);
   // Fascia a cavallo della mezzanotte (es. 22 -> 6)
   return(t.hour >= InpStartHour || t.hour < InpEndHour);
  }

//+------------------------------------------------------------------+
//| Restituisce +1 (BUY), -1 (SELL) o 0 (nessun trade) in base       |
//| all'RSI dell'ultima candela chiusa.                              |
//+------------------------------------------------------------------+
int GetSignal(double &rsiValue)
  {
   rsiValue = 0.0;

   if(BarsCalculated(rsiHandle) < InpRsiPeriod + 2)
      return(0);

   double rsi[];
   if(CopyBuffer(rsiHandle, 0, 1, 1, rsi) != 1)
      return(0);
   rsiValue = rsi[0];

   if(rsiValue > InpRsiMid && rsiValue <= InpRsiUpper)
      return(1);    // tra 50 e 70 -> BUY
   if(rsiValue < InpRsiMid && rsiValue >= InpRsiLower)
      return(-1);   // tra 30 e 50 -> SELL
   return(0);       // sopra 70, sotto 30 o esattamente 50 -> niente
  }

//+------------------------------------------------------------------+
double NormalizeLots(double lots)
  {
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double stepLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(stepLot > 0)
      lots = MathFloor(lots / stepLot + 1e-9) * stepLot;
   return(MathMax(minLot, MathMin(maxLot, lots)));
  }

//+------------------------------------------------------------------+
void TryOpenTrade()
  {
   datetime bar0 = iTime(_Symbol, InpTimeframe, 0);
   if(bar0 == 0 || bar0 == lastHandledBar)
      return;

   // Si entra solo all'inizio della candela: se e' troppo tardi si salta.
   if(TimeTradeServer() - bar0 > InpMaxEntryDelaySeconds)
     {
      lastHandledBar = bar0;
      return;
     }

   double rsiValue;
   int    signal = GetSignal(rsiValue);
   UpdatePanel(rsiValue, signal);

   if(signal == 0 || !InTradingHours())
     {
      lastHandledBar = bar0;
      return;
     }
   if(HasOpenPosition())
      return;   // la posizione precedente deve ancora chiudersi: riprova al prossimo tick

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
     {
      Print("Trading automatico disattivato: abilita 'Algo Trading'.");
      lastHandledBar = bar0;
      return;
     }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   double spreadPts = (tick.ask - tick.bid) / _Point;
   if(InpMaxSpreadPoints > 0 && spreadPts > InpMaxSpreadPoints)
      return;   // spread troppo alto: riprova ai tick successivi finche' resta tempo

   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double lots   = NormalizeLots(InpLots);
   double sl = 0.0, tp = 0.0;
   bool   ok;

   if(signal == 1)
     {
      if(InpStopLossPoints > 0)
         sl = NormalizeDouble(tick.ask - InpStopLossPoints * _Point, digits);
      if(InpTakeProfitPoints > 0)
         tp = NormalizeDouble(tick.ask + InpTakeProfitPoints * _Point, digits);
      ok = trade.Buy(lots, _Symbol, 0.0, sl, tp, InpComment);
     }
   else
     {
      if(InpStopLossPoints > 0)
         sl = NormalizeDouble(tick.bid + InpStopLossPoints * _Point, digits);
      if(InpTakeProfitPoints > 0)
         tp = NormalizeDouble(tick.bid - InpTakeProfitPoints * _Point, digits);
      ok = trade.Sell(lots, _Symbol, 0.0, sl, tp, InpComment);
     }

   lastHandledBar = bar0;
   if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
      PrintFormat("%s %s %.2f lotti | RSI=%.2f | spread=%.0f pts",
                  signal == 1 ? "BUY" : "SELL", _Symbol, lots, rsiValue, spreadPts);
   else
      PrintFormat("Apertura %s fallita: %u %s", signal == 1 ? "BUY" : "SELL",
                  trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
void UpdatePanel(double rsiValue, int signal)
  {
   string zone = "NESSUNA (fuori 30-70)";
   if(rsiValue > InpRsiMid && rsiValue <= InpRsiUpper)
      zone = "solo BUY";
   else
      if(rsiValue < InpRsiMid && rsiValue >= InpRsiLower)
         zone = "solo SELL";

   Comment(StringFormat("RSI M1 Bot  |  %s %s\nRSI(%d) = %.2f  ->  zona %s\nTrade di questa candela: %s",
                        _Symbol, EnumToString(InpTimeframe), InpRsiPeriod, rsiValue, zone,
                        signal == 1 ? "BUY" : (signal == -1 ? "SELL" : "nessuno")));
  }
//+------------------------------------------------------------------+
