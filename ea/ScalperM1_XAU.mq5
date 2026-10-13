//+------------------------------------------------------------------+
//|                                              ScalperM1_XAU.mq5   |
//|  v3 - Scalper continuo su M1, multi-strumento, auto-regolato     |
//|  - entra nella direzione della candela M1 in corso, anche piu'   |
//|    volte per candela                                             |
//|  - niente TP: break-even veloce + trailing (oppure TP fisso)      |
//|  - SL, spread massimo e slippage calcolati da soli (ATR/spread)  |
//|  - "bias": EMA M1 + conteggio candele decidono se favorire buy   |
//|    o sell (non blocca, rende piu' difficile il lato opposto)     |
//|  - pannello con Start / Start One / Finish / Stop                |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "3.00"
#property description "Scalper M1 continuo, auto-regolato su qualsiasi simbolo (XAU, Forex, indici)"

#include <Trade\Trade.mqh>

enum ExitMode
  {
   EXIT_TRAILING = 0, // Senza TP: break-even + trailing
   EXIT_FIXED_TP = 1  // TP fisso
  };

enum SignalMode
  {
   SIG_FOLLOW = 0, // Normale: segue la candela
   SIG_FADE   = 1, // Contrario: vende in alto e compra in basso alla candela
   SIG_INVERT = 2  // Tutto invertito (anche i segnali di inversione)
  };

//--- parametri ------------------------------------------------------
input group "Base"
input double   InpLots          = 0.01;          // Lotti
input SignalMode InpSignalMode = SIG_FOLLOW;    // Direzione dei trade
input ExitMode InpExitMode      = EXIT_TRAILING; // Uscita
input int      InpMaxPositions  = 3;             // Posizioni max PER DIREZIONE (le extra solo con le altre a break-even)
input bool     InpReversal      = true;          // Apre il trade opposto quando la candela finisce l'estensione (conto hedging)
input bool     InpAutoStart     = true;          // Parte da solo appena attaccato al grafico
input long     InpMagic         = 41378;         // Magic number

input group "Distanze in punti (0 = automatico)"
input int      InpSLPoints      = 0;   // Stop loss (auto = 0.5 x ATR M1, minimo 3 x spread)
input int      InpTPPoints      = 0;   // TP fisso, solo modalita' TP fisso (auto = uguale allo SL)
input int      InpMaxSpreadPts  = 0;   // Spread massimo (auto = 2 x spread normale del simbolo)
input int      InpDeviationPts  = 0;   // Slippage massimo (auto = 2 x spread normale)

input group "Bias buy/sell"
input bool     InpUseBias       = true; // Favorisci la direzione del bias (EMA M1 + candele)
input double   InpBiasStrength  = 2.0;  // Quanto e' piu' difficile entrare contro il bias

input group "Avanzate"
input double   InpSLATRMult     = 0.5;  // SL automatico = ATR M1 x questo
input int      InpMaxHoldSec    = 60;   // Chiude se dopo X secondi non e' arrivato a break-even (0 = off)
input int      InpCooldownMs    = 300;  // Pausa minima tra due ingressi (ms)

input group "Limiti giornalieri (valuta conto, 0 = off)"
input double   InpMaxDailyLoss  = 0;    // Perdita massima giornaliera
input double   InpDailyTarget   = 0;    // Obiettivo giornaliero
input int      InpMaxTradesDay  = 0;    // Numero massimo trade al giorno

//--- costanti della logica (in frazioni dello SL "r") ----------------
#define BE_TRIGGER_R   0.5   // break-even quando il profitto arriva a 0.5 r
#define BE_LOCK_R      0.1   // profitto bloccato al break-even
#define TRAIL_START_R  0.8   // trailing da 0.8 r
#define TRAIL_MIN_R    0.3   // distanza minima trailing
#define TRAIL_PCT      0.35  // il trailing restituisce al massimo il 35% del picco
#define TRAIL_TIGHT_R  0.15  // trailing stretto dopo l'estensione massima
#define EXT_ATR_MULT   1.2   // estensione massima = picco >= 1.2 x ATR M1
#define ENTRY_SPREAD_K 2.0   // ingresso: la candela deve essersi mossa di 2 x spread...
#define ENTRY_ATR_K    0.15  // ...oppure 0.15 x ATR (il maggiore dei due)
#define MOMENTUM_MS    3000  // il prezzo deve salire/scendere anche negli ultimi 3 s
#define REV_EXT_ATR    0.6   // inversione: la candela deve essersi estesa di 0.6 x ATR...
#define REV_PULL_ATR   0.2   // ...e il prezzo deve tornare indietro di 0.2 x ATR dal suo estremo
#define MAXPOS_LIMIT   40

//--- stato ------------------------------------------------------------
enum EAState { ST_STOPPED = 0, ST_RUNNING, ST_FINISHING };

CTrade   g_trade;
EAState  g_state   = ST_STOPPED;
bool     g_oneShot = false;
bool     g_hedging = true;

#define TICKBUF 8192
long     g_tMs[TICKBUF];
double   g_bid[TICKBUF];
int      g_head  = 0;
int      g_count = 0;

// spread (prezzo)
double   g_spr      = 0;
double   g_sprNorm  = 0;     // spread "normale" (media mobile lenta)
long     g_sprTicks = 0;

// indicatori interni
int      g_hATR  = INVALID_HANDLE;
int      g_hEMAf = INVALID_HANDLE;
int      g_hEMAs = INVALID_HANDLE;
double   g_bias  = 0;        // -1 (sell) ... +1 (buy)
string   g_biasInfo = "-";
datetime g_biasBar  = 0;

// posizioni seguite
ulong    g_pTicket[MAXPOS_LIMIT];
double   g_pBest[MAXPOS_LIMIT];
double   g_pRisk[MAXPOS_LIMIT];
bool     g_pBE[MAXPOS_LIMIT];
bool     g_pBuy[MAXPOS_LIMIT];
int      g_pN = 0;

long     g_lastEntryMs  = 0;
double   g_lastEntryPxBuy  = 0;
double   g_lastEntryPxSell = 0;
long     g_backoffMs    = 0;
string   g_lastReject   = "";
// dopo una chiusura non rientra nella stessa direzione, nella stessa candela,
// finche' il prezzo non supera il livello di chiusura (evita chiudi-riapri inutili)
double   g_rebuyAbove   = 0;
double   g_resellBelow  = 0;
datetime g_rebuyBar     = 0;
datetime g_resellBar    = 0;
long     g_lastModifyMs = 0;

// statistiche giornaliere
datetime g_statsDay   = 0;
bool     g_statsDirty = true;
double   g_dayPL      = 0;
int      g_dayTrades  = 0;
int      g_dayWins    = 0;
double   g_dayWinSum  = 0;
double   g_dayLossSum = 0;

// pannello
string   g_pfx         = "SM1_";
long     g_lastPanelMs = 0;
string   g_lastSignal  = "-";
string   g_blockReason = "";
string   g_posInfo     = "nessuna";

//+------------------------------------------------------------------+
int OnInit()
  {
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetAsyncMode(false);

   g_hedging = (AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);

   g_hATR  = iATR(_Symbol, PERIOD_M1, 14);
   g_hEMAf = iMA(_Symbol, PERIOD_M1, 9,  0, MODE_EMA, PRICE_CLOSE);
   g_hEMAs = iMA(_Symbol, PERIOD_M1, 21, 0, MODE_EMA, PRICE_CLOSE);
   if(g_hATR == INVALID_HANDLE || g_hEMAf == INVALID_HANDLE || g_hEMAs == INVALID_HANDLE)
     {
      Print("Errore creazione indicatori: ", GetLastError());
      return INIT_FAILED;
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

   PrintFormat("ScalperM1 v3 su %s: uscita=%s maxPos=%d conto %s, SL=%s spreadMax=%s",
               _Symbol, InpExitMode == EXIT_TRAILING ? "trailing" : "TP fisso",
               MaxPositions(), g_hedging ? "hedging" : "netting",
               InpSLPoints > 0 ? IntegerToString(InpSLPoints) : "auto",
               InpMaxSpreadPts > 0 ? IntegerToString(InpMaxSpreadPts) : "auto");
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
   if(g_hATR  != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hEMAf != INVALID_HANDLE) IndicatorRelease(g_hEMAf);
   if(g_hEMAs != INVALID_HANDLE) IndicatorRelease(g_hEMAs);
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
   UpdateBias();
   RefreshDailyStatsIfNeeded(tk.time);

   int n = ManagePositions(tk);

   if(n == 0 && g_state == ST_FINISHING)
      g_state = ST_STOPPED;
   if(g_state == ST_RUNNING)
      CheckEntry(tk, n);

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
      double px = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
      double gap = 0.2 * SLDist();
      datetime bar = iTime(_Symbol, PERIOD_M1, 0);
      // un deal SELL in uscita chiude un buy, un deal BUY in uscita chiude un sell
      if(HistoryDealGetInteger(trans.deal, DEAL_TYPE) == DEAL_TYPE_SELL)
        { g_rebuyAbove = px + gap; g_rebuyBar = bar; }
      else
        { g_resellBelow = px - gap; g_resellBar = bar; }

      PrintFormat("Chiuso #%I64d prezzo=%s profitto=%.2f",
                  HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID),
                  DoubleToString(px, _Digits),
                  HistoryDealGetDouble(trans.deal, DEAL_PROFIT));
     }
  }

//+------------------------------------------------------------------+
//| Tick buffer                                                      |
//+------------------------------------------------------------------+
void PushTick(long tMs, double bid)
  {
   g_tMs[g_head] = tMs;
   g_bid[g_head] = bid;
   g_head = (g_head + 1) % TICKBUF;
   if(g_count < TICKBUF)
      g_count++;
  }

// bid di winMs millisecondi fa; false se lo storico non basta o c'e' un buco
bool BidAgo(long nowMs, long winMs, double &bidAgo)
  {
   long cutoff = nowMs - winMs;
   for(int i = 1; i <= g_count; i++)
     {
      int idx = (g_head - i + TICKBUF) % TICKBUF;
      if(g_tMs[idx] <= cutoff)
        {
         if(cutoff - g_tMs[idx] > winMs)
            return false;
         bidAgo = g_bid[idx];
         return true;
        }
     }
   return false;
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

double MaxSpread()
  {
   if(InpMaxSpreadPts > 0)
      return InpMaxSpreadPts * _Point;
   return MathMax(2.0 * g_sprNorm, g_sprNorm + 3 * _Point);
  }

int DeviationPts()
  {
   if(InpDeviationPts > 0)
      return InpDeviationPts;
   return (int)MathMax(5.0, MathRound(2.0 * g_sprNorm / _Point));
  }

double ATR()
  {
   double b[];
   if(CopyBuffer(g_hATR, 0, 1, 1, b) == 1 && b[0] > 0)
      return b[0];
   return 20.0 * MathMax(g_sprNorm, _Point); // ripiego finche' l'ATR non e' pronto
  }

double SLDist()
  {
   if(InpSLPoints > 0)
      return InpSLPoints * _Point;
   return MathMax(InpSLATRMult * ATR(), 3.0 * g_sprNorm);
  }

double TPDist()
  {
   if(InpTPPoints > 0)
      return InpTPPoints * _Point;
   return SLDist();
  }

int MaxPositions()
  {
   if(!g_hedging)
      return 1; // su conto netting le posizioni si sommerebbero
   // per direzione: buy e sell insieme arrivano al massimo al doppio
   return (int)MathMax(1, MathMin(InpMaxPositions, MAXPOS_LIMIT / 2));
  }

//+------------------------------------------------------------------+
//| Bias: +1 favorisce i buy, -1 i sell                              |
//+------------------------------------------------------------------+
void UpdateBias()
  {
   datetime bar = iTime(_Symbol, PERIOD_M1, 0);
   if(bar == g_biasBar)
      return;

   double f[], s[];
   if(CopyBuffer(g_hEMAf, 0, 1, 2, f) != 2 || CopyBuffer(g_hEMAs, 0, 1, 1, s) != 1)
      return; // riprova al prossimo tick
   g_biasBar = bar;

   // EMA 9 sopra/sotto EMA 21 e pendenza della EMA 9
   double emaScore = (f[1] > s[0] ? 0.5 : -0.5) + (f[1] > f[0] ? 0.5 : -0.5);

   // ultime 10 candele chiuse: verdi meno rosse
   int bull = 0, bear = 0;
   for(int i = 1; i <= 10; i++)
     {
      double o = iOpen(_Symbol, PERIOD_M1, i), c = iClose(_Symbol, PERIOD_M1, i);
      if(c > o) bull++;
      else if(c < o) bear++;
     }
   double candleScore = (bull - bear) / 10.0;

   g_bias = 0.5 * emaScore + 0.5 * candleScore;
   g_biasInfo = StringFormat("%s %.0f%%  (EMA %s, %d verdi / %d rosse su 10)",
                             g_bias > 0.05 ? "BUY" : (g_bias < -0.05 ? "SELL" : "neutro"),
                             MathAbs(g_bias) * 100,
                             emaScore > 0 ? "su" : (emaScore < 0 ? "giu" : "piatta"), bull, bear);
  }

//+------------------------------------------------------------------+
//| Ingresso                                                         |
//+------------------------------------------------------------------+
void CheckEntry(const MqlTick &tk, int openCount)
  {
   g_blockReason = "";

   if(!(bool)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !(bool)MQLInfoInteger(MQL_TRADE_ALLOWED))
     { g_blockReason = "AutoTrading disattivato"; return; }
   if(tk.time_msc < g_backoffMs)
     { g_blockReason = "broker ha rifiutato: " + g_lastReject; return; }
   if(g_spr > MaxSpread())
     { g_blockReason = "spread anomalo"; return; }
   if(InpMaxDailyLoss > 0 && g_dayPL <= -InpMaxDailyLoss)
     { g_blockReason = "perdita max giornaliera"; return; }
   if(InpDailyTarget > 0 && g_dayPL >= InpDailyTarget)
     { g_blockReason = "target giornaliero"; return; }
   if(InpMaxTradesDay > 0 && g_dayTrades >= InpMaxTradesDay)
     { g_blockReason = "max trade giornalieri"; return; }
   if(tk.time_msc - g_lastEntryMs < MathMax(InpCooldownMs, 200))
      return;

   double open0 = iOpen(_Symbol, PERIOD_M1, 0);
   double high0 = iHigh(_Symbol, PERIOD_M1, 0);
   double low0  = iLow(_Symbol, PERIOD_M1, 0);
   double ago;
   if(open0 <= 0 || high0 <= 0 || low0 <= 0 || !BidAgo(tk.time_msc, MOMENTUM_MS, ago))
      return;

   double atr  = ATR();
   double move = tk.bid - open0;      // quanto si e' mossa la candela M1 in corso
   double push = tk.bid - ago;        // direzione degli ultimi 3 secondi

   // moltiplicatori del bias: entrare contro la direzione favorita e' piu' difficile
   double kBuy = 1.0, kSell = 1.0;
   if(InpUseBias)
     {
      if(g_bias < 0) kBuy  = 1.0 + InpBiasStrength * (-g_bias);
      if(g_bias > 0) kSell = 1.0 + InpBiasStrength * g_bias;
     }

   bool flipCont = (InpSignalMode != SIG_FOLLOW); // segnali di candela al contrario
   bool flipRev  = (InpSignalMode == SIG_INVERT); // segnali di inversione al contrario

   //--- 1) segnale di candela: la candela M1 si sta muovendo forte in una direzione
   //    (i moltiplicatori del bias si applicano alla direzione del trade che verra' aperto)
   double thr = MathMax(ENTRY_SPREAD_K * g_sprNorm, ENTRY_ATR_K * atr);
   bool up   = (move >=  thr * (flipCont ? kSell : kBuy) && push > 0);
   bool down = (move <= -thr * (flipCont ? kBuy : kSell) && push < 0);
   bool buy  = flipCont ? down : up;
   bool sell = flipCont ? up : down;
   string kind = flipCont ? "contro candela" : "candela";

   //--- 2) inversione: la candela si e' estesa e sta tornando indietro
   if(!buy && !sell && InpReversal && g_hedging)
     {
      double pull = MathMax(REV_PULL_ATR * atr, 2.0 * g_sprNorm);
      bool fromHigh = (high0 - open0 >= REV_EXT_ATR * atr && high0 - tk.bid >= pull * (flipRev ? kBuy : kSell) && push < 0);
      bool fromLow  = (open0 - low0 >= REV_EXT_ATR * atr && tk.bid - low0 >= pull * (flipRev ? kSell : kBuy) && push > 0);
      if(fromHigh)     { if(flipRev) buy = true;  else sell = true; kind = "inversione"; }
      else if(fromLow) { if(flipRev) sell = true; else buy = true;  kind = "inversione"; }
     }
   if(!buy && !sell)
      return;

   //--- niente chiudi-e-riapri: nella stessa candela rientra solo oltre il prezzo di chiusura
   datetime bar0 = iTime(_Symbol, PERIOD_M1, 0);
   if(buy && kind != "inversione" && g_rebuyBar == bar0 && tk.bid < g_rebuyAbove)
      return;
   if(sell && kind != "inversione" && g_resellBar == bar0 && tk.bid > g_resellBelow)
      return;

   //--- limiti per direzione
   int dir = buy ? 1 : -1;
   int sameDir = CountDir(dir);
   if(sameDir >= MaxPositions())
      return;
   if(sameDir > 0)
     {
      if(!AllAtBreakEvenDir(dir))
         return;
      double lastPx = buy ? g_lastEntryPxBuy : g_lastEntryPxSell;
      if(MathAbs(tk.bid - lastPx) < 0.5 * SLDist())
         return;
     }
   if(!g_hedging && openCount > 0)
      return; // su netting un trade opposto chiuderebbe quello aperto

   g_lastSignal = StringFormat("%s %s", buy ? "BUY" : "SELL", kind);
   OpenTrade(buy, tk);
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

// Lotto richiesto, ridotto se il margine libero non basta (lascia il 20% di margine di sicurezza).
// Ritorna 0 se non basta neanche per il lotto minimo.
double AffordableLots(bool isBuy, double price)
  {
   double lots = NormalizeLots(InpLots);
   double free = AccountInfoDouble(ACCOUNT_MARGIN_FREE) * 0.8;
   double m1;
   if(!OrderCalcMargin(isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL, _Symbol, 1.0, price, m1) || m1 <= 0)
      return lots; // non calcolabile: prova comunque
   if(lots * m1 <= free)
      return lots;
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double fit  = NormalizeLots(free / m1);
   if(free / m1 < vmin)
      return 0;
   static datetime warned = 0;
   if(TimeCurrent() - warned > 300)
     {
      warned = TimeCurrent();
      PrintFormat("Margine libero %.2f: lotto ridotto da %.2f a %.2f (servono %.2f per lotto)",
                  AccountInfoDouble(ACCOUNT_MARGIN_FREE), InpLots, fit, m1);
     }
   return fit;
  }

double NormPrice(double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts > 0)
      p = MathRound(p / ts) * ts;
   return NormalizeDouble(p, _Digits);
  }

double StopsMinDist()
  {
   long a = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long b = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   return (double)(a > b ? a : b) * _Point;
  }

void OpenTrade(bool isBuy, const MqlTick &tk)
  {
   double slDist = MathMax(SLDist(), StopsMinDist() + g_spr + _Point);
   double price  = isBuy ? tk.ask : tk.bid;
   double lots   = AffordableLots(isBuy, price);
   if(lots <= 0)
     {
      g_blockReason = "margine insufficiente anche per il lotto minimo";
      return;
     }
   // SL misurato dal prezzo di chiusura (bid per i buy, ask per i sell)
   double sl = NormPrice(isBuy ? tk.bid - slDist : tk.ask + slDist);
   double tp = 0;
   if(InpExitMode == EXIT_FIXED_TP)
     {
      double tpDist = MathMax(TPDist(), StopsMinDist() + _Point);
      tp = NormPrice(isBuy ? price + tpDist : price - tpDist);
     }

   g_trade.SetDeviationInPoints(DeviationPts());
   g_lastEntryMs = tk.time_msc;

   string cmt = StringFormat("SM1 b%+.0f", g_bias * 100);
   bool ok = isBuy ? g_trade.Buy(lots, _Symbol, price, sl, tp, cmt)
                   : g_trade.Sell(lots, _Symbol, price, sl, tp, cmt);

   uint rc = g_trade.ResultRetcode();
   if(ok && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED || rc == TRADE_RETCODE_DONE_PARTIAL))
     {
      if(isBuy) g_lastEntryPxBuy = tk.bid;
      else      g_lastEntryPxSell = tk.bid;
      PrintFormat("%s %.2f @ %s  SL=%s TP=%s  spread=%.0f bias=%+.0f%%",
                  isBuy ? "BUY" : "SELL", lots, DoubleToString(g_trade.ResultPrice(), _Digits),
                  DoubleToString(sl, _Digits), tp > 0 ? DoubleToString(tp, _Digits) : "-",
                  g_spr / _Point, g_bias * 100);
      if(g_oneShot)
        {
         g_oneShot = false;
         g_state = ST_FINISHING;
        }
     }
   else
     {
      g_backoffMs = tk.time_msc + 5000; // es. mercato chiuso / requote: riprova tra 5 s
      g_lastReject = StringFormat("%s (%u)", g_trade.ResultRetcodeDescription(), rc);
      PrintFormat("Ordine rifiutato: %u %s | %s %.2f lotti prezzo=%s SL=%s spread=%.0f stopsLevel=%d",
                  rc, g_trade.ResultRetcodeDescription(), isBuy ? "BUY" : "SELL", lots,
                  DoubleToString(price, _Digits), DoubleToString(sl, _Digits), g_spr / _Point,
                  (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL));
     }
  }

//+------------------------------------------------------------------+
//| Posizioni                                                        |
//+------------------------------------------------------------------+
int TrackIndex(ulong ticket, double open, double sl, bool isBuy)
  {
   for(int i = 0; i < g_pN; i++)
      if(g_pTicket[i] == ticket)
         return i;
   if(g_pN >= MAXPOS_LIMIT)
      return -1;
   int k = g_pN++;
   g_pTicket[k] = ticket;
   g_pBest[k]   = 0;
   g_pRisk[k]   = (sl > 0) ? MathAbs(open - sl) : SLDist();
   g_pBE[k]     = false;
   g_pBuy[k]    = isBuy;
   return k;
  }

void Untrack(int i)
  {
   g_pN--;
   g_pTicket[i] = g_pTicket[g_pN];
   g_pBest[i]   = g_pBest[g_pN];
   g_pRisk[i]   = g_pRisk[g_pN];
   g_pBE[i]     = g_pBE[g_pN];
   g_pBuy[i]    = g_pBuy[g_pN];
  }

bool IsMine()
  {
   return PositionGetString(POSITION_SYMBOL) == _Symbol &&
          PositionGetInteger(POSITION_MAGIC) == InpMagic;
  }

// numero di posizioni aperte in una direzione (+1 buy, -1 sell)
int CountDir(int dir)
  {
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsMine())
         continue;
      bool b = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
      if((dir > 0) == b)
         n++;
     }
   return n;
  }

bool AllAtBreakEvenDir(int dir)
  {
   for(int i = 0; i < g_pN; i++)
      if(g_pBuy[i] == (dir > 0) && !g_pBE[i])
         return false;
   return true;
  }

// gestisce tutte le posizioni del bot e ritorna quante sono aperte
int ManagePositions(const MqlTick &tk)
  {
   // togli dal tracking le posizioni non piu' aperte
   for(int i = g_pN - 1; i >= 0; i--)
      if(!PositionSelectByTicket(g_pTicket[i]))
         Untrack(i);

   int count = 0;
   g_posInfo = "";
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsMine())
         continue;
      count++;
      ManageOne(ticket, tk);
     }
   if(count == 0)
      g_posInfo = "nessuna";
   return count;
  }

void ManageOne(ulong ticket, const MqlTick &tk)
  {
   if(!PositionSelectByTicket(ticket))
      return;
   bool   isBuy  = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
   double open   = PositionGetDouble(POSITION_PRICE_OPEN);
   double curSL  = PositionGetDouble(POSITION_SL);
   double curTP  = PositionGetDouble(POSITION_TP);
   long   openMs = PositionGetInteger(POSITION_TIME_MSC);

   int k = TrackIndex(ticket, open, curSL, isBuy);
   if(k < 0)
      return;

   double fav = isBuy ? tk.bid - open : open - tk.ask;
   if(fav > g_pBest[k])
      g_pBest[k] = fav;
   double best = g_pBest[k];
   double r    = g_pRisk[k];

   if(StringLen(g_posInfo) < 80)
      g_posInfo += StringFormat("%s%s %+.0f%s", g_posInfo == "" ? "" : " | ",
                                isBuy ? "BUY" : "SELL", fav / _Point, g_pBE[k] ? " BE" : "");

   // 1) chiusura a tempo: solo se non e' mai arrivato al break-even E la candela M1 ora va contro
   //    (se la candela e' ancora a favore lo tiene: chiuderlo per riaprirlo costerebbe un altro spread)
   double o0 = iOpen(_Symbol, PERIOD_M1, 0);
   bool candleAgainst = (o0 > 0) && (isBuy ? tk.bid < o0 : tk.bid > o0);
   if(!g_pBE[k] && best < BE_TRIGGER_R * r && candleAgainst &&
      InpMaxHoldSec > 0 && tk.time_msc - openMs >= (long)InpMaxHoldSec * 1000)
     {
      ClosePos(ticket, StringFormat("tempo max senza BE (%+.0f pt)", fav / _Point));
      return;
     }

   if(InpExitMode == EXIT_FIXED_TP)
      return; // TP e SL sul server

   // 2) break-even veloce
   if(best >= BE_TRIGGER_R * r)
     {
      double lock = BE_LOCK_R * r;
      if(!g_pBE[k])
        {
         double beSL = NormPrice(isBuy ? open + lock : open - lock);
         if(ModifySL(ticket, isBuy, beSL, curTP, curSL, tk))
            g_pBE[k] = true;
        }
      if(fav <= lock)
        {
         ClosePos(ticket, StringFormat("ritorno a break-even (max %+.0f pt)", best / _Point));
         return;
        }
     }

   // 3) trailing: chiude appena il prezzo torna indietro dal massimo
   if(best >= TRAIL_START_R * r)
     {
      double dist = MathMax(TRAIL_MIN_R * r, TRAIL_PCT * best);
      if(best >= EXT_ATR_MULT * ATR())
         dist = MathMax(MathMin(dist, TRAIL_TIGHT_R * r), g_sprNorm); // estensione massima: stringe

      if(best - fav >= dist)
        {
         ClosePos(ticket, StringFormat("trailing: max %+.0f, chiuso a %+.0f pt", best / _Point, fav / _Point));
         return;
        }

      double lockPx = best - dist;
      double newSL  = NormPrice(isBuy ? open + lockPx : open - lockPx);
      double step   = MathMax(0.1 * r, _Point);
      bool better = isBuy ? (curSL == 0 || newSL >= curSL + step)
                          : (curSL == 0 || newSL <= curSL - step);
      if(better && tk.time_msc - g_lastModifyMs >= 300)
         ModifySL(ticket, isBuy, newSL, curTP, curSL, tk);
     }
  }

// true se lo SL e' gia' a quel livello (o migliore) oppure e' stato spostato
bool ModifySL(ulong ticket, bool isBuy, double newSL, double tp, double curSL, const MqlTick &tk)
  {
   if(curSL != 0 && (isBuy ? curSL >= newSL - _Point / 2 : curSL <= newSL + _Point / 2))
      return true;
   double minDist = StopsMinDist();
   if(isBuy && tk.bid - newSL < minDist)
      return false;
   if(!isBuy && newSL - tk.ask < minDist)
      return false;

   g_lastModifyMs = tk.time_msc;
   if(g_trade.PositionModify(ticket, newSL, tp))
      return true;
   PrintFormat("Modifica SL #%I64u fallita: %u %s", ticket, g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
   return false;
  }

void ClosePos(ulong ticket, string why)
  {
   g_trade.SetDeviationInPoints(DeviationPts());
   if(g_trade.PositionClose(ticket))
      PrintFormat("Chiusura #%I64u: %s", ticket, why);
   else
      PrintFormat("Chiusura #%I64u fallita: %u %s", ticket, g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
  }

void CloseAll(string why)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t != 0 && IsMine())
         ClosePos(t, why);
     }
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
   g_dayWinSum = 0;
   g_dayLossSum = 0;

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
         double net = profit + HistoryDealGetDouble(dl, DEAL_SWAP) + HistoryDealGetDouble(dl, DEAL_COMMISSION);
         if(profit > 0)
           {
            g_dayWins++;
            g_dayWinSum += net;
           }
         else
            g_dayLossSum += net;
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
   ObjectSetInteger(0, bg, OBJPROP_XSIZE, 400);
   ObjectSetInteger(0, bg, OBJPROP_YSIZE, 196);
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
   MakeLabel("dir",   20, 154,  9, clrKhaki);

   MakeButton("btnStart", "Start",       20, 182, 80, clrDodgerBlue);
   MakeButton("btnOne",   "Start One",  105, 182, 80, clrDodgerBlue);
   MakeButton("btnFin",   "Finish",     190, 182, 80, clrSteelBlue);
   MakeButton("btnStop",  "Stop+Close", 275, 182, 85, clrFireBrick);

   ObjectSetString(0, g_pfx + "title", OBJPROP_TEXT, "ScalperM1   " + _Symbol +
                   (InpSignalMode == SIG_FOLLOW ? "" : (InpSignalMode == SIG_FADE ? "   [contrario]" : "   [invertito]")));
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

   // stato
   string st;
   color  sc;
   if(g_state == ST_STOPPED)        { st = "FERMO  -  premi Start";      sc = clrGray; }
   else if(g_state == ST_FINISHING) { st = "IN CHIUSURA  -  nessun nuovo trade"; sc = clrOrange; }
   else if(g_blockReason != "")     { st = "IN PAUSA  -  " + g_blockReason; sc = clrOrange; }
   else                             { st = "ATTIVO";                     sc = clrLimeGreen; }
   SetText("state", st, sc);

   // risultato del giorno
   SetText("pl", StringFormat("Oggi  %+.2f %s", g_dayPL, cur), PLColor(g_dayPL));

   double wr = g_dayTrades > 0 ? 100.0 * g_dayWins / g_dayTrades : 0;
   int    losses = g_dayTrades - g_dayWins;
   SetText("stats", StringFormat("Trade %d    Vinti %d    Persi %d    Win rate %.0f%%",
                                 g_dayTrades, g_dayWins, losses, wr));

   double avgW = g_dayWins > 0 ? g_dayWinSum / g_dayWins : 0;
   double avgL = losses > 0 ? g_dayLossSum / losses : 0;
   SetText("avg", StringFormat("Vincita media %+.2f    Perdita media %+.2f", avgW, avgL));

   // posizioni aperte
   int    nOpen = 0;
   double floating = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsMine())
         continue;
      nOpen++;
      floating += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
     }
   SetText("open", StringFormat("Aperte %d (%d buy, %d sell)   In corso %+.2f   Saldo %.2f",
                                nOpen, CountDir(1), CountDir(-1), floating, AccountInfoDouble(ACCOUNT_BALANCE)),
           nOpen > 0 ? PLColor(floating) : clrSilver);

   // direzione favorita
   string dir = "Direzione: neutra";
   if(InpUseBias)
     {
      if(g_bias > 0.05)       dir = StringFormat("Direzione: favoriti i BUY (%.0f%%)", g_bias * 100);
      else if(g_bias < -0.05) dir = StringFormat("Direzione: favoriti i SELL (%.0f%%)", -g_bias * 100);
     }
   else
      dir = "Direzione: bias spento";
   SetText("dir", dir);

   ChartRedraw();
  }

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(id != CHARTEVENT_OBJECT_CLICK || StringFind(sparam, g_pfx + "btn") != 0)
      return;

   ObjectSetInteger(0, sparam, OBJPROP_STATE, false);

   if(sparam == g_pfx + "btnStart")
     {
      g_state = ST_RUNNING;
      g_oneShot = false;
     }
   else if(sparam == g_pfx + "btnOne")
     {
      g_state = ST_RUNNING;
      g_oneShot = true;
     }
   else if(sparam == g_pfx + "btnFin")
     {
      g_state = ST_FINISHING;
      g_oneShot = false;
     }
   else if(sparam == g_pfx + "btnStop")
     {
      g_state = ST_STOPPED;
      g_oneShot = false;
      CloseAll("Stop manuale");
     }

   PrintFormat("Pulsante %s -> stato %s", StringSubstr(sparam, StringLen(g_pfx)), StateText());
   UpdatePanel();
  }
//+------------------------------------------------------------------+
