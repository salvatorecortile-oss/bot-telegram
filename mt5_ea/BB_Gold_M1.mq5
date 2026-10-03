//+------------------------------------------------------------------+
//|                                                  BB_Gold_M1.mq5  |
//|  Bande di Bollinger su XAUUSD M1.                                |
//|                                                                  |
//|  - Modalita' SELL: almeno InpMinCandles candele VERDI di fila e  |
//|    una di esse (dalla InpMinCandles-esima in poi) tocca la banda |
//|    superiore. Finisce quando il prezzo tocca la banda inferiore. |
//|  - Modalita' BUY: almeno InpMinCandles candele ROSSE di fila e   |
//|    una di esse tocca la banda inferiore. Finisce quando il       |
//|    prezzo tocca la banda superiore.                              |
//|  - InpOnePerCandle = false: UNA sola operazione per modalita',   |
//|    aperta all'inizio della candela successiva e chiusa al tocco  |
//|    della banda opposta.                                          |
//|  - InpOnePerCandle = true: un'operazione A OGNI candela, aperta  |
//|    all'apertura e chiusa alla chiusura (chiusura e riapertura    |
//|    sullo stesso tick), finche' il prezzo tocca la banda opposta. |
//|  - InpMaxMinutes: se la modalita' dura piu' di N minuti senza     |
//|    toccare la banda opposta, chiude tutto e la modalita' finisce. |
//|  - Dopo la fine di una modalita' serve una nuova serie di        |
//|    candele + tocco per ripartire.                                |
//+------------------------------------------------------------------+
#property copyright "Salvatore Cortile"
#property version   "1.10"
#property description "XAUUSD M1: Bollinger 20/2, almeno 4 candele dello stesso colore + tocco della banda. Un trade unico o un trade per candela."

#include <Trade/Trade.mqh>

input group "Bollinger"
input ENUM_TIMEFRAMES InpTimeframe   = PERIOD_M1; // Timeframe di lavoro
input int             InpBandsPeriod = 20;        // Periodo
input double          InpBandsDev    = 2.0;       // Deviazione

input group "Segnale"
input int             InpMinCandles   = 4;     // Candele dello stesso colore di fila (minimo)
input bool            InpOnePerCandle = false; // false = un trade unico fino alla banda opposta; true = un trade per candela
input bool            InpAllowBuy     = true;  // Abilita la modalita' BUY
input bool            InpAllowSell    = true;  // Abilita la modalita' SELL
input int             InpMaxMinutes   = 30;    // Uscita a tempo: chiude dopo N minuti senza tocco della banda opposta (0 = spenta)

input group "Ordini"
input double          InpLots            = 0.01;     // Lotto
input double          InpEmergencySl     = 0.0;      // Stop di emergenza in prezzo (es. 10 = 10$ sull'oro; 0 = nessuno)
input int             InpMaxSpreadPoints = 0;        // Spread massimo per aprire, in points (0 = nessun filtro)
input int             InpSlippagePoints  = 30;       // Slippage massimo in points
input ulong           InpMagic           = 26100501; // Magic number
input string          InpComment         = "BB Gold M1";

CTrade   trade;
int      bandsHandle = INVALID_HANDLE;
datetime currentBar  = 0;
int      mode        = 0;      // +1 BUY, -1 SELL, 0 in attesa
datetime modeStart   = 0;      // inizio della modalita' attiva
bool     openedInMode = false; // modalita' trade unico: operazione gia' aperta
string   gvMode;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpMaxMinutes < 0 || InpBandsPeriod < 2 || InpBandsDev <= 0 || InpMinCandles < 1 || InpLots <= 0 || InpEmergencySl < 0)
     {
      Print("Parametri non validi.");
      return(INIT_PARAMETERS_INCORRECT);
     }
   bandsHandle = iBands(_Symbol, InpTimeframe, InpBandsPeriod, 0, InpBandsDev, PRICE_CLOSE);
   if(bandsHandle == INVALID_HANDLE)
     {
      Print("Impossibile creare le Bande di Bollinger: ", GetLastError());
      return(INIT_FAILED);
     }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   // Ripresa dopo un riavvio: la modalita' si ricava dalla posizione aperta o dalla variabile globale.
   gvMode = StringFormat("BBGOLD_%s_%I64u_mode", _Symbol, InpMagic);
   ulong t;
   int dir = PositionDir(t);
   if(dir != 0)
     {
      mode         = dir;
      modeStart    = (datetime)PositionGetInteger(POSITION_TIME);
      openedInMode = true;
     }
   else
      if(GlobalVariableCheck(gvMode))
        {
         mode      = (int)GlobalVariableGet(gvMode);
         modeStart = TimeCurrent();
        }

   PrintFormat("BB_Gold_M1 avviato su %s %s | Bollinger %d/%.1f | %d candele | %s | uscita a tempo %d min | stop %.2f | lotto %.2f",
               _Symbol, EnumToString(InpTimeframe), InpBandsPeriod, InpBandsDev, InpMinCandles,
               InpOnePerCandle ? "un trade per candela" : "trade unico fino alla banda opposta",
               InpMaxMinutes, InpEmergencySl, InpLots);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   IndicatorRelease(bandsHandle);
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   // 1) Fine modalita': il prezzo tocca la banda opposta (in tempo reale) o scade il tempo.
   CheckOppositeTouch();
   CheckTimeExit();

   // 2) Nuova candela: chiusura/riapertura e ricerca di una nuova modalita'.
   datetime bar0 = iTime(_Symbol, InpTimeframe, 0);
   if(bar0 != 0 && bar0 != currentBar)
     {
      currentBar = bar0;
      OnNewBar();
     }
   UpdatePanel();
  }

//+------------------------------------------------------------------+
void CheckOppositeTouch()
  {
   if(mode == 0)
      return;
   double upper, lower;
   if(!ReadBands(0, upper, lower))
      return;
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;

   bool touched = (mode == -1) ? (tick.bid <= lower) : (tick.bid >= upper);
   if(!touched)
      return;

   PrintFormat("Prezzo %s ha toccato la banda %s: fine modalita' %s.", DoubleToString(tick.bid, _Digits),
               mode == -1 ? "inferiore" : "superiore", mode == -1 ? "SELL" : "BUY");
   CloseMine();
   SetMode(0);
  }

//+------------------------------------------------------------------+
//| Uscita a tempo: la modalita' dura troppo senza toccare la banda. |
//+------------------------------------------------------------------+
void CheckTimeExit()
  {
   if(mode == 0 || InpMaxMinutes <= 0 || modeStart == 0)
      return;
   if(TimeCurrent() - modeStart < InpMaxMinutes * 60)
      return;
   PrintFormat("Modalita' %s attiva da %d minuti senza toccare la banda opposta: chiudo.",
               mode == -1 ? "SELL" : "BUY", InpMaxMinutes);
   CloseMine();
   SetMode(0);
  }

//+------------------------------------------------------------------+
void OnNewBar()
  {
   // Un trade per candela: la candela appena finita chiude la sua operazione.
   if(InpOnePerCandle)
      CloseMine();

   // Nessuna modalita' attiva: cerca la serie di candele + tocco sulla candela appena chiusa.
   if(mode == 0)
     {
      int signal = CheckSetup();
      if(signal != 0)
        {
         SetMode(signal);
         openedInMode = false;
         PrintFormat("Attivata modalita' %s: %d+ candele %s e tocco della banda %s.",
                     signal == -1 ? "SELL" : "BUY", InpMinCandles, signal == -1 ? "verdi" : "rosse",
                     signal == -1 ? "superiore" : "inferiore");
        }
     }

   if(mode == 0)
      return;

   // Apertura: ogni candela (modalita' per candela) oppure una volta sola (trade unico).
   ulong t;
   if(InpOnePerCandle || (!openedInMode && PositionDir(t) == 0))
      Open(mode);
  }

//+------------------------------------------------------------------+
//| -1 = setup SELL, +1 = setup BUY, 0 = niente, sulla candela 1.    |
//+------------------------------------------------------------------+
int CheckSetup()
  {
   double o = iOpen(_Symbol, InpTimeframe, 1), c = iClose(_Symbol, InpTimeframe, 1);
   int    color1 = (c > o) ? 1 : (c < o ? -1 : 0);
   if(color1 == 0)
      return(0);

   // Lunghezza della serie di candele dello stesso colore che termina sulla candela 1.
   int streak = 0;
   for(int i = 1; i < 200; i++)
     {
      double oi = iOpen(_Symbol, InpTimeframe, i), ci = iClose(_Symbol, InpTimeframe, i);
      int    col = (ci > oi) ? 1 : (ci < oi ? -1 : 0);
      if(col != color1)
         break;
      streak++;
     }
   if(streak < InpMinCandles)
      return(0);

   double upper, lower;
   if(!ReadBands(1, upper, lower))
      return(0);

   if(color1 == 1 && InpAllowSell && iHigh(_Symbol, InpTimeframe, 1) >= upper)
      return(-1);   // verdi + tocco banda superiore -> SELL
   if(color1 == -1 && InpAllowBuy && iLow(_Symbol, InpTimeframe, 1) <= lower)
      return(1);    // rosse + tocco banda inferiore -> BUY
   return(0);
  }

//+------------------------------------------------------------------+
void Open(int dir)
  {
   MqlTick tick;
   if(!SymbolInfoTick(_Symbol, tick))
      return;
   double spreadPts = (tick.ask - tick.bid) / _Point;
   if(InpMaxSpreadPoints > 0 && spreadPts > InpMaxSpreadPoints)
     {
      PrintFormat("Spread %.0f points troppo alto: operazione saltata su questa candela.", spreadPts);
      return;
     }

   double sl = 0.0;
   if(InpEmergencySl > 0)
      sl = NormalizeDouble(dir == 1 ? tick.ask - InpEmergencySl : tick.bid + InpEmergencySl, _Digits);

   bool ok = (dir == 1) ? trade.Buy(InpLots, _Symbol, 0.0, sl, 0.0, InpComment)
                        : trade.Sell(InpLots, _Symbol, 0.0, sl, 0.0, InpComment);
   if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
     {
      openedInMode = true;
      PrintFormat("Aperto %s %.2f a %s", dir == 1 ? "BUY" : "SELL", InpLots, DoubleToString(trade.ResultPrice(), _Digits));
     }
   else
      PrintFormat("Apertura fallita: %u %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
void CloseMine()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol || (ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      if(!trade.PositionClose(t, InpSlippagePoints))
         PrintFormat("Chiusura #%I64u fallita: %u %s", t, trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }
  }

//+------------------------------------------------------------------+
int PositionDir(ulong &ticket)
  {
   ticket = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol && (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
        {
         ticket = t;
         return(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? 1 : -1);
        }
     }
   return(0);
  }

//+------------------------------------------------------------------+
void SetMode(int m)
  {
   mode      = m;
   modeStart = (m != 0) ? TimeCurrent() : 0;
   GlobalVariableSet(gvMode, mode);
  }

//+------------------------------------------------------------------+
//| Bande superiore e inferiore della candela indicata.              |
//+------------------------------------------------------------------+
bool ReadBands(int shift, double &upper, double &lower)
  {
   double up[], lo[];
   if(CopyBuffer(bandsHandle, 1, shift, 1, up) != 1 || CopyBuffer(bandsHandle, 2, shift, 1, lo) != 1)
      return(false);
   upper = up[0];
   lower = lo[0];
   return(true);
  }

//+------------------------------------------------------------------+
void UpdatePanel()
  {
   double upper = 0, lower = 0;
   ReadBands(0, upper, lower);
   ulong t;
   int dir = PositionDir(t);
   string m = (mode == -1) ? "SELL (fino alla banda inferiore)" : (mode == 1 ? "BUY (fino alla banda superiore)" : "in attesa di serie + tocco");
   string left = (mode != 0 && InpMaxMinutes > 0 && modeStart > 0)
                 ? StringFormat(" (uscita a tempo tra %d min)", (int)MathMax(0, (modeStart + InpMaxMinutes * 60 - TimeCurrent()) / 60)) : "";
   Comment(StringFormat("BB Gold M1  |  %s %s  |  %s\nBanda sup %s  |  banda inf %s\nModalita': %s%s\nPosizione: %s",
                        _Symbol, EnumToString(InpTimeframe),
                        InpOnePerCandle ? "un trade per candela" : "trade unico",
                        DoubleToString(upper, _Digits), DoubleToString(lower, _Digits), m, left,
                        dir == 0 ? "nessuna" : (dir == 1 ? "BUY" : "SELL")));
  }
//+------------------------------------------------------------------+
