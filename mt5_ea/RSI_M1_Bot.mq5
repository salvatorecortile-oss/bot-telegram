//+------------------------------------------------------------------+
//|                                                  RSI_M1_Bot.mq5  |
//|  Expert Advisor per MT5: si attacca al grafico di QUALSIASI      |
//|  simbolo (EURUSD, GBPUSD, XAUUSD, ...) e opera sul timeframe     |
//|  scelto (default M1).                                            |
//|                                                                  |
//|  Regole:                                                         |
//|  - RSI (default 28 periodi) calcolato sulla candela CHIUSA.      |
//|  - RSI tra 50 e 70  -> BUY.                                      |
//|  - RSI tra 30 e 50  -> SELL.                                     |
//|  - RSI sopra 70 o sotto 30 -> nessuna operazione.                |
//|  - Tutto avviene sul PRIMO TICK della nuova candela: chiusura    |
//|    della posizione precedente e apertura della nuova sono una    |
//|    subito dopo l'altra, allo stesso prezzo di mercato.           |
//|  - Se la direzione resta uguale, la posizione puo' restare       |
//|    aperta (InpKeepSameDirection) per non pagare di nuovo lo      |
//|    spread a ogni minuto.                                         |
//+------------------------------------------------------------------+
#property copyright "Salvatore Cortile"
#property version   "1.10"
#property description "RSI 28 (70/50/30): tra 50 e 70 BUY, tra 30 e 50 SELL. Chiusura e riapertura istantanee al cambio candela."

#include <Trade/Trade.mqh>

input group "RSI"
input int                InpRsiPeriod   = 28;           // Periodo RSI
input ENUM_APPLIED_PRICE InpRsiPrice    = PRICE_CLOSE;  // Prezzo RSI
input double             InpRsiUpper    = 70.0;         // Livello alto (sopra = niente trade)
input double             InpRsiMid      = 50.0;         // Livello centrale (sopra = BUY, sotto = SELL)
input double             InpRsiLower    = 30.0;         // Livello basso (sotto = niente trade)

input group "Segnale"
input ENUM_TIMEFRAMES    InpTimeframe         = PERIOD_M1; // Timeframe di lavoro
input bool               InpKeepSameDirection = true;      // Stessa direzione: tieni aperta (true) o chiudi e riapri (false)

input group "Ordini"
input double             InpLots                 = 0.01;     // Lotto
input int                InpStopLossPoints       = 0;        // SL di emergenza in points (0 = nessuno)
input int                InpTakeProfitPoints     = 0;        // TP in points (0 = nessuno)
input int                InpMaxSpreadPoints      = 0;        // Spread massimo per aprire, in points (0 = nessun filtro)
input int                InpSlippagePoints       = 10;       // Slippage massimo in points
input int                InpMaxEntryDelaySeconds = 10;       // Apri solo nei primi N secondi della candela
input ulong              InpMagic                = 26100201; // Magic number
input string             InpComment              = "RSI M1 Bot";

input group "Orari (ora del server)"
input int                InpStartHour = 0;   // Ora inizio (0-23)
input int                InpEndHour   = 24;  // Ora fine (1-24, esclusa)

CTrade   trade;
int      rsiHandle     = INVALID_HANDLE;
datetime currentBar    = 0;     // candela corrente gia' valutata
int      desiredDir    = 0;     // +1 BUY, -1 SELL, 0 niente per la candela corrente
bool     openDoneOnBar = false; // apertura gia' tentata su questa candela
double   lastRsi       = 0.0;

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

   // Il timer riprova eventuali chiusure fallite anche senza tick.
   EventSetTimer(1);
   PrintFormat("RSI_M1_Bot avviato su %s %s | RSI %d (%.0f/%.0f/%.0f) | stessa direzione: %s",
               _Symbol, EnumToString(InpTimeframe), InpRsiPeriod,
               InpRsiUpper, InpRsiMid, InpRsiLower,
               InpKeepSameDirection ? "tieni aperta" : "chiudi e riapri");
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
   datetime bar0 = iTime(_Symbol, InpTimeframe, 0);
   if(bar0 != 0 && bar0 != currentBar)
     {
      // Primo tick della nuova candela: la precedente si e' appena chiusa.
      currentBar    = bar0;
      openDoneOnBar = false;
      desiredDir    = InTradingHours() ? GetSignal(lastRsi) : 0;
      UpdatePanel();
     }
   Sync();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   Sync();
  }

//+------------------------------------------------------------------+
//| Porta le posizioni del bot nello stato voluto per la candela     |
//| corrente: chiude quelle da chiudere e subito dopo apre la nuova. |
//+------------------------------------------------------------------+
void Sync()
  {
   if(currentBar == 0)
      return;

   int  periodSec   = PeriodSeconds(InpTimeframe);
   bool haveWanted  = false;
   bool haveOthers  = false;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol ||
         (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      int      dir      = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      datetime openBar  = openTime - (openTime % periodSec);

      bool keep = (dir == desiredDir) && (InpKeepSameDirection || openBar == currentBar);
      if(keep)
        {
         haveWanted = true;
         continue;
        }

      if(trade.PositionClose(ticket, InpSlippagePoints))
         PrintFormat("Chiusa %s #%I64u a %s", dir == 1 ? "BUY" : "SELL", ticket,
                     DoubleToString(trade.ResultPrice(), _Digits));
      else
        {
         haveOthers = true;
         PrintFormat("Chiusura #%I64u fallita: %u %s", ticket,
                     trade.ResultRetcode(), trade.ResultRetcodeDescription());
        }
     }

   if(desiredDir == 0 || haveWanted || haveOthers || openDoneOnBar)
      return;

   OpenTrade();
  }

//+------------------------------------------------------------------+
void OpenTrade()
  {
   if(TimeTradeServer() - currentBar > InpMaxEntryDelaySeconds)
     {
      openDoneOnBar = true;   // troppo tardi per questa candela
      return;
     }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
     {
      Print("Trading automatico disattivato: abilita 'Algo Trading'.");
      openDoneOnBar = true;
      return;
     }

   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   double spreadPts = (tick.ask - tick.bid) / _Point;
   if(InpMaxSpreadPoints > 0 && spreadPts > InpMaxSpreadPoints)
      return;   // spread troppo alto: riprova ai tick successivi finche' resta tempo

   double lots = NormalizeLots(InpLots);
   double sl = 0.0, tp = 0.0;
   bool   ok;

   if(desiredDir == 1)
     {
      if(InpStopLossPoints > 0)
         sl = NormalizeDouble(tick.ask - InpStopLossPoints * _Point, _Digits);
      if(InpTakeProfitPoints > 0)
         tp = NormalizeDouble(tick.ask + InpTakeProfitPoints * _Point, _Digits);
      ok = trade.Buy(lots, _Symbol, 0.0, sl, tp, InpComment);
     }
   else
     {
      if(InpStopLossPoints > 0)
         sl = NormalizeDouble(tick.bid + InpStopLossPoints * _Point, _Digits);
      if(InpTakeProfitPoints > 0)
         tp = NormalizeDouble(tick.bid - InpTakeProfitPoints * _Point, _Digits);
      ok = trade.Sell(lots, _Symbol, 0.0, sl, tp, InpComment);
     }

   openDoneOnBar = true;
   if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
      PrintFormat("Aperto %s %s %.2f lotti a %s | RSI=%.2f | spread=%.0f pts",
                  desiredDir == 1 ? "BUY" : "SELL", _Symbol, lots,
                  DoubleToString(trade.ResultPrice(), _Digits), lastRsi, spreadPts);
   else
      PrintFormat("Apertura %s fallita: %u %s", desiredDir == 1 ? "BUY" : "SELL",
                  trade.ResultRetcode(), trade.ResultRetcodeDescription());
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
//| +1 (BUY), -1 (SELL) o 0 in base all'RSI dell'ultima candela      |
//| chiusa.                                                          |
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
void UpdatePanel()
  {
   string zone = "NESSUNA (fuori 30-70)";
   if(lastRsi > InpRsiMid && lastRsi <= InpRsiUpper)
      zone = "BUY";
   else
      if(lastRsi < InpRsiMid && lastRsi >= InpRsiLower)
         zone = "SELL";

   Comment(StringFormat("RSI M1 Bot  |  %s %s\nRSI(%d) = %.2f  ->  zona %s\nDirezione di questa candela: %s",
                        _Symbol, EnumToString(InpTimeframe), InpRsiPeriod, lastRsi, zone,
                        desiredDir == 1 ? "BUY" : (desiredDir == -1 ? "SELL" : "nessuna")));
  }
//+------------------------------------------------------------------+
