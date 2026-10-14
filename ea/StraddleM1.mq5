//+------------------------------------------------------------------+
//|                                                 StraddleM1.mq5   |
//|  Bot a ordini pendenti (BUY STOP sopra / SELL STOP sotto), M1:   |
//|  - tiene sempre un BUY STOP sopra il prezzo e un SELL STOP sotto |
//|    a distanza D, ognuno con il suo SL, senza TP                  |
//|  - i pendenti "inseguono" il prezzo quando si allontana, ma non  |
//|    scappano quando il prezzo va verso di loro: cosi' scattano    |
//|    solo sui movimenti veloci                                     |
//|  - la posizione aperta ha uno SL che segue il prezzo (trailing)  |
//|  - mentre un buy e' aperto il SELL STOP resta sotto: se il prezzo |
//|    gira, il buy chiude in trailing e parte subito il sell        |
//|  - distanze automatiche dall'ATR M1: funziona su ogni simbolo    |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "2.00"
#property description "Straddle M1: BUY STOP/SELL STOP che seguono il prezzo + trailing stop, auto-regolato"

#include <Trade\Trade.mqh>

//--- parametri ------------------------------------------------------
input group "Base"
input double InpLots          = 0.01;  // Lotti
input bool   InpAutoStart     = true;  // Parte da solo appena attaccato al grafico
input long   InpMagic         = 52001; // Magic number

input group "Distanze in punti (0 = automatico dall'ATR M1)"
input int    InpEntryPts      = 0;     // Distanza dei pendenti dal prezzo (auto = 0.50 x ATR, min 3 x spread)
input int    InpSLPts         = 0;     // Stop loss: spazio di movimento del prezzo (auto = 0.50 x ATR, min 3 x spread)
input int    InpBEPts         = 0;     // Break-even dopo +X punti (auto = 0.25 x ATR)
input int    InpBELockPts     = 0;     // Punti bloccati al break-even (auto = meta' spread, copre la commissione)
input int    InpTrailStartPts = 0;     // Trailing parte da +X punti (auto = 0.40 x ATR)
input int    InpTrailDistPts  = 0;     // Distanza del trailing (auto = 0.30 x ATR)
input int    InpMaxSpreadPts  = 0;     // Spread massimo (auto = 2 x spread normale)

input group "Candele grandi"
input bool   InpBigOnly       = true;  // Lavora solo quando ci sono candele grandi
input double InpBigK          = 1.0;   // Candela grande = range >= ATR normale x questo
input int    InpBigSpreadMult = 6;     // ...e range >= spread x questo
input int    InpActiveSec     = 120;   // Dopo una candela grande resta attivo per X secondi
input int    InpMaxPerDir     = 2;     // Posizioni max per direzione (la 2a solo con la 1a a break-even)

input group "Uscita breakout fallito"
input bool   InpFailExit      = true;  // Chiudi subito i breakout falliti
input int    InpFailSec       = 20;    // ...se dopo X secondi non e' mai andato a favore ed e' in perdita

input group "Filtro orario (ora di MT5, quella del Market Watch)"
input bool   InpUseSessions   = false; // Lavora solo in queste fasce orarie
input int    InpSess1Start    = 9;     // Fascia 1: dalle ore
input int    InpSess1End      = 12;    // Fascia 1: alle ore
input int    InpSess2Start    = 15;    // Fascia 2: dalle ore
input int    InpSess2End      = 19;    // Fascia 2: alle ore

input group "Registro"
input bool   InpLogCSV        = true;  // Salva ogni trade in MQL5/Files/StraddleM1_trades.csv

input group "Limiti giornalieri (valuta conto, 0 = off)"
input double InpMaxDailyLoss  = 0;     // Perdita massima giornaliera
input double InpDailyTarget   = 0;     // Obiettivo giornaliero
input int    InpMaxTradesDay  = 0;     // Numero massimo trade al giorno

//--- costanti --------------------------------------------------------
#define K_ENTRY       0.50   // distanza pendenti = 0.50 x ATR (minimo 3 x spread)
#define K_SL          0.50   // SL = 0.50 x ATR (minimo 3 x spread) + lo spread
#define K_BE          0.25   // break-even da +0.25 x ATR
#define K_TRAIL_START 0.40   // trailing da +0.40 x ATR
#define K_TRAIL_DIST  0.30   // trailing a 0.30 x ATR dal prezzo
#define MAXTRACK      40
#define MOVE_STEP     0.20   // sposta un pendente solo se si e' allontanato del 20% della distanza
#define MODIFY_MS     800    // minimo tempo tra due modifiche dello stesso tipo

//--- stato ------------------------------------------------------------
enum EAState { ST_STOPPED = 0, ST_RUNNING, ST_FINISHING };

CTrade   g_trade;     // ordini a mercato / modifiche posizioni
CTrade   g_pend;      // ordini pendenti
EAState  g_state   = ST_STOPPED;
bool     g_hedging = true;
int      g_hATR    = INVALID_HANDLE;
int      g_hATRn   = INVALID_HANDLE;  // ATR "normale" (30 candele) per riconoscere le candele grandi
datetime g_activeUntil = 0;
string   g_mktInfo     = "-";

// massimo a favore / contro di ogni posizione (punti), per uscita breakout fallito e registro
ulong    g_tTicket[MAXTRACK];
double   g_tBest[MAXTRACK];
double   g_tWorst[MAXTRACK];
int      g_tN = 0;

double   g_spr      = 0;
double   g_sprNorm  = 0;
long     g_sprTicks = 0;

long     g_lastBuyStopMs  = 0;
long     g_lastSellStopMs = 0;
long     g_lastTrailMs    = 0;
long     g_backoffMs      = 0;
string   g_lastReject     = "";
string   g_blockReason    = "";

datetime g_statsDay   = 0;
bool     g_statsDirty = true;
double   g_dayPL      = 0;
int      g_dayTrades  = 0;
int      g_dayWins    = 0;
double   g_dayWinSum  = 0;
double   g_dayLossSum = 0;

string   g_pfx         = "STR_";
long     g_lastPanelMs = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_pend.SetExpertMagicNumber(InpMagic);
   g_pend.SetTypeFilling(ORDER_FILLING_RETURN);

   g_hedging = (AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);
   g_hATR  = iATR(_Symbol, PERIOD_M1, 14);
   g_hATRn = iATR(_Symbol, PERIOD_M1, 30);
   if(g_hATR == INVALID_HANDLE || g_hATRn == INVALID_HANDLE)
     {
      Print("Errore creazione ATR: ", GetLastError());
      return INIT_FAILED;
     }

   bool tester = (bool)MQLInfoInteger(MQL_TESTER);
   g_state = (InpAutoStart || tester) ? ST_RUNNING : ST_STOPPED;
   string gv = StateGVName();
   if(!tester && GlobalVariableCheck(gv))
     {
      g_state = (EAState)(int)GlobalVariableGet(gv);
      GlobalVariableDel(gv);
     }

   if(!tester || (bool)MQLInfoInteger(MQL_VISUAL_MODE))
      CreatePanel();

   PrintFormat("StraddleM1 su %s: conto %s", _Symbol, g_hedging ? "hedging" : "netting");
   return INIT_SUCCEEDED;
  }

string StateGVName()
  {
   return StringFormat("STR_state_%s_%I64d", _Symbol, InpMagic);
  }

void OnDeinit(const int reason)
  {
   if(reason == REASON_PARAMETERS || reason == REASON_CHARTCHANGE || reason == REASON_RECOMPILE)
      GlobalVariableSet(StateGVName(), (double)g_state);
   else
      DeletePendings(); // EA tolto dal grafico: non lasciare ordini pendenti sul conto
   if(g_hATR != INVALID_HANDLE)
      IndicatorRelease(g_hATR);
   if(g_hATRn != INVALID_HANDLE)
      IndicatorRelease(g_hATRn);
   ObjectsDeleteAll(0, g_pfx);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk) || tk.bid <= 0 || tk.ask <= 0)
      return;

   UpdateSpread(tk);
   RefreshDailyStatsIfNeeded(tk.time);

   UpdateMarket(tk);
   UntrackClosed();
   ManagePositions(tk);

   int nBuy = CountPos(true), nSell = CountPos(false);
   if(g_state == ST_FINISHING && nBuy + nSell == 0)
      g_state = ST_STOPPED;

   if(g_state == ST_RUNNING && CanTrade(tk))
      ManagePendings(tk, nBuy, nSell);
   else
      DeletePendings();

   if(tk.time_msc - g_lastPanelMs >= 250)
     {
      g_lastPanelMs = tk.time_msc;
      UpdatePanel();
     }
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || !HistoryDealSelect(trans.deal))
      return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic ||
      HistoryDealGetString(trans.deal, DEAL_SYMBOL) != _Symbol)
      return;
   g_statsDirty = true;
   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if((entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY) && InpLogCSV)
      LogTrade(trans.deal);
   PrintFormat("%s #%I64d prezzo=%s profitto=%.2f",
               entry == DEAL_ENTRY_IN ? "Aperto" : "Chiuso",
               HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID),
               DoubleToString(HistoryDealGetDouble(trans.deal, DEAL_PRICE), _Digits),
               HistoryDealGetDouble(trans.deal, DEAL_PROFIT));
  }

//+------------------------------------------------------------------+
//| Valori automatici                                                |
//+------------------------------------------------------------------+
void UpdateSpread(const MqlTick &tk)
  {
   g_spr = tk.ask - tk.bid;
   if(g_sprTicks == 0)
      g_sprNorm = g_spr;
   else
      g_sprNorm += (g_spr - g_sprNorm) * (g_sprTicks < 200 ? 0.05 : 0.002);
   g_sprTicks++;
  }

double ATR()
  {
   double b[];
   if(CopyBuffer(g_hATR, 0, 1, 1, b) == 1 && b[0] > 0)
      return b[0];
   return 20.0 * MathMax(g_sprNorm, _Point);
  }

double StopsMinDist()
  {
   long a = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long b = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   return (double)(a > b ? a : b) * _Point;
  }

double Dist(int inputPts, double k, double minSpreadMult)
  {
   double d = inputPts > 0 ? inputPts * _Point : k * ATR();
   return MathMax(d, MathMax(minSpreadMult * g_sprNorm, StopsMinDist() + _Point));
  }

double EntryDist()      { return Dist(InpEntryPts,      K_ENTRY,       3.0); }
double SLDist()         { return Dist(InpSLPts,         K_SL,          3.0); }
double TrailStartDist() { return Dist(InpTrailStartPts, K_TRAIL_START, 2.5); }
double TrailDist()      { return Dist(InpTrailDistPts,  K_TRAIL_DIST,  2.0); }
double BEDist()         { return Dist(InpBEPts,         K_BE,          2.0); }
double BELock()
  {
   if(InpBELockPts > 0)
      return InpBELockPts * _Point;
   return MathMax(_Point, 0.5 * g_sprNorm);
  }

double MaxSpread()
  {
   if(InpMaxSpreadPts > 0)
      return InpMaxSpreadPts * _Point;
   return MathMax(2.0 * g_sprNorm, g_sprNorm + 3 * _Point);
  }

double NormPrice(double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts > 0)
      p = MathRound(p / ts) * ts;
   return NormalizeDouble(p, _Digits);
  }

double NormalizeLots(double lots)
  {
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step > 0)
      lots = MathFloor(lots / step + 1e-9) * step;
   return MathMax(vmin, MathMin(vmax, lots));
  }

// lotto ridotto al margine libero (20% di riserva); 0 se non basta per il minimo
double AffordableLots(bool isBuy, double price)
  {
   double lots = NormalizeLots(InpLots);
   double free = AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.8;
   double m1;
   if(!OrderCalcMargin(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, _Symbol, 1.0, price, m1) || m1 <= 0)
      return lots;
   if(lots * m1 <= free)
      return lots;
   if(free / m1 < SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN))
      return 0;
   return NormalizeLots(free / m1);
  }

//+------------------------------------------------------------------+
//| Filtri                                                           |
//+------------------------------------------------------------------+
bool CanTrade(const MqlTick &tk)
  {
   g_blockReason = "";
   if(!(bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !(bool)MQLInfoInteger(MQL_TRADE_ALLOWED))
      g_blockReason = "AutoTrading disattivato";
   else if(tk.time_msc < g_backoffMs)
      g_blockReason = "broker ha rifiutato: " + g_lastReject;
   else if(InpUseSessions && !InSession(TimeCurrent()))
      g_blockReason = "fuori orario";
   else if(g_spr > MaxSpread())
      g_blockReason = "spread anomalo";
   else if(!MarketActive())
      g_blockReason = "candele piccole, aspetto una candela grande";
   else if(InpMaxDailyLoss > 0 && g_dayPL <= -InpMaxDailyLoss)
      g_blockReason = "perdita max giornaliera";
   else if(InpDailyTarget > 0 && g_dayPL >= InpDailyTarget)
      g_blockReason = "target giornaliero";
   else if(InpMaxTradesDay > 0 && g_dayTrades >= InpMaxTradesDay)
      g_blockReason = "max trade giornalieri";
   return g_blockReason == "";
  }

bool InSession(datetime t)
  {
   MqlDateTime d;
   TimeToStruct(t, d);
   return InRange(d.hour, InpSess1Start, InpSess1End) || InRange(d.hour, InpSess2Start, InpSess2End);
  }

bool InRange(int h, int from, int to)
  {
   if(from == to) return false;
   if(from < to)  return h >= from && h < to;
   return h >= from || h < to;
  }

//+------------------------------------------------------------------+
//| Candele grandi: il mercato e' "attivo"?                          |
//| Guarda la candela in corso e le ultime 3 chiuse: se una e' grande |
//| (>= ATR normale e >= 6 spread) il bot resta attivo per 2 minuti.  |
//+------------------------------------------------------------------+
double ATRNormal()
  {
   double b[];
   if(CopyBuffer(g_hATRn, 0, 1, 1, b) == 1 && b[0] > 0)
      return b[0];
   return ATR();
  }

void UpdateMarket(const MqlTick &tk)
  {
   double big = MathMax(InpBigK * ATRNormal(), InpBigSpreadMult * g_sprNorm);
   double maxRange = 0;
   for(int i = 0; i <= 3; i++)
     {
      double h = iHigh(_Symbol, PERIOD_M1, i), l = iLow(_Symbol, PERIOD_M1, i);
      if(h > 0 && l > 0)
         maxRange = MathMax(maxRange, h - l);
     }
   if(maxRange >= big)
      g_activeUntil = TimeCurrent() + InpActiveSec;

   bool active = !InpBigOnly || TimeCurrent() < g_activeUntil;
   g_mktInfo = StringFormat("Mercato %s   candela max %.0f / serve %.0f pt",
                            active ? "ATTIVO" : "calmo", maxRange / _Point, big / _Point);
  }

bool MarketActive()
  {
   return !InpBigOnly || TimeCurrent() < g_activeUntil;
  }

//+------------------------------------------------------------------+
//| Posizioni e ordini del bot                                       |
//+------------------------------------------------------------------+
bool IsMinePos()
  {
   return PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagic;
  }

bool IsMineOrder()
  {
   return OrderGetString(ORDER_SYMBOL) == _Symbol && OrderGetInteger(ORDER_MAGIC) == InpMagic;
  }

int CountPos(bool buy)
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsMinePos())
         continue;
      if((PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) == buy)
         n++;
     }
   return n;
  }

// ticket del pendente di quel tipo (0 se non c'e'); se ce n'e' piu' di uno cancella i doppioni
ulong FindPending(ENUM_ORDER_TYPE type, double &price)
  {
   ulong found = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t == 0 || !IsMineOrder() || OrderGetInteger(ORDER_TYPE) != type)
         continue;
      if(found == 0)
        {
         found = t;
         price = OrderGetDouble(ORDER_PRICE_OPEN);
        }
      else
         g_pend.OrderDelete(t);
     }
   return found;
  }

void DeletePendings()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t != 0 && IsMineOrder())
         g_pend.OrderDelete(t);
     }
  }

//+------------------------------------------------------------------+
//| Pendenti: BUY STOP sopra, SELL STOP sotto                        |
//+------------------------------------------------------------------+
void ManagePendings(const MqlTick &tk, int nBuy, int nSell)
  {
   double d    = EntryDist();
   double step = MathMax(MOVE_STEP * d, _Point);

   // un solo trade aperto per direzione; su conto netting nessun pendente opposto
   int maxDir = g_hedging ? (int)MathMax(1, InpMaxPerDir) : 1;
   bool wantBuy  = (nBuy == 0  || (nBuy < maxDir  && AllAtBE(true)))  && (g_hedging || nSell == 0);
   bool wantSell = (nSell == 0 || (nSell < maxDir && AllAtBE(false))) && (g_hedging || nBuy == 0);

   double buyT  = tk.ask + d;
   double sellT = tk.bid - d;

   // con una posizione aperta il pendente opposto sta OLTRE il suo SL:
   // scatta solo se la posizione e' gia' chiusa e il prezzo continua dall'altra parte
   double gap = 0.5 * d;
   double sBuy = PosSL(true), sSell = PosSL(false);
   if(sBuy > 0)  sellT = MathMin(sellT, sBuy - g_sprNorm - gap);
   if(sSell > 0) buyT  = MathMax(buyT,  sSell + g_sprNorm + gap);

   SyncStop(true,  wantBuy,  NormPrice(buyT),  step, sSell > 0, tk);
   SyncStop(false, wantSell, NormPrice(sellT), step, sBuy > 0,  tk);
  }

// true se tutte le posizioni aperte in quella direzione hanno lo SL gia' oltre l'entrata
bool AllAtBE(bool buy)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsMinePos())
         continue;
      if((PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) != buy)
         continue;
      double open = PositionGetDouble(POSITION_PRICE_OPEN), sl = PositionGetDouble(POSITION_SL);
      if(sl <= 0 || (buy ? sl < open : sl > open))
         return false;
     }
   return true;
  }

// SL piu' protettivo delle posizioni aperte in quella direzione (0 se nessuna)
double PosSL(bool buy)
  {
   double res = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsMinePos())
         continue;
      if((PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) != buy)
         continue;
      double sl = PositionGetDouble(POSITION_SL);
      if(sl <= 0)
         continue;
      if(res == 0 || (buy ? sl < res : sl > res))
         res = sl;
     }
   return res;
  }

void SyncStop(bool isBuy, bool want, double target, double step, bool anchored, const MqlTick &tk)
  {
   ENUM_ORDER_TYPE type = isBuy ? ORDER_TYPE_BUY_STOP : ORDER_TYPE_SELL_STOP;
   double cur = 0;
   ulong  t   = FindPending(type, cur);

   if(!want)
     {
      if(t != 0)
         g_pend.OrderDelete(t);
      return;
     }

   long last = isBuy ? g_lastBuyStopMs : g_lastSellStopMs;
   if(tk.time_msc - last < MODIFY_MS)
      return;

   // SL misurato dal prezzo che lo fa scattare: il buy chiude sul bid, il sell sull'ask
   double sl = NormPrice(isBuy ? target - g_sprNorm - SLDist() : target + g_sprNorm + SLDist());

   if(t == 0)
     {
      double lots = AffordableLots(isBuy, target);
      if(lots <= 0)
        {
         g_blockReason = "margine insufficiente";
         return;
        }
      MarkSent(isBuy, tk.time_msc);
      ENUM_ORDER_TYPE_TIME tt = (SymbolInfoInteger(_Symbol, SYMBOL_EXPIRATION_MODE) & SYMBOL_EXPIRATION_GTC) != 0
                                ? ORDER_TIME_GTC : ORDER_TIME_DAY;
      bool ok = isBuy ? g_pend.BuyStop(lots, target, _Symbol, sl, 0, tt, 0, "STR")
                      : g_pend.SellStop(lots, target, _Symbol, sl, 0, tt, 0, "STR");
      if(!ok || (g_pend.ResultRetcode() != TRADE_RETCODE_DONE && g_pend.ResultRetcode() != TRADE_RETCODE_PLACED))
         Rejected(g_pend, tk);
      return;
     }

   // insegue il prezzo solo quando si allontana: il BUY STOP scende se il prezzo scende,
   // il SELL STOP sale se il prezzo sale. Mai il contrario, altrimenti non scatterebbe mai.
   // senza posizione opposta: insegue solo quando il prezzo si allontana.
   // con posizione opposta aperta: segue anche il suo SL (puo' allontanarsi).
   bool move = isBuy ? (cur - target >= step) : (target - cur >= step);
   if(anchored && MathAbs(cur - target) >= step)
      move = true;
   if(!move)
      return;

   // non toccare un pendente troppo vicino al prezzo (freeze level del broker)
   double fz = StopsMinDist();
   if(isBuy ? (cur - tk.ask < fz) : (tk.bid - cur < fz))
      return;

   MarkSent(isBuy, tk.time_msc);
   if(!g_pend.OrderModify(t, target, sl, 0, ORDER_TIME_GTC, 0))
     {
      // se la modifica non e' accettata (es. tipo di scadenza) ricrea l'ordine al tick successivo
      g_pend.OrderDelete(t);
     }
  }

void MarkSent(bool isBuy, long ms)
  {
   if(isBuy) g_lastBuyStopMs = ms;
   else      g_lastSellStopMs = ms;
  }

void Rejected(CTrade &tr, const MqlTick &tk)
  {
   g_backoffMs  = tk.time_msc + 5000;
   g_lastReject = StringFormat("%s (%u)", tr.ResultRetcodeDescription(), tr.ResultRetcode());
   PrintFormat("Ordine rifiutato: %s", g_lastReject);
  }

//+------------------------------------------------------------------+
//| Posizioni aperte: break-even, trailing, breakout fallito         |
//+------------------------------------------------------------------+
int TrackIdx(ulong ticket)
  {
   for(int i = 0; i < g_tN; i++)
      if(g_tTicket[i] == ticket)
         return i;
   if(g_tN >= MAXTRACK)
      return -1;
   g_tTicket[g_tN] = ticket;
   g_tBest[g_tN] = 0;
   g_tWorst[g_tN] = 0;
   return g_tN++;
  }

void UntrackAt(int i)
  {
   g_tN--;
   g_tTicket[i] = g_tTicket[g_tN];
   g_tBest[i]   = g_tBest[g_tN];
   g_tWorst[i]  = g_tWorst[g_tN];
  }

// pulizia di sicurezza (le posizioni chiuse vengono tolte da LogTrade dopo averle registrate)
void UntrackClosed()
  {
   if(InpLogCSV && g_tN < MAXTRACK / 2)
      return;
   for(int i = g_tN - 1; i >= 0; i--)
      if(!PositionSelectByTicket(g_tTicket[i]))
        {
         g_tN--;
         g_tTicket[i] = g_tTicket[g_tN];
         g_tBest[i]   = g_tBest[g_tN];
         g_tWorst[i]  = g_tWorst[g_tN];
        }
  }

void ManagePositions(const MqlTick &tk)
  {
   double beAt  = BEDist();
   double lock  = BELock();
   double start = TrailStartDist();
   double dist  = TrailDist();
   double step  = MathMax(0.1 * dist, _Point);
   double fz    = StopsMinDist();
   bool   canModify = (tk.time_msc - g_lastTrailMs >= 300);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || !IsMinePos())
         continue;
      bool   isBuy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
      double open  = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl    = PositionGetDouble(POSITION_SL);
      double tp    = PositionGetDouble(POSITION_TP);
      long   age   = (long)(TimeCurrent() - (datetime)PositionGetInteger(POSITION_TIME));
      double fav   = isBuy ? tk.bid - open : open - tk.ask;

      int k = TrackIdx(t);
      if(k >= 0)
        {
         g_tBest[k]  = MathMax(g_tBest[k],  fav / _Point);
         g_tWorst[k] = MathMin(g_tWorst[k], fav / _Point);
        }

      // breakout fallito: dopo X secondi non e' mai arrivato nemmeno a meta' del break-even ed e' in perdita
      if(InpFailExit && age >= InpFailSec && k >= 0 &&
         g_tBest[k] * _Point < 0.5 * beAt && fav < 0)
        {
         if(g_trade.PositionClose(t))
            PrintFormat("Breakout fallito #%I64u chiuso a %+.0f pt dopo %d s", t, fav / _Point, (int)age);
         continue;
        }

      if(!canModify || (fav < beAt && fav < start))
         continue;

      // 1) break-even: SL all'entrata + qualche punto, appena il trade va a favore
      // 2) trailing: SL a distanza fissa dal prezzo (vince il piu' protettivo dei due)
      double newSL = 0;
      if(fav >= beAt)
         newSL = isBuy ? open + lock : open - lock;
      if(fav >= start)
        {
         double tr = isBuy ? tk.bid - dist : tk.ask + dist;
         newSL = (newSL == 0) ? tr : (isBuy ? MathMax(newSL, tr) : MathMin(newSL, tr));
        }
      newSL = NormPrice(newSL);
      bool better = isBuy ? (sl == 0 || newSL >= sl + step) : (sl == 0 || newSL <= sl - step);
      bool legal  = isBuy ? (tk.bid - newSL >= fz) : (newSL - tk.ask >= fz);
      if(better && legal)
        {
         g_lastTrailMs = tk.time_msc;
         if(!g_trade.PositionModify(t, newSL, tp))
            PrintFormat("Trailing #%I64u fallito: %s", t, g_trade.ResultRetcodeDescription());
        }
     }
  }

//+------------------------------------------------------------------+
//| Registro CSV: una riga per ogni trade chiuso                     |
//+------------------------------------------------------------------+
void LogTrade(ulong deal)
  {
   long   posId  = HistoryDealGetInteger(deal, DEAL_POSITION_ID);
   double exitPx = HistoryDealGetDouble(deal, DEAL_PRICE);
   double net    = HistoryDealGetDouble(deal, DEAL_PROFIT) + HistoryDealGetDouble(deal, DEAL_COMMISSION) +
                   HistoryDealGetDouble(deal, DEAL_SWAP);
   long   reason = HistoryDealGetInteger(deal, DEAL_REASON);
   datetime tOut = (datetime)HistoryDealGetInteger(deal, DEAL_TIME);
   bool   wasBuy = HistoryDealGetInteger(deal, DEAL_TYPE) == DEAL_TYPE_SELL; // un SELL in uscita chiude un buy

   double best = 0, worst = 0;
   for(int i = g_tN - 1; i >= 0; i--)
      if(g_tTicket[i] == (ulong)posId)
        {
         best = g_tBest[i];
         worst = g_tWorst[i];
         UntrackAt(i);
        }

   // prezzo e ora di entrata dalla storia della posizione
   double entryPx = 0;
   datetime tIn = 0;
   if(HistorySelectByPosition(posId))
      for(int i = 0; i < HistoryDealsTotal(); i++)
        {
         ulong d = HistoryDealGetTicket(i);
         if(HistoryDealGetInteger(d, DEAL_ENTRY) == DEAL_ENTRY_IN)
           {
            entryPx = HistoryDealGetDouble(d, DEAL_PRICE);
            tIn = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
            net += HistoryDealGetDouble(d, DEAL_COMMISSION);
           }
        }
   g_statsDirty = true; // HistorySelectByPosition ha cambiato la selezione della storia

   string why;
   if(reason == DEAL_REASON_SL)
      why = (net < 0) ? "stop loss" : (best * _Point >= TrailStartDist() ? "trailing" : "break-even");
   else if(reason == DEAL_REASON_TP)
      why = "take profit";
   else if(reason == DEAL_REASON_EXPERT)
      why = "breakout fallito / stop manuale";
   else
      why = "manuale";

   string file = "StraddleM1_trades.csv";
   int h = FileOpen(file, FILE_READ | FILE_WRITE | FILE_CSV | FILE_ANSI | FILE_SHARE_READ, ';');
   if(h == INVALID_HANDLE)
      return;
   if(FileSize(h) == 0)
      FileWrite(h, "data", "simbolo", "tipo", "entrata", "uscita", "profitto netto", "durata s",
                "max a favore pt", "max contro pt", "motivo", "spread pt", "ATR pt");
   FileSeek(h, 0, SEEK_END);
   FileWrite(h, TimeToString(tOut, TIME_DATE | TIME_SECONDS), _Symbol, wasBuy ? "BUY" : "SELL",
             DoubleToString(entryPx, _Digits), DoubleToString(exitPx, _Digits),
             DoubleToString(net, 2), (string)(int)(tIn > 0 ? tOut - tIn : 0),
             DoubleToString(best, 0), DoubleToString(worst, 0), why,
             DoubleToString(g_sprNorm / _Point, 0), DoubleToString(ATR() / _Point, 0));
   FileClose(h);
  }

void CloseAll()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t != 0 && IsMinePos())
         g_trade.PositionClose(t);
     }
  }

//+------------------------------------------------------------------+
//| Statistiche giornaliere                                          |
//+------------------------------------------------------------------+
void RefreshDailyStatsIfNeeded(datetime now)
  {
   MqlDateTime d;
   TimeToStruct(now, d);
   d.hour = 0; d.min = 0; d.sec = 0;
   datetime dayStart = StructToTime(d);
   if(!g_statsDirty && dayStart == g_statsDay)
      return;

   g_statsDay = dayStart;
   g_statsDirty = false;
   g_dayPL = 0; g_dayTrades = 0; g_dayWins = 0; g_dayWinSum = 0; g_dayLossSum = 0;
   if(!HistorySelect(dayStart, now + 86400))
      return;

   int n = HistoryDealsTotal();
   for(int i = 0; i < n; i++)
     {
      ulong dl = HistoryDealGetTicket(i);
      if(dl == 0 || HistoryDealGetInteger(dl, DEAL_MAGIC) != InpMagic ||
         HistoryDealGetString(dl, DEAL_SYMBOL) != _Symbol)
         continue;
      double profit = HistoryDealGetDouble(dl, DEAL_PROFIT);
      double net = profit + HistoryDealGetDouble(dl, DEAL_COMMISSION) + HistoryDealGetDouble(dl, DEAL_SWAP);
      g_dayPL += net;
      long entry = HistoryDealGetInteger(dl, DEAL_ENTRY);
      if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY)
        {
         g_dayTrades++;
         if(profit > 0) { g_dayWins++; g_dayWinSum += net; }
         else           g_dayLossSum += net;
        }
     }
  }

//+------------------------------------------------------------------+
//| Dashboard                                                        |
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
   ObjectSetInteger(0, bg, OBJPROP_XSIZE, 430);
   ObjectSetInteger(0, bg, OBJPROP_YSIZE, 214);
   ObjectSetInteger(0, bg, OBJPROP_BGCOLOR, C'20,24,32');
   ObjectSetInteger(0, bg, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, bg, OBJPROP_COLOR, C'70,80,100');
   ObjectSetInteger(0, bg, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, bg, OBJPROP_HIDDEN, true);

   MakeLabel("title", 20,  28, 11, clrWhite);
   MakeLabel("state", 20,  50,  9, clrSilver);
   MakeLabel("pl",    20,  76, 12, clrWhite);
   MakeLabel("stats", 20, 100,  9, clrSilver);
   MakeLabel("avg",   20, 118,  9, clrSilver);
   MakeLabel("open",  20, 136,  9, clrSilver);
   MakeLabel("mkt",   20, 154,  9, clrKhaki);
   MakeLabel("dist",  20, 172,  9, clrGray);

   MakeButton("btnStart", "Start",       20, 200, 80, clrDodgerBlue);
   MakeButton("btnFin",   "Finish",     105, 200, 80, clrSteelBlue);
   MakeButton("btnStop",  "Stop+Close", 190, 200, 90, clrFireBrick);

   ObjectSetString(0, g_pfx + "title", OBJPROP_TEXT, "StraddleM1   " + _Symbol);
   UpdatePanel();
  }

void SetText(string name, string text, color clr = clrNONE)
  {
   string n = g_pfx + name;
   if(ObjectFind(0, n) < 0)
      return;
   ObjectSetString(0, n, OBJPROP_TEXT, text);
   if(clr != clrNONE)
      ObjectSetInteger(0, n, OBJPROP_COLOR, clr);
  }

color PLColor(double v)
  {
   if(v > 0) return clrLimeGreen;
   if(v < 0) return clrTomato;
   return clrSilver;
  }

void UpdatePanel()
  {
   if(ObjectFind(0, g_pfx + "bg") < 0)
      return;

   string cur = AccountInfoString(ACCOUNT_CURRENCY);
   if(g_state == ST_STOPPED)        SetText("state", "FERMO  -  premi Start", clrGray);
   else if(g_state == ST_FINISHING) SetText("state", "IN CHIUSURA  -  nessun nuovo ordine", clrOrange);
   else if(g_blockReason != "")     SetText("state", "IN PAUSA  -  " + g_blockReason, clrOrange);
   else                             SetText("state", "ATTIVO", clrLimeGreen);

   SetText("pl", StringFormat("Oggi  %+.2f %s", g_dayPL, cur), PLColor(g_dayPL));

   int losses = g_dayTrades - g_dayWins;
   double wr = g_dayTrades > 0 ? 100.0 * g_dayWins / g_dayTrades : 0;
   SetText("stats", StringFormat("Trade %d    Vinti %d    Persi %d    Win rate %.0f%%",
                                 g_dayTrades, g_dayWins, losses, wr));
   SetText("avg", StringFormat("Vincita media %+.2f    Perdita media %+.2f",
                               g_dayWins > 0 ? g_dayWinSum / g_dayWins : 0,
                               losses > 0 ? g_dayLossSum / losses : 0));

   int nOpen = 0;
   double floating = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsMinePos())
         continue;
      nOpen++;
      floating += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
     }
   SetText("open", StringFormat("Aperte %d   In corso %+.2f   Saldo %.2f",
                                nOpen, floating, AccountInfoDouble(ACCOUNT_BALANCE)),
           nOpen > 0 ? PLColor(floating) : clrSilver);

   SetText("mkt", g_mktInfo, MarketActive() ? clrLimeGreen : clrKhaki);
   SetText("dist", StringFormat("Pendenti %.0f  SL %.0f  BE da +%.0f  trailing %.0f da +%.0f (punti)",
                                EntryDist() / _Point, SLDist() / _Point, BEDist() / _Point,
                                TrailDist() / _Point, TrailStartDist() / _Point));
   ChartRedraw();
  }

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(id != CHARTEVENT_OBJECT_CLICK || StringFind(sparam, g_pfx + "btn") != 0)
      return;
   ObjectSetInteger(0, sparam, OBJPROP_STATE, false);

   if(sparam == g_pfx + "btnStart")
      g_state = ST_RUNNING;
   else if(sparam == g_pfx + "btnFin")
      g_state = ST_FINISHING;
   else if(sparam == g_pfx + "btnStop")
     {
      g_state = ST_STOPPED;
      DeletePendings();
      CloseAll();
     }
   UpdatePanel();
  }
//+------------------------------------------------------------------+
