//+------------------------------------------------------------------+
//|                                              FiboRetraceM1.mq5   |
//|  v1.1 - Ritracciamento di Fibonacci (0.382 / 0.5 / 0.618)        |
//|  - time frame a scelta: M1 (default), M5, M15, H1, H4            |
//|  - chiusura prima del weekend (opzionale)                         |
//|  - trova l'ultimo impulso M1 (swing low -> swing high o viceversa)|
//|  - quando il prezzo ritraccia nella zona apre nella direzione     |
//|    dell'impulso: limit, mercato, oppure mercato dopo pin bar /    |
//|    engulfing                                                      |
//|  - SL sul livello 1.1 (oltre lo swing), TP a scelta: RR, livelli  |
//|    di Fibonacci o ATR                                             |
//|  - pensato per l'ottimizzazione: ogni combinazione e' un input    |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "1.10"
#property description "Ritracciamento di Fibonacci su M1: ingresso a 0.382 / 0.5 / 0.618, SL a 1.1"

#include <Trade\Trade.mqh>

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
   TP_ATR    = 7  // ATR M1 x InpTPATRMult
  };

enum TrendFilter
  {
   TREND_NONE   = 0, // Nessuno: basta la direzione dell'impulso
   TREND_EMA    = 1, // EMA in salita (buy) / in discesa (sell)
   TREND_STRUCT = 2  // Struttura: massimi e minimi crescenti (buy) / decrescenti (sell)
  };

enum FiboTF
  {
   TF_M1  = 0, // M1
   TF_M5  = 1, // M5
   TF_M15 = 2, // M15
   TF_H1  = 3, // H1
   TF_H4  = 4  // H4
  };

enum SessMode
  {
   SESS_ALL  = 0, // Tutto il giorno
   SESS_1    = 1, // Solo fascia 1
   SESS_2    = 2, // Solo fascia 2
   SESS_BOTH = 3  // Fascia 1 + fascia 2
  };

//--- parametri ------------------------------------------------------
input group "Base"
input double      InpLots        = 0.01;         // Lotti
input long        InpMagic       = 61800;        // Magic number
input FiboTF      InpTF          = TF_M1;        // Time frame di swing, candele e indicatori

input group "Ingresso"
input EntryMode   InpEntryMode   = ENTRY_LIMIT;  // Tipo di ingresso
input bool        InpLvl382      = true;         // Entra a 0.382
input bool        InpLvl500      = true;         // Entra a 0.5
input bool        InpLvl618      = true;         // Entra a 0.618
input double      InpTouchTol    = 0.06;         // Mercato: entra solo entro questa frazione dello swing oltre il livello
input double      InpPinWick     = 0.6;          // Pin bar: coda almeno questa frazione della candela

input group "Stop loss / Take profit"
input double      InpSLFib       = 1.1;          // SL sul livello di Fibonacci (1.1 = oltre lo swing)
input TPMode      InpTPMode      = TP_RR2;       // Take profit
input double      InpTPATRMult   = 2.0;          // TP ATR: multiplo dell'ATR del time frame

input group "Swing e trend"
input int         InpSwingDepth  = 5;            // Candele a sinistra e a destra per confermare uno swing
input int         InpLookback    = 300;          // Candele analizzate (del time frame scelto)
input double      InpMinLegATR   = 2.0;          // Impulso minimo = ATR del time frame x questo
input int         InpMinLegPts   = 0;            // Impulso minimo in punti (0 = off)
input int         InpMaxLegBars  = 60;           // Ignora l'impulso dopo X candele dalla fine
input TrendFilter InpTrendFilter = TREND_NONE;   // Filtro trend
input int         InpEMAPeriod   = 50;           // Periodo EMA del filtro trend

input group "Orari (ora di MT5 = ora italiana + 1)"
input SessMode    InpSessMode    = SESS_ALL;     // Quando lavora
input int         InpSess1Start  = 10;           // Fascia 1 inizio (10 = 9:00 italiane)
input int         InpSess1End    = 13;           // Fascia 1 fine (13 = 12:00 italiane)
input int         InpSess2Start  = 15;           // Fascia 2 inizio (15 = 14:00 italiane)
input int         InpSess2End    = 19;           // Fascia 2 fine (19 = 18:00 italiane)

input group "Weekend (ora di MT5)"
input bool        InpWeekend     = false;        // Venerdi': niente trade nuovi la sera e chiusura prima del weekend
input int         InpFriNoNew    = 2100;         // Venerdi': niente trade nuovi dalle (HHMM)
input int         InpFriClose    = 2245;         // Venerdi': chiude tutto alle (HHMM)

input group "Ottimizzazione"
input int         InpMinTrades   = 30;           // Custom max: scarta i passaggi con meno trade

//--- stato ------------------------------------------------------------
#define MAX_SWINGS 40

CTrade   g_trade;
ENUM_TIMEFRAMES g_tf = PERIOD_M1;
int      g_hATR = INVALID_HANDLE;
int      g_hEMA = INVALID_HANDLE;
datetime g_lastBar = 0;
bool     g_draw    = false;

// impulso corrente
bool     g_legOk   = false;  // c'e' un impulso
bool     g_legDead = true;   // impulso non piu' tradabile
int      g_legDir  = 0;      // +1 impulso in salita (cerca buy), -1 in discesa (cerca sell)
double   g_H = 0, g_L = 0;
datetime g_tH = 0, g_tL = 0;
double   g_atr = 0;
double   g_extreme = 0;      // punto piu' profondo del ritracciamento finora
string   g_status = "avvio";

double   g_lv[3]   = {0.382, 0.5, 0.618};
bool     g_used[3];          // livello gia' usato su questo impulso
ulong    g_pend[3];          // ticket del limit per livello

//+------------------------------------------------------------------+
int OnInit()
  {
   if(!InpLvl382 && !InpLvl500 && !InpLvl618)
     {
      Print("Nessun livello attivo: attiva almeno uno tra 0.382, 0.5 e 0.618");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpSwingDepth < 1 || InpLookback < 4 * InpSwingDepth + 10 || InpSLFib <= 1.0)
      return INIT_PARAMETERS_INCORRECT;

   switch(InpTF)
     {
      case TF_M5:  g_tf = PERIOD_M5;  break;
      case TF_M15: g_tf = PERIOD_M15; break;
      case TF_H1:  g_tf = PERIOD_H1;  break;
      case TF_H4:  g_tf = PERIOD_H4;  break;
      default:     g_tf = PERIOD_M1;  break;
     }

   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(50);

   g_hATR = iATR(_Symbol, g_tf, 14);
   g_hEMA = iMA(_Symbol, g_tf, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR == INVALID_HANDLE || g_hEMA == INVALID_HANDLE)
     {
      Print("Errore creazione indicatori: ", GetLastError());
      return INIT_FAILED;
     }

   bool tester = (bool)MQLInfoInteger(MQL_TESTER);
   g_draw = !tester || (bool)MQLInfoInteger(MQL_VISUAL_MODE);

   ArrayInitialize(g_used, false);
   ArrayInitialize(g_pend, 0);
   DeleteStrayOrders();

   PrintFormat("FiboRetrace %s su %s: ingresso=%s livelli=%s%s%s SL=%.3f TP=%s orari=%s trend=%s",
               EnumToString(g_tf), _Symbol, EnumToString(InpEntryMode),
               InpLvl382 ? "0.382 " : "", InpLvl500 ? "0.5 " : "", InpLvl618 ? "0.618" : "",
               InpSLFib, EnumToString(InpTPMode), EnumToString(InpSessMode), EnumToString(InpTrendFilter));
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   CancelPendings();
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hEMA != INVALID_HANDLE) IndicatorRelease(g_hEMA);
   ObjectsDeleteAll(0, "FIBM1_");
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   // weekend: il venerdi' sera chiude tutto, cosi' nessun trade resta aperto sul gap del lunedi'
   if(InpWeekend && IsFriday(TimeCurrent()) && HHMM(TimeCurrent()) >= InpFriClose)
     {
      CancelPendings();
      CloseAll();
     }

   datetime bt = iTime(_Symbol, g_tf, 0);
   bool newBar = (bt != g_lastBar && bt != 0);
   if(newBar)
     {
      g_lastBar = bt;
      UpdateLeg();
     }

   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk))
      return;

   if(g_legOk && !g_legDead)
     {
      double slLevel = FibPrice(InpSLFib);
      if(g_legDir > 0)
        {
         g_extreme = MathMin(g_extreme, tk.bid);
         if(tk.bid > g_H)         Kill("nuovo massimo oltre lo swing, attendo il prossimo");
         else if(tk.bid <= slLevel) Kill("prezzo oltre il livello SL, impulso annullato");
        }
      else
        {
         g_extreme = MathMax(g_extreme, tk.bid);
         if(tk.bid < g_L)         Kill("nuovo minimo oltre lo swing, attendo il prossimo");
         else if(tk.bid >= slLevel) Kill("prezzo oltre il livello SL, impulso annullato");
        }
     }

   if(!g_legOk || g_legDead)
     {
      CancelPendings();
      ShowPanel();
      return;
     }

   if(!InSession())
     {
      CancelPendings();
      g_status = "fuori orario";
      ShowPanel();
      return;
     }

   switch(InpEntryMode)
     {
      case ENTRY_LIMIT:  ManageLimits(tk); break;
      case ENTRY_MARKET: CheckTouch(tk);   break;
      default:           if(newBar) CheckConfirm(tk); break;
     }
   ShowPanel();
  }

//+------------------------------------------------------------------+
//| Impulso: ultimo swing low/high confermati con i frattali          |
//+------------------------------------------------------------------+
bool IsSwingHigh(const double &hi[], int i, int n)
  {
   for(int k = 1; k <= n; k++)
      if(hi[i + k] > hi[i] || hi[i - k] >= hi[i])
         return false;
   return true;
  }

bool IsSwingLow(const double &lo[], int i, int n)
  {
   for(int k = 1; k <= n; k++)
      if(lo[i + k] < lo[i] || lo[i - k] <= lo[i])
         return false;
   return true;
  }

void UpdateLeg()
  {
   int n = InpLookback, N = InpSwingDepth;
   double hi[], lo[], cl[];
   datetime tm[];
   ArraySetAsSeries(hi, true);
   ArraySetAsSeries(lo, true);
   ArraySetAsSeries(cl, true);
   ArraySetAsSeries(tm, true);
   if(CopyHigh(_Symbol, g_tf, 0, n, hi) < n || CopyLow(_Symbol, g_tf, 0, n, lo) < n ||
      CopyClose(_Symbol, g_tf, 0, n, cl) < n || CopyTime(_Symbol, g_tf, 0, n, tm) < n)
      return;

   double a[];
   if(CopyBuffer(g_hATR, 0, 1, 1, a) == 1)
      g_atr = a[0];

   // swing dal piu' recente al piu' vecchio
   int sh[MAX_SWINGS], sl[MAX_SWINGS];
   int nsh = 0, nsl = 0;
   for(int i = N + 1; i < n - N && (nsh < MAX_SWINGS || nsl < MAX_SWINGS); i++)
     {
      if(nsh < MAX_SWINGS && IsSwingHigh(hi, i, N)) sh[nsh++] = i;
      if(nsl < MAX_SWINGS && IsSwingLow(lo, i, N))  sl[nsl++] = i;
     }
   if(nsh == 0 || nsl == 0 || sh[0] == sl[0])
     {
      NoLeg("nessuno swing chiaro");
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

   bool same = g_legOk && dir == g_legDir && tH == g_tH && tL == g_tL;
   if(!same)
     {
      CancelPendings();
      g_legOk   = true;
      g_legDead = false;
      g_legDir  = dir;
      g_H = H; g_L = L; g_tH = tH; g_tL = tL;
      ArrayInitialize(g_used, false);
      ArrayInitialize(g_pend, 0);
      g_status = StringFormat("impulso %s %s -> %s", dir > 0 ? "rialzista" : "ribassista",
                              DoubleToString(dir > 0 ? L : H, _Digits), DoubleToString(dir > 0 ? H : L, _Digits));

      string why = "";
      if(!LegValid(dir, s, hi, lo, sh, nsh, sl, nsl, why))
         Kill(why);
      DrawFib();
     }
   if(g_legDead)
      return;

   // cosa e' successo dopo la fine dell'impulso
   g_extreme = (dir > 0) ? H : L;
   for(int i = 1; i < e; i++)
     {
      if(dir > 0)
        {
         if(hi[i] > H) { Kill("nuovo massimo oltre lo swing, attendo il prossimo"); return; }
         if(cl[i] < L) { Kill("chiusura sotto lo swing low, impulso annullato"); return; }
         g_extreme = MathMin(g_extreme, lo[i]);
        }
      else
        {
         if(lo[i] < L) { Kill("nuovo minimo oltre lo swing, attendo il prossimo"); return; }
         if(cl[i] > H) { Kill("chiusura sopra lo swing high, impulso annullato"); return; }
         g_extreme = MathMax(g_extreme, hi[i]);
        }
     }
   if(e > InpMaxLegBars)
      Kill("impulso troppo vecchio");
  }

bool LegValid(int dir, int s, const double &hi[], const double &lo[],
              const int &sh[], int nsh, const int &sl[], int nsl, string &why)
  {
   double R = g_H - g_L;
   if(R <= 0 || R < InpMinLegATR * g_atr || R < InpMinLegPts * _Point)
     {
      why = "impulso troppo piccolo";
      return false;
     }

   if(InpTrendFilter == TREND_EMA)
     {
      double e1[], es[];
      if(CopyBuffer(g_hEMA, 0, 1, 1, e1) != 1 || CopyBuffer(g_hEMA, 0, s, 1, es) != 1)
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
   else if(InpTrendFilter == TREND_STRUCT)
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
      bool ok = (dir > 0) ? (g_H > hi[ph] && g_L > lo[pl]) : (g_L < lo[pl] && g_H < hi[ph]);
      if(!ok)
        {
         why = (dir > 0) ? "niente massimi e minimi crescenti" : "niente massimi e minimi decrescenti";
         return false;
        }
     }
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

void NoLeg(string why)
  {
   CancelPendings();
   g_legOk   = false;
   g_legDead = true;
   g_status  = why;
  }

void Kill(string why)
  {
   g_legDead = true;
   g_status  = why;
   CancelPendings();
  }

//+------------------------------------------------------------------+
//| Livelli, SL e TP                                                  |
//+------------------------------------------------------------------+
// 0 = fine dell'impulso, 1 = inizio, 1.1 = oltre l'inizio, -0.272 = estensione
double FibPrice(double f)
  {
   double R = g_H - g_L;
   return (g_legDir > 0) ? g_H - f * R : g_L + f * R;
  }

bool LevelOn(int k)
  {
   return (k == 0) ? InpLvl382 : (k == 1) ? InpLvl500 : InpLvl618;
  }

string LevelCmt(int k)
  {
   return (k == 0) ? "FIB382" : (k == 1) ? "FIB500" : "FIB618";
  }

double Norm(double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0)
      return NormalizeDouble(p, _Digits);
   return NormalizeDouble(MathRound(p / ts) * ts, _Digits);
  }

bool CalcSLTP(double entry, double &sl, double &tp)
  {
   int dir = g_legDir;
   sl = FibPrice(InpSLFib);
   double risk = MathAbs(entry - sl);
   if(risk <= 0 || (dir > 0 && sl >= entry) || (dir < 0 && sl <= entry))
      return false;

   switch(InpTPMode)
     {
      case TP_RR1:    tp = entry + dir * 1.0 * risk; break;
      case TP_RR15:   tp = entry + dir * 1.5 * risk; break;
      case TP_RR2:    tp = entry + dir * 2.0 * risk; break;
      case TP_RR3:    tp = entry + dir * 3.0 * risk; break;
      case TP_SWING:  tp = FibPrice(0.0);    break;
      case TP_EXT272: tp = FibPrice(-0.272); break;
      case TP_EXT618: tp = FibPrice(-0.618); break;
      default:        tp = entry + dir * InpTPATRMult * g_atr; break;
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

//+------------------------------------------------------------------+
//| Ingresso con ordini limit                                         |
//+------------------------------------------------------------------+
void ManageLimits(const MqlTick &tk)
  {
   double minD = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   for(int k = 0; k < 3; k++)
     {
      if(!LevelOn(k) || g_used[k])
         continue;
      if(g_pend[k] != 0)
        {
         if(OrderSelect(g_pend[k]))
            continue;          // ancora in attesa
         g_used[k] = true;     // eseguito (o tolto a mano): non lo rimette
         g_pend[k] = 0;
         continue;
        }

      double px = Norm(FibPrice(g_lv[k]));
      // il prezzo e' gia' sul livello o oltre: il limit non si puo' piu' mettere
      if((g_legDir > 0 && tk.ask <= px + minD) || (g_legDir < 0 && tk.bid >= px - minD))
        {
         g_used[k] = true;
         continue;
        }
      double sl, tp;
      if(!CalcSLTP(px, sl, tp))
        {
         g_used[k] = true;
         continue;
        }
      bool ok = (g_legDir > 0)
                ? g_trade.BuyLimit(InpLots, px, _Symbol, sl, tp, ORDER_TIME_GTC, 0, LevelCmt(k))
                : g_trade.SellLimit(InpLots, px, _Symbol, sl, tp, ORDER_TIME_GTC, 0, LevelCmt(k));
      if(ok && g_trade.ResultOrder() > 0)
         g_pend[k] = g_trade.ResultOrder();
      else
        {
         g_used[k] = true;
         PrintFormat("Limit %s rifiutato: %d %s", LevelCmt(k), g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
        }
     }
  }

void CancelPendings()
  {
   for(int k = 0; k < 3; k++)
     {
      if(g_pend[k] == 0)
         continue;
      ulong t = g_pend[k];
      g_pend[k] = 0;
      if(OrderSelect(t))
         g_trade.OrderDelete(t);
      else
         g_used[k] = true;   // nel frattempo e' stato eseguito
     }
  }

void DeleteStrayOrders()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t > 0 && OrderGetInteger(ORDER_MAGIC) == InpMagic && OrderGetString(ORDER_SYMBOL) == _Symbol)
         g_trade.OrderDelete(t);
     }
  }

//+------------------------------------------------------------------+
//| Ingresso a mercato al tocco del livello                           |
//+------------------------------------------------------------------+
void CheckTouch(const MqlTick &tk)
  {
   double tol = InpTouchTol * (g_H - g_L);
   for(int k = 0; k < 3; k++)
     {
      if(!LevelOn(k) || g_used[k])
         continue;
      double px = FibPrice(g_lv[k]);
      if(g_legDir > 0)
        {
         if(tk.bid > px) continue;                               // non ancora arrivato
         if(tk.bid < px - tol) { g_used[k] = true; continue; }   // gia' troppo oltre: perso
        }
      else
        {
         if(tk.bid < px) continue;
         if(tk.bid > px + tol) { g_used[k] = true; continue; }
        }
      OpenMarket(k, tk);
     }
  }

//+------------------------------------------------------------------+
//| Ingresso a mercato dopo pin bar / engulfing nella zona            |
//+------------------------------------------------------------------+
void CheckConfirm(const MqlTick &tk)
  {
   bool bull = (g_legDir > 0);
   bool pat  = false;
   if(InpEntryMode == ENTRY_PINBAR || InpEntryMode == ENTRY_PIN_OR_ENG) pat = pat || IsPinBar(bull);
   if(InpEntryMode == ENTRY_ENGULF || InpEntryMode == ENTRY_PIN_OR_ENG) pat = pat || IsEngulfing(bull);
   if(!pat)
      return;

   // la candela di conferma deve stare nella zona di ritracciamento
   double zone = FibPrice(0.382);
   if(bull ? iLow(_Symbol, g_tf, 1) > zone : iHigh(_Symbol, g_tf, 1) < zone)
      return;

   // un solo trade per conferma, sul livello piu' profondo raggiunto e non ancora usato
   int pick = -1;
   for(int k = 0; k < 3; k++)
     {
      if(!LevelOn(k))
         continue;
      double px = FibPrice(g_lv[k]);
      bool reached = bull ? (g_extreme <= px) : (g_extreme >= px);
      if(reached)
         pick = k;
     }
   if(pick < 0 || g_used[pick])
      return;
   for(int k = 0; k <= pick; k++)
      g_used[k] = true;
   OpenMarket(pick, tk);
  }

bool IsPinBar(bool bull)
  {
   double o = iOpen(_Symbol, g_tf, 1), h = iHigh(_Symbol, g_tf, 1);
   double l = iLow(_Symbol, g_tf, 1),  c = iClose(_Symbol, g_tf, 1);
   double range = h - l;
   if(range <= 0)
      return false;
   double body  = MathAbs(c - o);
   double lower = MathMin(o, c) - l;
   double upper = h - MathMax(o, c);
   if(bull)
      return lower >= InpPinWick * range && lower >= 2.0 * body;
   return upper >= InpPinWick * range && upper >= 2.0 * body;
  }

bool IsEngulfing(bool bull)
  {
   double o1 = iOpen(_Symbol, g_tf, 1), c1 = iClose(_Symbol, g_tf, 1);
   double o2 = iOpen(_Symbol, g_tf, 2), c2 = iClose(_Symbol, g_tf, 2);
   if(MathAbs(c1 - o1) <= MathAbs(c2 - o2))
      return false;
   if(bull)
      return c1 > o1 && c2 < o2 && c1 >= o2 && o1 <= c2;
   return c1 < o1 && c2 > o2 && c1 <= o2 && o1 >= c2;
  }

void OpenMarket(int k, const MqlTick &tk)
  {
   g_used[k] = true;   // un tentativo per livello: niente raffiche di ordini se il broker rifiuta
   double entry = (g_legDir > 0) ? tk.ask : tk.bid;
   double sl, tp;
   if(!CalcSLTP(entry, sl, tp))
      return;
   bool ok = (g_legDir > 0)
             ? g_trade.Buy(InpLots, _Symbol, 0, sl, tp, LevelCmt(k))
             : g_trade.Sell(InpLots, _Symbol, 0, sl, tp, LevelCmt(k));
   if(!ok)
      PrintFormat("Ordine %s rifiutato: %d %s", LevelCmt(k), g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
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

void CloseAll()
  {
   for(int k = PositionsTotal() - 1; k >= 0; k--)
     {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(g_trade.PositionClose(tk))
         Print("Posizione chiusa prima del weekend: ", tk);
     }
  }

bool InSession()
  {
   if(InpWeekend && IsFriday(TimeCurrent()) && HHMM(TimeCurrent()) >= InpFriNoNew)
      return false;
   if(InpSessMode == SESS_ALL)
      return true;
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   bool s1 = dt.hour >= InpSess1Start && dt.hour < InpSess1End;
   bool s2 = dt.hour >= InpSess2Start && dt.hour < InpSess2End;
   if(InpSessMode == SESS_1) return s1;
   if(InpSessMode == SESS_2) return s2;
   return s1 || s2;
  }

//+------------------------------------------------------------------+
//| Grafico                                                           |
//+------------------------------------------------------------------+
void DrawFib()
  {
   if(!g_draw)
      return;
   string nm = "FIBM1_leg";
   ObjectDelete(0, nm);
   // primo punto = inizio dell'impulso (livello 1), secondo = fine (livello 0)
   datetime t1 = (g_legDir > 0) ? g_tL : g_tH;
   double   p1 = (g_legDir > 0) ? g_L  : g_H;
   datetime t2 = (g_legDir > 0) ? g_tH : g_tL;
   double   p2 = (g_legDir > 0) ? g_H  : g_L;
   if(!ObjectCreate(0, nm, OBJ_FIBO, 0, t1, p1, t2, p2))
      return;
   double lv[] = {0.0, 0.382, 0.5, 0.618, 1.0, 0.0, -0.272, -0.618};
   lv[5] = InpSLFib;
   int cnt = ArraySize(lv);
   ObjectSetInteger(0, nm, OBJPROP_LEVELS, cnt);
   for(int i = 0; i < cnt; i++)
     {
      ObjectSetDouble(0, nm, OBJPROP_LEVELVALUE, i, lv[i]);
      ObjectSetString(0, nm, OBJPROP_LEVELTEXT, i, (i == 5 ? "SL " : "") + DoubleToString(lv[i], 3) + "  %$");
      ObjectSetInteger(0, nm, OBJPROP_LEVELCOLOR, i, i == 5 ? clrRed : (lv[i] > 0.3 && lv[i] < 0.7) ? clrGold : clrSilver);
     }
   ObjectSetInteger(0, nm, OBJPROP_COLOR, g_legDir > 0 ? clrDodgerBlue : clrOrangeRed);
   ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, true);
   ChartRedraw();
  }

void ShowPanel()
  {
   if(!g_draw)
      return;
   string lv = "";
   for(int k = 0; k < 3; k++)
      if(LevelOn(k))
         lv += StringFormat("  %s %s", LevelCmt(k), g_pend[k] != 0 ? "limit" : g_used[k] ? "usato" : "libero");
   Comment(StringFormat("FiboRetraceM1  |  %s  |  TP %s\n%s%s\nLivelli:%s",
                        EnumToString(InpEntryMode), EnumToString(InpTPMode),
                        g_legDead ? "IN ATTESA: " : "ATTIVO: ", g_status, lv));
  }

//+------------------------------------------------------------------+
//| Custom max: recovery factor (profitto / drawdown), solo con       |
//| abbastanza trade per essere significativo                         |
//+------------------------------------------------------------------+
double OnTester()
  {
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < InpMinTrades)
      return -1000;
   double profit = TesterStatistics(STAT_PROFIT);
   double dd     = TesterStatistics(STAT_EQUITY_DD);
   return profit / MathMax(dd, 1.0);
  }
//+------------------------------------------------------------------+
