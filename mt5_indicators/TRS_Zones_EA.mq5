//+------------------------------------------------------------------+
//|                                                TRS_Zones_EA.mq5  |
//|  EA di TEST per il metodo TRS.                                   |
//|  Usa le stesse regole dell'indicatore TRS_Zones (zone di         |
//|  reazione, zone forti, rifiuti, rimbalzi, breakout) e apre i     |
//|  trade con stop e target definiti, per misurare nello Strategy   |
//|  Tester quale setup funziona davvero.                            |
//|                                                                  |
//|  A fine test stampa nel Diario le statistiche per setup          |
//|  (RZ / BO / RB).                                                 |
//+------------------------------------------------------------------+
#property copyright   "bot-telegram"
#property version     "1.00"
#property description "EA di test del metodo TRS: entra sui segnali RZ/BO/RB con stop e target definiti"

#include <Trade/Trade.mqh>

#define SIG_REACTION 1   // breakout di una zona di reazione
#define SIG_BREAKOUT 2   // breakout di una zona forte / di rifiuto
#define SIG_BOUNCE   3   // rimbalzo su una zona forte / di rifiuto

enum ENUM_ZONE_KIND
  {
   ZK_REACTION  = 0,
   ZK_STRONG    = 1,
   ZK_REJECTION = 2
  };

//--- input
input group "=== Setup da operare ==="
input bool   InpTradeRZ         = true;  // Opera breakout zone di reazione (RZ)
input bool   InpTradeBO         = true;  // Opera breakout zone forti/rifiuto (BO)
input bool   InpTradeRB         = true;  // Opera rimbalzi su zone (RB)

input group "=== Gestione del rischio ==="
input double InpRiskPercent     = 0.5;   // Rischio per trade (% del saldo)
input double InpFixedLots       = 0.0;   // Lotti fissi (se > 0 ignora il rischio %)
input double InpRR              = 1.5;   // Take profit (multiplo dello stop = R)
input double InpSLBufferATR     = 0.10;  // Margine dello stop oltre la zona (x ATR)
input double InpMinSLATR        = 0.30;  // Stop minimo (x ATR)
input double InpMaxSLATR        = 2.00;  // Stop massimo (x ATR): oltre, trade saltato

input group "=== Filtri operativi ==="
input int    InpStartHour       = 8;     // Ora inizio operativita' (ora server)
input int    InpEndHour         = 20;    // Ora fine operativita' (ora server)
input int    InpMaxTradesDay    = 3;     // Max trade al giorno
input int    InpMaxLossesDay    = 2;     // Stop giornata dopo N perdite
input int    InpMaxSpreadPts    = 0;     // Spread massimo in punti (0 = nessun limite)
input bool   InpOnePosition     = true;  // Una sola posizione alla volta
input ulong  InpMagic           = 260101; // Magic number

input group "=== Regole zone (come l'indicatore) ==="
input int    InpWarmupBars      = 500;   // Candele di storico per inizializzare le zone
input int    InpATRPeriod       = 14;    // Periodo ATR
input int    InpRangeBars       = 3;     // Zona reazione: candele del range
input double InpRangeMaxATR     = 1.0;   // Zona reazione: altezza max (x ATR)
input double InpRangeMinATR     = 0.2;   // Zona reazione: altezza min (x ATR)
input int    InpImpulseBars     = 5;     // Zona reazione: candele del movimento prima
input double InpImpulseATR      = 2.5;   // Zona reazione: movimento minimo (x ATR)
input int    InpReactionExpiry  = 30;    // Zona reazione: scadenza (candele)
input bool   InpBreakOnClose    = true;  // Zona reazione: breakout solo su chiusura
input bool   InpOnlyWithTrend   = true;  // Zona reazione: solo nella direzione del movimento
input bool   InpUseStrong       = true;  // Usa zone forti
input int    InpSwingBars       = 5;     // Zona forte: candele sx/dx dello swing
input double InpStrongATR       = 2.5;   // Zona forte: inversione minima (x ATR)
input bool   InpUseRejection    = true;  // Usa zone di rifiuto
input double InpWickBodyRatio   = 3.0;   // Rifiuto: ombra >= N volte il corpo
input double InpWickMinATR      = 1.2;   // Rifiuto: ombra minima (x ATR)
input int    InpMinRetestBars   = 3;     // Candele minime prima del retest
input int    InpMaxBounces      = 1;     // Max rimbalzi per zona
input int    InpZoneExpiry      = 300;   // Vita di una zona (candele)
input int    InpMaxZones        = 30;    // Max zone forti/rifiuto attive
input double InpZoneMinATR      = 0.10;  // Spessore minimo zona (x ATR)
input double InpZoneMaxATR      = 0.60;  // Spessore massimo zona (x ATR)
input int    InpCooldownBars    = 8;     // Candele minime tra due segnali

//--- strutture e variabili globali
struct Zone
  {
   int               kind;
   int               side;       // +1 supporto, -1 resistenza, 0 range di reazione
   int               trend;
   double            top;
   double            bottom;
   int               startBar;
   int               activeFrom;
   int               endBar;
   int               touches;
   bool              alive;
   bool              broken;
  };

CTrade   trade;
Zone     g_zones[];
int      g_zoneCount       = 0;
int      g_lastReactionEnd = -1;
int      g_lastSignalBar   = -1000000;
int      g_atrHandle       = INVALID_HANDLE;
bool     g_ready           = false;
datetime g_lastBar         = 0;

//--- storico delle candele chiuse (indice 0 = la piu' vecchia)
double   g_o[], g_h[], g_l[], g_c[], g_atr[];
datetime g_t[];
int      g_n = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   g_atrHandle = iATR(_Symbol, _Period, InpATRPeriod);
   if(g_atrHandle == INVALID_HANDLE)
     {
      Print("TRS EA: impossibile creare l'ATR, errore ", GetLastError());
      return(INIT_FAILED);
     }
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(30);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   PrintStats();
   if(g_atrHandle != INVALID_HANDLE)
      IndicatorRelease(g_atrHandle);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   datetime t0 = iTime(_Symbol, _Period, 0);
   if(t0 == 0 || t0 == g_lastBar)
      return;

   if(!g_ready)
     {
      if(WarmUp())
         g_lastBar = t0;
      return;
     }

//--- tutte le candele chiuse arrivate dall'ultimo aggiornamento
   MqlRates r[];
   double   a[];
   ArraySetAsSeries(r, false);
   ArraySetAsSeries(a, false);
   datetime from = g_t[g_n - 1] + 1;
   datetime to   = t0 - 1;
   int nr = CopyRates(_Symbol, _Period, from, to, r);
   if(nr <= 0)
     {
      g_lastBar = t0;
      return;
     }
   int na = CopyBuffer(g_atrHandle, 0, from, to, a);
   if(na != nr)
      return;   // ATR non ancora pronto: riprova al prossimo tick

   for(int k = 0; k < nr; k++)
     {
      AppendBar(r[k], a[k]);
      ProcessBar(g_n - 1, k == nr - 1);   // si opera solo sull'ultima candela chiusa
     }
   CompactZones();
   g_lastBar = t0;
  }

//+------------------------------------------------------------------+
//| Carica lo storico iniziale e costruisce le zone senza operare    |
//+------------------------------------------------------------------+
bool WarmUp()
  {
   int avail = Bars(_Symbol, _Period) - 2;
   int want  = MathMin(InpWarmupBars, avail);
   if(want < MinStartIndex() + 20)
      return(false);
   if(BarsCalculated(g_atrHandle) < want + 1)
      return(false);

   MqlRates r[];
   double   a[];
   ArraySetAsSeries(r, false);
   ArraySetAsSeries(a, false);
   int nr = CopyRates(_Symbol, _Period, 1, want, r);
   int na = CopyBuffer(g_atrHandle, 0, 1, want, a);
   if(nr <= 0 || na != nr)
      return(false);

   g_n = 0;
   for(int k = 0; k < nr; k++)
      AppendBar(r[k], a[k]);
   for(int i = MinStartIndex(); i < g_n; i++)
      ProcessBar(i, false);
   CompactZones();
   g_ready = true;
   PrintFormat("TRS EA: inizializzato con %d candele, %d zone attive", g_n, g_zoneCount);
   return(true);
  }

//+------------------------------------------------------------------+
void AppendBar(const MqlRates &r, const double atr)
  {
   int n = g_n + 1;
   ArrayResize(g_o,   n, 10000);
   ArrayResize(g_h,   n, 10000);
   ArrayResize(g_l,   n, 10000);
   ArrayResize(g_c,   n, 10000);
   ArrayResize(g_atr, n, 10000);
   ArrayResize(g_t,   n, 10000);
   g_o[g_n]   = r.open;
   g_h[g_n]   = r.high;
   g_l[g_n]   = r.low;
   g_c[g_n]   = r.close;
   g_atr[g_n] = atr;
   g_t[g_n]   = r.time;
   g_n = n;
  }

//+------------------------------------------------------------------+
int RangeBars()     { return(MathMax(2, InpRangeBars)); }
int SwingBars()     { return(MathMax(1, InpSwingBars)); }
int MinStartIndex() { return(InpATRPeriod + InpImpulseBars + RangeBars() + 2 * SwingBars() + 5); }

//+------------------------------------------------------------------+
//| Elabora una candela chiusa: prima le zone esistenti, poi le nuove|
//+------------------------------------------------------------------+
void ProcessBar(const int i, const bool live)
  {
   if(i < MinStartIndex())
      return;
   if(g_atr[i] <= 0.0 || g_atr[i] == EMPTY_VALUE)
      return;

   for(int k = 0; k < g_zoneCount; k++)
     {
      if(!g_zones[k].alive || i < g_zones[k].activeFrom)
         continue;
      if(g_zones[k].kind == ZK_REACTION)
         ProcessReaction(g_zones[k], i, live);
      else
         ProcessSR(g_zones[k], i, live);
     }

   DetectReaction(i);
   if(InpUseStrong)
      DetectStrong(i);
   if(InpUseRejection)
      DetectRejection(i);
  }

//+------------------------------------------------------------------+
//| 1) Zona di reazione                                              |
//+------------------------------------------------------------------+
void DetectReaction(const int i)
  {
   for(int k = 0; k < g_zoneCount; k++)
      if(g_zones[k].alive && g_zones[k].kind == ZK_REACTION)
         return;

   int w0 = i - RangeBars() + 1;
   if(w0 <= g_lastReactionEnd)
      return;

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
void ProcessReaction(Zone &z, const int i, const bool live)
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
   OnSignal(i, dir * SIG_REACTION, z, live);
  }

//+------------------------------------------------------------------+
//| 2) Zona forte                                                    |
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
//| 3) Zona di rifiuto                                               |
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
//| 4) Breakout / rimbalzo su zone forti e di rifiuto                |
//+------------------------------------------------------------------+
void ProcessSR(Zone &z, const int i, const bool live)
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
         OnSignal(i, -SIG_BREAKOUT, z, live);
         return;
        }
      bool fresh  = (g_l[i - 1] > z.top);
      bool touch  = (g_l[i] <= z.top);
      bool reject = (g_c[i] > z.top) && (g_c[i] > g_o[i] || (bodyBot - g_l[i]) >= body);
      if(fresh && touch)
        {
         z.touches++;
         if(reject && z.touches <= InpMaxBounces)
            OnSignal(i, SIG_BOUNCE, z, live);
        }
     }
   else             // resistenza
     {
      if(g_c[i] > z.top)
        {
         KillZone(z, i, true);
         OnSignal(i, SIG_BREAKOUT, z, live);
         return;
        }
      bool fresh  = (g_h[i - 1] < z.bottom);
      bool touch  = (g_h[i] >= z.bottom);
      bool reject = (g_c[i] < z.bottom) && (g_c[i] < g_o[i] || (g_h[i] - bodyTop) >= body);
      if(fresh && touch)
        {
         z.touches++;
         if(reject && z.touches <= InpMaxBounces)
            OnSignal(i, -SIG_BOUNCE, z, live);
        }
     }
  }

//+------------------------------------------------------------------+
//| Helpers zone                                                     |
//+------------------------------------------------------------------+
void ClampZone(double &top, double &bot, const double atr, const int side)
  {
   double minH = InpZoneMinATR * atr;
   double maxH = InpZoneMaxATR * atr;
   double h = top - bot;
   if(side > 0)
     {
      if(h < minH)
         top = bot + minH;
      if(h > maxH)
         top = bot + maxH;
     }
   else
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
//| Elimina le zone morte (l'EA non deve disegnarle)                 |
//+------------------------------------------------------------------+
void CompactZones()
  {
   int j = 0;
   for(int k = 0; k < g_zoneCount; k++)
     {
      if(!g_zones[k].alive)
         continue;
      if(j != k)
         g_zones[j] = g_zones[k];
      j++;
     }
   g_zoneCount = j;
   ArrayResize(g_zones, j, 256);
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
//| Trading                                                          |
//+------------------------------------------------------------------+
void OnSignal(const int i, const int code, const Zone &z, const bool live)
  {
   int type = MathAbs(code);
   if(type == SIG_REACTION && !InpTradeRZ)
      return;
   if(type == SIG_BREAKOUT && !InpTradeBO)
      return;
   if(type == SIG_BOUNCE   && !InpTradeRB)
      return;
//--- stessi filtri dell'indicatore: fascia oraria e distanza minima tra segnali
   if(!TimeAllowed(g_t[i]) || i - g_lastSignalBar < InpCooldownBars)
      return;
   g_lastSignalBar = i;
   if(!live)
      return;
   if(InpOnePosition && HasPosition())
      return;
   if(DayLimitsHit())
      return;
   if(InpMaxSpreadPts > 0 && SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPts)
      return;

   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk))
      return;

   bool   buy   = (code > 0);
   double atr   = g_atr[g_n - 1];
   double buf   = InpSLBufferATR * atr;
   double entry = buy ? tk.ask : tk.bid;
   double sl    = buy ? z.bottom - buf : z.top + buf;
   double dist  = buy ? entry - sl : sl - entry;

   if(dist <= 0.0)
      return;   // il prezzo e' gia' oltre lo stop
   if(dist < InpMinSLATR * atr)
     {
      dist = InpMinSLATR * atr;
      sl   = buy ? entry - dist : entry + dist;
     }
   if(dist > InpMaxSLATR * atr)
      return;   // stop troppo largo: trade saltato

   double stopsLevel = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(dist <= stopsLevel)
      return;

   double tp = buy ? entry + InpRR * dist : entry - InpRR * dist;
   sl = NormalizeDouble(sl, _Digits);
   tp = NormalizeDouble(tp, _Digits);

   double lots = CalcLots(buy, entry, sl);
   if(lots <= 0.0)
      return;

   string cmt = "TRS " + SignalTag(code);
   bool ok = buy ? trade.Buy(lots, _Symbol, 0.0, sl, tp, cmt)
             : trade.Sell(lots, _Symbol, 0.0, sl, tp, cmt);
   if(!ok)
      PrintFormat("TRS EA: ordine %s fallito, retcode %d", cmt, trade.ResultRetcode());
  }

//+------------------------------------------------------------------+
double CalcLots(const bool buy, const double entry, const double sl)
  {
   double lots;
   if(InpFixedLots > 0.0)
      lots = InpFixedLots;
   else
     {
      //--- perdita reale di 1 lotto dall'ingresso allo stop, calcolata da MT5
      double risk = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0;
      double pnl  = 0.0;
      if(!OrderCalcProfit(buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, _Symbol, 1.0, entry, sl, pnl))
         return(0.0);
      double lossPerLot = -pnl;
      if(lossPerLot <= 0.0)
         return(0.0);
      lots = risk / lossPerLot;
     }

   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0.0)
      step = 0.01;
   lots = MathFloor(lots / step) * step;
   if(lots < vmin)
     {
      Print("TRS EA: rischio troppo basso per il lotto minimo, trade saltato");
      return(0.0);
     }
   lots = MathMin(lots, vmax);
   return(NormalizeDouble(lots, 2));
  }

//+------------------------------------------------------------------+
bool TimeAllowed(const datetime t)
  {
   if(InpStartHour == InpEndHour)
      return(true);
   MqlDateTime dt;
   TimeToStruct(t, dt);
   if(InpStartHour < InpEndHour)
      return(dt.hour >= InpStartHour && dt.hour < InpEndHour);
   return(dt.hour >= InpStartHour || dt.hour < InpEndHour);   // fascia a cavallo della mezzanotte
  }

//+------------------------------------------------------------------+
bool HasPosition()
  {
   for(int k = PositionsTotal() - 1; k >= 0; k--)
     {
      ulong ticket = PositionGetTicket(k);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return(true);
     }
   return(false);
  }

//+------------------------------------------------------------------+
bool DayLimitsHit()
  {
   datetime dayStart = iTime(_Symbol, PERIOD_D1, 0);
   if(dayStart == 0 || !HistorySelect(dayStart, TimeCurrent() + 60))
      return(false);
   int entries = 0, losses = 0;
   int total = HistoryDealsTotal();
   for(int k = 0; k < total; k++)
     {
      ulong d = HistoryDealGetTicket(k);
      if(d == 0)
         continue;
      if(HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol ||
         (ulong)HistoryDealGetInteger(d, DEAL_MAGIC) != InpMagic)
         continue;
      long entry = HistoryDealGetInteger(d, DEAL_ENTRY);
      if(entry == DEAL_ENTRY_IN)
         entries++;
      else
         if(entry == DEAL_ENTRY_OUT)
           {
            double p = HistoryDealGetDouble(d, DEAL_PROFIT) +
                       HistoryDealGetDouble(d, DEAL_SWAP) +
                       HistoryDealGetDouble(d, DEAL_COMMISSION);
            if(p < 0.0)
               losses++;
           }
     }
   return(entries >= InpMaxTradesDay || losses >= InpMaxLossesDay);
  }

//+------------------------------------------------------------------+
//| Statistiche per setup, stampate nel Diario a fine test           |
//+------------------------------------------------------------------+
int TagIndex(const string cmt)
  {
   if(StringFind(cmt, "RZ") >= 0)
      return(0);
   if(StringFind(cmt, "BO") >= 0)
      return(1);
   if(StringFind(cmt, "RB") >= 0)
      return(2);
   return(-1);
  }

//+------------------------------------------------------------------+
void PrintStats()
  {
   if(!HistorySelect(0, TimeCurrent() + 60))
      return;
   int total = HistoryDealsTotal();

//--- 1° giro: posizione -> setup (dal commento del deal di ingresso)
   ulong posIds[];
   int   posTag[];
   int   np = 0;
   for(int k = 0; k < total; k++)
     {
      ulong d = HistoryDealGetTicket(k);
      if(d == 0 || (ulong)HistoryDealGetInteger(d, DEAL_MAGIC) != InpMagic)
         continue;
      if(HistoryDealGetInteger(d, DEAL_ENTRY) != DEAL_ENTRY_IN)
         continue;
      ArrayResize(posIds, np + 1, 1000);
      ArrayResize(posTag, np + 1, 1000);
      posIds[np] = (ulong)HistoryDealGetInteger(d, DEAL_POSITION_ID);
      posTag[np] = TagIndex(HistoryDealGetString(d, DEAL_COMMENT));
      np++;
     }

//--- 2° giro: risultati delle chiusure
   string names[3] = {"RZ breakout zona reazione", "BO breakout zona forte  ", "RB rimbalzo su zona     "};
   int    cnt[3]   = {0, 0, 0};
   int    win[3]   = {0, 0, 0};
   double gp[3]    = {0.0, 0.0, 0.0};
   double gl[3]    = {0.0, 0.0, 0.0};
   for(int k = 0; k < total; k++)
     {
      ulong d = HistoryDealGetTicket(k);
      if(d == 0 || (ulong)HistoryDealGetInteger(d, DEAL_MAGIC) != InpMagic)
         continue;
      if(HistoryDealGetInteger(d, DEAL_ENTRY) != DEAL_ENTRY_OUT)
         continue;
      ulong pid = (ulong)HistoryDealGetInteger(d, DEAL_POSITION_ID);
      int tag = -1;
      for(int j = 0; j < np; j++)
         if(posIds[j] == pid)
           {
            tag = posTag[j];
            break;
           }
      if(tag < 0)
         continue;
      double p = HistoryDealGetDouble(d, DEAL_PROFIT) +
                 HistoryDealGetDouble(d, DEAL_SWAP) +
                 HistoryDealGetDouble(d, DEAL_COMMISSION);
      cnt[tag]++;
      if(p > 0.0)
        {
         win[tag]++;
         gp[tag] += p;
        }
      else
         gl[tag] += -p;
     }

   Print("================ TRS EA - risultati per setup ================");
   for(int t = 0; t < 3; t++)
     {
      if(cnt[t] == 0)
        {
         PrintFormat("%s | nessun trade", names[t]);
         continue;
        }
      double pf = (gl[t] > 0.0) ? gp[t] / gl[t] : 0.0;
      PrintFormat("%s | trade: %d | vinti: %.1f%% | netto: %.2f | profit factor: %.2f | media/trade: %.2f",
                  names[t], cnt[t], 100.0 * win[t] / cnt[t], gp[t] - gl[t], pf,
                  (gp[t] - gl[t]) / cnt[t]);
     }
   Print("==============================================================");
  }
//+------------------------------------------------------------------+
