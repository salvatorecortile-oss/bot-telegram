//+------------------------------------------------------------------+
//|                                                   TRS_Zones.mq5  |
//|  Traduce in regole oggettive i concetti del PDF "TRS":           |
//|   1) Zone di reazione  -> range di consolidamento + breakout     |
//|   2) Zone forti        -> swing con inversione forte             |
//|   3) Rifiuti           -> candele con ombra lunga                |
//|   4) Rimbalzi/Breakout -> reazione del prezzo sulle zone 2) e 3) |
//|                                                                  |
//|  Lavora solo su candele CHIUSE: un segnale apparso non cambia    |
//|  piu' (niente repaint dei segnali).                              |
//+------------------------------------------------------------------+
#property copyright   "bot-telegram"
#property version     "1.00"
#property description "Zone di reazione, zone forti, rifiuti, rimbalzi e breakout (metodo TRS con regole oggettive)"
#property indicator_chart_window
#property indicator_buffers 3
#property indicator_plots   3

#property indicator_label1  "Segnale BUY"
#property indicator_type1   DRAW_ARROW
#property indicator_color1  clrLime
#property indicator_width1  2

#property indicator_label2  "Segnale SELL"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  clrRed
#property indicator_width2  2

#property indicator_label3  "Codice segnale"
#property indicator_type3   DRAW_NONE

//--- codici segnale (buffer 2): segno = direzione (+ buy, - sell)
#define SIG_REACTION 1   // breakout di una zona di reazione
#define SIG_BREAKOUT 2   // breakout di una zona forte / di rifiuto
#define SIG_BOUNCE   3   // rimbalzo su una zona forte / di rifiuto

#define PREFIX "TRSZ_"

enum ENUM_ZONE_KIND
  {
   ZK_REACTION  = 0,
   ZK_STRONG    = 1,
   ZK_REJECTION = 2
  };

//--- input
input group "=== Generale ==="
input int    InpLookback        = 1500;  // Candele analizzate
input int    InpATRPeriod       = 14;    // Periodo ATR (misura della volatilita')

input group "=== 1) Zone di reazione ==="
input bool   InpShowReaction    = true;  // Attiva zone di reazione
input int    InpRangeBars       = 3;     // Candele che formano il range
input double InpRangeMaxATR     = 1.0;   // Altezza massima del range (x ATR)
input double InpRangeMinATR     = 0.2;   // Altezza minima del range (x ATR)
input int    InpImpulseBars     = 5;     // Candele del movimento prima del range
input double InpImpulseATR      = 2.5;   // Ampiezza minima del movimento (x ATR)
input int    InpReactionExpiry  = 30;    // Candele dopo cui la zona scade
input bool   InpBreakOnClose    = true;  // Breakout solo con chiusura fuori dal range
input bool   InpOnlyWithTrend   = true;  // Segnala solo breakout nella direzione del movimento

input group "=== 2) Zone forti ==="
input bool   InpShowStrong      = true;  // Attiva zone forti
input int    InpSwingBars       = 5;     // Candele a sx/dx per confermare lo swing
input double InpStrongATR       = 2.5;   // Inversione minima dopo lo swing (x ATR)

input group "=== 3) Rifiuti ==="
input bool   InpShowRejection   = true;  // Attiva zone di rifiuto
input double InpWickBodyRatio   = 3.0;   // Ombra >= N volte il corpo
input double InpWickMinATR      = 1.2;   // Ombra minima (x ATR)

input group "=== 4) Rimbalzi / Breakout sulle zone ==="
input bool   InpSignalBounce    = true;  // Segnala rimbalzi
input bool   InpSignalBreakout  = true;  // Segnala breakout
input int    InpMinRetestBars   = 3;     // Candele minime prima che la zona sia testabile
input int    InpMaxBounces      = 1;     // Max rimbalzi segnalati per zona
input int    InpZoneExpiry      = 300;   // Candele di vita di una zona
input int    InpMaxZones        = 30;    // Max zone forti/rifiuto attive
input double InpZoneMinATR      = 0.10;  // Spessore minimo zona (x ATR)
input double InpZoneMaxATR      = 0.60;  // Spessore massimo zona (x ATR)

input group "=== Filtri segnali ==="
input int    InpCooldownBars    = 8;     // Candele minime tra due segnali
input int    InpStartHour       = 8;     // Ora inizio segnali (ora server)
input int    InpEndHour         = 20;    // Ora fine segnali (ora server)

input group "=== Grafica ==="
input bool   InpShowDeadZones   = false; // Mostra zone gia' rotte/scadute
input bool   InpShowSignalText  = true;  // Scritta accanto alle frecce
input int    InpExtendBars      = 10;    // Prolunga a destra le zone attive
input color  InpColReaction     = C'95,95,30';    // Zona di reazione
input color  InpColStrongSup    = C'0,85,55';     // Zona forte (supporto)
input color  InpColStrongRes    = C'105,30,30';   // Zona forte (resistenza)
input color  InpColRejSup       = C'0,60,100';    // Rifiuto (supporto)
input color  InpColRejRes       = C'95,40,95';    // Rifiuto (resistenza)
input color  InpColDead         = C'45,45,45';    // Zona rotta/scaduta
input color  InpColText         = clrSilver;      // Colore scritte

input group "=== Avvisi ==="
input bool   InpAlertPopup      = true;  // Popup su nuovo segnale
input bool   InpAlertPush       = false; // Notifica push al telefono (MT5 mobile)

//--- strutture e variabili globali
struct Zone
  {
   int               kind;       // ENUM_ZONE_KIND
   int               side;       // +1 supporto, -1 resistenza, 0 range di reazione
   int               trend;      // direzione del movimento prima del range (+1/-1)
   double            top;
   double            bottom;
   int               startBar;   // candela di origine (per il disegno)
   int               activeFrom; // prima candela che puo' generare segnali
   int               endBar;     // candela di rottura/scadenza (-1 se attiva)
   int               touches;    // ritorni del prezzo sulla zona
   bool              alive;
   bool              broken;
  };

double   BuyBuf[], SellBuf[], CodeBuf[];
Zone     g_zones[];
int      g_zoneCount      = 0;
int      g_lastReactionEnd = -1;
int      g_lastSignalBar  = -1000000;
int      g_atrHandle      = INVALID_HANDLE;
datetime g_lastBarTime    = 0;
datetime g_lastAlertTime  = 0;
bool     g_firstRun       = true;

double   g_o[], g_h[], g_l[], g_c[], g_atr[];
datetime g_t[];

//+------------------------------------------------------------------+
int OnInit()
  {
   SetIndexBuffer(0, BuyBuf,  INDICATOR_DATA);
   SetIndexBuffer(1, SellBuf, INDICATOR_DATA);
   SetIndexBuffer(2, CodeBuf, INDICATOR_DATA);
   ArraySetAsSeries(BuyBuf,  false);
   ArraySetAsSeries(SellBuf, false);
   ArraySetAsSeries(CodeBuf, false);

   PlotIndexSetInteger(0, PLOT_ARROW, 233);
   PlotIndexSetInteger(1, PLOT_ARROW, 234);
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(2, PLOT_EMPTY_VALUE, 0.0);

   IndicatorSetString(INDICATOR_SHORTNAME, "TRS Zones");
   IndicatorSetInteger(INDICATOR_DIGITS, _Digits);

   g_atrHandle = iATR(_Symbol, _Period, InpATRPeriod);
   if(g_atrHandle == INVALID_HANDLE)
     {
      Print("TRS Zones: impossibile creare l'ATR, errore ", GetLastError());
      return(INIT_FAILED);
     }
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0, PREFIX);
   if(g_atrHandle != INVALID_HANDLE)
      IndicatorRelease(g_atrHandle);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   if(rates_total < 100)
      return(0);

   ArraySetAsSeries(time,  false);
   ArraySetAsSeries(open,  false);
   ArraySetAsSeries(high,  false);
   ArraySetAsSeries(low,   false);
   ArraySetAsSeries(close, false);

//--- ricalcolo solo alla nascita di una nuova candela
   if(prev_calculated > 0 && time[rates_total - 1] == g_lastBarTime)
      return(rates_total);

   if(BarsCalculated(g_atrHandle) < rates_total)
      return(0);
   ArraySetAsSeries(g_atr, false);
   if(CopyBuffer(g_atrHandle, 0, 0, rates_total, g_atr) != rates_total)
      return(0);

   ArrayCopy(g_t, time);
   ArrayCopy(g_o, open);
   ArrayCopy(g_h, high);
   ArrayCopy(g_l, low);
   ArrayCopy(g_c, close);

   Rebuild(rates_total);
   CheckAlert(rates_total);

   g_lastBarTime = time[rates_total - 1];
   g_firstRun = false;
   return(rates_total);
  }

//+------------------------------------------------------------------+
//| Ricostruisce zone e segnali sulle ultime InpLookback candele     |
//+------------------------------------------------------------------+
void Rebuild(const int rates_total)
  {
   ObjectsDeleteAll(0, PREFIX);
   ArrayInitialize(BuyBuf,  EMPTY_VALUE);
   ArrayInitialize(SellBuf, EMPTY_VALUE);
   ArrayInitialize(CodeBuf, 0.0);
   ArrayResize(g_zones, 0, 256);
   g_zoneCount = 0;
   g_lastReactionEnd = -1;
   g_lastSignalBar = -1000000;

   int warmup = InpATRPeriod + InpImpulseBars + RangeBars() + 2 * SwingBars() + 5;
   int first  = MathMax(warmup, rates_total - InpLookback);
   int last   = rates_total - 2;   // ultima candela chiusa

   for(int i = first; i <= last; i++)
     {
      if(g_atr[i] <= 0.0 || g_atr[i] == EMPTY_VALUE)
         continue;

      //--- prima si valutano le zone gia' esistenti, poi si cercano le nuove
      for(int k = 0; k < g_zoneCount; k++)
        {
         if(!g_zones[k].alive || i < g_zones[k].activeFrom)
            continue;
         if(g_zones[k].kind == ZK_REACTION)
            ProcessReaction(g_zones[k], i);
         else
            ProcessSR(g_zones[k], i);
        }

      if(InpShowReaction)
         DetectReaction(i);
      if(InpShowStrong)
         DetectStrong(i);
      if(InpShowRejection)
         DetectRejection(i);
     }

   DrawZones(rates_total);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| 1) Zona di reazione: N candele con corpi compressi dopo un       |
//|    movimento direzionale. Massimo/minimo = estremi dei corpi.    |
//+------------------------------------------------------------------+
void DetectReaction(const int i)
  {
   for(int k = 0; k < g_zoneCount; k++)
      if(g_zones[k].alive && g_zones[k].kind == ZK_REACTION)
         return;   // una sola zona di reazione attiva per volta

   int w0 = i - RangeBars() + 1;
   if(w0 <= g_lastReactionEnd)
      return;      // non riusare candele gia' in una zona

   double top = -DBL_MAX, bot = DBL_MAX;
   for(int b = w0; b <= i; b++)
     {
      top = MathMax(top, MathMax(g_o[b], g_c[b]));
      bot = MathMin(bot, MathMin(g_o[b], g_c[b]));
     }
   double h = top - bot;
   if(h < InpRangeMinATR * g_atr[i] || h > InpRangeMaxATR * g_atr[i])
      return;

   double move = g_c[w0 - 1] - g_c[w0 - 1 - InpImpulseBars];
   if(MathAbs(move) < InpImpulseATR * g_atr[i])
      return;

   Zone z;
   z.kind       = ZK_REACTION;
   z.side       = 0;
   z.trend      = (move > 0) ? 1 : -1;
   z.top        = top;
   z.bottom     = bot;
   z.startBar   = w0;
   z.activeFrom = i + 1;
   z.endBar     = -1;
   z.touches    = 0;
   z.alive      = true;
   z.broken     = false;
   AddZone(z);
   g_lastReactionEnd = i;
  }

//+------------------------------------------------------------------+
void ProcessReaction(Zone &z, const int i)
  {
   if(i - z.startBar > InpReactionExpiry)
     {
      KillZone(z, i, false);
      return;
     }
   double upRef = InpBreakOnClose ? g_c[i] : g_h[i];
   double dnRef = InpBreakOnClose ? g_c[i] : g_l[i];
   bool up = (upRef > z.top);
   bool dn = (dnRef < z.bottom);
   if(up && dn)
     {
      up = (g_c[i] > g_o[i]);
      dn = !up;
     }
   if(!up && !dn)
      return;

   int dir = up ? 1 : -1;
   KillZone(z, i, true);
   if(InpOnlyWithTrend && dir != z.trend)
      return;
   AddSignal(i, dir * SIG_REACTION);
  }

//+------------------------------------------------------------------+
//| 2) Zona forte: swing high/low seguito da un'inversione di almeno |
//|    InpStrongATR x ATR. Zona = dall'estremo (ombra) ai corpi.     |
//+------------------------------------------------------------------+
void DetectStrong(const int i)
  {
   int n = SwingBars();
   int s = i - n;
   bool isLow = true, isHigh = true;
   for(int k = 1; k <= n; k++)
     {
      if(g_l[s] >= g_l[s - k] || g_l[s] > g_l[s + k])
         isLow = false;
      if(g_h[s] <= g_h[s - k] || g_h[s] < g_h[s + k])
         isHigh = false;
     }
   int activeFrom = MathMax(i + 1, s + InpMinRetestBars);

   if(isLow)
     {
      double maxClose = -DBL_MAX;
      for(int b = s + 1; b <= i; b++)
         maxClose = MathMax(maxClose, g_c[b]);
      if(maxClose - g_l[s] >= InpStrongATR * g_atr[s])
        {
         double bot = g_l[s];
         double top = DBL_MAX;
         for(int b = s - 1; b <= s + 1; b++)
            top = MathMin(top, MathMin(g_o[b], g_c[b]));
         top = MathMax(top, bot);
         ClampZone(top, bot, g_atr[s], +1);
         TryAddSR(ZK_STRONG, +1, top, bot, s, activeFrom, i);
        }
     }
   if(isHigh)
     {
      double minClose = DBL_MAX;
      for(int b = s + 1; b <= i; b++)
         minClose = MathMin(minClose, g_c[b]);
      if(g_h[s] - minClose >= InpStrongATR * g_atr[s])
        {
         double top = g_h[s];
         double bot = -DBL_MAX;
         for(int b = s - 1; b <= s + 1; b++)
            bot = MathMax(bot, MathMax(g_o[b], g_c[b]));
         bot = MathMin(bot, top);
         ClampZone(top, bot, g_atr[s], -1);
         TryAddSR(ZK_STRONG, -1, top, bot, s, activeFrom, i);
        }
     }
  }

//+------------------------------------------------------------------+
//| 3) Rifiuto: candela con ombra lunga (rispetto al corpo e all'ATR)|
//|    Zona = l'ombra stessa.                                        |
//+------------------------------------------------------------------+
void DetectRejection(const int i)
  {
   double bodyTop = MathMax(g_o[i], g_c[i]);
   double bodyBot = MathMin(g_o[i], g_c[i]);
   double body    = bodyTop - bodyBot;
   double lw      = bodyBot - g_l[i];
   double uw      = g_h[i] - bodyTop;
   double minW    = InpWickMinATR * g_atr[i];
   int activeFrom = i + MathMax(1, InpMinRetestBars);

   if(lw >= minW && lw >= InpWickBodyRatio * body && lw > uw)
     {
      double top = bodyBot, bot = g_l[i];
      ClampZone(top, bot, g_atr[i], +1);
      TryAddSR(ZK_REJECTION, +1, top, bot, i, activeFrom, i);
     }
   else
      if(uw >= minW && uw >= InpWickBodyRatio * body && uw > lw)
        {
         double top = g_h[i], bot = bodyTop;
         ClampZone(top, bot, g_atr[i], -1);
         TryAddSR(ZK_REJECTION, -1, top, bot, i, activeFrom, i);
        }
  }

//+------------------------------------------------------------------+
//| 4) Comportamento del prezzo su zone forti / di rifiuto           |
//|    - chiusura oltre la zona            -> BREAKOUT               |
//|    - ritorno sulla zona e rifiuto      -> RIMBALZO               |
//+------------------------------------------------------------------+
void ProcessSR(Zone &z, const int i)
  {
   if(i - z.startBar > InpZoneExpiry)
     {
      KillZone(z, i, false);
      return;
     }
   double bodyTop = MathMax(g_o[i], g_c[i]);
   double bodyBot = MathMin(g_o[i], g_c[i]);
   double body    = bodyTop - bodyBot;

   if(z.side > 0)   // supporto
     {
      if(g_c[i] < z.bottom)
        {
         KillZone(z, i, true);
         if(InpSignalBreakout)
            AddSignal(i, -SIG_BREAKOUT);
         return;
        }
      bool fresh  = (g_l[i - 1] > z.top);   // il prezzo arriva da fuori zona
      bool touch  = (g_l[i] <= z.top);
      bool reject = (g_c[i] > z.top) && (g_c[i] > g_o[i] || (bodyBot - g_l[i]) >= body);
      if(fresh && touch)
        {
         z.touches++;
         if(reject && InpSignalBounce && z.touches <= InpMaxBounces)
            AddSignal(i, SIG_BOUNCE);
        }
     }
   else             // resistenza
     {
      if(g_c[i] > z.top)
        {
         KillZone(z, i, true);
         if(InpSignalBreakout)
            AddSignal(i, SIG_BREAKOUT);
         return;
        }
      bool fresh  = (g_h[i - 1] < z.bottom);
      bool touch  = (g_h[i] >= z.bottom);
      bool reject = (g_c[i] < z.bottom) && (g_c[i] < g_o[i] || (g_h[i] - bodyTop) >= body);
      if(fresh && touch)
        {
         z.touches++;
         if(reject && InpSignalBounce && z.touches <= InpMaxBounces)
            AddSignal(i, -SIG_BOUNCE);
        }
     }
  }

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
int RangeBars() { return(MathMax(2, InpRangeBars)); }

//+------------------------------------------------------------------+
bool HourAllowed(const datetime t)
  {
   if(InpStartHour == InpEndHour)
      return(true);
   MqlDateTime dt;
   TimeToStruct(t, dt);
   if(InpStartHour < InpEndHour)
      return(dt.hour >= InpStartHour && dt.hour < InpEndHour);
   return(dt.hour >= InpStartHour || dt.hour < InpEndHour);   // fascia a cavallo della mezzanotte
  }

int SwingBars() { return(MathMax(1, InpSwingBars)); }

//+------------------------------------------------------------------+
void ClampZone(double &top, double &bot, const double atr, const int side)
  {
   double minH = InpZoneMinATR * atr;
   double maxH = InpZoneMaxATR * atr;
   double h = top - bot;
   if(side > 0)   // supporto: ancorato al minimo
     {
      if(h < minH)
         top = bot + minH;
      if(h > maxH)
         top = bot + maxH;
     }
   else           // resistenza: ancorata al massimo
     {
      if(h < minH)
         bot = top - minH;
      if(h > maxH)
         bot = top - maxH;
     }
  }

//+------------------------------------------------------------------+
void TryAddSR(const int kind, const int side, const double top, const double bot,
              const int startBar, const int activeFrom, const int i)
  {
//--- niente doppioni: se si sovrappone a una zona attiva dello stesso lato, si scarta
   int aliveCount = 0, oldest = -1;
   for(int k = 0; k < g_zoneCount; k++)
     {
      if(!g_zones[k].alive || g_zones[k].kind == ZK_REACTION)
         continue;
      if(g_zones[k].side == side && g_zones[k].bottom <= top && bot <= g_zones[k].top)
         return;
      aliveCount++;
      if(oldest < 0)
         oldest = k;
     }
   if(aliveCount >= InpMaxZones && oldest >= 0)
      KillZone(g_zones[oldest], i, false);

   Zone z;
   z.kind       = kind;
   z.side       = side;
   z.trend      = 0;
   z.top        = top;
   z.bottom     = bot;
   z.startBar   = startBar;
   z.activeFrom = activeFrom;
   z.endBar     = -1;
   z.touches    = 0;
   z.alive      = true;
   z.broken     = false;
   AddZone(z);
  }

//+------------------------------------------------------------------+
void AddZone(const Zone &z)
  {
   ArrayResize(g_zones, g_zoneCount + 1, 256);
   g_zones[g_zoneCount] = z;
   g_zoneCount++;
  }

//+------------------------------------------------------------------+
void KillZone(Zone &z, const int i, const bool broken)
  {
   z.alive  = false;
   z.endBar = i;
   z.broken = broken;
  }

//+------------------------------------------------------------------+
string SignalName(const int code)
  {
   string dir = (code > 0) ? "BUY" : "SELL";
   switch(MathAbs(code))
     {
      case SIG_REACTION:
         return(dir + " breakout zona di reazione");
      case SIG_BREAKOUT:
         return(dir + " breakout zona forte/rifiuto");
      case SIG_BOUNCE:
         return(dir + " rimbalzo su zona");
     }
   return(dir);
  }

//+------------------------------------------------------------------+
string SignalTag(const int code)
  {
   switch(MathAbs(code))
     {
      case SIG_REACTION:
         return("RZ");
      case SIG_BREAKOUT:
         return("BO");
      case SIG_BOUNCE:
         return("RB");
     }
   return("");
  }

//+------------------------------------------------------------------+
void AddSignal(const int i, const int code)
  {
   if(!HourAllowed(g_t[i]) || i - g_lastSignalBar < InpCooldownBars)
      return;
   g_lastSignalBar = i;

   double off = 0.4 * g_atr[i];
   double price;
   if(code > 0)
     {
      price = g_l[i] - off;
      BuyBuf[i] = price;
     }
   else
     {
      price = g_h[i] + off;
      SellBuf[i] = price;
     }
   CodeBuf[i] = code;

   if(!InpShowSignalText)
      return;
   string name = PREFIX + "S" + IntegerToString(i) + "_" + IntegerToString(code);
   double tp   = (code > 0) ? price - off : price + off;
   if(ObjectCreate(0, name, OBJ_TEXT, 0, g_t[i], tp))
     {
      ObjectSetString(0, name, OBJPROP_TEXT, SignalTag(code));
      ObjectSetInteger(0, name, OBJPROP_COLOR, InpColText);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 7);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, (code > 0) ? ANCHOR_UPPER : ANCHOR_LOWER);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetString(0, name, OBJPROP_TOOLTIP, SignalName(code));
     }
  }

//+------------------------------------------------------------------+
color ZoneColor(const Zone &z)
  {
   if(!z.alive)
      return(InpColDead);
   if(z.kind == ZK_REACTION)
      return(InpColReaction);
   if(z.kind == ZK_STRONG)
      return(z.side > 0 ? InpColStrongSup : InpColStrongRes);
   return(z.side > 0 ? InpColRejSup : InpColRejRes);
  }

//+------------------------------------------------------------------+
string ZoneTooltip(const Zone &z)
  {
   string kind = (z.kind == ZK_REACTION) ? "Zona di reazione" :
                 (z.kind == ZK_STRONG)   ? "Zona forte" : "Zona di rifiuto";
   string side = (z.side > 0) ? " (supporto)" : (z.side < 0) ? " (resistenza)" : "";
   string state = z.alive ? "attiva" : (z.broken ? "rotta" : "scaduta");
   return(StringFormat("%s%s | %s | %s - %s | tocchi: %d",
                       kind, side, state,
                       DoubleToString(z.bottom, _Digits),
                       DoubleToString(z.top, _Digits),
                       z.touches));
  }

//+------------------------------------------------------------------+
void DrawZones(const int rates_total)
  {
   datetime future = g_t[rates_total - 1] + PeriodSeconds() * InpExtendBars;
   for(int k = 0; k < g_zoneCount; k++)
     {
      if(!g_zones[k].alive && !InpShowDeadZones)
         continue;
      datetime t1 = g_t[g_zones[k].startBar];
      datetime t2 = g_zones[k].alive ? future : g_t[g_zones[k].endBar];
      string name = PREFIX + "Z" + IntegerToString(k);
      if(!ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, g_zones[k].top, t2, g_zones[k].bottom))
         continue;
      ObjectSetInteger(0, name, OBJPROP_COLOR, ZoneColor(g_zones[k]));
      ObjectSetInteger(0, name, OBJPROP_FILL, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetString(0, name, OBJPROP_TOOLTIP, ZoneTooltip(g_zones[k]));
     }
  }

//+------------------------------------------------------------------+
void CheckAlert(const int rates_total)
  {
   int bar = rates_total - 2;
   if(bar < 0 || CodeBuf[bar] == 0.0)
      return;
   if(g_t[bar] == g_lastAlertTime)
      return;
   g_lastAlertTime = g_t[bar];
   if(g_firstRun)
      return;   // niente avvisi al caricamento del grafico

   string tf  = StringSubstr(EnumToString((ENUM_TIMEFRAMES)_Period), 7);
   string msg = StringFormat("TRS Zones %s %s: %s", _Symbol, tf, SignalName((int)CodeBuf[bar]));
   if(InpAlertPopup)
      Alert(msg);
   if(InpAlertPush)
      SendNotification(msg);
  }
//+------------------------------------------------------------------+
