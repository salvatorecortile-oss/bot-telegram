//+------------------------------------------------------------------+
//|                                          LiquiditySweep_XAU.mq5  |
//|  Sweep di liquidita' su 4 livelli, conferma su M5:               |
//|  - minimo e massimo di ieri (D1)                                 |
//|  - minimo e massimo del range Asia (calcolato a sessione chiusa) |
//|  Sweep    = una candela M5 chiude oltre il livello               |
//|  Entrata  = entro N candele M5 una candela chiude di nuovo       |
//|             dentro il range -> ordine a mercato alla chiusura    |
//|  SL oltre l'estremo dello sweep (+ margine), TP = rischio x RR   |
//|  Se il prezzo va troppo oltre o resta fuori troppo a lungo il    |
//|  livello e' rotto davvero: nessun trade finche' non rientra      |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "1.00"
#property description "Liquidity sweep: massimo/minimo di ieri (D1) e range Asia, conferma M5, RR fisso"

#include <Trade\Trade.mqh>

//--- parametri ------------------------------------------------------
input group "Base"
input double InpLots           = 0.01;  // Lotti (fisso)
input long   InpMagic          = 53001; // Magic number
input double InpRR             = 2.0;   // TP = rischio x questo (2 = 1:2)

input group "Livelli"
input bool   InpUseD1          = true;  // Sweep di massimo e minimo di ieri (D1)
input bool   InpUseAsia        = true;  // Sweep di massimo e minimo del range Asia
input int    InpAsiaStart      = 100;   // Range Asia: dalle (HHMM, ora di MT5)
input int    InpAsiaEnd        = 800;   // Range Asia: alle (HHMM, ora di MT5)

input group "Sweep e conferma (candele M5)"
input int    InpMaxBarsOut     = 12;    // Candele M5 max chiuse fuori dal livello (12 = 1 ora)
input double InpMaxDepthATR    = 2.0;   // Profondita' max dello sweep oltre il livello (x ATR M5, 0 = off)
input int    InpMaxDepthPts    = 0;     // Profondita' max in punti (0 = off)
input int    InpATRPeriod      = 14;    // Periodo ATR M5

input group "Stop loss e break-even"
input int    InpSLBufferPts    = 20;    // Punti oltre l'estremo dello sweep
input double InpMaxSLATR       = 4.0;   // SL massimo (x ATR M5, 0 = off): oltre, il trade si salta
input int    InpMaxSLPts       = 0;     // SL massimo in punti (0 = off)
input int    InpMinSLPts       = 50;    // SL minimo in punti (se piu' vicino viene allargato)
input double InpBreakEvenR     = 0;     // Break-even a +X R (0 = off)
input int    InpBELockPts      = 10;    // Punti bloccati al break-even

input group "Limiti"
input int    InpMaxTradesLevel = 3;     // Trade max per livello al giorno (0 = nessun limite)
input bool   InpOnePerLevel    = true;  // Un solo trade aperto per livello alla volta
input bool   InpOnePerBar      = true;  // Due livelli confermano sulla stessa candela: un solo trade
input int    InpMaxSpreadPts   = 60;    // Spread massimo in punti (0 = off)

input group "Sessioni di entrata (HHMM, ora di MT5 = ora italiana + 1)"
input bool   InpUseLondon      = true;  // Entrate nella sessione di Londra
input int    InpLonStart       = 900;   // Londra: dalle
input int    InpLonEnd         = 1400;  // Londra: alle
input bool   InpUseNY          = true;  // Entrate nella sessione di New York
input int    InpNYStart        = 1530;  // New York: dalle
input int    InpNYEnd          = 1900;  // New York: alle

input group "Grafico"
input bool   InpDrawLevels     = true;  // Disegna i livelli sul grafico

//--- stato ------------------------------------------------------------
#define NLEV 4
enum LevState { LS_OFF = 0, LS_IDLE, LS_SWEEP, LS_BLOCKED };

struct SLevel
{
   string name;
   int    side;     // -1 = minimo (setup BUY), +1 = massimo (setup SELL)
   double price;
   int    state;
   double extreme;  // estremo raggiunto durante lo sweep (dove va lo SL)
   int    barsOut;  // candele M5 chiuse fuori dal livello
   int    trades;   // trade aperti oggi su questo livello
};

CTrade   g_trade;
SLevel   g_lev[NLEV];
int      g_hATR         = INVALID_HANDLE;
datetime g_day          = 0;
datetime g_lastBar      = 0;
datetime g_lastTradeBar = 0;
int      g_lastTradeDir = 0;
bool     g_d1Done       = false;
bool     g_asiaDone     = false;
bool     g_quiet        = false;  // in ottimizzazione: niente log e niente grafica
string   g_pfx          = "LSW_";

//+------------------------------------------------------------------+
void Log(string s)
{
   if(!g_quiet) Print(s);
}

int HHMMToSec(int v) { return (v / 100) * 3600 + (v % 100) * 60; }

int HHMM(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return dt.hour * 100 + dt.min;
}

string StateName(int s)
{
   switch(s)
   {
      case LS_IDLE:    return "attesa";
      case LS_SWEEP:   return "SWEEP in corso";
      case LS_BLOCKED: return "rotto (attende rientro)";
   }
   return "-";
}

//+------------------------------------------------------------------+
int OnInit()
{
   g_quiet = (bool)MQLInfoInteger(MQL_OPTIMIZATION);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(30);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   g_hATR = iATR(_Symbol, PERIOD_M5, InpATRPeriod);
   if(g_hATR == INVALID_HANDLE)
   {
      Print("ATR non disponibile");
      return INIT_FAILED;
   }

   g_lev[0].name = "PDL";   g_lev[0].side = -1;
   g_lev[1].name = "PDH";   g_lev[1].side = +1;
   g_lev[2].name = "AsiaL"; g_lev[2].side = -1;
   g_lev[3].name = "AsiaH"; g_lev[3].side = +1;
   g_day = 0;
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   ObjectsDeleteAll(0, g_pfx);
   Comment("");
}

//+------------------------------------------------------------------+
void NewDay(datetime day)
{
   g_day          = day;
   g_d1Done       = !InpUseD1;
   g_asiaDone     = !InpUseAsia;
   g_lastTradeBar = 0;
   for(int i = 0; i < NLEV; i++)
   {
      g_lev[i].price   = 0;
      g_lev[i].state   = LS_OFF;
      g_lev[i].extreme = 0;
      g_lev[i].barsOut = 0;
      g_lev[i].trades  = 0;
   }
   if(!g_quiet) ObjectsDeleteAll(0, g_pfx);
}

bool IsOutside(const SLevel &L, double c) { return L.side < 0 ? c < L.price : c > L.price; }
bool IsInside(const SLevel &L, double c)  { return L.side < 0 ? c > L.price : c < L.price; }

void ActivateLevel(int i, double price)
{
   g_lev[i].price   = price;
   g_lev[i].extreme = 0;
   g_lev[i].barsOut = 0;
   // se l'ultima candela chiusa e' gia' fuori, il livello e' gia' rotto: serve prima un rientro
   double c = iClose(_Symbol, PERIOD_M5, 1);
   g_lev[i].state = (c > 0 && IsOutside(g_lev[i], c)) ? LS_BLOCKED : LS_IDLE;
   Log(StringFormat("Livello %s = %s (%s)", g_lev[i].name, DoubleToString(price, _Digits), StateName(g_lev[i].state)));
   DrawLevel(i);
}

bool LoadD1()
{
   if(iTime(_Symbol, PERIOD_D1, 0) < g_day) return false;  // candela di oggi non ancora disponibile
   int sh = 1;
   MqlDateTime dt;
   TimeToStruct(iTime(_Symbol, PERIOD_D1, sh), dt);
   if(dt.day_of_week == 0) sh = 2;                          // salta la candela corta della domenica
   double h = iHigh(_Symbol, PERIOD_D1, sh);
   double l = iLow(_Symbol, PERIOD_D1, sh);
   if(h <= 0 || l <= 0) return false;
   ActivateLevel(0, l);
   ActivateLevel(1, h);
   return true;
}

bool LoadAsia()
{
   int s = HHMMToSec(InpAsiaStart), e = HHMMToSec(InpAsiaEnd);
   if(e <= s) return true;  // orari non validi: range Asia non usato
   MqlRates r[];
   int n = CopyRates(_Symbol, PERIOD_M5, g_day + s, g_day + e - 1, r);
   if(n < 0) return false;  // dati non ancora pronti, riprova al prossimo tick
   if(n < (e - s) / 300 / 2)
   {
      Log("Range Asia: troppe poche candele oggi, livelli Asia non usati");
      return true;
   }
   double h = r[0].high, l = r[0].low;
   for(int k = 1; k < n; k++)
   {
      h = MathMax(h, r[k].high);
      l = MathMin(l, r[k].low);
   }
   ActivateLevel(2, l);
   ActivateLevel(3, h);
   return true;
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime now = TimeCurrent();
   datetime day = (datetime)((long)now - (long)now % 86400);
   if(day != g_day) NewDay(day);
   if(!g_d1Done) g_d1Done = LoadD1();
   if(!g_asiaDone && (int)((long)now % 86400) >= HHMMToSec(InpAsiaEnd)) g_asiaDone = LoadAsia();

   ManageBreakEven();

   datetime bar0 = iTime(_Symbol, PERIOD_M5, 0);
   if(bar0 == 0 || bar0 == g_lastBar) return;
   g_lastBar = bar0;

   MqlRates r[];
   if(CopyRates(_Symbol, PERIOD_M5, 1, 1, r) != 1) return;
   double atr[1];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) != 1 || atr[0] <= 0) return;

   for(int i = 0; i < NLEV; i++)
      ProcessLevel(i, r[0], atr[0]);

   UpdatePanel();
}

//+------------------------------------------------------------------+
bool TooDeep(const SLevel &L, double atr)
{
   double depth = L.side < 0 ? L.price - L.extreme : L.extreme - L.price;
   if(InpMaxDepthATR > 0 && depth > InpMaxDepthATR * atr) return true;
   if(InpMaxDepthPts > 0 && depth > InpMaxDepthPts * _Point) return true;
   return false;
}

// una candela M5 appena chiusa: aggiorna lo stato del livello
void ProcessLevel(int i, const MqlRates &bar, double atr)
{
   if(g_lev[i].state == LS_OFF || g_lev[i].price <= 0) return;
   double c   = bar.close;
   double ext = g_lev[i].side < 0 ? bar.low : bar.high;

   switch(g_lev[i].state)
   {
      case LS_IDLE:
         if(IsOutside(g_lev[i], c))
         {
            g_lev[i].state   = LS_SWEEP;
            g_lev[i].extreme = ext;
            g_lev[i].barsOut = 1;
            if(TooDeep(g_lev[i], atr))
            {
               g_lev[i].state = LS_BLOCKED;
               Log(g_lev[i].name + ": rottura troppo profonda, niente trade");
            }
            else
               Log(g_lev[i].name + ": sweep iniziato, attendo il rientro");
         }
         break;

      case LS_SWEEP:
         g_lev[i].extreme = g_lev[i].side < 0 ? MathMin(g_lev[i].extreme, bar.low) : MathMax(g_lev[i].extreme, bar.high);
         if(TooDeep(g_lev[i], atr))
         {
            g_lev[i].state = IsInside(g_lev[i], c) ? LS_IDLE : LS_BLOCKED;
            Log(g_lev[i].name + ": sweep troppo profondo, niente trade");
         }
         else if(IsInside(g_lev[i], c))
         {
            TryEntry(i, atr);
            g_lev[i].state = LS_IDLE;
         }
         else if(++g_lev[i].barsOut > InpMaxBarsOut)
         {
            g_lev[i].state = LS_BLOCKED;
            Log(g_lev[i].name + ": nessun rientro entro " + IntegerToString(InpMaxBarsOut) + " candele, livello rotto");
         }
         break;

      case LS_BLOCKED:
         if(IsInside(g_lev[i], c)) g_lev[i].state = LS_IDLE;
         break;
   }
}

//+------------------------------------------------------------------+
bool InSession(datetime t)
{
   int hm = HHMM(t);
   if(InpUseLondon && hm >= InpLonStart && hm < InpLonEnd) return true;
   if(InpUseNY && hm >= InpNYStart && hm < InpNYEnd) return true;
   return false;
}

bool HasOpenFor(string tag)
{
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(StringFind(PositionGetString(POSITION_COMMENT), tag) >= 0) return true;
   }
   return false;
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

void TryEntry(int i, double atr)
{
   string name = g_lev[i].name;
   string tag  = "LS " + name;
   int    dir  = -g_lev[i].side;  // sweep del minimo -> BUY, del massimo -> SELL

   if(!InSession(TimeCurrent()))                                  { Log(name + ": rientro fuori sessione, niente trade"); return; }
   if(InpMaxTradesLevel > 0 && g_lev[i].trades >= InpMaxTradesLevel) { Log(name + ": trade massimi di oggi raggiunti"); return; }
   if(InpOnePerLevel && HasOpenFor(tag))                         { Log(name + ": c'e' gia' un trade aperto su questo livello"); return; }
   if(InpOnePerBar && g_lastTradeBar == g_lastBar && g_lastTradeDir == dir) { Log(name + ": trade gia' aperto su questa candela"); return; }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0 || bid <= 0) return;
   if(InpMaxSpreadPts > 0 && ask - bid > InpMaxSpreadPts * _Point) { Log(name + ": spread troppo alto"); return; }

   double entry, sl, risk;
   if(dir > 0)
   {
      entry = ask;
      sl    = g_lev[i].extreme - InpSLBufferPts * _Point;
      risk  = entry - sl;
   }
   else
   {
      entry = bid;
      sl    = g_lev[i].extreme + InpSLBufferPts * _Point + (ask - bid);  // lo SL del sell scatta sull'ask
      risk  = sl - entry;
   }
   if(risk <= 0) return;

   double minSL = MathMax(InpMinSLPts, (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 5) * _Point;
   if(risk < minSL)
   {
      risk = minSL;
      sl   = entry - dir * risk;
   }
   if(InpMaxSLATR > 0 && risk > InpMaxSLATR * atr)
   {
      Log(StringFormat("%s: SL troppo lontano (%.0f punti > %.1f x ATR), niente trade", name, risk / _Point, InpMaxSLATR));
      return;
   }
   if(InpMaxSLPts > 0 && risk > InpMaxSLPts * _Point)
   {
      Log(StringFormat("%s: SL troppo lontano (%.0f punti), niente trade", name, risk / _Point));
      return;
   }

   double tp   = entry + dir * risk * InpRR;
   sl          = NormalizeDouble(sl, _Digits);
   tp          = NormalizeDouble(tp, _Digits);
   double lots = NormLots(InpLots);

   bool ok = dir > 0 ? g_trade.Buy(lots, _Symbol, 0, sl, tp, tag)
                     : g_trade.Sell(lots, _Symbol, 0, sl, tp, tag);
   if(ok && (g_trade.ResultRetcode() == TRADE_RETCODE_DONE || g_trade.ResultRetcode() == TRADE_RETCODE_PLACED))
   {
      g_lev[i].trades++;
      g_lastTradeBar = g_lastBar;
      g_lastTradeDir = dir;
      Log(StringFormat("%s %s: entrata %s SL %s TP %s (rischio %.0f punti)", dir > 0 ? "BUY" : "SELL", name,
                       DoubleToString(entry, _Digits), DoubleToString(sl, _Digits), DoubleToString(tp, _Digits), risk / _Point));
   }
   else
      Log(StringFormat("%s: ordine rifiutato (%u %s)", name, g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription()));
}

//+------------------------------------------------------------------+
// break-even a +X R: il rischio iniziale si ricava dal TP (TP = rischio x RR)
void ManageBreakEven()
{
   if(InpBreakEvenR <= 0 || InpRR <= 0) return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double stops = (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 2) * _Point;

   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;

      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);
      if(tp <= 0) continue;
      double risk = MathAbs(tp - open) / InpRR;

      if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
      {
         double nsl = NormalizeDouble(open + InpBELockPts * _Point, _Digits);
         if(sl < nsl && bid - open >= InpBreakEvenR * risk && bid - nsl > stops)
            g_trade.PositionModify(tk, nsl, tp);
      }
      else
      {
         double nsl = NormalizeDouble(open - InpBELockPts * _Point, _Digits);
         if((sl == 0 || sl > nsl) && open - ask >= InpBreakEvenR * risk && nsl - ask > stops)
            g_trade.PositionModify(tk, nsl, tp);
      }
   }
}

//+------------------------------------------------------------------+
void DrawLevel(int i)
{
   if(!InpDrawLevels || g_quiet) return;
   string nm = g_pfx + g_lev[i].name;
   if(ObjectFind(0, nm) < 0) ObjectCreate(0, nm, OBJ_HLINE, 0, 0, g_lev[i].price);
   ObjectSetDouble(0, nm, OBJPROP_PRICE, g_lev[i].price);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, i < 2 ? clrTomato : clrDeepSkyBlue);
   ObjectSetInteger(0, nm, OBJPROP_STYLE, i < 2 ? STYLE_SOLID : STYLE_DASH);
   ObjectSetString(0, nm, OBJPROP_TEXT, g_lev[i].name);
   ObjectSetString(0, nm, OBJPROP_TOOLTIP, g_lev[i].name);
}

void UpdatePanel()
{
   if(g_quiet) return;
   string s = "LiquiditySweep  |  conferma M5  |  RR 1:" + DoubleToString(InpRR, 1) + "\n";
   s += InSession(TimeCurrent()) ? "Sessione: ATTIVA\n" : "Sessione: fuori orario\n";
   for(int i = 0; i < NLEV; i++)
   {
      if(g_lev[i].state == LS_OFF) { s += g_lev[i].name + ": -\n"; continue; }
      s += StringFormat("%s %s: %s  trade oggi %d\n", g_lev[i].name, DoubleToString(g_lev[i].price, _Digits),
                        StateName(g_lev[i].state), g_lev[i].trades);
   }
   Comment(s);
}
//+------------------------------------------------------------------+
