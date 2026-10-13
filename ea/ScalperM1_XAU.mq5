//+------------------------------------------------------------------+
//|                                              ScalperM1_XAU.mq5   |
//|  Scalper tick-momentum per XAUUSD                                |
//|  - una posizione alla volta                                      |
//|  - ingresso nella direzione del movimento degli ultimi N ms      |
//|  - filtri: spread, orario, trend EMA, candela M1, ATR, RSI       |
//|  - uscita: TP fisso oppure "runner" (break-even veloce +         |
//|    trailing che chiude appena il prezzo torna indietro)          |
//|  - pannello con Start / Start One / Finish / Stop                |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "2.00"
#property description "Tick-momentum scalper XAUUSD con BE veloce, trailing e filtri trend/ATR"

#include <Trade\Trade.mqh>

enum TradeProfile
  {
   PROFILE_AGGRESSIVE = 0, // Aggressivo: tanti trade, filtri spenti
   PROFILE_CUSTOM     = 1  // Personalizzato: usa i parametri qui sotto
  };

enum ExitMode
  {
   EXIT_FIXED_TP = 0, // TP fisso
   EXIT_RUNNER   = 1  // Break-even + trailing (lascia correre)
  };

//--- parametri ------------------------------------------------------
input group "Profilo"
input TradeProfile InpProfile        = PROFILE_AGGRESSIVE; // Profilo di trading

input group "Gestione ordine"
input double   InpLots               = 0.01;  // Lotti
input int      InpSLPoints           = 50;    // Stop loss iniziale (punti, 50 = 0.50$)
input bool     InpSLAddSpread        = true;  // Aggiungi lo spread corrente allo SL
input int      InpDeviation          = 10;    // Slippage massimo (punti)
input long     InpMagic              = 41378; // Magic number

input group "Uscita"
input ExitMode InpExitMode           = EXIT_RUNNER; // Modalita' di uscita
input int      InpTPPoints           = 50;    // TP fisso (solo modalita' TP fisso)
input int      InpRunnerMaxTP        = 400;   // TP di sicurezza in modalita' runner (0 = nessuno)
input int      InpBEActivatePts      = 25;    // Sposta a break-even dopo +X punti
input int      InpBELockPts          = 5;     // Punti di profitto bloccati al break-even
input int      InpTrailStartPts      = 40;    // Trailing attivo dopo +X punti
input int      InpTrailMinPts        = 15;    // Distanza minima trailing (punti)
input int      InpTrailPct           = 35;    // Trailing: % del profitto massimo che puo' restituire
input double   InpExtATRMult         = 1.2;   // "Estensione massima" = profitto >= ATR(M1) x questo (0 = off)
input int      InpTrailTightPts      = 8;     // Trailing stretto dopo l'estensione massima (punti)
input int      InpTrailStepPts       = 5;     // Sposta lo SL sul server ogni X punti
input int      InpMaxHoldSec         = 60;    // Chiude se dopo X secondi non ha raggiunto il BE (0 = off)
input int      InpReverseActivatePts = 20;    // (TP fisso) uscita su inversione dopo +X punti
input int      InpReverseExitPoints  = 20;    // (TP fisso) chiudi se ritraccia X punti (0 = off)

input group "Segnale momentum"
input int      InpMomentumPoints     = 30;    // Movimento minimo nella finestra (punti)
input int      InpMomentumMs         = 5000;  // Finestra del movimento (millisecondi)
input int      InpMinTicksInWindow   = 5;     // Tick minimi nella finestra
input bool     InpRequireExtreme     = true;  // Prezzo deve essere vicino all'estremo della finestra
input int      InpExtremeTolPoints   = 5;     // Tolleranza dall'estremo (punti)
input int      InpCooldownMs         = 1000;  // Pausa dopo una chiusura (millisecondi)

input group "Filtro trend (EMA)"
input bool            InpUseTrendFilter = true;      // Opera solo nella direzione del trend
input ENUM_TIMEFRAMES InpTrendTF        = PERIOD_M5; // Timeframe del trend
input int             InpTrendFastEMA   = 20;        // EMA veloce
input int             InpTrendSlowEMA   = 50;        // EMA lenta

input group "Filtro candela M1"
input bool     InpUseCandleFilter    = true;  // La candela M1 attuale deve andare nella direzione del trade
input int      InpMinBodyPts         = 10;    // Corpo minimo della candela (punti)

input group "Filtro volatilita' (ATR M1)"
input bool     InpUseATRFilter       = true;  // Usa filtro ATR
input int      InpATRPeriod          = 14;    // Periodo ATR
input int      InpMinATRPts          = 40;    // ATR minimo (punti): sotto = mercato troppo fermo
input int      InpMaxATRPts          = 0;     // ATR massimo (punti): sopra = news/caos (0 = off)

input group "Filtro RSI M1"
input bool     InpUseRSIFilter       = false; // Usa filtro RSI (evita ingressi a fine movimento)
input int      InpRSIPeriod          = 14;    // Periodo RSI
input int      InpRSIMaxBuy          = 75;    // Non comprare sopra questo RSI
input int      InpRSIMinSell         = 25;    // Non vendere sotto questo RSI

input group "Filtri generali"
input int      InpMaxSpread          = 25;    // Spread massimo (punti)
input bool     InpUseTimeFilter      = true;  // Usa filtro orario (ora server)
input int      InpStartHour          = 9;     // Ora inizio (server)
input int      InpEndHour            = 21;    // Ora fine (server, esclusa)

input group "Limiti giornalieri (valuta conto, 0 = off)"
input double   InpMaxDailyLoss       = 0;     // Perdita massima giornaliera
input double   InpDailyTarget        = 0;     // Obiettivo giornaliero
input int      InpMaxTradesDay       = 0;     // Numero massimo trade al giorno

input group "Avvio"
input bool     InpAutoStart          = false; // Parte in RUNNING senza premere Start (sempre attivo nel tester)

//--- valori effettivi (input oppure profilo aggressivo) ---------------
int      cMomentumPoints;
int      cMomentumMs;
int      cMinTicksInWindow;
bool     cRequireExtreme;
int      cCooldownMs;
bool     cUseTrendFilter;
bool     cUseCandleFilter;
int      cMinBodyPts;
bool     cUseATRFilter;
int      cMinATRPts;
bool     cUseTimeFilter;

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
bool     g_beDone      = false;
long     g_lastModifyMs = 0;
string   g_posInfo     = "nessuna";

// indicatori
int      g_hFast = INVALID_HANDLE;
int      g_hSlow = INVALID_HANDLE;
int      g_hATR  = INVALID_HANDLE;
int      g_hRSI  = INVALID_HANDLE;
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
void ApplyProfile()
  {
   cMomentumPoints   = InpMomentumPoints;
   cMomentumMs       = InpMomentumMs;
   cMinTicksInWindow = InpMinTicksInWindow;
   cRequireExtreme   = InpRequireExtreme;
   cCooldownMs       = InpCooldownMs;
   cUseTrendFilter   = InpUseTrendFilter;
   cUseCandleFilter  = InpUseCandleFilter;
   cMinBodyPts       = InpMinBodyPts;
   cUseATRFilter     = InpUseATRFilter;
   cMinATRPts        = InpMinATRPts;
   cUseTimeFilter    = InpUseTimeFilter;

   if(InpProfile == PROFILE_AGGRESSIVE)
     {
      // entra su movimenti piccoli e veloci, quasi senza filtri: tanti trade su ogni candela M1
      cMomentumPoints   = 15;
      cMomentumMs       = 3000;
      cMinTicksInWindow = 3;
      cRequireExtreme   = false;
      cCooldownMs       = 300;
      cUseTrendFilter   = false;
      cUseCandleFilter  = true;   // solo direzione della candela M1, senza corpo minimo
      cMinBodyPts       = 0;
      cUseATRFilter     = false;
      cUseTimeFilter    = false;  // lavora sempre; lo spread massimo protegge da rollover e news
     }
  }

int OnInit()
  {
   ApplyProfile();
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(InpDeviation);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetAsyncMode(false);

   if(InpTPPoints <= 0 || InpSLPoints <= 0 || cMomentumMs <= 0)
     {
      Print("Parametri non validi: TP, SL e finestra devono essere > 0");
      return INIT_PARAMETERS_INCORRECT;
     }

   g_hFast = iMA(_Symbol, InpTrendTF, InpTrendFastEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hSlow = iMA(_Symbol, InpTrendTF, InpTrendSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
   g_hATR  = iATR(_Symbol, PERIOD_M1, InpATRPeriod);
   g_hRSI  = iRSI(_Symbol, PERIOD_M1, InpRSIPeriod, PRICE_CLOSE);
   if(g_hFast == INVALID_HANDLE || g_hSlow == INVALID_HANDLE ||
      g_hATR == INVALID_HANDLE || g_hRSI == INVALID_HANDLE)
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

   PrintFormat("ScalperM1 v2 avviato su %s [%s]: uscita=%s SL=%d(+spread=%s) BE=%d trail=%d/%d%% momentum=%dpt/%dms maxSpread=%d",
               _Symbol, InpProfile == PROFILE_AGGRESSIVE ? "AGGRESSIVO" : "personalizzato", InpExitMode == EXIT_RUNNER ? "runner" : "TP fisso", InpSLPoints,
               InpSLAddSpread ? "si" : "no", InpBEActivatePts, InpTrailStartPts, InpTrailPct,
               cMomentumPoints, cMomentumMs, InpMaxSpread);
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
   if(g_hFast != INVALID_HANDLE) IndicatorRelease(g_hFast);
   if(g_hSlow != INVALID_HANDLE) IndicatorRelease(g_hSlow);
   if(g_hATR  != INVALID_HANDLE) IndicatorRelease(g_hATR);
   if(g_hRSI  != INVALID_HANDLE) IndicatorRelease(g_hRSI);
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
      g_posInfo = "nessuna";
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

   if(cUseTimeFilter && !InTradingHours(tk.time))
     { g_blockReason = "fuori orario"; return; }

   if(InpMaxDailyLoss > 0 && g_dayPL <= -InpMaxDailyLoss)
     { g_blockReason = "perdita max giornaliera"; return; }
   if(InpDailyTarget > 0 && g_dayPL >= InpDailyTarget)
     { g_blockReason = "target giornaliero"; return; }
   if(InpMaxTradesDay > 0 && g_dayTrades >= InpMaxTradesDay)
     { g_blockReason = "max trade giornalieri"; return; }

   if(tk.time_msc - g_lastCloseMs < cCooldownMs)
     { g_blockReason = "cooldown"; return; }
   if(tk.time_msc - g_lastEntryMs < 500) // evita doppi invii
      return;

   double bidAgo = 0, hi = 0, lo = 0;
   int ticks = 0;
   if(!WindowStats(tk.time_msc, cMomentumMs, bidAgo, hi, lo, ticks))
      return;
   if(ticks < cMinTicksInWindow)
      return;

   double delta = (tk.bid - bidAgo) / _Point;
   double tol   = InpExtremeTolPoints * _Point;

   bool buy  = delta >=  cMomentumPoints;
   bool sell = delta <= -cMomentumPoints;

   if(cRequireExtreme)
     {
      if(buy  && tk.bid < hi - tol) buy  = false;
      if(sell && tk.bid > lo + tol) sell = false;
     }

   if(!buy && !sell)
      return;

   g_lastSignal = StringFormat("%s  delta %+.0f pt in %d ms", buy ? "BUY" : "SELL", delta, cMomentumMs);

   string why = FilterReject(buy, tk);
   if(why != "")
     {
      g_lastSignal += "  -> scartato: " + why;
      return;
     }
   OpenTrade(buy, tk, delta);
  }

//+------------------------------------------------------------------+
//| Indicatori e filtri                                              |
//+------------------------------------------------------------------+
bool GetBuf(int handle, int shift, double &val)
  {
   if(handle == INVALID_HANDLE)
      return false;
   double b[];
   if(CopyBuffer(handle, 0, shift, 1, b) != 1)
      return false;
   val = b[0];
   return true;
  }

// +1 trend rialzista, -1 ribassista, 0 dati non pronti
int TrendDir()
  {
   double fast, slow;
   if(!GetBuf(g_hFast, 1, fast) || !GetBuf(g_hSlow, 1, slow))
      return 0;
   if(fast > slow) return 1;
   if(fast < slow) return -1;
   return 0;
  }

double ATRPoints()
  {
   double v;
   if(!GetBuf(g_hATR, 1, v))
      return -1;
   return v / _Point;
  }

// Ritorna "" se il segnale passa tutti i filtri, altrimenti il motivo dello scarto.
string FilterReject(bool isBuy, const MqlTick &tk)
  {
   if(cUseTrendFilter)
     {
      int t = TrendDir();
      if(t == 0)                return "trend non pronto";
      if(isBuy && t < 0)        return "contro trend";
      if(!isBuy && t > 0)       return "contro trend";
     }

   if(cUseCandleFilter)
     {
      double o = iOpen(_Symbol, PERIOD_M1, 0);
      if(o <= 0)                return "candela non pronta";
      double body = (tk.bid - o) / _Point;
      if(isBuy && body < cMinBodyPts)   return "candela M1 non rialzista";
      if(!isBuy && -body < cMinBodyPts) return "candela M1 non ribassista";
     }

   if(cUseATRFilter)
     {
      double atr = ATRPoints();
      if(atr < 0)                                return "ATR non pronto";
      if(atr < cMinATRPts)                     return StringFormat("ATR basso (%.0f)", atr);
      if(InpMaxATRPts > 0 && atr > InpMaxATRPts) return StringFormat("ATR alto (%.0f)", atr);
     }

   if(InpUseRSIFilter)
     {
      double rsi;
      if(!GetBuf(g_hRSI, 0, rsi))         return "RSI non pronto";
      if(isBuy && rsi > InpRSIMaxBuy)     return StringFormat("RSI %.0f ipercomprato", rsi);
      if(!isBuy && rsi < InpRSIMinSell)   return StringFormat("RSI %.0f ipervenduto", rsi);
     }
   return "";
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
   double tpDist = (InpExitMode == EXIT_FIXED_TP) ? InpTPPoints * _Point : InpRunnerMaxTP * _Point;
   double slDist = InpSLPoints * _Point + (InpSLAddSpread ? spread : 0);
   double lots   = NormalizeLots(InpLots);

   double price, sl, tp;
   if(isBuy)
     {
      price = tk.ask;
      tp = tpDist > 0 ? NormPrice(price + tpDist) : 0;
      sl = NormPrice(price - slDist);
     }
   else
     {
      price = tk.bid;
      tp = tpDist > 0 ? NormPrice(price - tpDist) : 0;
      sl = NormPrice(price + slDist);
     }

   // distanza minima stop del broker (rispetto al prezzo di chiusura)
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(minDist > 0)
     {
      double closePx = isBuy ? tk.bid : tk.ask;
      if((tp > 0 && MathAbs(tp - closePx) < minDist) || MathAbs(closePx - sl) < minDist)
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
   bool   isBuy  = (type == POSITION_TYPE_BUY);
   double open   = PositionGetDouble(POSITION_PRICE_OPEN);
   double curSL  = PositionGetDouble(POSITION_SL);
   double curTP  = PositionGetDouble(POSITION_TP);
   long   openMs = PositionGetInteger(POSITION_TIME_MSC);

   if(g_trackTicket != ticket)
     {
      g_trackTicket = ticket;
      g_bestFav = 0;
      g_beDone = false;
     }

   double fav = isBuy ? (tk.bid - open) : (open - tk.ask);
   if(fav > g_bestFav)
      g_bestFav = fav;

   double favPts  = fav / _Point;
   double peakPts = g_bestFav / _Point;
   g_posInfo = StringFormat("%s %+.0f pt (max %+.0f)%s", isBuy ? "BUY" : "SELL", favPts, peakPts, g_beDone ? "  BE ok" : "");

   //--- modalita' TP fisso: logica originale
   if(InpExitMode == EXIT_FIXED_TP)
     {
      if(InpReverseExitPoints > 0 &&
         peakPts >= InpReverseActivatePts &&
         peakPts - favPts >= InpReverseExitPoints)
        {
         ClosePos(ticket, StringFormat("inversione (max %+.0f, ora %+.0f pt)", peakPts, favPts));
         return;
        }
      if(InpMaxHoldSec > 0 && tk.time_msc - openMs >= (long)InpMaxHoldSec * 1000)
         ClosePos(ticket, StringFormat("tempo max (%+.0f pt)", favPts));
      return;
     }

   //--- modalita' runner
   // 1) uscita a tempo solo se il trade non e' mai arrivato al break-even
   if(!g_beDone && peakPts < InpBEActivatePts &&
      InpMaxHoldSec > 0 && tk.time_msc - openMs >= (long)InpMaxHoldSec * 1000)
     {
      ClosePos(ticket, StringFormat("tempo max senza BE (%+.0f pt)", favPts));
      return;
     }

   // 2) break-even appena il trade corre a favore
   if(peakPts >= InpBEActivatePts)
     {
      if(!g_beDone)
        {
         double beSL = NormPrice(isBuy ? open + InpBELockPts * _Point : open - InpBELockPts * _Point);
         if(ModifySL(ticket, isBuy, beSL, curTP, curSL, tk))
           {
            g_beDone = true;
            PrintFormat("Break-even #%I64u: SL=%.2f (max %+.0f pt)", ticket, beSL, peakPts);
           }
        }
      // protezione locale: se torna sotto il livello BE chiude subito (anche se la modifica e' fallita)
      if(favPts <= InpBELockPts)
        {
         ClosePos(ticket, StringFormat("ritorno a break-even (max %+.0f pt)", peakPts));
         return;
        }
     }

   // 3) trailing: chiude appena il prezzo torna indietro dal massimo
   if(peakPts >= InpTrailStartPts)
     {
      double dist = MathMax((double)InpTrailMinPts, peakPts * InpTrailPct / 100.0);
      bool   ext  = false;
      if(InpExtATRMult > 0)
        {
         double atr = ATRPoints();
         if(atr > 0 && peakPts >= atr * InpExtATRMult)
           {
            dist = MathMin(dist, (double)InpTrailTightPts);
            ext = true;
           }
        }
      g_posInfo += StringFormat("  trail %.0f%s", dist, ext ? " (estensione)" : "");

      if(peakPts - favPts >= dist)
        {
         ClosePos(ticket, StringFormat("trailing%s: max %+.0f, chiuso a %+.0f pt", ext ? " stretto" : "", peakPts, favPts));
         return;
        }

      // aggiorna lo SL anche sul server (protezione se la connessione cade)
      double lockPts = peakPts - dist;
      double newSL = NormPrice(isBuy ? open + lockPts * _Point : open - lockPts * _Point);
      bool better = isBuy ? (curSL == 0 || newSL >= curSL + InpTrailStepPts * _Point)
                          : (curSL == 0 || newSL <= curSL - InpTrailStepPts * _Point);
      if(better && tk.time_msc - g_lastModifyMs >= 300)
         ModifySL(ticket, isBuy, newSL, curTP, curSL, tk);
     }
  }

// Sposta lo SL rispettando la distanza minima del broker. true se lo SL e' gia' a quel livello o e' stato modificato.
bool ModifySL(ulong ticket, bool isBuy, double newSL, double tp, double curSL, const MqlTick &tk)
  {
   if(curSL != 0 && MathAbs(curSL - newSL) < _Point / 2)
      return true;
   if(isBuy && curSL != 0 && newSL < curSL)
      return true; // mai peggiorare lo SL
   if(!isBuy && curSL != 0 && newSL > curSL)
      return true;

   long stopsLvl  = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   long freezeLvl = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double minDist = (double)(stopsLvl > freezeLvl ? stopsLvl : freezeLvl) * _Point;
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
   ObjectSetInteger(0, bg, OBJPROP_XSIZE, 520);
   ObjectSetInteger(0, bg, OBJPROP_YSIZE, 186);
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
   MakeLabel("filt",   20, 118,  9, clrKhaki);
   MakeLabel("pos",    20, 136,  9, clrLime);

   MakeButton("btnStart", "Start",      20, 172, 80, clrDodgerBlue);
   MakeButton("btnOne",   "Start One", 105, 172, 80, clrDodgerBlue);
   MakeButton("btnFin",   "Finish",    190, 172, 80, clrSteelBlue);
   MakeButton("btnStop",  "Stop+Close",275, 172, 85, clrFireBrick);

   ObjectSetString(0, g_pfx + "title", OBJPROP_TEXT, "ScalperM1 " + _Symbol +
                   (InpProfile == PROFILE_AGGRESSIVE ? "  [AGGRESSIVO]" : "  [personalizzato]"));
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
   else if(g_state == ST_STOPPED)
      st += "  (premi Start)";
   SetText("state", st);

   double avg = g_sprN > 0 ? g_sprSum / (double)g_sprN : 0;
   SetText("spread", StringFormat("Spread: %d / limite %d   (visti: min %d  media %.1f  max %d)",
                                  g_sprNow, InpMaxSpread, g_sprN > 0 ? g_sprMin : 0, avg, g_sprMax));

   double wr = g_dayTrades > 0 ? 100.0 * g_dayWins / g_dayTrades : 0;
   SetText("day", StringFormat("Oggi: %d trade  win %.0f%%  P/L netto %.2f",
                               g_dayTrades, wr, g_dayPL));
   SetText("signal", "Ultimo segnale: " + g_lastSignal);

   int    td  = TrendDir();
   double atr = ATRPoints();
   double rsi = 0;
   GetBuf(g_hRSI, 0, rsi);
   MqlTick tk;
   double body = 0;
   if(SymbolInfoTick(_Symbol, tk))
      body = (tk.bid - iOpen(_Symbol, PERIOD_M1, 0)) / _Point;
   SetText("filt", StringFormat("Trend %s: %s   ATR %.0f   RSI %.0f   candela %+.0f",
                                StringSubstr(EnumToString(InpTrendTF), 7),
                                td > 0 ? "UP" : (td < 0 ? "DOWN" : "-"), atr, rsi, body));
   SetText("pos", "Posizione: " + g_posInfo);
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
