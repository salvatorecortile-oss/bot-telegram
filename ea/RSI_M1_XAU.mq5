//+------------------------------------------------------------------+
//|                                                 RSI_M1_XAU.mq5   |
//|  Bot RSI su M1, sempre attivo, senza filtri:                     |
//|  - BUY quando l'RSI scende a 30 o sotto e una candela M1 chiude  |
//|    con l'RSI di nuovo sopra 30; chiude quando l'RSI tocca 70     |
//|  - SELL quando l'RSI sale a 70 o sopra e una candela M1 chiude   |
//|    con l'RSI di nuovo sotto 70; chiude quando l'RSI tocca 30     |
//|  SL oltre il minimo/massimo del tratto in cui l'RSI e' stato     |
//|  oltre 30/70 (+ margine), nessun TP fisso                        |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "2.00"
#property description "RSI M1: entra al rientro da 30/70, esce al tocco del livello opposto, SL oltre l'estremo"

#include <Trade\Trade.mqh>

//--- parametri ------------------------------------------------------
input group "Base"
input double InpLots           = 0.01;  // Lotti (fisso)
input long   InpMagic          = 54001; // Magic number

input group "RSI (M1)"
input int    InpRSIPeriod      = 28;    // Periodo RSI
input double InpRSILow         = 30;    // BUY al rientro sopra / chiusura dei SELL al tocco
input double InpRSIHigh        = 70;    // SELL al rientro sotto / chiusura dei BUY al tocco

input group "Stop loss"
input int    InpSLBufferPts    = 20;    // Punti oltre il minimo/massimo del tratto
input double InpSLBufferATR    = 0.3;   // ...piu' questa frazione di ATR M5 (0 = off)
input int    InpATRPeriod      = 14;    // Periodo ATR M5

//--- stato ------------------------------------------------------------
CTrade   g_trade;
int      g_hRSI      = INVALID_HANDLE;
int      g_hATR      = INVALID_HANDLE;
datetime g_lastBar   = 0;
bool     g_os        = false;  // RSI in ipervenduto
double   g_osLow     = 0;      // minimo del tratto in ipervenduto
bool     g_ob        = false;  // RSI in ipercomprato
double   g_obHigh    = 0;      // massimo del tratto in ipercomprato
double   g_rsiNow    = 0;
bool     g_quiet     = false;  // in ottimizzazione: niente log e niente pannello

//+------------------------------------------------------------------+
void Log(string s)
{
   if(!g_quiet) Print(s);
}

//+------------------------------------------------------------------+
int OnInit()
{
   g_quiet = (bool)MQLInfoInteger(MQL_OPTIMIZATION);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(30);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   g_hRSI = iRSI(_Symbol, PERIOD_M1, InpRSIPeriod, PRICE_CLOSE);
   g_hATR = iATR(_Symbol, PERIOD_M5, InpATRPeriod);
   if(g_hRSI == INVALID_HANDLE || g_hATR == INVALID_HANDLE)
   {
      Print("RSI M1 o ATR M5 non disponibile");
      return INIT_FAILED;
   }
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hRSI != INVALID_HANDLE) IndicatorRelease(g_hRSI);
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   Comment("");
}

//+------------------------------------------------------------------+
void OnTick()
{
   // uscita: a ogni tick, appena l'RSI tocca il livello opposto
   double now[1];
   if(CopyBuffer(g_hRSI, 0, 0, 1, now) == 1)
   {
      g_rsiNow = now[0];
      if(now[0] >= InpRSIHigh) CloseAll(POSITION_TYPE_BUY);
      if(now[0] <= InpRSILow)  CloseAll(POSITION_TYPE_SELL);
   }

   datetime bar0 = iTime(_Symbol, PERIOD_M1, 0);
   if(bar0 == 0 || bar0 == g_lastBar) return;
   g_lastBar = bar0;

   // entrata: sulla candela M1 appena chiusa
   MqlRates r[];
   if(CopyRates(_Symbol, PERIOD_M1, 1, 1, r) != 1) return;
   double rsi[1], atr[1];
   if(CopyBuffer(g_hRSI, 0, 1, 1, rsi) != 1) return;
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) != 1 || atr[0] <= 0) return;

   if(rsi[0] <= InpRSILow)
   {
      g_osLow = g_os ? MathMin(g_osLow, r[0].low) : r[0].low;
      g_os    = true;
   }
   else if(g_os)
   {
      g_os = false;
      Open(+1, MathMin(g_osLow, r[0].low), atr[0]);
   }

   if(rsi[0] >= InpRSIHigh)
   {
      g_obHigh = g_ob ? MathMax(g_obHigh, r[0].high) : r[0].high;
      g_ob     = true;
   }
   else if(g_ob)
   {
      g_ob = false;
      Open(-1, MathMax(g_obHigh, r[0].high), atr[0]);
   }

   UpdatePanel();
}

//+------------------------------------------------------------------+
void CloseAll(ENUM_POSITION_TYPE type)
{
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetInteger(POSITION_TYPE) != type) continue;
      if(g_trade.PositionClose(tk))
         Log(StringFormat("%s chiuso: RSI %.1f al livello opposto", type == POSITION_TYPE_BUY ? "BUY" : "SELL", g_rsiNow));
   }
}

int CountOpen()
{
   int n = 0;
   for(int k = PositionsTotal() - 1; k >= 0; k--)
   {
      ulong tk = PositionGetTicket(k);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      n++;
   }
   return n;
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

// dir = +1 BUY / -1 SELL, ext = estremo del tratto oltre 30/70 (dove va lo SL)
void Open(int dir, double ext, double atr)
{
   string name = dir > 0 ? "BUY" : "SELL";
   double ask  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid  = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0 || bid <= 0) return;

   double buf = InpSLBufferPts * _Point + InpSLBufferATR * atr;
   double entry = dir > 0 ? ask : bid;
   double sl    = dir > 0 ? ext - buf : ext + buf + (ask - bid);  // lo SL del sell scatta sull'ask

   // il broker vuole lo SL ad almeno "stops level" punti dal prezzo
   double minDist = (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 5) * _Point;
   if(dir * (entry - sl) < minDist) sl = entry - dir * minDist;
   sl = NormalizeDouble(sl, _Digits);

   bool ok = dir > 0 ? g_trade.Buy(NormLots(InpLots), _Symbol, 0, sl, 0, "RSI M1")
                     : g_trade.Sell(NormLots(InpLots), _Symbol, 0, sl, 0, "RSI M1");
   if(ok && (g_trade.ResultRetcode() == TRADE_RETCODE_DONE || g_trade.ResultRetcode() == TRADE_RETCODE_PLACED))
      Log(StringFormat("%s: entrata %s SL %s (rischio %.0f punti), uscita al tocco RSI %s", name,
                       DoubleToString(entry, _Digits), DoubleToString(sl, _Digits), MathAbs(entry - sl) / _Point,
                       DoubleToString(dir > 0 ? InpRSIHigh : InpRSILow, 0)));
   else
      Log(StringFormat("%s: ordine rifiutato (%u %s)", name, g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription()));
}

//+------------------------------------------------------------------+
void UpdatePanel()
{
   if(g_quiet) return;
   string s = StringFormat("RSI M1 (%d)  |  sempre attivo, nessun filtro\n", InpRSIPeriod);
   s += StringFormat("RSI: %.1f  %s\n", g_rsiNow, g_os ? "(ipervenduto, attendo rientro sopra " + DoubleToString(InpRSILow, 0) + ")"
                                            : (g_ob ? "(ipercomprato, attendo rientro sotto " + DoubleToString(InpRSIHigh, 0) + ")" : ""));
   s += StringFormat("Posizioni aperte: %d\n", CountOpen());
   Comment(s);
}
//+------------------------------------------------------------------+
