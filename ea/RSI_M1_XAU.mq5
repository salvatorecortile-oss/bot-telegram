//+------------------------------------------------------------------+
//|                                                 RSI_M1_XAU.mq5   |
//|  Bot RSI su M1:                                                  |
//|  - BUY quando l'RSI scende a 30 o sotto e una candela M1 chiude  |
//|    con l'RSI di nuovo sopra 30                                   |
//|  - SELL quando l'RSI sale a 70 o sopra e una candela M1 chiude   |
//|    con l'RSI di nuovo sotto 70                                   |
//|  SL oltre il minimo/massimo del tratto in cui l'RSI e' stato     |
//|  oltre 30/70 (+ margine), TP = rischio x RR (1:2)                |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "1.00"
#property description "RSI M1: rientro da 30 (BUY) e da 70 (SELL), SL oltre l'estremo, RR fisso"

#include <Trade\Trade.mqh>

//--- parametri ------------------------------------------------------
input group "Base"
input double InpLots           = 0.01;  // Lotti (fisso)
input long   InpMagic          = 54001; // Magic number
input double InpRR             = 2.0;   // TP = rischio x questo (2 = 1:2)

input group "RSI (M1)"
input int    InpRSIPeriod      = 28;    // Periodo RSI
input double InpRSILow         = 30;    // Ipervenduto: BUY quando richiude sopra
input double InpRSIHigh        = 70;    // Ipercomprato: SELL quando richiude sotto

input group "Stop loss e break-even"
input int    InpSLBufferPts    = 20;    // Punti oltre il minimo/massimo del tratto
input double InpSLBufferATR    = 0.3;   // ...piu' questa frazione di ATR M5 (0 = off)
input int    InpATRPeriod      = 14;    // Periodo ATR M5
input double InpMaxSLATR       = 4.0;   // SL massimo (x ATR M5, 0 = off): oltre, il trade si salta
input int    InpMaxSLPts       = 0;     // SL massimo in punti (0 = off)
input int    InpMinSLPts       = 50;    // SL minimo in punti (se piu' vicino viene allargato)
input double InpBreakEvenR     = 0;     // Break-even a +X R (0 = off)
input int    InpBELockPts      = 10;    // Punti bloccati al break-even

input group "Limiti"
input int    InpMaxTradesDay   = 3;     // Trade max al giorno (0 = nessun limite)
input int    InpMaxOpen        = 1;     // Posizioni aperte insieme al massimo
input int    InpMaxSpreadPts   = 60;    // Spread massimo in punti (0 = off)
input int    InpTrendEMA       = 0;     // Solo a favore del trend: EMA su D1 di X giorni (0 = off)

input group "Sessioni di entrata (HHMM, ora di MT5 = ora italiana + 1)"
input bool   InpUseLondon      = true;  // Entrate nella sessione di Londra
input int    InpLonStart       = 1000;  // Londra: dalle
input int    InpLonEnd         = 1400;  // Londra: alle
input bool   InpUseNY          = true;  // Entrate nella sessione di New York
input int    InpNYStart        = 1530;  // New York: dalle
input int    InpNYEnd          = 1900;  // New York: alle

//--- stato ------------------------------------------------------------
CTrade   g_trade;
int      g_hRSI      = INVALID_HANDLE;
int      g_hATR      = INVALID_HANDLE;
int      g_hEMA      = INVALID_HANDLE;
datetime g_lastBar   = 0;
datetime g_day       = 0;
int      g_dayTrades = 0;
bool     g_os        = false;  // RSI in ipervenduto
double   g_osLow     = 0;      // minimo del tratto in ipervenduto
bool     g_ob        = false;  // RSI in ipercomprato
double   g_obHigh    = 0;      // massimo del tratto in ipercomprato
double   g_rsi       = 0;
bool     g_quiet     = false;  // in ottimizzazione: niente log e niente pannello

//+------------------------------------------------------------------+
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
   if(InpTrendEMA > 0)
   {
      g_hEMA = iMA(_Symbol, PERIOD_D1, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
      if(g_hEMA == INVALID_HANDLE)
      {
         Print("EMA D1 non disponibile");
         return INIT_FAILED;
      }
   }
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   if(g_hRSI != INVALID_HANDLE) IndicatorRelease(g_hRSI);
   if(g_hATR != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hEMA != INVALID_HANDLE) IndicatorRelease(g_hEMA);
   Comment("");
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime now = TimeCurrent();
   datetime day = (datetime)((long)now - (long)now % 86400);
   if(day != g_day)
   {
      g_day       = day;
      g_dayTrades = 0;
   }

   ManageBreakEven();

   datetime bar0 = iTime(_Symbol, PERIOD_M1, 0);
   if(bar0 == 0 || bar0 == g_lastBar) return;
   g_lastBar = bar0;

   // candela M1 appena chiusa
   MqlRates r[];
   if(CopyRates(_Symbol, PERIOD_M1, 1, 1, r) != 1) return;
   double rsi[1], atr[1];
   if(CopyBuffer(g_hRSI, 0, 1, 1, rsi) != 1) return;
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) != 1 || atr[0] <= 0) return;
   g_rsi = rsi[0];

   if(rsi[0] <= InpRSILow)
   {
      g_osLow = g_os ? MathMin(g_osLow, r[0].low) : r[0].low;
      g_os    = true;
   }
   else if(g_os)
   {
      g_os = false;
      TryEntry(+1, MathMin(g_osLow, r[0].low), atr[0]);
   }

   if(rsi[0] >= InpRSIHigh)
   {
      g_obHigh = g_ob ? MathMax(g_obHigh, r[0].high) : r[0].high;
      g_ob     = true;
   }
   else if(g_ob)
   {
      g_ob = false;
      TryEntry(-1, MathMax(g_obHigh, r[0].high), atr[0]);
   }

   UpdatePanel();
}

//+------------------------------------------------------------------+
bool InSession(datetime t)
{
   int hm = HHMM(t);
   if(InpUseLondon && hm >= InpLonStart && hm < InpLonEnd) return true;
   if(InpUseNY && hm >= InpNYStart && hm < InpNYEnd) return true;
   return false;
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
void TryEntry(int dir, double ext, double atr)
{
   string name = dir > 0 ? "BUY" : "SELL";

   if(!InSession(TimeCurrent()))                              { Log(name + ": segnale fuori sessione, niente trade"); return; }
   if(InpMaxTradesDay > 0 && g_dayTrades >= InpMaxTradesDay) { Log(name + ": trade massimi di oggi raggiunti"); return; }
   if(InpMaxOpen > 0 && CountOpen() >= InpMaxOpen)           { Log(name + ": posizioni massime gia' aperte"); return; }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0 || bid <= 0) return;
   if(g_hEMA != INVALID_HANDLE)
   {
      // trend = chiusura di ieri sopra/sotto l'EMA D1 di ieri
      double ema[1];
      double c1 = iClose(_Symbol, PERIOD_D1, 1);
      if(CopyBuffer(g_hEMA, 0, 1, 1, ema) != 1 || c1 <= 0) return;
      if((dir > 0 && c1 < ema[0]) || (dir < 0 && c1 > ema[0])) { Log(name + ": contro il trend D1, niente trade"); return; }
   }
   if(InpMaxSpreadPts > 0 && ask - bid > InpMaxSpreadPts * _Point) { Log(name + ": spread troppo alto"); return; }

   double buf = InpSLBufferPts * _Point + InpSLBufferATR * atr;
   double entry, sl, risk;
   if(dir > 0)
   {
      entry = ask;
      sl    = ext - buf;
      risk  = entry - sl;
   }
   else
   {
      entry = bid;
      sl    = ext + buf + (ask - bid);  // lo SL del sell scatta sull'ask
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

   bool ok = dir > 0 ? g_trade.Buy(lots, _Symbol, 0, sl, tp, "RSI M1")
                     : g_trade.Sell(lots, _Symbol, 0, sl, tp, "RSI M1");
   if(ok && (g_trade.ResultRetcode() == TRADE_RETCODE_DONE || g_trade.ResultRetcode() == TRADE_RETCODE_PLACED))
   {
      g_dayTrades++;
      Log(StringFormat("%s: entrata %s SL %s TP %s (rischio %.0f punti)", name,
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
void UpdatePanel()
{
   if(g_quiet) return;
   string s = StringFormat("RSI M1 (%d)  |  RR 1:%s\n", InpRSIPeriod, DoubleToString(InpRR, 1));
   s += InSession(TimeCurrent()) ? "Sessione: ATTIVA\n" : "Sessione: fuori orario\n";
   s += StringFormat("RSI: %.1f  %s\n", g_rsi, g_os ? "(ipervenduto, attendo rientro sopra " + DoubleToString(InpRSILow, 0) + ")"
                                         : (g_ob ? "(ipercomprato, attendo rientro sotto " + DoubleToString(InpRSIHigh, 0) + ")" : ""));
   s += StringFormat("Trade oggi: %d   Aperti: %d\n", g_dayTrades, CountOpen());
   Comment(s);
}
//+------------------------------------------------------------------+
