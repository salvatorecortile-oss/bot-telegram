//+------------------------------------------------------------------+
//|                                              ScalperM1_XAU.mq5   |
//|  Scalper tick-momentum per XAUUSD (replica logica analizzata):   |
//|  - una posizione alla volta                                      |
//|  - ingresso nella direzione del movimento degli ultimi N ms      |
//|  - TP fisso (50 pt) / SL = 50 pt + spread corrente               |
//|  - uscita anticipata su inversione o tempo massimo               |
//|  - filtro spread, filtro orario, limiti giornalieri              |
//|  - pannello con Start / Start One / Finish / Stop                |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "1.00"
#property description "Tick-momentum scalper XAUUSD con TP 50pt e SL 50pt+spread"

#include <Trade\Trade.mqh>

//--- parametri ------------------------------------------------------
input group "Gestione ordine"
input double InpLots               = 0.10;  // Lotti
input int    InpTPPoints           = 50;    // Take profit (punti, 50 = 0.50$)
input int    InpSLPoints           = 50;    // Stop loss base (punti)
input bool   InpSLAddSpread        = true;  // Aggiungi lo spread corrente allo SL
input int    InpDeviation          = 10;    // Slippage massimo (punti)
input long   InpMagic              = 41378;  // Magic number

input group "Segnale momentum"
input int    InpMomentumPoints     = 30;    // Movimento minimo nella finestra (punti)
input int    InpMomentumMs         = 5000;  // Finestra del movimento (millisecondi)
input int    InpMinTicksInWindow   = 5;     // Tick minimi nella finestra
input bool   InpRequireExtreme     = true;  // Prezzo deve essere vicino all'estremo della finestra
input int    InpExtremeTolPoints   = 5;     // Tolleranza dall'estremo (punti)
input int    InpCooldownMs         = 1000;  // Pausa dopo una chiusura (millisecondi)

input group "Uscita anticipata"
input int    InpMaxHoldSec         = 60;    // Chiusura dopo X secondi (0 = off)
input int    InpReverseActivatePts = 20;    // Attiva uscita su inversione dopo +X punti
input int    InpReverseExitPoints  = 20;    // Chiudi se ritraccia X punti dal massimo (0 = off)

input group "Filtri"
input int    InpMaxSpread          = 18;    // Spread massimo (punti)
input bool   InpUseTimeFilter      = true;  // Usa filtro orario (ora server)
input int    InpStartHour          = 9;     // Ora inizio (server)
input int    InpEndHour            = 21;    // Ora fine (server, esclusa)

input group "Limiti giornalieri (valuta conto, 0 = off)"
input double InpMaxDailyLoss       = 0;     // Perdita massima giornaliera
input double InpDailyTarget        = 0;     // Obiettivo giornaliero
input int    InpMaxTradesDay       = 0;     // Numero massimo trade al giorno

input group "Avvio"
input bool   InpAutoStart          = false; // Parte in RUNNING senza premere Start (sempre attivo nel tester)

//--- stato ------------------------------------------------------------
enum EAState { ST_STOPPED = 0, ST_RUNNING, ST_FINISHING };

CTrade   g_trade;
EAState  g_state = ST_STOPPED;
bool     g_oneShot = false;   // modalita' Start One

#define TICKBUF 8192
long     g_tMs[TICKBUF];
double   g_bid[TICKBUF];
int      g_head  = 0;
int      g_count = 0;

// spread stats (punti)
int      g_sprMin = INT_MAX, g_sprMax = 0;
double   g_sprSum = 0;
long     g_sprN   = 0;
int      g_sprNow = 0;

// gestione posizione
ulong    g_trackTicket = 0;
double   g_bestFav     = 0;
long     g_lastCloseMs = 0;
long     g_lastEntryMs = 0;

// statistiche giornaliere
datetime g_statsDay    = 0;
bool     g_statsDirty  = true;
double   g_dayPL       = 0;
int      g_dayTrades   = 0;
int      g_dayWins     = 0;

// pannello
string   g_pfx        = "SM1_";
long     g_lastPanelMs = 0;
string   g_lastSignal = "-";
string   g_blockReason = "";

//+------------------------------------------------------------------+
int OnInit()
  {
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetAsyncMode(false);

   if(InpTPPoints <= 0 || InpSLPoints <= 0 || InpMomentumMs <= 0)
     {
      Print("Parametri non validi: TP, SL e finestra devono essere > 0");
      return INIT_PARAMETERS_INCORRECT;
     }

   bool tester = (bool)MQLInfoInteger(MQL_TESTER);
   g_state = (InpAutoStart || tester) ? ST_RUNNING : ST_STOPPED;

   // dopo un cambio parametri / timeframe / ricompilazione riprende lo stato precedente
   string gv = StateGVName();
   if(!tester && GlobalVariableCheck(gv))
     {
      g_state = (EAState)(int)GlobalVariableGet(gv);
      GlobalVariableDel(gv);
     }

   if(!tester || (bool)MQLInfoInteger(MQL_VISUAL_MODE))
      CreatePanel();

   PrintFormat("ScalperM1 avviato su %s: TP=%d SL=%d(+spread=%s) momentum=%dpt/%dms maxSpread=%d",
               _Symbol, InpTPPoints, InpSLPoints, InpSLAddSpread ? "si" : "no",
               InpMomentumPoints, InpMomentumMs, InpMaxSpread);
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
string StateGVName()
  {
   return StringFormat("SM1_state_%s_%I64d", _Symbol, InpMagic);
  }

void OnDeinit(const int reason)
  {
   if(reason == REASON_PARAMETERS || reason == REASON_CHARTCHANGE || reason == REASON_RECOMPILE)
      GlobalVariableSet(StateGVName(), (double)g_state);
   ObjectsDeleteAll(0, g_pfx);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk) || tk.bid <= 0 || tk.ask <= 0)
      return;

   PushTick(tk.time_msc, tk.bid);
   UpdateSpread(tk);
   RefreshDailyStatsIfNeeded(tk.time);

   ulong ticket = 0;
   bool hasPos = GetMyPosition(ticket);

   if(hasPos)
      ManagePosition(ticket, tk);
   else
     {
      g_trackTicket = 0;
      if(g_state == ST_FINISHING)
         g_state = ST_STOPPED;
      if(g_state == ST_RUNNING)
         CheckEntry(tk);
     }

   if(tk.time_msc - g_lastPanelMs >= 250)
     {
      g_lastPanelMs = tk.time_msc;
      UpdatePanel();
     }
  }

//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
   if(!HistoryDealSelect(trans.deal))
      return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic)
      return;
   if(HistoryDealGetString(trans.deal, DEAL_SYMBOL) != _Symbol)
      return;

   g_statsDirty = true;
   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY)
     {
      g_lastCloseMs = HistoryDealGetInteger(trans.deal, DEAL_TIME_MSC);
      PrintFormat("Chiuso #%I64u prezzo=%.2f profitto=%.2f",
                  HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID),
                  HistoryDealGetDouble(trans.deal, DEAL_PRICE),
                  HistoryDealGetDouble(trans.deal, DEAL_PROFIT));
     }
  }

//+------------------------------------------------------------------+
//| Buffer tick                                                      |
//+------------------------------------------------------------------+
void PushTick(long tMs, double bid)
  {
   g_tMs[g_head] = tMs;
   g_bid[g_head] = bid;
   g_head = (g_head + 1) % TICKBUF;
   if(g_count < TICKBUF)
      g_count++;
  }

// Restituisce il bid all'inizio della finestra e max/min/tick dentro la finestra.
bool WindowStats(long nowMs, long winMs, double &bidAgo, double &hi, double &lo, int &ticks)
  {
   long cutoff = nowMs - winMs;
   hi = -DBL_MAX;
   lo = DBL_MAX;
   ticks = 0;
   for(int i = 1; i <= g_count; i++)
     {
      int idx = (g_head - i + TICKBUF) % TICKBUF;
      if(g_tMs[idx] <= cutoff)
        {
         // tick troppo vecchio (buco di quotazioni, apertura mercato): niente segnale
         if(cutoff - g_tMs[idx] > winMs)
            return false;
         bidAgo = g_bid[idx];
         return ticks > 0;
        }
      double b = g_bid[idx];
      if(b > hi) hi = b;
      if(b < lo) lo = b;
      ticks++;
     }
   return false; // storico ancora insufficiente
  }

//+------------------------------------------------------------------+
//| Spread                                                           |
//+------------------------------------------------------------------+
void UpdateSpread(const MqlTick &tk)
  {
   g_sprNow = (int)MathRound((tk.ask - tk.bid) / _Point);
   if(g_sprNow < g_sprMin) g_sprMin = g_sprNow;
   if(g_sprNow > g_sprMax) g_sprMax = g_sprNow;
   g_sprSum += g_sprNow;
   g_sprN++;
  }

//+------------------------------------------------------------------+
//| Entrata                                                          |
//+------------------------------------------------------------------+
void CheckEntry(const MqlTick &tk)
  {
   g_blockReason = "";

   if(!(bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !(bool)MQLInfoInteger(MQL_TRADE_ALLOWED))
     { g_blockReason = "AutoTrading disattivato"; return; }

   if(g_sprNow > InpMaxSpread)
     { g_blockReason = "spread alto"; return; }

   if(InpUseTimeFilter && !InTradingHours(tk.time))
     { g_blockReason = "fuori orario"; return; }

   if(InpMaxDailyLoss > 0 && g_dayPL <= -InpMaxDailyLoss)
     { g_blockReason = "perdita max giornaliera"; return; }
   if(InpDailyTarget > 0 && g_dayPL >= InpDailyTarget)
     { g_blockReason = "target giornaliero"; return; }
   if(InpMaxTradesDay > 0 && g_dayTrades >= InpMaxTradesDay)
     { g_blockReason = "max trade giornalieri"; return; }

   if(tk.time_msc - g_lastCloseMs < InpCooldownMs)
     { g_blockReason = "cooldown"; return; }
   if(tk.time_msc - g_lastEntryMs < 500) // evita doppi invii
      return;

   double bidAgo = 0, hi = 0, lo = 0;
   int ticks = 0;
   if(!WindowStats(tk.time_msc, InpMomentumMs, bidAgo, hi, lo, ticks))
      return;
   if(ticks < InpMinTicksInWindow)
      return;

   double delta = (tk.bid - bidAgo) / _Point;
   double tol   = InpExtremeTolPoints * _Point;

   bool buy  = delta >=  InpMomentumPoints;
   bool sell = delta <= -InpMomentumPoints;

   if(InpRequireExtreme)
     {
      if(buy  && tk.bid < hi - tol) buy  = false;
      if(sell && tk.bid > lo + tol) sell = false;
     }

   if(!buy && !sell)
      return;

   g_lastSignal = StringFormat("%s  delta %+.0f pt in %d ms", buy ? "BUY" : "SELL", delta, InpMomentumMs);
   OpenTrade(buy, tk, delta);
  }

bool InTradingHours(datetime t)
  {
   MqlDateTime d;
   TimeToStruct(t, d);
   if(InpStartHour == InpEndHour)
      return true;
   if(InpStartHour < InpEndHour)
      return d.hour >= InpStartHour && d.hour < InpEndHour;
   return d.hour >= InpStartHour || d.hour < InpEndHour; // finestra a cavallo di mezzanotte
  }

//+------------------------------------------------------------------+
double NormalizeLots(double lots)
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step > 0)
      lots = MathFloor(lots / step + 1e-9) * step;
   return MathMax(vmin, MathMin(vmax, lots));
  }

double NormPrice(double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts > 0)
      p = MathRound(p / ts) * ts;
   return NormalizeDouble(p, _Digits);
  }

void OpenTrade(bool isBuy, const MqlTick &tk, double delta)
  {
   double spread = tk.ask - tk.bid;
   double tpDist = InpTPPoints * _Point;
   double slDist = InpSLPoints * _Point + (InpSLAddSpread ? spread : 0);
   double lots   = NormalizeLots(InpLots);

   double price, sl, tp;
   if(isBuy)
     {
      price = tk.ask;
      tp = NormPrice(price + tpDist);
      sl = NormPrice(price - slDist);
     }
   else
     {
      price = tk.bid;
      tp = NormPrice(price - tpDist);
      sl = NormPrice(price + slDist);
     }

   // distanza minima stop del broker (rispetto al prezzo di chiusura)
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(minDist > 0)
     {
      double closePx = isBuy ? tk.bid : tk.ask;
      if(MathAbs(tp - closePx) < minDist || MathAbs(closePx - sl) < minDist)
        {
         g_blockReason = "stops level broker";
         return;
        }
     }

   g_lastEntryMs = tk.time_msc;
   string cmt = StringFormat("SM1 d%+.0f s%d", delta, g_sprNow);
   bool ok = isBuy ? g_trade.Buy(lots, _Symbol, price, sl, tp, cmt)
                   : g_trade.Sell(lots, _Symbol, price, sl, tp, cmt);

   uint rc = g_trade.ResultRetcode();
   if(ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED || rc == TRADE_RETCODE_DONE_PARTIAL))
     {
      PrintFormat("%s %.2f @ %.2f  SL=%.2f TP=%.2f  delta=%+.0fpt spread=%d",
                  isBuy ? "BUY" : "SELL", lots, g_trade.ResultPrice(), sl, tp, delta, g_sprNow);
      if(g_oneShot)
        {
         g_oneShot = false;
         g_state = ST_FINISHING; // si ferma quando questo trade si chiude
        }
     }
   else
     {
      PrintFormat("Ordine rifiutato: %u %s", rc, g_trade.ResultRetcodeDescription());
     }
  }

//+------------------------------------------------------------------+
//| Posizione aperta                                                 |
//+------------------------------------------------------------------+
bool GetMyPosition(ulong &ticket)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      ticket = t;
      return true;
     }
   return false;
  }

void ManagePosition(ulong ticket, const MqlTick &tk)
  {
   if(!PositionSelectByTicket(ticket))
      return;

   long   type   = PositionGetInteger(POSITION_TYPE);
   double open   = PositionGetDouble(POSITION_PRICE_OPEN);
   long   openMs = PositionGetInteger(POSITION_TIME_MSC);

   if(g_trackTicket != ticket)
     {
      g_trackTicket = ticket;
      g_bestFav = 0;
     }

   double fav = (type == POSITION_TYPE_BUY) ? (tk.bid - open) : (open - tk.ask);
   if(fav > g_bestFav)
      g_bestFav = fav;

   // uscita su inversione: solo dopo che il trade e' andato in profitto di X punti
   if(InpReverseExitPoints > 0 &&
      g_bestFav >= InpReverseActivatePts * _Point &&
      g_bestFav - fav >= InpReverseExitPoints * _Point)
     {
      ClosePos(ticket, StringFormat("inversione (max %+.0f, ora %+.0f pt)", g_bestFav / _Point, fav / _Point));
      return;
     }

   // uscita a tempo
   if(InpMaxHoldSec > 0 && tk.time_msc - openMs >= (long)InpMaxHoldSec * 1000)
     {
      ClosePos(ticket, StringFormat("tempo max (%+.0f pt)", fav / _Point));
      return;
     }
  }

void ClosePos(ulong ticket, string why)
  {
   if(g_trade.PositionClose(ticket, InpDeviation))
      PrintFormat("Chiusura anticipata #%I64u: %s", ticket, why);
   else
      PrintFormat("Chiusura #%I64u fallita: %u %s", ticket, g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
//| Statistiche giornaliere (solo trade di questo EA)                |
//+------------------------------------------------------------------+
void RefreshDailyStatsIfNeeded(datetime now)
  {
   MqlDateTime d;
   TimeToStruct(now, d);
   d.hour = 0; d.min = 0; d.sec = 0;
   datetime dayStart = StructToTime(d);

   if(!g_statsDirty && dayStart == g_statsDay)
      return;

   g_statsDay   = dayStart;
   g_statsDirty = false;
   g_dayPL = 0;
   g_dayTrades = 0;
   g_dayWins = 0;

   if(!HistorySelect(dayStart, now + 86400))
      return;

   int n = HistoryDealsTotal();
   for(int i = 0; i < n; i++)
     {
      ulong dl = HistoryDealGetTicket(i);
      if(dl == 0)
         continue;
      if(HistoryDealGetInteger(dl, DEAL_MAGIC) != InpMagic)
         continue;
      if(HistoryDealGetString(dl, DEAL_SYMBOL) != _Symbol)
         continue;

      double profit = HistoryDealGetDouble(dl, DEAL_PROFIT);
      g_dayPL += profit
                 + HistoryDealGetDouble(dl, DEAL_COMMISSION)
                 + HistoryDealGetDouble(dl, DEAL_SWAP);

      long entry = HistoryDealGetInteger(dl, DEAL_ENTRY);
      if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY)
        {
         g_dayTrades++;
         if(profit > 0)
            g_dayWins++;
        }
     }
  }

//+------------------------------------------------------------------+
//| Pannello                                                         |
//+------------------------------------------------------------------+
void MakeLabel(string name, int x, int y, int size, color clr)
  {
   string n = g_pfx + name;
   ObjectCreate(0, n, OBJ_LABEL, 0, 0, 0);
   ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, size);
   ObjectSetString(0, n, OBJPROP_FONT, "Consolas");
   ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   ObjectSetString(0, n, OBJPROP_TEXT, " ");
  }

void MakeButton(string name, string text, int x, int y, int w, color bg)
  {
   string n = g_pfx + name;
   ObjectCreate(0, n, OBJ_BUTTON, 0, 0, 0);
   ObjectSetInteger(0, n, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, n, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, n, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, n, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, n, OBJPROP_YSIZE, 24);
   ObjectSetInteger(0, n, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, n, OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, n, OBJPROP_FONTSIZE, 9);
   ObjectSetInteger(0, n, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, n, OBJPROP_HIDDEN, true);
   ObjectSetString(0, n, OBJPROP_TEXT, text);
  }

void CreatePanel()
  {
   string bg = g_pfx + "bg";
   ObjectCreate(0, bg, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, bg, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, bg, OBJPROP_XDISTANCE, 10);
   ObjectSetInteger(0, bg, OBJPROP_YDISTANCE, 20);
   ObjectSetInteger(0, bg, OBJPROP_XSIZE, 360);
   ObjectSetInteger(0, bg, OBJPROP_YSIZE, 150);
   ObjectSetInteger(0, bg, OBJPROP_BGCOLOR, C'20,24,32');
   ObjectSetInteger(0, bg, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, bg, OBJPROP_COLOR, C'70,80,100');
   ObjectSetInteger(0, bg, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, bg, OBJPROP_HIDDEN, true);

   MakeLabel("title",  20,  26, 10, clrWhite);
   MakeLabel("state",  20,  46,  9, clrAqua);
   MakeLabel("spread", 20,  64,  9, clrOrange);
   MakeLabel("day",    20,  82,  9, clrSilver);
   MakeLabel("signal", 20, 100,  9, clrSilver);

   MakeButton("btnStart", "Start",      20, 138, 80, clrDodgerBlue);
   MakeButton("btnOne",   "Start One", 105, 138, 80, clrDodgerBlue);
   MakeButton("btnFin",   "Finish",    190, 138, 80, clrSteelBlue);
   MakeButton("btnStop",  "Stop+Close",275, 138, 85, clrFireBrick);

   ObjectSetString(0, g_pfx + "title", OBJPROP_TEXT, "ScalperM1 " + _Symbol);
   UpdatePanel();
  }

string StateText()
  {
   switch(g_state)
     {
      case ST_RUNNING:   return "working";
      case ST_FINISHING: return "finishing";
      default:           return "stopped";
     }
  }

void SetText(string name, string text)
  {
   string n = g_pfx + name;
   if(ObjectFind(0, n) >= 0)
      ObjectSetString(0, n, OBJPROP_TEXT, text);
  }

void UpdatePanel()
  {
   if(ObjectFind(0, g_pfx + "bg") < 0)
      return;

   string st = "Stato: " + StateText();
   if(g_state == ST_RUNNING && g_blockReason != "")
      st += "  (" + g_blockReason + ")";
   SetText("state", st);

   double avg = g_sprN > 0 ? g_sprSum / (double)g_sprN : 0;
   SetText("spread", StringFormat("Spread: %d   min %d  media %.2f  max %d",
                                  g_sprNow, g_sprN > 0 ? g_sprMin : 0, avg, g_sprMax));

   double wr = g_dayTrades > 0 ? 100.0 * g_dayWins / g_dayTrades : 0;
   SetText("day", StringFormat("Oggi: %d trade  win %.0f%%  P/L netto %.2f",
                               g_dayTrades, wr, g_dayPL));
   SetText("signal", "Ultimo segnale: " + g_lastSignal);
   ChartRedraw();
  }

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(id != CHARTEVENT_OBJECT_CLICK || StringFind(sparam, g_pfx + "btn") != 0)
      return;

   ObjectSetInteger(0, sparam, OBJPROP_STATE, false);

   if(sparam == g_pfx + "btnStart")
      g_state = ST_RUNNING;
   else if(sparam == g_pfx + "btnOne")
     {
      // un solo trade: entra al prossimo segnale e poi si ferma
      g_state = ST_RUNNING;
      g_oneShot = true;
     }
   else if(sparam == g_pfx + "btnFin")
      g_state = ST_FINISHING;
   else if(sparam == g_pfx + "btnStop")
     {
      g_state = ST_STOPPED;
      ulong t;
      if(GetMyPosition(t))
         ClosePos(t, "Stop manuale");
     }

   if(sparam != g_pfx + "btnOne")
      g_oneShot = false;

   PrintFormat("Pulsante %s -> stato %s", StringSubstr(sparam, StringLen(g_pfx)), StateText());
   UpdatePanel();
  }
//+------------------------------------------------------------------+
