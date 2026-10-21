//+------------------------------------------------------------------+
//|                                                 RSI_M1_XAU.mq5   |
//|  Bot RSI(28) su M1, sempre attivo, senza filtri:                 |
//|  - BUY quando l'RSI scende a 30 o sotto e una candela M1 chiude  |
//|    con l'RSI di nuovo sopra 30                                   |
//|  - SELL quando l'RSI sale a 70 o sopra e una candela M1 chiude   |
//|    con l'RSI di nuovo sotto 70                                   |
//|  Un solo trade per ogni tocco di 30/70                           |
//|  SL = ATR x moltiplicatore (si adatta alla volatilita')          |
//|  TP = quando l'RSI torna a 50                                    |
//|  Opzioni (accendi/spegni): chiusura prima del weekend, fascia    |
//|  oraria di entrata, volatilita' (ATR) minima e massima           |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "3.10"
#property description "RSI M1: entra al rientro da 30/70, esce quando l'RSI torna a 50, SL in ATR"

#include <Trade\Trade.mqh>

//--- parametri ------------------------------------------------------
input group "Base"
input double InpLots           = 0.01;  // Lotti (fisso)
input long   InpMagic          = 54001; // Magic number

input group "RSI (M1)"
input int    InpRSIPeriod      = 28;    // Periodo RSI
input double InpRSILow         = 30;    // BUY quando l'RSI rientra sopra questo livello
input double InpRSIHigh        = 70;    // SELL quando l'RSI rientra sotto questo livello
input double InpRSIExit        = 50;    // TP: BUY chiude con RSI >= questo, SELL con RSI <= 100 - questo

input group "Stop loss (ATR)"
input ENUM_TIMEFRAMES InpATRTF = PERIOD_M1; // Time frame ATR
input int    InpATRPeriod      = 14;    // Periodo ATR
input double InpSLATR          = 2.0;   // SL = ATR x questo

input group "Operazioni"
input bool   InpOneAtTime      = true;  // Una operazione alla volta: segnale ignorato se c'e' gia' un trade aperto

input group "Weekend (ora di MT5)"
input bool   InpWeekend        = true;  // Venerdi': niente trade nuovi la sera e chiusura prima del weekend
input int    InpFriNoNew       = 2100;  // Venerdi': niente trade nuovi dalle (HHMM)
input int    InpFriClose       = 2245;  // Venerdi': chiude tutto alle (HHMM)

input group "Fascia oraria di entrata (ora di MT5 = ora italiana + 1)"
input bool   InpUseHours       = false; // Entra solo in questa fascia (le uscite restano sempre attive)
input int    InpHourStart      = 1300;  // Dalle (HHMM)
input int    InpHourEnd        = 2000;  // Alle (HHMM)

input group "Volatilita' (ATR in % del prezzo; 0,07% = circa 3 $ con il gold a 4500)"
input bool   InpUseATRFilter   = false; // Entra solo se l'ATR e' tra il minimo e il massimo
input double InpMinATRPct      = 0.065; // ATR minimo (% del prezzo): sotto lo spread pesa troppo
input double InpMaxATRPct      = 0.13;  // ATR massimo (% del prezzo): sopra e' news / mercato impazzito

//--- stato ------------------------------------------------------------
CTrade   g_trade;
int      g_hRSI      = INVALID_HANDLE;
int      g_hATR      = INVALID_HANDLE;
datetime g_lastBar   = 0;
bool     g_os        = false;  // RSI in ipervenduto (<= 30)
bool     g_ob        = false;  // RSI in ipercomprato (>= 70)
double   g_rsiNow    = 0;
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

bool IsFriday(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return dt.day_of_week == 5;
}

//+------------------------------------------------------------------+
int OnInit()
{
   g_quiet = (bool)MQLInfoInteger(MQL_OPTIMIZATION);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(30);
   g_trade.SetTypeFillingBySymbol(_Symbol);

   g_hRSI = iRSI(_Symbol, PERIOD_M1, InpRSIPeriod, PRICE_CLOSE);
   g_hATR = iATR(_Symbol, InpATRTF, InpATRPeriod);
   if(g_hRSI == INVALID_HANDLE || g_hATR == INVALID_HANDLE)
   {
      Print("RSI M1 o ATR non disponibile");
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
   // weekend: il venerdi' sera chiude tutto, cosi' nessun trade resta aperto sul gap del lunedi'
   if(InpWeekend && IsFriday(TimeCurrent()) && HHMM(TimeCurrent()) >= InpFriClose)
   {
      CloseAll(POSITION_TYPE_BUY);
      CloseAll(POSITION_TYPE_SELL);
   }

   // TP: a ogni tick, appena l'RSI torna a 50
   double now[1];
   if(CopyBuffer(g_hRSI, 0, 0, 1, now) == 1)
   {
      g_rsiNow = now[0];
      if(now[0] >= InpRSIExit)       CloseAll(POSITION_TYPE_BUY);
      if(now[0] <= 100 - InpRSIExit) CloseAll(POSITION_TYPE_SELL);
   }

   datetime bar0 = iTime(_Symbol, PERIOD_M1, 0);
   if(bar0 == 0 || bar0 == g_lastBar) return;
   g_lastBar = bar0;

   // entrata: sulla candela M1 appena chiusa, una sola volta per ogni tocco di 30/70
   double rsi[1], atr[1];
   if(CopyBuffer(g_hRSI, 0, 1, 1, rsi) != 1) return;
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) != 1 || atr[0] <= 0) return;

   if(rsi[0] <= InpRSILow) g_os = true;
   else if(g_os)
   {
      g_os = false;
      Open(+1, atr[0]);
   }

   if(rsi[0] >= InpRSIHigh) g_ob = true;
   else if(g_ob)
   {
      g_ob = false;
      Open(-1, atr[0]);
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
         Log(StringFormat("%s chiuso: RSI %.1f tornato a %s", type == POSITION_TYPE_BUY ? "BUY" : "SELL", g_rsiNow,
                          DoubleToString(InpRSIExit, 0)));
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

// dir = +1 BUY / -1 SELL
void Open(int dir, double atr)
{
   string name = dir > 0 ? "BUY" : "SELL";
   if(InpOneAtTime && CountOpen() > 0) { Log(name + ": c'e' gia' un'operazione aperta, segnale ignorato"); return; }

   datetime t  = TimeCurrent();
   int      hm = HHMM(t);
   if(InpWeekend && IsFriday(t) && hm >= InpFriNoNew)                { Log(name + ": venerdi' sera, niente trade nuovi"); return; }
   if(InpUseHours && (hm < InpHourStart || hm >= InpHourEnd))         { Log(name + ": fuori dalla fascia oraria"); return; }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0 || bid <= 0) return;

   if(InpUseATRFilter)
   {
      double pct = atr / bid * 100.0;
      if(pct < InpMinATRPct) { Log(StringFormat("%s: ATR troppo basso (%.3f%%), niente trade", name, pct)); return; }
      if(pct > InpMaxATRPct) { Log(StringFormat("%s: ATR troppo alto (%.3f%%), niente trade", name, pct)); return; }
   }

   // il broker vuole lo SL ad almeno "stops level" punti dal prezzo
   double dist    = InpSLATR * atr;
   double minDist = (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 5) * _Point;
   dist = MathMax(dist, minDist);

   double entry = dir > 0 ? ask : bid;
   double sl    = NormalizeDouble(entry - dir * dist, _Digits);

   bool ok = dir > 0 ? g_trade.Buy(NormLots(InpLots), _Symbol, 0, sl, 0, "RSI M1")
                     : g_trade.Sell(NormLots(InpLots), _Symbol, 0, sl, 0, "RSI M1");
   if(ok && (g_trade.ResultRetcode() == TRADE_RETCODE_DONE || g_trade.ResultRetcode() == TRADE_RETCODE_PLACED))
      Log(StringFormat("%s: entrata %s SL %s (%.0f punti = %.1f x ATR), TP quando l'RSI torna a %s", name,
                       DoubleToString(entry, _Digits), DoubleToString(sl, _Digits), dist / _Point, InpSLATR,
                       DoubleToString(InpRSIExit, 0)));
   else
      Log(StringFormat("%s: ordine rifiutato (%u %s)", name, g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription()));
}

//+------------------------------------------------------------------+
void UpdatePanel()
{
   if(g_quiet) return;
   string s = StringFormat("RSI M1 (%d)  |  SL %.1f x ATR  |  TP a RSI %s\n", InpRSIPeriod, InpSLATR, DoubleToString(InpRSIExit, 0));
   s += StringFormat("Weekend: %s  |  Fascia oraria: %s  |  Filtro ATR: %s\n", InpWeekend ? "SI" : "NO",
                     InpUseHours ? StringFormat("%04d-%04d", InpHourStart, InpHourEnd) : "NO", InpUseATRFilter ? "SI" : "NO");
   s += StringFormat("RSI: %.1f  %s\n", g_rsiNow, g_os ? "(sotto " + DoubleToString(InpRSILow, 0) + ", attendo il rientro)"
                                            : (g_ob ? "(sopra " + DoubleToString(InpRSIHigh, 0) + ", attendo il rientro)" : ""));
   s += StringFormat("Posizioni aperte: %d\n", CountOpen());
   Comment(s);
}
//+------------------------------------------------------------------+
