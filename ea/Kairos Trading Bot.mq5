//+------------------------------------------------------------------+
//|                                          Kairos Trading Bot.mq5  |
//|  KAIROS TRADING BOT by YardFX - versione definitiva, XAUUSD M1   |
//|  - MATTINA (9-11 italiane) -> Fibonacci: ritracciamento 0.5 /    |
//|    0.618 dell'ultimo impulso, ingresso dopo pin bar, SL a 1.1,   |
//|    TP RR 1:3 (versione C)                                        |
//|  - POMERIGGIO (12-19 italiane) -> RSI(28): entra al rientro da   |
//|    30/70, esce quando l'RSI torna al livello di uscita, SL ATR   |
//|  Ogni strategia ha il suo magic number: le posizioni restano     |
//|  separate e ognuna gestisce solo le sue                          |
//|  Dashboard sul grafico con lo stato di entrambe le strategie     |
//+------------------------------------------------------------------+
#property copyright "YardFX"
#property version   "2.00"
#property description "Kairos Trading Bot by YardFX - Fibonacci (mattina) + RSI (pomeriggio) su XAUUSD M1"

#include <Trade\Trade.mqh>

#define PNL     "KTB_"   // prefisso degli oggetti della dashboard
#define PNL_W   340      // larghezza della dashboard

enum EntryMode
  {
   ENTRY_LIMIT      = 0, // Ordini limit sui livelli
   ENTRY_MARKET     = 1, // Mercato al tocco del livello
   ENTRY_PINBAR     = 2, // Mercato dopo pin bar nella zona
   ENTRY_ENGULF     = 3, // Mercato dopo engulfing nella zona
   ENTRY_PIN_OR_ENG = 4  // Mercato dopo pin bar o engulfing
  };

enum TPMode
  {
   TP_RR1    = 0, // Rischio/rendimento 1:1
   TP_RR15   = 1, // Rischio/rendimento 1:1.5
   TP_RR2    = 2, // Rischio/rendimento 1:2
   TP_RR3    = 3, // Rischio/rendimento 1:3
   TP_SWING  = 4, // Livello 0 (torna allo swing high/low)
   TP_EXT272 = 5, // Estensione -0.272
   TP_EXT618 = 6, // Estensione -0.618
   TP_ATR    = 7  // ATR M1 x InpFbTPATRMult
  };

enum TrendFilter
  {
   TREND_NONE   = 0, // Nessuno: basta la direzione dell'impulso
   TREND_EMA    = 1, // EMA in salita (buy) / in discesa (sell)
   TREND_STRUCT = 2  // Struttura: massimi e minimi crescenti (buy) / decrescenti (sell)
  };

//--- parametri ------------------------------------------------------
input group "=== FIBONACCI (mattina) ==="
input bool        InpFbOn         = true;          // Strategia Fibonacci attiva
input double      InpFbLots       = 0.01;          // Lotti
input long        InpFbMagic      = 61800;         // Magic number
input int         InpFbHourStart  = 1000;          // Entra dalle (HHMM, ora FPG fissa)
input int         InpFbHourEnd    = 1200;          // Entra fino alle (HHMM, ora FPG fissa)
input EntryMode   InpFbEntryMode  = ENTRY_PINBAR;  // Tipo di ingresso
input bool        InpFbLvl382     = false;         // Entra a 0.382
input bool        InpFbLvl500     = true;          // Entra a 0.5
input bool        InpFbLvl618     = true;          // Entra a 0.618
input double      InpFbTouchTol   = 0.06;          // Mercato: entra solo entro questa frazione dello swing oltre il livello
input double      InpFbPinWick    = 0.6;           // Pin bar: coda almeno questa frazione della candela
input double      InpFbSLFib      = 1.1;           // SL sul livello di Fibonacci (1.1 = oltre lo swing)
input TPMode      InpFbTPMode     = TP_RR3;        // Take profit
input double      InpFbTPATRMult  = 2.0;           // TP ATR: multiplo dell'ATR M1
input int         InpFbSwingDepth = 3;             // Candele a sinistra e a destra per confermare uno swing
input int         InpFbLookback   = 300;           // Candele M1 analizzate
input double      InpFbMinLegATR  = 4.0;           // Impulso minimo = ATR M1 x questo
input int         InpFbMinLegPts  = 0;             // Impulso minimo in punti (0 = off)
input int         InpFbMaxLegBars = 60;            // Ignora l'impulso dopo X candele dalla fine
input TrendFilter InpFbTrend      = TREND_EMA;     // Filtro trend
input int         InpFbEMAPeriod  = 50;            // Periodo EMA del filtro trend

input group "=== RSI (pomeriggio) ==="
input bool        InpRsOn         = true;          // Strategia Kairos attiva
input double      InpRsLots       = 0.01;          // Lotti
input long        InpRsMagic      = 54001;         // Magic number
input int         InpRsPeriod     = 28;            // Periodo RSI
input double      InpRsLow        = 30;            // BUY quando l'RSI rientra sopra questo livello
input double      InpRsHigh       = 70;            // SELL quando l'RSI rientra sotto questo livello
input double      InpRsExit       = 65;            // TP BUY: chiude quando l'RSI sale a questo livello
input double      InpRsExitSell   = 50;            // TP SELL: chiude quando l'RSI scende a questo livello
input bool        InpRsEntryTouch = false;         // Entrata al tocco di 30/70 (false = al rientro)
input ENUM_TIMEFRAMES InpRsATRTF  = PERIOD_M1;     // Time frame ATR
input int         InpRsATRPeriod  = 14;            // Periodo ATR
input double      InpRsSLATR      = 2.5;           // SL = ATR x questo
input bool        InpRsBreakEven  = false;         // Break-even quando l'RSI tocca il livello sotto
input double      InpRsBERSI      = 50;            // Livello RSI del break-even
input int         InpRsBELockPts  = 0;             // Punti bloccati oltre l'entrata
input bool        InpRsOneAtTime  = true;          // Una operazione Kairos alla volta
input double      InpRsConfirmPts = 0;             // Filtro rumore: il rientro deve chiudere oltre 30/70 di almeno X punti (0 = off)
input int         InpRsConfirmBars= 1;             // Filtro rumore: candele M1 di fila oltre la soglia prima di entrare (1 = off)
input int         InpRsSLPauseMin = 0;             // Filtro rumore: dopo uno SL, minuti senza nuovi trade nella stessa direzione (0 = off)
input bool        InpRsWeekend    = true;          // Venerdi': niente trade nuovi la sera e chiusura prima del weekend (anche il Fibonacci)
input int         InpRsFriNoNew   = 2100;          // Venerdi': niente trade nuovi dalle (HHMM)
input int         InpRsFriClose   = 2245;          // Venerdi': chiude tutto alle (HHMM)
input bool        InpRsUseHours   = true;          // Entra solo nella fascia oraria
input int         InpRsHourStart  = 1300;          // Dalle (HHMM, ora MT5 = italiana + 1)
input int         InpRsHourEnd    = 2000;          // Alle (HHMM)
input bool        InpRsUseATRFilter = true;        // Entra solo se l'ATR e' tra il minimo e il massimo
input double      InpRsMinATRPct  = 0.05;          // ATR minimo (% del prezzo)
input double      InpRsMaxATRPct  = 0.13;          // ATR massimo (% del prezzo)

input group "=== Dashboard ==="
input bool        InpPanel        = true;          // Mostra la dashboard sul grafico
input int         InpItaOffset    = -1;            // Ore di differenza ora FPG - ora italiana (-1 = automatico, segue l'ora legale)
input int         InpPanelX       = 12;            // Posizione dashboard: distanza dal bordo sinistro
input int         InpPanelY       = 28;            // Posizione dashboard: distanza dall'alto

input group "=== Ottimizzazione ==="
input int         InpMinTrades    = 30;            // Custom max: scarta i passaggi con meno trade

//--- comune ---------------------------------------------------------
bool     g_quiet = false;   // in ottimizzazione: niente log
bool     g_draw  = false;   // pannello e Fibonacci sul grafico

void Log(string s)
  {
   if(!g_quiet) Print(s);
  }

int HHMM(datetime t)
  {
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return dt.hour * 100 + dt.min;
  }

bool IsFriday(datetime t)
  {
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return dt.day_of_week == 5;
  }

double Norm(double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0)
      return NormalizeDouble(p, _Digits);
   return NormalizeDouble(MathRound(p / ts) * ts, _Digits);
  }

double NormLots(double v)
  {
   double mn = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double mx = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double st = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(st <= 0) st = 0.01;
   v = MathFloor(v / st + 1e-9) * st;
   return NormalizeDouble(MathMax(mn, MathMin(mx, v)), 2);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   if(!InpFbOn && !InpRsOn)
     {
      Print("Nessuna strategia attiva");
      return INIT_PARAMETERS_INCORRECT;
     }
   g_quiet = (bool)MQLInfoInteger(MQL_OPTIMIZATION);
   g_draw  = !(bool)MQLInfoInteger(MQL_TESTER) || (bool)MQLInfoInteger(MQL_VISUAL_MODE);
   if(g_draw && InpPanel)
     {
      ChartSetInteger(0, CHART_FOREGROUND, false);   // dashboard e disegni davanti alle candele
      Comment("");
     }

   if(InpFbOn && FbInit() != INIT_SUCCEEDED)
      return INIT_PARAMETERS_INCORRECT;
   if(InpRsOn && RsInit() != INIT_SUCCEEDED)
      return INIT_FAILED;

   if(g_draw && InpPanel)
     {
      EventSetTimer(1);   // dashboard aggiornata ogni secondo anche senza tick (mercato fermo)
      ShowPanel(true);
     }

   Log(StringFormat("Kairos Trading Bot su %s: Fibonacci %s (%04d-%04d), RSI %s (%s)", _Symbol,
                    InpFbOn ? "ON" : "OFF", InpFbHourStart, InpFbHourEnd,
                    InpRsOn ? "ON" : "OFF", InpRsUseHours ? StringFormat("%04d-%04d", InpRsHourStart, InpRsHourEnd) : "sempre"));
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   FbDeinit();
   RsDeinit();
   ObjectsDeleteAll(0, PNL);
   Comment("");
  }

void OnTick()
  {
   if(InpFbOn) FbOnTick();
   if(InpRsOn) RsOnTick();
   ShowPanel(false);
  }

void OnTimer()
  {
   ShowPanel(true);
  }

// la dashboard e' disegnata in fondo al file (sezione DASHBOARD)

// Custom max: recovery factor (profitto / drawdown) dei due insieme
double OnTester()
  {
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < InpMinTrades)
      return -1000;
   double profit = TesterStatistics(STAT_PROFIT);
   double dd     = TesterStatistics(STAT_EQUITY_DD);
   return profit / MathMax(dd, 1.0);
  }

//+==================================================================+
//|  FIBONACCI                                                        |
//+==================================================================+
#define MAX_SWINGS 40

CTrade   g_fbTrade;
int      g_fbATR = INVALID_HANDLE;
int      g_fbEMA = INVALID_HANDLE;
datetime g_fbLastBar = 0;

bool     g_fbLegOk   = false;  // c'e' un impulso
bool     g_fbLegDead = true;   // impulso non piu' tradabile
int      g_fbDir     = 0;      // +1 impulso in salita (cerca buy), -1 in discesa (cerca sell)
double   g_fbH = 0, g_fbL = 0;
datetime g_fbTH = 0, g_fbTL = 0;
double   g_fbAtr = 0;
double   g_fbExtreme = 0;      // punto piu' profondo del ritracciamento finora
string   g_fbStatus = "avvio";

double   g_fbLv[3] = {0.382, 0.5, 0.618};
bool     g_fbUsed[3];          // livello gia' usato su questo impulso
ulong    g_fbPend[3];          // ticket del limit per livello

int FbInit()
  {
   if(!InpFbLvl382 && !InpFbLvl500 && !InpFbLvl618)
     {
      Print("Fibonacci: nessun livello attivo");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpFbSwingDepth < 1 || InpFbLookback < 4 * InpFbSwingDepth + 10 || InpFbSLFib <= 1.0)
      return INIT_PARAMETERS_INCORRECT;

   g_fbTrade.SetExpertMagicNumber(InpFbMagic);
   g_fbTrade.SetTypeFillingBySymbol(_Symbol);
   g_fbTrade.SetDeviationInPoints(50);

   g_fbATR = iATR(_Symbol, PERIOD_M1, 14);
   g_fbEMA = iMA(_Symbol, PERIOD_M1, InpFbEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   if(g_fbATR == INVALID_HANDLE || g_fbEMA == INVALID_HANDLE)
     {
      Print("Fibonacci: errore creazione indicatori ", GetLastError());
      return INIT_FAILED;
     }
   ArrayInitialize(g_fbUsed, false);
   ArrayInitialize(g_fbPend, 0);
   FbDeleteStrayOrders();
   return INIT_SUCCEEDED;
  }

void FbDeinit()
  {
   FbCancelPendings();
   if(g_fbATR != INVALID_HANDLE) IndicatorRelease(g_fbATR);
   if(g_fbEMA != INVALID_HANDLE) IndicatorRelease(g_fbEMA);
   ObjectsDeleteAll(0, "FIBM1_");
  }

bool FbInSession()
  {
   int hm = HHMM(TimeCurrent());
   return hm >= InpFbHourStart && hm < InpFbHourEnd;
  }

void FbOnTick()
  {
   // weekend: stessa chiusura del venerdi' sera del Kairos, cosi' nessun trade resta aperto sul gap del lunedi'
   if(InpRsWeekend && IsFriday(TimeCurrent()) && HHMM(TimeCurrent()) >= InpRsFriClose)
      FbCloseAll();

   datetime bt = iTime(_Symbol, PERIOD_M1, 0);
   bool newBar = (bt != g_fbLastBar && bt != 0);
   if(newBar)
     {
      g_fbLastBar = bt;
      FbUpdateLeg();
     }

   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk))
      return;

   if(g_fbLegOk && !g_fbLegDead)
     {
      double slLevel = FbPrice(InpFbSLFib);
      if(g_fbDir > 0)
        {
         g_fbExtreme = MathMin(g_fbExtreme, tk.bid);
         if(tk.bid > g_fbH)           FbKill("nuovo massimo oltre lo swing, attendo il prossimo");
         else if(tk.bid <= slLevel)   FbKill("prezzo oltre il livello SL, impulso annullato");
        }
      else
        {
         g_fbExtreme = MathMax(g_fbExtreme, tk.bid);
         if(tk.bid < g_fbL)           FbKill("nuovo minimo oltre lo swing, attendo il prossimo");
         else if(tk.bid >= slLevel)   FbKill("prezzo oltre il livello SL, impulso annullato");
        }
     }

   if(!g_fbLegOk || g_fbLegDead)
     {
      FbCancelPendings();
      return;
     }
   if(!FbInSession())
     {
      FbCancelPendings();
      g_fbStatus = "fuori orario";
      return;
     }

   switch(InpFbEntryMode)
     {
      case ENTRY_LIMIT:  FbManageLimits(tk); break;
      case ENTRY_MARKET: FbCheckTouch(tk);   break;
      default:           if(newBar) FbCheckConfirm(tk); break;
     }
  }

//--- impulso: ultimo swing low/high confermati con i frattali -------
bool FbIsSwingHigh(const double &hi[], int i, int n)
  {
   for(int k = 1; k <= n; k++)
      if(hi[i + k] > hi[i] || hi[i - k] >= hi[i])
         return false;
   return true;
  }

bool FbIsSwingLow(const double &lo[], int i, int n)
  {
   for(int k = 1; k <= n; k++)
      if(lo[i + k] < lo[i] || lo[i - k] <= lo[i])
         return false;
   return true;
  }

int ArgMax(const double &v[], int from, int to)
  {
   int best = from;
   for(int i = from; i <= to; i++)
      if(v[i] > v[best]) best = i;
   return best;
  }

int ArgMin(const double &v[], int from, int to)
  {
   int best = from;
   for(int i = from; i <= to; i++)
      if(v[i] < v[best]) best = i;
   return best;
  }

void FbUpdateLeg()
  {
   int n = InpFbLookback, N = InpFbSwingDepth;
   double hi[], lo[], cl[];
   datetime tm[];
   ArraySetAsSeries(hi, true);
   ArraySetAsSeries(lo, true);
   ArraySetAsSeries(cl, true);
   ArraySetAsSeries(tm, true);
   if(CopyHigh(_Symbol, PERIOD_M1, 0, n, hi) < n || CopyLow(_Symbol, PERIOD_M1, 0, n, lo) < n ||
      CopyClose(_Symbol, PERIOD_M1, 0, n, cl) < n || CopyTime(_Symbol, PERIOD_M1, 0, n, tm) < n)
      return;

   double a[];
   if(CopyBuffer(g_fbATR, 0, 1, 1, a) == 1)
      g_fbAtr = a[0];

   // swing dal piu' recente al piu' vecchio
   int sh[MAX_SWINGS], sl[MAX_SWINGS];
   int nsh = 0, nsl = 0;
   for(int i = N + 1; i < n - N && (nsh < MAX_SWINGS || nsl < MAX_SWINGS); i++)
     {
      if(nsh < MAX_SWINGS && FbIsSwingHigh(hi, i, N)) sh[nsh++] = i;
      if(nsl < MAX_SWINGS && FbIsSwingLow(lo, i, N))  sl[nsl++] = i;
     }
   if(nsh == 0 || nsl == 0 || sh[0] == sl[0])
     {
      FbNoLeg("nessuno swing chiaro");
      return;
     }

   int dir = (sl[0] > sh[0]) ? 1 : -1;
   int e, s;   // e = fine dell'impulso (indice), s = inizio
   double H, L;
   if(dir > 0)
     {
      e = ArgMax(hi, sh[0], sl[0]);
      s = ArgMin(lo, e, sl[0]);
      H = hi[e];
      L = lo[s];
     }
   else
     {
      e = ArgMin(lo, sl[0], sh[0]);
      s = ArgMax(hi, e, sh[0]);
      L = lo[e];
      H = hi[s];
     }
   datetime tH = (dir > 0) ? tm[e] : tm[s];
   datetime tL = (dir > 0) ? tm[s] : tm[e];

   bool same = g_fbLegOk && dir == g_fbDir && tH == g_fbTH && tL == g_fbTL;
   if(!same)
     {
      FbCancelPendings();
      g_fbLegOk   = true;
      g_fbLegDead = false;
      g_fbDir     = dir;
      g_fbH = H; g_fbL = L; g_fbTH = tH; g_fbTL = tL;
      ArrayInitialize(g_fbUsed, false);
      ArrayInitialize(g_fbPend, 0);
      g_fbStatus = StringFormat("impulso %s %s -> %s", dir > 0 ? "rialzista" : "ribassista",
                                DoubleToString(dir > 0 ? L : H, _Digits), DoubleToString(dir > 0 ? H : L, _Digits));

      FbDraw();
      string why = "";
      if(!FbLegValid(dir, s, hi, lo, sh, nsh, sl, nsl, why))
         FbKill(why);   // impulso scartato: il disegno diventa grigio
     }
   if(g_fbLegDead)
      return;

   // cosa e' successo dopo la fine dell'impulso
   g_fbExtreme = (dir > 0) ? H : L;
   for(int i = 1; i < e; i++)
     {
      if(dir > 0)
        {
         if(hi[i] > H) { FbKill("nuovo massimo oltre lo swing, attendo il prossimo"); return; }
         if(cl[i] < L) { FbKill("chiusura sotto lo swing low, impulso annullato"); return; }
         g_fbExtreme = MathMin(g_fbExtreme, lo[i]);
        }
      else
        {
         if(lo[i] < L) { FbKill("nuovo minimo oltre lo swing, attendo il prossimo"); return; }
         if(cl[i] > H) { FbKill("chiusura sopra lo swing high, impulso annullato"); return; }
         g_fbExtreme = MathMax(g_fbExtreme, hi[i]);
        }
     }
   if(e > InpFbMaxLegBars)
      FbKill("impulso troppo vecchio");
  }

bool FbLegValid(int dir, int s, const double &hi[], const double &lo[],
                const int &sh[], int nsh, const int &sl[], int nsl, string &why)
  {
   double R = g_fbH - g_fbL;
   if(R <= 0 || R < InpFbMinLegATR * g_fbAtr || R < InpFbMinLegPts * _Point)
     {
      why = "impulso troppo piccolo";
      return false;
     }

   if(InpFbTrend == TREND_EMA)
     {
      double e1[], es[];
      if(CopyBuffer(g_fbEMA, 0, 1, 1, e1) != 1 || CopyBuffer(g_fbEMA, 0, s, 1, es) != 1)
        {
         why = "EMA non disponibile";
         return false;
        }
      if((dir > 0 && e1[0] <= es[0]) || (dir < 0 && e1[0] >= es[0]))
        {
         why = "EMA contro l'impulso";
         return false;
        }
     }
   else if(InpFbTrend == TREND_STRUCT)
     {
      // swing precedenti, piu' vecchi dell'inizio dell'impulso
      int ph = -1, pl = -1;
      for(int i = 0; i < nsh; i++) if(sh[i] > s) { ph = sh[i]; break; }
      for(int i = 0; i < nsl; i++) if(sl[i] > s) { pl = sl[i]; break; }
      if(ph < 0 || pl < 0)
        {
         why = "struttura non disponibile";
         return false;
        }
      bool ok = (dir > 0) ? (g_fbH > hi[ph] && g_fbL > lo[pl]) : (g_fbL < lo[pl] && g_fbH < hi[ph]);
      if(!ok)
        {
         why = (dir > 0) ? "niente massimi e minimi crescenti" : "niente massimi e minimi decrescenti";
         return false;
        }
     }
   return true;
  }

void FbNoLeg(string why)
  {
   FbCancelPendings();
   g_fbLegOk   = false;
   g_fbLegDead = true;
   g_fbStatus  = why;
  }

void FbKill(string why)
  {
   bool wasAlive = !g_fbLegDead;
   g_fbLegDead = true;
   g_fbStatus  = why;
   FbCancelPendings();
   if(wasAlive)
      FbDrawDead();
  }

//--- livelli, SL e TP -----------------------------------------------
// 0 = fine dell'impulso, 1 = inizio, 1.1 = oltre l'inizio, -0.272 = estensione
double FbPrice(double f)
  {
   double R = g_fbH - g_fbL;
   return (g_fbDir > 0) ? g_fbH - f * R : g_fbL + f * R;
  }

bool FbLevelOn(int k)
  {
   return (k == 0) ? InpFbLvl382 : (k == 1) ? InpFbLvl500 : InpFbLvl618;
  }

string FbLevelCmt(int k)
  {
   return (k == 0) ? "FIB382" : (k == 1) ? "FIB500" : "FIB618";
  }

bool FbCalcSLTP(double entry, double &sl, double &tp)
  {
   int dir = g_fbDir;
   sl = FbPrice(InpFbSLFib);
   double risk = MathAbs(entry - sl);
   if(risk <= 0 || (dir > 0 && sl >= entry) || (dir < 0 && sl <= entry))
      return false;

   switch(InpFbTPMode)
     {
      case TP_RR1:    tp = entry + dir * 1.0 * risk; break;
      case TP_RR15:   tp = entry + dir * 1.5 * risk; break;
      case TP_RR2:    tp = entry + dir * 2.0 * risk; break;
      case TP_RR3:    tp = entry + dir * 3.0 * risk; break;
      case TP_SWING:  tp = FbPrice(0.0);    break;
      case TP_EXT272: tp = FbPrice(-0.272); break;
      case TP_EXT618: tp = FbPrice(-0.618); break;
      default:        tp = entry + dir * InpFbTPATRMult * g_fbAtr; break;
     }
   if((dir > 0 && tp <= entry) || (dir < 0 && tp >= entry))
      return false;

   double minD = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(MathAbs(entry - sl) < minD || MathAbs(tp - entry) < minD)
      return false;

   sl = Norm(sl);
   tp = Norm(tp);
   return true;
  }

//--- ingresso con ordini limit --------------------------------------
void FbManageLimits(const MqlTick &tk)
  {
   double minD = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   for(int k = 0; k < 3; k++)
     {
      if(!FbLevelOn(k) || g_fbUsed[k])
         continue;
      if(g_fbPend[k] != 0)
        {
         if(OrderSelect(g_fbPend[k]))
            continue;           // ancora in attesa
         g_fbUsed[k] = true;    // eseguito (o tolto a mano): non lo rimette
         g_fbPend[k] = 0;
         continue;
        }

      double px = Norm(FbPrice(g_fbLv[k]));
      // il prezzo e' gia' sul livello o oltre: il limit non si puo' piu' mettere
      if((g_fbDir > 0 && tk.ask <= px + minD) || (g_fbDir < 0 && tk.bid >= px - minD))
        {
         g_fbUsed[k] = true;
         continue;
        }
      double sl, tp;
      if(!FbCalcSLTP(px, sl, tp))
        {
         g_fbUsed[k] = true;
         continue;
        }
      double lots = NormLots(InpFbLots);
      bool ok = (g_fbDir > 0)
                ? g_fbTrade.BuyLimit(lots, px, _Symbol, sl, tp, ORDER_TIME_GTC, 0, FbLevelCmt(k))
                : g_fbTrade.SellLimit(lots, px, _Symbol, sl, tp, ORDER_TIME_GTC, 0, FbLevelCmt(k));
      if(ok && g_fbTrade.ResultOrder() > 0)
         g_fbPend[k] = g_fbTrade.ResultOrder();
      else
        {
         g_fbUsed[k] = true;
         Log(StringFormat("Fibonacci: limit %s rifiutato: %d %s", FbLevelCmt(k), g_fbTrade.ResultRetcode(), g_fbTrade.ResultRetcodeDescription()));
        }
     }
  }

void FbCancelPendings()
  {
   for(int k = 0; k < 3; k++)
     {
      if(g_fbPend[k] == 0)
         continue;
      ulong t = g_fbPend[k];
      g_fbPend[k] = 0;
      if(OrderSelect(t))
         g_fbTrade.OrderDelete(t);
      else
         g_fbUsed[k] = true;   // nel frattempo e' stato eseguito
     }
  }

void FbCloseAll()
  {
   for(int k = PositionsTotal() - 1; k >= 0; k--)
     {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpFbMagic) continue;
      if(g_fbTrade.PositionClose(tk))
         Log("Fibonacci: posizione chiusa prima del weekend");
     }
  }

void FbDeleteStrayOrders()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t > 0 && OrderGetInteger(ORDER_MAGIC) == InpFbMagic && OrderGetString(ORDER_SYMBOL) == _Symbol)
         g_fbTrade.OrderDelete(t);
     }
  }

//--- ingresso a mercato al tocco del livello ------------------------
void FbCheckTouch(const MqlTick &tk)
  {
   double tol = InpFbTouchTol * (g_fbH - g_fbL);
   for(int k = 0; k < 3; k++)
     {
      if(!FbLevelOn(k) || g_fbUsed[k])
         continue;
      double px = FbPrice(g_fbLv[k]);
      if(g_fbDir > 0)
        {
         if(tk.bid > px) continue;                                 // non ancora arrivato
         if(tk.bid < px - tol) { g_fbUsed[k] = true; continue; }   // gia' troppo oltre: perso
        }
      else
        {
         if(tk.bid < px) continue;
         if(tk.bid > px + tol) { g_fbUsed[k] = true; continue; }
        }
      FbOpenMarket(k, tk);
     }
  }

//--- ingresso a mercato dopo pin bar / engulfing nella zona ---------
void FbCheckConfirm(const MqlTick &tk)
  {
   bool bull = (g_fbDir > 0);
   bool pat  = false;
   if(InpFbEntryMode == ENTRY_PINBAR || InpFbEntryMode == ENTRY_PIN_OR_ENG) pat = pat || FbIsPinBar(bull);
   if(InpFbEntryMode == ENTRY_ENGULF || InpFbEntryMode == ENTRY_PIN_OR_ENG) pat = pat || FbIsEngulfing(bull);
   if(!pat)
      return;

   // la candela di conferma deve stare nella zona di ritracciamento
   double zone = FbPrice(0.382);
   if(bull ? iLow(_Symbol, PERIOD_M1, 1) > zone : iHigh(_Symbol, PERIOD_M1, 1) < zone)
      return;

   // un solo trade per conferma, sul livello piu' profondo raggiunto e non ancora usato
   int pick = -1;
   for(int k = 0; k < 3; k++)
     {
      if(!FbLevelOn(k))
         continue;
      double px = FbPrice(g_fbLv[k]);
      bool reached = bull ? (g_fbExtreme <= px) : (g_fbExtreme >= px);
      if(reached)
         pick = k;
     }
   if(pick < 0 || g_fbUsed[pick])
      return;
   for(int k = 0; k <= pick; k++)
      g_fbUsed[k] = true;
   FbOpenMarket(pick, tk);
  }

bool FbIsPinBar(bool bull)
  {
   double o = iOpen(_Symbol, PERIOD_M1, 1), h = iHigh(_Symbol, PERIOD_M1, 1);
   double l = iLow(_Symbol, PERIOD_M1, 1),  c = iClose(_Symbol, PERIOD_M1, 1);
   double range = h - l;
   if(range <= 0)
      return false;
   double body  = MathAbs(c - o);
   double lower = MathMin(o, c) - l;
   double upper = h - MathMax(o, c);
   if(bull)
      return lower >= InpFbPinWick * range && lower >= 2.0 * body;
   return upper >= InpFbPinWick * range && upper >= 2.0 * body;
  }

bool FbIsEngulfing(bool bull)
  {
   double o1 = iOpen(_Symbol, PERIOD_M1, 1), c1 = iClose(_Symbol, PERIOD_M1, 1);
   double o2 = iOpen(_Symbol, PERIOD_M1, 2), c2 = iClose(_Symbol, PERIOD_M1, 2);
   if(MathAbs(c1 - o1) <= MathAbs(c2 - o2))
      return false;
   if(bull)
      return c1 > o1 && c2 < o2 && c1 >= o2 && o1 <= c2;
   return c1 < o1 && c2 > o2 && c1 <= o2 && o1 >= c2;
  }

void FbOpenMarket(int k, const MqlTick &tk)
  {
   g_fbUsed[k] = true;   // un tentativo per livello: niente raffiche di ordini se il broker rifiuta
   double entry = (g_fbDir > 0) ? tk.ask : tk.bid;
   double sl, tp;
   if(!FbCalcSLTP(entry, sl, tp))
      return;
   double lots = NormLots(InpFbLots);
   bool ok = (g_fbDir > 0)
             ? g_fbTrade.Buy(lots, _Symbol, 0, sl, tp, FbLevelCmt(k))
             : g_fbTrade.Sell(lots, _Symbol, 0, sl, tp, FbLevelCmt(k));
   if(!ok)
     {
      Log(StringFormat("Fibonacci: ordine %s rifiutato: %d %s", FbLevelCmt(k), g_fbTrade.ResultRetcode(), g_fbTrade.ResultRetcodeDescription()));
      return;
     }
   double px = g_fbTrade.ResultPrice() > 0 ? g_fbTrade.ResultPrice() : entry;
   Log(StringFormat("Fibonacci %s %s: entrata %s SL %s TP %s (impulso %s -> %s)", FbLevelCmt(k), g_fbDir > 0 ? "BUY" : "SELL",
                    DoubleToString(px, _Digits), DoubleToString(sl, _Digits), DoubleToString(tp, _Digits),
                    DoubleToString(g_fbDir > 0 ? g_fbL : g_fbH, _Digits), DoubleToString(g_fbDir > 0 ? g_fbH : g_fbL, _Digits)));
   FbDrawTrade(k, px, sl, tp);
  }

//--- grafico --------------------------------------------------------
// Fibonacci dell'impulso corrente: si aggiorna a ogni impulso nuovo
void FbDraw()
  {
   if(!g_draw)
      return;
   FbDrawFibo("FIBM1_leg", true, g_fbDir > 0 ? clrDodgerBlue : clrOrangeRed, false);
   ChartRedraw();
  }

// impulso annullato: il disegno resta ma diventa grigio
void FbDrawDead()
  {
   if(!g_draw || ObjectFind(0, "FIBM1_leg") < 0)
      return;
   FbDrawFibo("FIBM1_leg", true, clrDimGray, true);
   ChartRedraw();
  }

void FbDrawFibo(string nm, bool rayRight, color legColor, bool dim)
  {
   ObjectDelete(0, nm);
   // primo punto = inizio dell'impulso (livello 1), secondo = fine (livello 0)
   datetime t1 = (g_fbDir > 0) ? g_fbTL : g_fbTH;
   double   p1 = (g_fbDir > 0) ? g_fbL  : g_fbH;
   datetime t2 = (g_fbDir > 0) ? g_fbTH : g_fbTL;
   double   p2 = (g_fbDir > 0) ? g_fbH  : g_fbL;
   if(!ObjectCreate(0, nm, OBJ_FIBO, 0, t1, p1, t2, p2))
      return;
   double lv[] = {0.0, 0.382, 0.5, 0.618, 1.0, 0.0, -0.272, -0.618};
   lv[5] = InpFbSLFib;
   int cnt = ArraySize(lv);
   ObjectSetInteger(0, nm, OBJPROP_LEVELS, cnt);
   for(int i = 0; i < cnt; i++)
     {
      color c = dim ? clrDimGray : (i == 5 ? clrRed : (lv[i] > 0.3 && lv[i] < 0.7) ? clrGold : clrSilver);
      ObjectSetDouble(0, nm, OBJPROP_LEVELVALUE, i, lv[i]);
      ObjectSetString(0, nm, OBJPROP_LEVELTEXT, i, (dim && i == 0 ? "ANNULLATO " : "") + (i == 5 ? "SL " : "") + DoubleToString(lv[i], 3) + "  %$");
      ObjectSetInteger(0, nm, OBJPROP_LEVELCOLOR, i, c);
     }
   ObjectSetInteger(0, nm, OBJPROP_COLOR, legColor);
   ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, rayRight);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, true);
  }

// a ogni trade Fibonacci lascia sul grafico il suo schema fisso: Fibonacci dell'impulso,
// freccia sull'entrata e scritta con livello, entrata, SL e TP (restano anche dopo la chiusura)
void FbDrawTrade(int k, double entry, double sl, double tp)
  {
   if(!g_draw)
      return;
   datetime now = TimeCurrent();
   string id = "FIBT_" + IntegerToString((long)now) + "_" + IntegerToString(k);
   bool buy = (g_fbDir > 0);
   color c = buy ? clrDodgerBlue : clrOrangeRed;

   FbDrawFibo(id + "_fib", false, c, false);

   string ar = id + "_arrow";
   if(ObjectCreate(0, ar, buy ? OBJ_ARROW_BUY : OBJ_ARROW_SELL, 0, now, entry))
     {
      ObjectSetInteger(0, ar, OBJPROP_COLOR, c);
      ObjectSetInteger(0, ar, OBJPROP_WIDTH, 3);
     }

   string tx = id + "_txt";
   if(ObjectCreate(0, tx, OBJ_TEXT, 0, now, sl))
     {
      ObjectSetString(0, tx, OBJPROP_TEXT, StringFormat("%s %s %s  SL %s  TP %s", FbLevelCmt(k), buy ? "BUY" : "SELL",
                      DoubleToString(entry, _Digits), DoubleToString(sl, _Digits), DoubleToString(tp, _Digits)));
      ObjectSetInteger(0, tx, OBJPROP_COLOR, c);
      ObjectSetInteger(0, tx, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, tx, OBJPROP_ANCHOR, buy ? ANCHOR_LEFT_UPPER : ANCHOR_LEFT_LOWER);
     }
   ChartRedraw();
  }


//+==================================================================+
//|  KAIROS (RSI)                                                     |
//+==================================================================+
CTrade   g_rsTrade;
int      g_rsRSI     = INVALID_HANDLE;
int      g_rsATR     = INVALID_HANDLE;
datetime g_rsLastBar = 0;
bool     g_rsOS      = false;  // RSI in ipervenduto (<= 30)
bool     g_rsOB      = false;  // RSI in ipercomprato (>= 70)
int      g_rsUpBars  = 0;      // candele di fila con il rientro confermato (BUY)
int      g_rsDnBars  = 0;      // candele di fila con il rientro confermato (SELL)
bool     g_rsArmBuy  = false;  // entrata al tocco: pronto a comprare al prossimo tocco di 30
bool     g_rsArmSell = false;  // entrata al tocco: pronto a vendere al prossimo tocco di 70
double   g_rsNow     = 0;

int RsInit()
  {
   g_rsTrade.SetExpertMagicNumber(InpRsMagic);
   g_rsTrade.SetDeviationInPoints(30);
   g_rsTrade.SetTypeFillingBySymbol(_Symbol);

   g_rsRSI = iRSI(_Symbol, PERIOD_M1, InpRsPeriod, PRICE_CLOSE);
   g_rsATR = iATR(_Symbol, InpRsATRTF, InpRsATRPeriod);
   if(g_rsRSI == INVALID_HANDLE || g_rsATR == INVALID_HANDLE)
     {
      Print("Kairos: RSI M1 o ATR non disponibile");
      return INIT_FAILED;
     }
   return INIT_SUCCEEDED;
  }

void RsDeinit()
  {
   if(g_rsRSI != INVALID_HANDLE) IndicatorRelease(g_rsRSI);
   if(g_rsATR != INVALID_HANDLE) IndicatorRelease(g_rsATR);
  }

void RsOnTick()
  {
   // weekend: il venerdi' sera chiude tutto, cosi' nessun trade resta aperto sul gap del lunedi'
   if(InpRsWeekend && IsFriday(TimeCurrent()) && HHMM(TimeCurrent()) >= InpRsFriClose)
     {
      RsCloseAll(POSITION_TYPE_BUY);
      RsCloseAll(POSITION_TYPE_SELL);
     }

   // TP: a ogni tick, appena l'RSI torna al livello di uscita
   double now[1];
   bool   rsiOk = CopyBuffer(g_rsRSI, 0, 0, 1, now) == 1;
   if(rsiOk)
     {
      g_rsNow = now[0];
      if(now[0] >= InpRsExit)       RsCloseAll(POSITION_TYPE_BUY);
      if(now[0] <= InpRsExitSell)   RsCloseAll(POSITION_TYPE_SELL);
      if(InpRsBreakEven)
        {
         if(now[0] >= InpRsBERSI)       RsBreakEven(POSITION_TYPE_BUY);
         if(now[0] <= 100 - InpRsBERSI) RsBreakEven(POSITION_TYPE_SELL);
        }
     }

   if(InpRsEntryTouch)
     {
      if(rsiOk) RsEntryOnTouch();
      return;
     }

   datetime bar0 = iTime(_Symbol, PERIOD_M1, 0);
   if(bar0 == 0 || bar0 == g_rsLastBar) return;
   g_rsLastBar = bar0;

   // entrata: sulla candela M1 appena chiusa, una sola volta per ogni tocco di 30/70
   double rsi[1], atr[1];
   if(CopyBuffer(g_rsRSI, 0, 1, 1, rsi) != 1) return;
   if(CopyBuffer(g_rsATR, 0, 1, 1, atr) != 1 || atr[0] <= 0) return;

   // con i filtri spenti (0 punti, 1 candela) entra alla prima chiusura sopra 30 / sotto 70, come sempre
   if(rsi[0] <= InpRsLow)
     {
      g_rsOS = true;
      g_rsUpBars = 0;
     }
   else if(g_rsOS)
     {
      g_rsUpBars = (rsi[0] >= InpRsLow + InpRsConfirmPts) ? g_rsUpBars + 1 : 0;
      if(g_rsUpBars >= MathMax(InpRsConfirmBars, 1))
        {
         g_rsOS = false;
         g_rsUpBars = 0;
         RsOpen(+1, atr[0]);
        }
     }

   if(rsi[0] >= InpRsHigh)
     {
      g_rsOB = true;
      g_rsDnBars = 0;
     }
   else if(g_rsOB)
     {
      g_rsDnBars = (rsi[0] <= InpRsHigh - InpRsConfirmPts) ? g_rsDnBars + 1 : 0;
      if(g_rsDnBars >= MathMax(InpRsConfirmBars, 1))
        {
         g_rsOB = false;
         g_rsDnBars = 0;
         RsOpen(-1, atr[0]);
        }
     }
  }

// true se negli ultimi InpRsSLPauseMin minuti un trade RSI nella direzione dir e' stato chiuso dallo stop loss
bool RsRecentSL(int dir)
  {
   if(InpRsSLPauseMin <= 0)
      return false;
   datetime now = TimeCurrent();
   if(!HistorySelect(now - InpRsSLPauseMin * 60, now + 60))
      return false;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0) continue;
      if(HistoryDealGetInteger(d, DEAL_MAGIC) != InpRsMagic) continue;
      if(HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol) continue;
      if(HistoryDealGetInteger(d, DEAL_REASON) != DEAL_REASON_SL) continue;
      long entry = HistoryDealGetInteger(d, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY) continue;
      // un BUY si chiude con un deal SELL e viceversa
      long type = HistoryDealGetInteger(d, DEAL_TYPE);
      if((dir > 0 && type == DEAL_TYPE_SELL) || (dir < 0 && type == DEAL_TYPE_BUY))
         return true;
     }
   return false;
  }

// entrata al tocco: a ogni tick, appena l'RSI tocca 30 (BUY) o 70 (SELL).
// Si riarma solo quando una candela M1 chiude con l'RSI di nuovo dentro 30-70
void RsEntryOnTouch()
  {
   datetime bar0 = iTime(_Symbol, PERIOD_M1, 0);
   if(bar0 != 0 && bar0 != g_rsLastBar)
     {
      g_rsLastBar = bar0;
      double rsi[1];
      if(CopyBuffer(g_rsRSI, 0, 1, 1, rsi) == 1)
        {
         if(rsi[0] > InpRsLow)  g_rsArmBuy  = true;
         if(rsi[0] < InpRsHigh) g_rsArmSell = true;
        }
     }

   if(!g_rsArmBuy && !g_rsArmSell) return;
   double atr[1];
   if(CopyBuffer(g_rsATR, 0, 1, 1, atr) != 1 || atr[0] <= 0) return;

   if(g_rsArmBuy && g_rsNow <= InpRsLow)
     {
      g_rsArmBuy = false;
      RsOpen(+1, atr[0]);
     }
   if(g_rsArmSell && g_rsNow >= InpRsHigh)
     {
      g_rsArmSell = false;
      RsOpen(-1, atr[0]);
     }
  }

void RsCloseAll(ENUM_POSITION_TYPE type)
  {
   for(int k = PositionsTotal() - 1; k >= 0; k--)
     {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpRsMagic) continue;
      if(PositionGetInteger(POSITION_TYPE) != type) continue;
      if(g_rsTrade.PositionClose(tk))
         Log(StringFormat("Kairos: %s chiuso, RSI %.1f", type == POSITION_TYPE_BUY ? "BUY" : "SELL", g_rsNow));
     }
  }

// SL all'entrata (+ punti bloccati), solo se il prezzo lo permette
void RsBreakEven(ENUM_POSITION_TYPE type)
  {
   double bid   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double stops = (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 2) * _Point;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
     {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpRsMagic) continue;
      if(PositionGetInteger(POSITION_TYPE) != type) continue;

      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      if(type == POSITION_TYPE_BUY)
        {
         double nsl = NormalizeDouble(open + InpRsBELockPts * _Point, _Digits);
         if(sl < nsl && bid - nsl > stops && g_rsTrade.PositionModify(tk, nsl, 0))
            Log(StringFormat("Kairos: BUY a break-even, RSI %.1f", g_rsNow));
        }
      else
        {
         double nsl = NormalizeDouble(open - InpRsBELockPts * _Point, _Digits);
         if((sl == 0 || sl > nsl) && nsl - ask > stops && g_rsTrade.PositionModify(tk, nsl, 0))
            Log(StringFormat("Kairos: SELL a break-even, RSI %.1f", g_rsNow));
        }
     }
  }

int CountOpen(long magic)
  {
   int n = 0;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
     {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != magic) continue;
      n++;
     }
   return n;
  }

// dir = +1 BUY / -1 SELL
void RsOpen(int dir, double atr)
  {
   string name = dir > 0 ? "BUY" : "SELL";
   if(InpRsOneAtTime && CountOpen(InpRsMagic) > 0) { Log("Kairos " + name + ": c'e' gia' un'operazione aperta, segnale ignorato"); return; }
   if(RsRecentSL(dir)) { Log(StringFormat("Kairos %s: stop loss negli ultimi %d minuti, segnale ignorato", name, InpRsSLPauseMin)); return; }

   datetime t  = TimeCurrent();
   int      hm = HHMM(t);
   if(InpRsWeekend && IsFriday(t) && hm >= InpRsFriNoNew)                { Log("Kairos " + name + ": venerdi' sera, niente trade nuovi"); return; }
   if(InpRsUseHours && (hm < InpRsHourStart || hm >= InpRsHourEnd))      { Log("Kairos " + name + ": fuori dalla fascia oraria"); return; }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0 || bid <= 0) return;

   if(InpRsUseATRFilter)
     {
      double pct = atr / bid * 100.0;
      if(pct < InpRsMinATRPct) { Log(StringFormat("Kairos %s: ATR troppo basso (%.3f%%), niente trade", name, pct)); return; }
      if(pct > InpRsMaxATRPct) { Log(StringFormat("Kairos %s: ATR troppo alto (%.3f%%), niente trade", name, pct)); return; }
     }

   // il broker vuole lo SL ad almeno "stops level" punti dal prezzo
   double dist    = InpRsSLATR * atr;
   double minDist = (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 5) * _Point;
   dist = MathMax(dist, minDist);

   double entry = dir > 0 ? ask : bid;
   double sl    = NormalizeDouble(entry - dir * dist, _Digits);

   bool ok = dir > 0 ? g_rsTrade.Buy(NormLots(InpRsLots), _Symbol, 0, sl, 0, "RSI M1")
                     : g_rsTrade.Sell(NormLots(InpRsLots), _Symbol, 0, sl, 0, "RSI M1");
   if(ok && (g_rsTrade.ResultRetcode() == TRADE_RETCODE_DONE || g_rsTrade.ResultRetcode() == TRADE_RETCODE_PLACED))
      Log(StringFormat("Kairos %s: entrata %s SL %s (%.0f punti = %.1f x ATR), TP quando l'RSI torna a %s", name,
                       DoubleToString(entry, _Digits), DoubleToString(sl, _Digits), dist / _Point, InpRsSLATR,
                       DoubleToString(dir > 0 ? InpRsExit : InpRsExitSell, 0)));
   else
      Log(StringFormat("Kairos %s: ordine rifiutato (%u %s)", name, g_rsTrade.ResultRetcode(), g_rsTrade.ResultRetcodeDescription()));
  }

//+------------------------------------------------------------------+

//+==================================================================+
//|  DASHBOARD                                                        |
//+==================================================================+

color    CLR_BG     = C'16,24,38';     // sfondo: blu notte, stacca dal nero di MT5
color    CLR_BORDER = C'217,180,90';   // bordo oro
color    CLR_HEAD   = C'27,39,58';     // barra dei titoli di sezione
color    CLR_LINE   = C'38,52,74';
color    CLR_GOLD   = C'241,220,163';
color    CLR_GOLD2  = C'217,180,90';
color    CLR_TEXT   = C'233,237,243';
color    CLR_MUTED  = C'154,167,186';
color    CLR_GREEN  = C'95,197,138';
color    CLR_RED    = C'229,118,118';
color    CLR_BLUE   = C'110,170,240';

ulong    g_pnlLastMs   = 0;
int      g_pnlH        = 0;      // altezza attuale della dashboard (lo sfondo non si accorcia mai a meta' aggiornamento)
int      g_itaOff      = 1;      // ore di differenza ora FPG - ora italiana
ulong    g_statsLastMs = 0;
double   g_dayPL = 0;
int      g_dayN = 0, g_dayWin = 0, g_dayLoss = 0;

void PRect(string id, int x, int y, int w, int h, color bg, color border)
  {
   string nm = PNL + id;
   if(ObjectFind(0, nm) < 0)
     {
      ObjectCreate(0, nm, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, nm, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, nm, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, nm, OBJPROP_BACK, false);
     }
   ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, nm, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, nm, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, nm, OBJPROP_YSIZE, h);
   ObjectSetInteger(0, nm, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, border);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, 1);
  }

void PText(string id, int x, int y, string text, color c, int size = 9, bool bold = false, bool right = false)
  {
   string nm = PNL + id;
   if(ObjectFind(0, nm) < 0)
     {
      ObjectCreate(0, nm, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, nm, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, nm, OBJPROP_BACK, false);
     }
   ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, nm, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, right ? ANCHOR_RIGHT_UPPER : ANCHOR_LEFT_UPPER);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, c);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, size);
   ObjectSetString(0, nm, OBJPROP_FONT, bold ? "Segoe UI Semibold" : "Segoe UI");
   ObjectSetString(0, nm, OBJPROP_TEXT, text);
  }

// riga "etichetta ......... valore"
void PRow(string id, int &y, string label, string value, color vc)
  {
   int x = InpPanelX;
   PText(id + "_l", x + 14, y, label, CLR_MUTED, 9);
   PText(id + "_v", x + PNL_W - 14, y, value, vc, 9, true, true);
   y += 19;
  }

// titolo di sezione con fascia oraria a destra
void PSection(string id, int &y, string title, string right)
  {
   int x = InpPanelX;
   y += 6;
   PRect(id + "_bar", x + 8, y, PNL_W - 16, 22, CLR_HEAD, CLR_HEAD);
   PRect(id + "_acc", x + 8, y, 3, 22, CLR_GOLD2, CLR_GOLD2);
   PText(id + "_t", x + 18, y + 3, title, CLR_GOLD, 9, true);
   PText(id + "_r", x + PNL_W - 16, y + 3, right, CLR_TEXT, 9, true, true);
   y += 30;
  }

// HHMM ora MT5 -> "HH:MM" ora italiana
// ultima domenica del mese (marzo o ottobre), alle 00:00
datetime LastSunday(int year, int month)
  {
   MqlDateTime d;
   ZeroMemory(d);
   d.year = year;
   d.mon  = month + 1;
   d.day  = 1;
   datetime last = StructToTime(d) - 86400;   // ultimo giorno del mese
   MqlDateTime l;
   TimeToStruct(last, l);
   return last - l.day_of_week * 86400;
  }

// ora legale italiana: dall'ultima domenica di marzo all'ultima di ottobre, alle 01:00 UTC
bool ItalyDST(datetime gmt)
  {
   MqlDateTime d;
   TimeToStruct(gmt, d);
   return gmt >= LastSunday(d.year, 3) + 3600 && gmt < LastSunday(d.year, 10) + 3600;
  }

// ore di differenza ora FPG - ora italiana: dal set, oppure calcolate (ora del server meno ora italiana)
int ItaOffsetHours()
  {
   if(InpItaOffset >= 0 || (bool)MQLInfoInteger(MQL_TESTER))
      return InpItaOffset >= 0 ? InpItaOffset : 1;
   datetime gmt = TimeGMT();
   datetime ita = gmt + (ItalyDST(gmt) ? 7200 : 3600);
   return (int)MathRound((double)(TimeTradeServer() - ita) / 3600.0);
  }

string ItaTime(int hhmm)
  {
   int m = (hhmm / 100) * 60 + hhmm % 100 - g_itaOff * 60;
   m = (m % 1440 + 1440) % 1440;
   return StringFormat("%02d:%02d", m / 60, m % 60);
  }

// carattere unicode (punto, freccia, trattino lungo...) senza scriverlo nel sorgente
string U(int code)
  {
   return ShortToString((ushort)code);
  }

string Money(double v)
  {
   return (v >= 0 ? "+" : "") + DoubleToString(v, 2) + " $";
  }

double FloatingPL(long magic, int &n)
  {
   double pl = 0;
   n = 0;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
     {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != magic) continue;
      pl += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      n++;
     }
   return pl;
  }

// operazioni chiuse oggi dalle due strategie (ora del server)
void CalcToday()
  {
   datetime now = TimeCurrent();
   MqlDateTime dt;
   TimeToStruct(now, dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   g_dayPL = 0; g_dayN = 0; g_dayWin = 0; g_dayLoss = 0;
   if(!HistorySelect(StructToTime(dt), now + 60))
      return;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0 || HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol) continue;
      long mg = HistoryDealGetInteger(d, DEAL_MAGIC);
      if(mg != InpFbMagic && mg != InpRsMagic) continue;
      double net = HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) +
                   HistoryDealGetDouble(d, DEAL_COMMISSION);
      g_dayPL += net;
      long entry = HistoryDealGetInteger(d, DEAL_ENTRY);
      if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY)
        {
         g_dayN++;
         if(HistoryDealGetDouble(d, DEAL_PROFIT) >= 0) g_dayWin++; else g_dayLoss++;
        }
     }
  }

void ShowPanel(bool force)
  {
   if(!g_draw || !InpPanel)
      return;
   ulong ms = GetTickCount64();
   if(!force && ms - g_pnlLastMs < 300)
      return;
   g_pnlLastMs = ms;
   if(ms - g_statsLastMs > 5000)
     {
      g_statsLastMs = ms;
      CalcToday();
     }

   g_itaOff = ItaOffsetHours();
   int x = InpPanelX, y = InpPanelY;
   PRect("bg", x, y, PNL_W, g_pnlH > 0 ? g_pnlH : 100, CLR_BG, CLR_BORDER);   // altezza giusta calcolata in fondo

   // --- intestazione
   y += 10;
   PText("title", x + 14, y, "KAIROS TRADING BOT", CLR_GOLD, 13, true);
   bool canTrade = (bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && (bool)MQLInfoInteger(MQL_TRADE_ALLOWED);
   PText("state", x + PNL_W - 14, y + 4, canTrade ? U(0x25CF) + " ONLINE" : U(0x25CF) + " ALGO OFF",
         canTrade ? CLR_GREEN : CLR_RED, 9, true, true);
   y += 24;
   PText("sub", x + 14, y, _Symbol + "  " + U(0x00B7) + "  M1  " + U(0x00B7) + "  by YardFX", CLR_MUTED, 8);
   y += 20;
   PRect("sep", x + 14, y, PNL_W - 28, 1, CLR_LINE, CLR_LINE);
   y += 4;

   int hm = HHMM(TimeCurrent());

   // --- Fibonacci
   if(InpFbOn)
     {
      PSection("fb", y, "FIBONACCI  " + U(0x00B7) + "  MATTINA", ItaTime(InpFbHourStart) + " " + U(0x2013) + " " + ItaTime(InpFbHourEnd));
      bool inS = FbInSession();
      PRow("fb1", y, "Stato", inS ? "In fascia oraria" : "Fuori orario", inS ? CLR_GREEN : CLR_MUTED);
      string leg = "Nessun impulso";
      color  lc  = CLR_MUTED;
      if(g_fbLegOk)
        {
         leg = StringFormat("%s  %s " + U(0x2192) + " %s", g_fbDir > 0 ? "Rialzista" : "Ribassista",
                            DoubleToString(g_fbDir > 0 ? g_fbL : g_fbH, _Digits), DoubleToString(g_fbDir > 0 ? g_fbH : g_fbL, _Digits));
         lc  = g_fbLegDead ? CLR_MUTED : (g_fbDir > 0 ? CLR_BLUE : CLR_RED);
        }
      PRow("fb2", y, "Impulso", leg, lc);
      string lv = "";
      for(int k = 0; k < 3; k++)
        {
         if(!FbLevelOn(k)) continue;
         if(lv != "") lv += "   ";
         lv += DoubleToString(g_fbLv[k], g_fbLv[k] == 0.5 ? 1 : 3) + (g_fbUsed[k] ? " usato" : " libero");
        }
      PRow("fb3", y, "Livelli", lv, CLR_TEXT);
      PRow("fb4", y, "Stop / Target", StringFormat("SL %.1f  " + U(0x00B7) + "  %s", InpFbSLFib, FbTPText()), CLR_TEXT);
      int n;
      double pl = FloatingPL(InpFbMagic, n);
      PRow("fb5", y, "Posizioni", n == 0 ? "Nessuna" : StringFormat("%d  " + U(0x00B7) + "  %s", n, Money(pl)),
           n == 0 ? CLR_MUTED : (pl >= 0 ? CLR_GREEN : CLR_RED));
      string note = g_fbLegDead ? g_fbStatus : (g_fbLegOk ? "Attendo il ritracciamento e la pin bar" : g_fbStatus);
      if(StringLen(note) > 0)
        {
         string first = StringSubstr(note, 0, 1);
         StringToUpper(first);
         note = first + StringSubstr(note, 1);
        }
      PText("fb6", x + 14, y, U(0x203A) + " " + note, CLR_MUTED, 8);
      y += 18;
     }

   // --- RSI
   if(InpRsOn)
     {
      PSection("rs", y, "RSI  " + U(0x00B7) + "  POMERIGGIO",
               InpRsUseHours ? ItaTime(InpRsHourStart) + " " + U(0x2013) + " " + ItaTime(InpRsHourEnd) : "Sempre");
      bool inS = !InpRsUseHours || (hm >= InpRsHourStart && hm < InpRsHourEnd);
      PRow("rs1", y, "Stato", inS ? "In fascia oraria" : "Fuori orario", inS ? CLR_GREEN : CLR_MUTED);
      string st = "neutro";
      color  sc = CLR_TEXT;
      if(g_rsOS)               { st = "ipervenduto, attendo il rientro"; sc = CLR_BLUE; }
      else if(g_rsOB)          { st = "ipercomprato, attendo il rientro"; sc = CLR_RED; }
      if(RsRecentSL(+1) || RsRecentSL(-1)) { st = "pausa dopo uno stop loss"; sc = CLR_MUTED; }
      PRow("rs2", y, StringFormat("RSI (%d)", InpRsPeriod), StringFormat("%.1f  " + U(0x00B7) + "  %s", g_rsNow, st), sc);
      double atr[1];
      string vol = "-";
      color  vc  = CLR_TEXT;
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      if(bid > 0 && CopyBuffer(g_rsATR, 0, 1, 1, atr) == 1)
        {
         double pct = atr[0] / bid * 100.0;
         bool ok = !InpRsUseATRFilter || (pct >= InpRsMinATRPct && pct <= InpRsMaxATRPct);
         vol = StringFormat("ATR %.3f%%  " + U(0x00B7) + "  %s", pct, ok ? "ok" : (pct < InpRsMinATRPct ? "troppo bassa" : "troppo alta"));
         vc  = ok ? CLR_TEXT : CLR_MUTED;
        }
      PRow("rs3", y, "Volatilit" + U(0x00E0), vol, vc);
      PRow("rs4", y, "Stop / Target", StringFormat("SL %.1f" + U(0x00D7) + "ATR  " + U(0x00B7) + "  BUY %s / SELL %s", InpRsSLATR,
                                                    DoubleToString(InpRsExit, 0), DoubleToString(InpRsExitSell, 0)), CLR_TEXT);
      int n;
      double pl = FloatingPL(InpRsMagic, n);
      PRow("rs5", y, "Posizioni", n == 0 ? "Nessuna" : StringFormat("%d  " + U(0x00B7) + "  %s", n, Money(pl)),
           n == 0 ? CLR_MUTED : (pl >= 0 ? CLR_GREEN : CLR_RED));
     }

   // --- oggi
   PSection("dy", y, "OGGI", StringFormat("%d operazioni", g_dayN));
   PRow("dy1", y, "Vinte / perse", StringFormat("%d / %d", g_dayWin, g_dayLoss), CLR_TEXT);
   PRow("dy2", y, "Risultato chiuso", Money(g_dayPL), g_dayPL >= 0 ? CLR_GREEN : CLR_RED);
   PRow("dy3", y, "Saldo / Equity", StringFormat("%s / %s", DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2),
                                                 DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2)), CLR_TEXT);

   // --- piede
   y += 4;
   PRect("sep2", x + 14, y, PNL_W - 28, 1, CLR_LINE, CLR_LINE);
   y += 7;
   MqlDateTime t;
   TimeToStruct(TimeTradeServer(), t);
   PText("foot", x + 14, y, StringFormat("Ora FPG %02d:%02d   " + U(0x00B7) + "   ora italiana %s", t.hour, t.min, ItaTime(t.hour * 100 + t.min)),
         CLR_MUTED, 8);
   y += 20;

   if(y - InpPanelY != g_pnlH)
     {
      g_pnlH = y - InpPanelY;
      ObjectSetInteger(0, PNL + "bg", OBJPROP_YSIZE, g_pnlH);
     }
   ChartRedraw();
  }

string FbTPText()
  {
   switch(InpFbTPMode)
     {
      case TP_RR1:    return "TP RR 1:1";
      case TP_RR15:   return "TP RR 1:1.5";
      case TP_RR2:    return "TP RR 1:2";
      case TP_RR3:    return "TP RR 1:3";
      case TP_SWING:  return "TP swing";
      case TP_EXT272: return "TP -0.272";
      case TP_EXT618: return "TP -0.618";
      default:        return "TP ATR";
     }
  }
//+------------------------------------------------------------------+
