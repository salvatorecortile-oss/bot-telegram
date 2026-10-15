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
#property version   "3.00"
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
input int    InpScaleRefATR   = 0;     // Scala le distanze con la volatilita': ATR (punti) per cui valgono i numeri sopra (0 = off)

input group "Filtro laterale (lavora solo sui movimenti veri)"
input bool   InpBigOnly       = true;  // Attivo: niente trade quando il mercato lateralizza
input int    InpERPeriod      = 6;     // Candele per misurare la direzionalita'
input double InpERMin         = 0.40;  // Direzionalita' minima (0 = laterale puro, 1 = linea dritta)
input double InpBigK          = 0.8;   // Candela grande = range >= ATR normale x questo
input int    InpBigSpreadMult = 6;     // ...e range >= spread x questo
input bool   InpTrendSide     = true;  // Pendente solo nella direzione del movimento
input int    InpActiveSec     = 20;    // Tiene la decisione per X secondi (evita on/off continui)
input int    InpMaxPerDir     = 2;     // Posizioni max per direzione (la 2a solo con la 1a a break-even)

input group "Modalita' laterale (limit)"
input bool   InpRangeMode     = true;  // In laterale usa SELL LIMIT in alto e BUY LIMIT in basso
input int    InpRangeBars     = 15;    // Candele M1 per disegnare il range
input double InpRangeMaxER    = 0.25;  // Laterale se la direzionalita' e' sotto questo valore
input int    InpRangeMinSpr   = 8;     // Range minimo = spread x questo (sotto non conviene)
input double InpRangeSLPct    = 0.30;  // SL oltre il bordo = larghezza del range x questo
input int    InpRangeMaxSLPts = 40;    // ...ma mai piu' di X punti (0 = nessun limite)
input bool   InpRangeUseTP    = false; // Metti anche il TP (false = solo break-even + trailing, come gli stop)
input double InpRangeTPPct    = 0.50;  // TP verso l'altro bordo: 0.5 = meta' range

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

input group "Volume / IB"
input double InpRebatePerLot  = 10.0;  // Rebate per lotto (solo per la stima in dashboard, 0 = nascondi)

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
CTrade   g_pend;      // ordini pendenti breakout (stop)
CTrade   g_rng;       // ordini e posizioni della modalita' laterale (limit), magic + 1
EAState  g_state   = ST_STOPPED;
bool     g_hedging = true;
int      g_hATR    = INVALID_HANDLE;
int      g_hATRn   = INVALID_HANDLE;  // ATR "normale" (30 candele) per riconoscere le candele grandi
datetime g_activeUntil = 0;
double   g_er          = 0;   // direzionalita' 0..1
int      g_trendDir    = 0;   // +1 salita, -1 discesa
double   g_rH = 0, g_rL = 0;        // massimo e minimo del range
bool     g_rangeOK     = false;     // mercato laterale con range abbastanza largo
string   g_modeInfo    = "-";
long     g_lastBuyLimMs  = 0;
long     g_lastSellLimMs = 0;
string   g_mktInfo     = "-";   // stato del mercato (breve)
long     g_chartFg     = 0;     // impostazione originale "grafico in primo piano"
double   g_rangeNow    = 0;     // candela piu' grande tra la corrente e l'ultima chiusa
double   g_bigNeed     = 0;     // grandezza minima richiesta

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
double   g_dayLots    = 0;   // lotti chiusi oggi (andata e ritorno = 1 volta il volume)

string   g_pfx         = "STR_";
long     g_lastPanelMs = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_pend.SetExpertMagicNumber(InpMagic);
   g_pend.SetTypeFilling(ORDER_FILLING_RETURN);
   g_rng.SetExpertMagicNumber(InpMagic + 1);
   g_rng.SetTypeFilling(ORDER_FILLING_RETURN);

   // grafico dietro agli oggetti: la dashboard copre candele e frecce dei trade
   g_chartFg = ChartGetInteger(0, CHART_FOREGROUND);
   ChartSetInteger(0, CHART_FOREGROUND, false);

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
     {
      DeletePendings(); // EA tolto dal grafico: non lasciare ordini pendenti sul conto
      DeleteRangePendings();
      ChartSetInteger(0, CHART_FOREGROUND, g_chartFg);
     }
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

   UpdateRange(tk);

   int nBuy = CountPos(true), nSell = CountPos(false);
   if(g_state == ST_FINISHING && nBuy + nSell + CountRangePos(true) + CountRangePos(false) == 0)
      g_state = ST_STOPPED;

   // movimento -> breakout con gli STOP; laterale -> LIMIT ai bordi del range; altrimenti attesa
   bool base = (g_state == ST_RUNNING) && CanTrade(tk);
   bool brk  = base && MarketActive();
   bool rng  = base && !brk && InpRangeMode && g_rangeOK;

   if(brk) ManagePendings(tk, nBuy, nSell);
   else    DeletePendings();
   if(rng) ManageRange(tk);
   else    DeleteRangePendings();

   if(base && !brk && !rng)
      g_blockReason = "aspetto un movimento";
   g_modeInfo = brk ? "BREAKOUT (stop)" : (rng ? "LATERALE (limit)" : "attesa");

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
   if(!IsOurMagic(HistoryDealGetInteger(trans.deal, DEAL_MAGIC)) ||
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

// valore in punti scelto dall'utente: viene usato cosi' com'e' (solo il minimo tecnico del broker);
// 0 = automatico dall'ATR, con un minimo legato allo spread
// Con InpScaleRefATR > 0 i valori in punti si allargano/stringono con la volatilita':
// es. riferimento 150 e ATR normale 450 -> tutte le distanze x3. Limitato tra 0.5x e 4x.
double VolScale()
  {
   if(InpScaleRefATR <= 0)
      return 1.0;
   double f = ATRNormal() / (InpScaleRefATR * _Point);
   return MathMax(0.5, MathMin(4.0, f));
  }

double Dist(int inputPts, double k, double minSpreadMult)
  {
   double brokerMin = StopsMinDist() + _Point;
   if(inputPts > 0)
      return MathMax(inputPts * _Point * VolScale(), brokerMin);
   return MathMax(k * ATR(), MathMax(minSpreadMult * g_sprNorm, brokerMin));
  }

double EntryDist()      { return Dist(InpEntryPts,      K_ENTRY,       3.0); }
double SLDist()         { return Dist(InpSLPts,         K_SL,          3.0); }
double TrailStartDist() { return Dist(InpTrailStartPts, K_TRAIL_START, 2.5); }
double TrailDist()      { return Dist(InpTrailDistPts,  K_TRAIL_DIST,  2.0); }
double BEDist()         { return Dist(InpBEPts,         K_BE,          2.0); }
double BELock()
  {
   double lock = (InpBELockPts > 0) ? InpBELockPts * _Point : MathMax(_Point, 0.5 * g_sprNorm);
   // i punti bloccati devono essere meno del livello di break-even, altrimenti lo SL finirebbe sopra il prezzo
   return MathMin(lock, MathMax(_Point, 0.5 * BEDist()));
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

// Due condizioni insieme, ricalcolate a ogni tick:
//  1) DIREZIONALITA' (Efficiency Ratio di Kaufman sulle ultime N candele M1):
//     spostamento netto / somma di tutti i movimenti. In laterale il prezzo va su e giu'
//     e torna dov'era -> valore basso. In un candelone o in una discesa -> valore alto.
//  2) CANDELA GRANDE: la candela in corso o l'ultima chiusa e' >= 0.8 x ATR normale
//     (e >= 6 x spread). Le candeline piccole non bastano.
// Se una delle due manca il bot cancella i pendenti e aspetta.
void UpdateMarket(const MqlTick &tk)
  {
   int n = (int)MathMax(2, InpERPeriod);
   double cN = iClose(_Symbol, PERIOD_M1, n);
   double path = 0, prev = tk.bid;
   bool ok = cN > 0;
   for(int i = 1; i <= n && ok; i++)
     {
      double c = iClose(_Symbol, PERIOD_M1, i);
      if(c <= 0) { ok = false; break; }
      path += MathAbs(prev - c);
      prev = c;
     }
   double net = ok ? tk.bid - cN : 0;
   g_er = (ok && path > 0) ? MathAbs(net) / path : 0;

   double big = MathMax(InpBigK * ATRNormal(), InpBigSpreadMult * g_sprNorm);
   double r0 = iHigh(_Symbol, PERIOD_M1, 0) - iLow(_Symbol, PERIOD_M1, 0);
   double r1 = iHigh(_Symbol, PERIOD_M1, 1) - iLow(_Symbol, PERIOD_M1, 1);
   double maxRange = MathMax(r0, r1);

   bool directional = g_er >= InpERMin;
   bool bigCandle   = maxRange >= big;
   if(directional && bigCandle)
     {
      g_activeUntil = TimeCurrent() + MathMax(1, InpActiveSec);
      g_trendDir = net > 0 ? 1 : -1;
     }

   g_rangeNow = maxRange;
   g_bigNeed  = big;
   string why = !directional ? "laterale" : (!bigCandle ? "candele piccole" : "");
   g_mktInfo = MarketActive() ? (g_trendDir > 0 ? "ATTIVO in salita" : "ATTIVO in discesa")
                              : "FERMO (" + why + ")";
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

bool IsOurMagic(long m)
  {
   return m == InpMagic || m == InpMagic + 1;
  }

bool IsRangePos()
  {
   return PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagic + 1;
  }

bool IsRangeOrder()
  {
   return OrderGetString(ORDER_SYMBOL) == _Symbol && OrderGetInteger(ORDER_MAGIC) == InpMagic + 1;
  }

int CountRangePos(bool buy)
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsRangePos())
         continue;
      if((PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) == buy)
         n++;
     }
   return n;
  }

void DeleteRangePendings()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t != 0 && IsRangeOrder())
         g_rng.OrderDelete(t);
     }
  }

ulong FindRangePending(ENUM_ORDER_TYPE type, double &price)
  {
   ulong found = 0;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t == 0 || !IsRangeOrder() || OrderGetInteger(ORDER_TYPE) != type)
         continue;
      if(found == 0)
        {
         found = t;
         price = OrderGetDouble(ORDER_PRICE_OPEN);
        }
      else
         g_rng.OrderDelete(t);
     }
   return found;
  }

//+------------------------------------------------------------------+
//| Modalita' laterale: SELL LIMIT sul massimo del range, BUY LIMIT  |
//| sul minimo, TP verso il centro, SL appena fuori dal range.       |
//+------------------------------------------------------------------+
void UpdateRange(const MqlTick &tk)
  {
   int n = (int)MathMax(5, InpRangeBars);
   int hi = iHighest(_Symbol, PERIOD_M1, MODE_HIGH, n, 1);
   int lo = iLowest(_Symbol, PERIOD_M1, MODE_LOW, n, 1);
   g_rangeOK = false;
   if(hi < 0 || lo < 0)
      return;
   g_rH = iHigh(_Symbol, PERIOD_M1, hi);
   g_rL = iLow(_Symbol, PERIOD_M1, lo);
   double w = g_rH - g_rL;
   bool lateral = g_er < InpRangeMaxER;
   bool wide    = w >= InpRangeMinSpr * g_sprNorm && w <= 4.0 * ATRNormal();
   bool inside  = tk.bid < g_rH && tk.bid > g_rL;
   g_rangeOK = lateral && wide && inside;
  }

void ManageRange(const MqlTick &tk)
  {
   double w   = g_rH - g_rL;
   double mid = g_rL + InpRangeTPPct * w;          // TP del buy
   double midS = g_rH - InpRangeTPPct * w;         // TP del sell
   double slx = MathMax(InpRangeSLPct * w, 2.0 * g_sprNorm);
   if(InpRangeMaxSLPts > 0)   // dopo una news il range e' enorme: lo SL non deve diventarlo
      slx = MathMin(slx, MathMax(InpRangeMaxSLPts * _Point, 2.0 * g_sprNorm));

   // SELL LIMIT: scatta quando il bid tocca il massimo; SL e TP valgono sull'ask
   SyncLimit(false, CountRangePos(false) == 0, NormPrice(g_rH),
             NormPrice(g_rH + slx + g_sprNorm), InpRangeUseTP ? NormPrice(midS) : 0, w, tk);
   // BUY LIMIT: prezzo ask = minimo + spread, cosi' scatta quando il bid tocca il minimo
   SyncLimit(true, CountRangePos(true) == 0, NormPrice(g_rL + g_sprNorm),
             NormPrice(g_rL - slx), InpRangeUseTP ? NormPrice(mid) : 0, w, tk);
  }

void SyncLimit(bool isBuy, bool want, double price, double sl, double tp, double w, const MqlTick &tk)
  {
   ENUM_ORDER_TYPE type = isBuy ? ORDER_TYPE_BUY_LIMIT : ORDER_TYPE_SELL_LIMIT;
   double cur = 0;
   ulong  t   = FindRangePending(type, cur);
   if(!want)
     {
      if(t != 0) g_rng.OrderDelete(t);
      return;
     }
   long last = isBuy ? g_lastBuyLimMs : g_lastSellLimMs;
   if(tk.time_msc - last < MODIFY_MS)
      return;

   // il limit deve stare dalla parte giusta del prezzo, oltre la distanza minima del broker
   double fz = StopsMinDist();
   if(isBuy ? (tk.ask - price < fz + _Point) : (price - tk.bid < fz + _Point))
      return;

   if(isBuy) g_lastBuyLimMs = tk.time_msc; else g_lastSellLimMs = tk.time_msc;

   if(t == 0)
     {
      double lots = AffordableLots(isBuy, price);
      if(lots <= 0)
         return;
      ENUM_ORDER_TYPE_TIME tt = (SymbolInfoInteger(_Symbol, SYMBOL_EXPIRATION_MODE) & SYMBOL_EXPIRATION_GTC) != 0
                                ? ORDER_TIME_GTC : ORDER_TIME_DAY;
      bool ok = isBuy ? g_rng.BuyLimit(lots, price, _Symbol, sl, tp, tt, 0, "RNG")
                      : g_rng.SellLimit(lots, price, _Symbol, sl, tp, tt, 0, "RNG");
      if(!ok || (g_rng.ResultRetcode() != TRADE_RETCODE_DONE && g_rng.ResultRetcode() != TRADE_RETCODE_PLACED))
         Rejected(g_rng, tk);
      return;
     }

   // il range e' cambiato: sposta il limit sul nuovo bordo
   if(MathAbs(cur - price) >= 0.1 * w)
      if(!g_rng.OrderModify(t, price, sl, tp, ORDER_TIME_GTC, 0))
         g_rng.OrderDelete(t);
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
   if(InpBigOnly && InpTrendSide)
     {
      // solo il pendente nella direzione del movimento in corso
      wantBuy  = wantBuy  && g_trendDir > 0;
      wantSell = wantSell && g_trendDir < 0;
     }

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
      if(t == 0)
         continue;
      bool isRng = IsRangePos();   // trade della modalita' laterale (limit): stesso BE e trailing
      if(!isRng && !IsMinePos())
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
      if(!isRng && InpFailExit && age >= InpFailSec && k >= 0 &&
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
   bool isRange = HistoryDealGetInteger(deal, DEAL_MAGIC) == InpMagic + 1;
   FileWrite(h, TimeToString(tOut, TIME_DATE | TIME_SECONDS), _Symbol,
             (isRange ? "RANGE " : "") + (wasBuy ? "BUY" : "SELL"),
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
      if(t != 0 && (IsMinePos() || IsRangePos()))
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
   g_dayPL = 0; g_dayTrades = 0; g_dayWins = 0; g_dayWinSum = 0; g_dayLossSum = 0; g_dayLots = 0;
   if(!HistorySelect(dayStart, now + 86400))
      return;

   int n = HistoryDealsTotal();
   for(int i = 0; i < n; i++)
     {
      ulong dl = HistoryDealGetTicket(i);
      if(dl == 0 || !IsOurMagic(HistoryDealGetInteger(dl, DEAL_MAGIC)) ||
         HistoryDealGetString(dl, DEAL_SYMBOL) != _Symbol)
         continue;
      double profit = HistoryDealGetDouble(dl, DEAL_PROFIT);
      double net = profit + HistoryDealGetDouble(dl, DEAL_COMMISSION) + HistoryDealGetDouble(dl, DEAL_SWAP);
      g_dayPL += net;
      long entry = HistoryDealGetInteger(dl, DEAL_ENTRY);
      if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY)
        {
         g_dayTrades++;
         g_dayLots += HistoryDealGetDouble(dl, DEAL_VOLUME);
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
   ObjectSetInteger(0, n, OBJPROP_BACK, false);
   ObjectSetInteger(0, n, OBJPROP_ZORDER, 10);
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
   ObjectSetInteger(0, n, OBJPROP_BACK, false);
   ObjectSetInteger(0, n, OBJPROP_ZORDER, 10);
   ObjectSetString(0, n, OBJPROP_TEXT, text);
  }

#define PANEL_W  300
#define ROW_H    17

int g_rowY = 0;

// una riga della dashboard, una sotto l'altra
void Row(string name, int size, color clr, int extra = 0)
  {
   g_rowY += extra;
   MakeLabel(name, 22, g_rowY, size, clr);
   g_rowY += ROW_H + (size > 9 ? 5 : 0);
  }

void Section(string name, string text)
  {
   g_rowY += 6;
   MakeLabel(name, 22, g_rowY, 8, C'110,120,140');
   ObjectSetString(0, g_pfx + name, OBJPROP_TEXT, text);
   g_rowY += ROW_H - 2;
  }

void CreatePanel()
  {
   // sfondo per primo, cosi' le scritte create dopo restano sopra
   string bg = g_pfx + "bg";
   ObjectCreate(0, bg, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, bg, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, bg, OBJPROP_XDISTANCE, 10);
   ObjectSetInteger(0, bg, OBJPROP_YDISTANCE, 20);
   ObjectSetInteger(0, bg, OBJPROP_XSIZE, PANEL_W);
   ObjectSetInteger(0, bg, OBJPROP_BGCOLOR, C'20,24,32');
   ObjectSetInteger(0, bg, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, bg, OBJPROP_COLOR, C'70,80,100');
   ObjectSetInteger(0, bg, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, bg, OBJPROP_HIDDEN, true);
   ObjectSetInteger(0, bg, OBJPROP_BACK, false);
   ObjectSetInteger(0, bg, OBJPROP_ZORDER, 5);

   g_rowY = 30;
   Row("title", 11, clrWhite);
   Row("state", 10, clrSilver);
   Row("reason", 9, clrOrange);

   Section("h1", "OGGI");
   Row("pl",     12, clrWhite);
   Row("trades",  9, clrSilver);
   Row("wl",      9, clrSilver);
   Row("avgw",    9, clrSilver);
   Row("avgl",    9, clrSilver);
   Row("lots",    9, clrSilver);

   Section("h2", "POSIZIONI");
   Row("open",    9, clrSilver);
   Row("float",   9, clrSilver);
   Row("bal",     9, clrSilver);

   Section("h3", "MERCATO");
   Row("mode",    9, clrWhite);
   Row("mkt",     9, clrKhaki);
   Row("dir",     9, clrSilver);
   Row("cand",    9, clrSilver);
   Row("range",   9, clrSilver);

   Section("h4", "DISTANZE (punti)");
   Row("d1",      9, clrGray);
   Row("d2",      9, clrGray);
   Row("d3",      9, clrGray);

   int by = g_rowY + 8;
   MakeButton("btnStart", "Start",       22, by, 82, clrDodgerBlue);
   MakeButton("btnFin",   "Finish",     109, by, 82, clrSteelBlue);
   MakeButton("btnStop",  "Stop+Close", 196, by, 92, clrFireBrick);

   // altezza dello sfondo in base a quante righe ci sono
   ObjectSetInteger(0, bg, OBJPROP_YSIZE, by + 24 + 12 - 20);

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

   // stato + motivo su due righe
   if(g_state == ST_STOPPED)        { SetText("state", "FERMO", clrGray);          SetText("reason", "premi Start", clrGray); }
   else if(g_state == ST_FINISHING) { SetText("state", "IN CHIUSURA", clrOrange);  SetText("reason", "nessun nuovo ordine", clrOrange); }
   else if(g_blockReason != "")     { SetText("state", "IN PAUSA", clrOrange);     SetText("reason", g_blockReason, clrOrange); }
   else                             { SetText("state", "ATTIVO", clrLimeGreen);    SetText("reason", " "); }

   // oggi
   SetText("pl", StringFormat("%+.2f %s", g_dayPL, cur), PLColor(g_dayPL));
   int losses = g_dayTrades - g_dayWins;
   double wr = g_dayTrades > 0 ? 100.0 * g_dayWins / g_dayTrades : 0;
   SetText("trades", StringFormat("Trade %d     Win rate %.0f%%", g_dayTrades, wr));
   SetText("wl",     StringFormat("Vinti %d     Persi %d", g_dayWins, losses));
   SetText("avgw",   StringFormat("Vincita media   %+.2f", g_dayWins > 0 ? g_dayWinSum / g_dayWins : 0), clrLimeGreen);
   SetText("avgl",   StringFormat("Perdita media   %+.2f", losses > 0 ? g_dayLossSum / losses : 0), clrTomato);
   if(InpRebatePerLot > 0)
      SetText("lots", StringFormat("Lotti %.2f     Rebate ~%.2f", g_dayLots, g_dayLots * InpRebatePerLot), clrKhaki);
   else
      SetText("lots", StringFormat("Lotti %.2f", g_dayLots), clrKhaki);

   // posizioni
   int nOpen = 0;
   double floating = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !(IsMinePos() || IsRangePos()))
         continue;
      nOpen++;
      floating += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
     }
   SetText("open",  StringFormat("Aperte %d   (%d buy, %d sell)", nOpen,
                                 CountPos(true) + CountRangePos(true), CountPos(false) + CountRangePos(false)));
   SetText("float", StringFormat("In corso   %+.2f", floating), nOpen > 0 ? PLColor(floating) : clrSilver);
   SetText("bal",   StringFormat("Saldo   %.2f %s", AccountInfoDouble(ACCOUNT_BALANCE), cur));

   // mercato
   bool okDir  = g_er >= InpERMin;
   bool okCand = g_rangeNow >= g_bigNeed;
   SetText("mode", "Modalita'  " + g_modeInfo,
           g_modeInfo == "attesa" ? clrGray : (StringFind(g_modeInfo, "LATERALE") == 0 ? clrDeepSkyBlue : clrLimeGreen));
   SetText("mkt",  g_mktInfo, MarketActive() ? clrLimeGreen : clrKhaki);
   SetText("dir",  StringFormat("Direzione  %.2f  (min %.2f)  %s", g_er, InpERMin, okDir ? "OK" : "NO"),
           okDir ? clrLimeGreen : clrTomato);
   SetText("cand", StringFormat("Candela  %.0f  (min %.0f)  %s", g_rangeNow / _Point, g_bigNeed / _Point, okCand ? "OK" : "NO"),
           okCand ? clrLimeGreen : clrTomato);
   if(InpRangeMode)
      SetText("range", StringFormat("Range  %.0f  (min %.0f)  %s", (g_rH - g_rL) / _Point,
                                    InpRangeMinSpr * g_sprNorm / _Point, g_rangeOK ? "OK" : "-"),
              g_rangeOK ? clrDeepSkyBlue : clrGray);
   else
      SetText("range", "Range  spento", clrGray);

   // distanze
   SetText("d1", StringFormat("Pendenti %.0f     SL %.0f%s", EntryDist() / _Point, SLDist() / _Point,
                              InpScaleRefATR > 0 ? StringFormat("   (x%.1f)", VolScale()) : ""));
   SetText("d2", StringFormat("Break-even da +%.0f  (blocca %.0f)", BEDist() / _Point, BELock() / _Point));
   SetText("d3", StringFormat("Trailing %.0f  da +%.0f", TrailDist() / _Point, TrailStartDist() / _Point));
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
      DeleteRangePendings();
      CloseAll();
     }
   UpdatePanel();
  }
//+------------------------------------------------------------------+
