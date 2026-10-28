//+------------------------------------------------------------------+
//|                                              TVRatings_XAU.mq5   |
//|  v1 - Replica delle "Technical Ratings" di TradingView           |
//|  (widget "Analisi tecnica": Forte acquisto ... Forte vendita)    |
//|  - 15 componenti medie mobili + 11 oscillatori, voto +1/-1/0     |
//|  - calcolo sulle candele CHIUSE del timeframe scelto             |
//|  - ingresso sul passaggio di soglia, filtro su un secondo TF     |
//|  - lotto fisso o % del saldo, SL/TP in pips o multipli di ATR    |
//|  - uscita su rating neutro / girato, oppure solo SL e TP         |
//|  Tutti gli indicatori sono calcolati nel codice con le formule   |
//|  di TradingView (RMA di Wilder, EMA con seme SMA, ecc.), non con |
//|  gli indicatori standard di MT5, che in alcuni casi differiscono |
//|  (es. iADX).                                                     |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "1.00"
#property description "Technical Ratings stile TradingView su XAUUSD: segnale + filtro multi-timeframe"

#include <Trade\Trade.mqh>

#define NA EMPTY_VALUE   // valore "non disponibile" (come na in Pine)

enum RatingSource
  {
   SRC_TOTAL = 0, // Rating totale
   SRC_MA    = 1, // Rating medie mobili
   SRC_OSC   = 2  // Rating oscillatori
  };

enum EntryMode
  {
   ENTRY_CROSS = 0, // Solo quando il rating attraversa la soglia
   ENTRY_LEVEL = 1  // Ogni candela in cui il rating e' oltre la soglia
  };

enum TradeDir
  {
   DIR_BOTH = 0, // Buy e Sell
   DIR_BUY  = 1, // Solo Buy
   DIR_SELL = 2  // Solo Sell
  };

enum ExitMode
  {
   EXIT_SLTP    = 0, // Solo SL e TP
   EXIT_NEUTRAL = 1, // Chiude quando il rating torna neutro (o si gira)
   EXIT_REVERSE = 2  // Chiude solo quando il rating si gira
  };

enum LotMode
  {
   LOT_FIXED = 0, // Lotto fisso
   LOT_RISK  = 1  // % del saldo rischiata sullo SL
  };

enum StopMode
  {
   STOP_PIPS = 0, // SL e TP in pips
   STOP_ATR  = 1  // SL e TP in multipli di ATR
  };

//--- parametri ------------------------------------------------------
input group "Segnale"
input ENUM_TIMEFRAMES InpSignalTF    = PERIOD_H1;   // Timeframe del segnale
input RatingSource    InpSignalSrc   = SRC_TOTAL;   // Rating usato per il segnale
input EntryMode       InpEntryMode   = ENTRY_CROSS; // Modalita' di ingresso
input double          InpBuyLevel    = 0.5;         // Soglia BUY (rating sopra)
input double          InpSellLevel   = -0.5;        // Soglia SELL (rating sotto)
input TradeDir        InpDirection   = DIR_BOTH;    // Direzioni ammesse

input group "Filtro sul secondo timeframe"
input bool            InpUseFilter   = true;        // Usa il filtro
input ENUM_TIMEFRAMES InpFilterTF    = PERIOD_D1;   // Timeframe del filtro
input RatingSource    InpFilterSrc   = SRC_TOTAL;   // Rating usato per il filtro
input double          InpFilterLevel = 0.1;         // BUY se filtro > livello, SELL se filtro < -livello (0.1 = almeno Acquisto, -0.1 = non contrario)

input group "Uscita"
input ExitMode        InpExitMode    = EXIT_NEUTRAL; // Tipo di uscita
input double          InpNeutralBand = 0.1;          // Fascia neutra (+/-): neutro = tra -X e +X

input group "Gestione del rischio"
input LotMode         InpLotMode     = LOT_FIXED;   // Calcolo del lotto
input double          InpFixedLots   = 0.01;        // Lotto fisso
input double          InpRiskPercent = 1.0;         // Rischio % del saldo (solo modalita' %)
input StopMode        InpStopMode    = STOP_ATR;    // SL/TP in pips o ATR
input double          InpSLPips      = 500;         // SL in pips (0 = nessuno) - 500 pips = 5.00 $
input double          InpTPPips      = 1000;        // TP in pips (0 = nessuno)
input int             InpATRPeriod   = 14;          // Periodo ATR (sul TF del segnale)
input double          InpSLATR       = 1.5;         // SL = ATR x (0 = nessuno)
input double          InpTPATR       = 3.0;         // TP = ATR x (0 = nessuno)
input double          InpPipSize     = 0.01;        // Valore di 1 pip in prezzo (oro: 0.01)

input group "Filtri orario e spread"
input bool            InpUseHours    = false;       // Usa il filtro orario (ora del server)
input int             InpStartHour   = 8;           // Ora di inizio (inclusa)
input int             InpEndHour     = 20;          // Ora di fine (esclusa; se < inizio passa la mezzanotte)
input double          InpMaxSpread   = 50;          // Spread massimo in pips (0 = off)

input group "Ordini"
input long            InpMagic       = 26102801;    // Magic number
input double          InpSlippage    = 30;          // Slippage massimo in pips
input string          InpComment     = "TVRatings"; // Commento ordini

input group "Calcolo e grafico"
input int             InpHistoryBars = 800;         // Candele usate per il calcolo
input bool            InpShowPanel   = true;        // Mostra i rating sul grafico
input bool            InpLogRatings  = false;       // Scrive i rating nel journal a ogni candela

input group "Medie mobili (default TradingView)"
input int    InpMA1      = 10;    // SMA/EMA 1
input int    InpMA2      = 20;    // SMA/EMA 2
input int    InpMA3      = 30;    // SMA/EMA 3
input int    InpMA4      = 50;    // SMA/EMA 4
input int    InpMA5      = 100;   // SMA/EMA 5
input int    InpMA6      = 200;   // SMA/EMA 6
input int    InpHullLen  = 9;     // Hull MA
input int    InpVWMALen  = 20;    // VWMA
input int    InpIchiConv = 9;     // Ichimoku Tenkan
input int    InpIchiBase = 26;    // Ichimoku Kijun
input int    InpIchiSpanB= 52;    // Ichimoku Span B
input int    InpIchiShift= 25;    // Ichimoku spostamento nuvola (TradingView: displacement 26 = 25 candele)

input group "Oscillatori (default TradingView)"
input int    InpRSILen   = 14;    // RSI
input int    InpStochK   = 14;    // Stocastico %K
input int    InpStochSm  = 3;     // Stocastico smussamento %K
input int    InpStochD   = 3;     // Stocastico %D
input int    InpCCILen   = 20;    // CCI
input bool   InpCCITypical = false; // CCI su prezzo tipico (false = su chiusura, come TradingView)
input int    InpADXLen   = 14;    // ADX / DI
input int    InpAOFast   = 5;     // Awesome Oscillator veloce
input int    InpAOSlow   = 34;    // Awesome Oscillator lento
input int    InpMomLen   = 10;    // Momentum
input int    InpMACDFast = 12;    // MACD veloce
input int    InpMACDSlow = 26;    // MACD lento
input int    InpMACDSig  = 9;     // MACD signal
input int    InpSRSIK    = 3;     // Stoch RSI %K
input int    InpSRSID    = 3;     // Stoch RSI %D
input int    InpSRSIRsi  = 14;    // Stoch RSI periodo RSI
input int    InpSRSIStoch= 14;    // Stoch RSI periodo stocastico
input int    InpWPRLen   = 14;    // Williams %R
input int    InpBBPLen   = 13;    // Bull Bear Power
input int    InpUO1      = 7;     // Ultimate Oscillator 1
input int    InpUO2      = 14;    // Ultimate Oscillator 2
input int    InpUO3      = 28;    // Ultimate Oscillator 3
input int    InpTrendLen = 50;    // Trend (Stoch RSI e Bull Bear Power): prezzo sopra/sotto media
input bool   InpTrendEMA = false; // Trend con EMA (false = SMA)

//--- strutture --------------------------------------------------------
struct Series
  {
   double v[];
  };

struct Rating
  {
   double ma, osc, total;
   int    nMA, nOsc;              // componenti valide
   int    bMA, sMA, bOsc, sOsc;   // quanti in acquisto / vendita
   bool   ok;
  };

//--- stato ------------------------------------------------------------
CTrade          g_trade;
ENUM_TIMEFRAMES g_sigTF, g_fltTF;
int             g_maLen[6];

// serie di prezzo e indicatori (indice 0 = candela piu' vecchia)
double g_c[], g_h[], g_l[], g_vol[], g_hl2[], g_cciSrc[];
Series g_sma[6], g_ema[6];
double g_hma[], g_vwma[], g_conv[], g_base[], g_spanB[];
double g_rsi[], g_stK[], g_stD[], g_cci[], g_pdi[], g_mdi[], g_adx[];
double g_ao[], g_mom[], g_macd[], g_macdSig[], g_srK[], g_srD[];
double g_wpr[], g_bull[], g_bear[], g_uo[], g_trend[], g_atr[];

Rating   g_sigCur, g_sigPrev, g_flt;
double   g_sigATR    = NA;
datetime g_lastSigBar = 0;   // candela (in corso) del TF segnale gia' elaborata
datetime g_lastFltBar = 0;
datetime g_sigClosed  = 0;   // orario della candela chiusa usata
datetime g_fltClosed  = 0;

int      g_pending    = 0;   // 1 = buy, -1 = sell, valido solo nella candela corrente
datetime g_pendingBar = 0;
string   g_status     = "avvio";
string   g_pfx        = "TVR_";
bool     g_draw       = true;

//+------------------------------------------------------------------+
int OnInit()
  {
   g_sigTF = (InpSignalTF == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : InpSignalTF;
   g_fltTF = (InpFilterTF == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : InpFilterTF;

   g_maLen[0] = InpMA1; g_maLen[1] = InpMA2; g_maLen[2] = InpMA3;
   g_maLen[3] = InpMA4; g_maLen[4] = InpMA5; g_maLen[5] = InpMA6;

   if(InpPipSize <= 0 || InpHistoryBars < 100 || InpBuyLevel <= InpSellLevel)
     {
      Print("Parametri non validi: controlla dimensione pip, candele di calcolo e soglie");
      return INIT_PARAMETERS_INCORRECT;
     }
   for(int k = 0; k < 6; k++)
      if(g_maLen[k] < 1) return INIT_PARAMETERS_INCORRECT;
   if(InpHistoryBars < MinBars() + 50)
      Print("Attenzione: InpHistoryBars basso, la media a ", MaxMALen(), " periodi non avra' il tempo di stabilizzarsi");

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints((ulong)MathMax(1.0, MathRound(InpSlippage * InpPipSize / _Point)));
   g_trade.SetTypeFillingBySymbol(_Symbol);

   g_draw = InpShowPanel && !MQLInfoInteger(MQL_OPTIMIZATION) &&
            (!MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_VISUAL_MODE));
   g_sigCur.ok = false; g_flt.ok = false;
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0, g_pfx);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   datetime sigBar = iTime(_Symbol, g_sigTF, 0);
   if(sigBar == 0) return;

   //--- nuova candela sul TF del segnale: ricalcolo, uscite, nuovo segnale
   if(sigBar != g_lastSigBar)
     {
      Rating cur, prv;
      double atr;
      if(!CalcRatings(g_sigTF, cur, prv, atr, g_sigClosed))
        {
         g_status = "dati " + TFName(g_sigTF) + " non ancora pronti";
         DrawPanel();
         return;                       // riprova al prossimo tick
        }
      g_lastSigBar = sigBar;
      g_sigCur = cur; g_sigPrev = prv; g_sigATR = atr;

      if(InpUseFilter) UpdateFilter();

      if(InpLogRatings)
         PrintFormat("%s %s  MA %+.3f  OSC %+.3f  TOT %+.3f  (%s)", TFName(g_sigTF),
                     TimeToString(g_sigClosed), cur.ma, cur.osc, cur.total, RatingText(cur.total));

      ManageExit();
      g_pending    = NewSignal();
      g_pendingBar = sigBar;
      g_status     = (g_pending == 0) ? "nessun segnale" : (g_pending > 0 ? "segnale BUY" : "segnale SELL");
     }
   else if(InpUseFilter && iTime(_Symbol, g_fltTF, 0) != g_lastFltBar)
      UpdateFilter();                  // filtro non ancora pronto o nuova candela del filtro

   //--- il segnale resta valido per tutta la candela: se spread/orario
   //    bloccano l'ingresso all'apertura, riprova ai tick successivi
   if(g_pending != 0 && g_pendingBar == sigBar)
      TryEntry(g_pending);

   DrawPanel();
  }

//+------------------------------------------------------------------+
//| Filtro: ricalcolato solo quando chiude una candela del suo TF     |
//+------------------------------------------------------------------+
void UpdateFilter()
  {
   datetime fBar = iTime(_Symbol, g_fltTF, 0);
   if(fBar == 0 || fBar == g_lastFltBar) return;
   Rating cur, prv;
   double atr;
   if(CalcRatings(g_fltTF, cur, prv, atr, g_fltClosed))
     {
      g_flt = cur;
      g_lastFltBar = fBar;
     }
   else
      g_flt.ok = false;
  }

//+------------------------------------------------------------------+
//| Segnale sulla candela appena chiusa                              |
//+------------------------------------------------------------------+
int NewSignal()
  {
   if(!g_sigCur.ok) return 0;
   double v = Pick(g_sigCur, InpSignalSrc);
   double p = g_sigPrev.ok ? Pick(g_sigPrev, InpSignalSrc) : NA;

   bool buy, sell;
   if(InpEntryMode == ENTRY_CROSS)
     {
      buy  = (p != NA && p <= InpBuyLevel  && v > InpBuyLevel);
      sell = (p != NA && p >= InpSellLevel && v < InpSellLevel);
     }
   else
     {
      buy  = (v > InpBuyLevel);
      sell = (v < InpSellLevel);
     }
   if(InpDirection == DIR_SELL) buy  = false;
   if(InpDirection == DIR_BUY)  sell = false;
   if(buy)  return 1;
   if(sell) return -1;
   return 0;
  }

//+------------------------------------------------------------------+
//| Ingresso                                                         |
//+------------------------------------------------------------------+
void TryEntry(const int dir)
  {
   if(HasPosition()) { g_pending = 0; return; }   // una sola posizione alla volta

   if(InpUseFilter)
     {
      if(!g_flt.ok) { g_status = "filtro " + TFName(g_fltTF) + " non disponibile"; return; }
      double f = Pick(g_flt, InpFilterSrc);
      if((dir > 0 && !(f > InpFilterLevel)) || (dir < 0 && !(f < -InpFilterLevel)))
        {
         g_status  = StringFormat("%s bloccato dal filtro %s (%+.2f)", dir > 0 ? "BUY" : "SELL", TFName(g_fltTF), f);
         g_pending = 0;
         return;
        }
     }

   if(InpUseHours && !InHours())
     { g_status = "fuori orario, segnale in attesa"; return; }

   MqlTick tk;
   if(!SymbolInfoTick(_Symbol, tk) || tk.ask <= 0 || tk.bid <= 0) return;
   double spreadPips = (tk.ask - tk.bid) / InpPipSize;
   if(InpMaxSpread > 0 && spreadPips > InpMaxSpread)
     { g_status = StringFormat("spread alto (%.0f pips), segnale in attesa", spreadPips); return; }

   //--- distanze SL / TP
   double slDist = 0, tpDist = 0;
   if(InpStopMode == STOP_PIPS)
     {
      slDist = InpSLPips * InpPipSize;
      tpDist = InpTPPips * InpPipSize;
     }
   else
     {
      if(g_sigATR == NA || g_sigATR <= 0) { g_status = "ATR non disponibile"; return; }
      slDist = InpSLATR * g_sigATR;
      tpDist = InpTPATR * g_sigATR;
     }
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
   if(slDist > 0 && slDist < minDist) slDist = minDist;
   if(tpDist > 0 && tpDist < minDist) tpDist = minDist;

   bool   isBuy = (dir > 0);
   double price = isBuy ? tk.ask : tk.bid;
   double sl = 0, tp = 0;
   if(slDist > 0) sl = NormPrice(isBuy ? price - slDist : price + slDist);
   if(tpDist > 0) tp = NormPrice(isBuy ? price + tpDist : price - tpDist);

   double lots = CalcLots(isBuy, price, slDist);
   if(lots <= 0) { g_status = "lotto non calcolabile"; g_pending = 0; return; }

   double margin = 0;
   ENUM_ORDER_TYPE type = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if(OrderCalcMargin(type, _Symbol, lots, price, margin) &&
      margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE))
     { g_status = "margine insufficiente"; g_pending = 0; return; }

   bool sent = isBuy ? g_trade.Buy(lots, _Symbol, price, sl, tp, InpComment)
                     : g_trade.Sell(lots, _Symbol, price, sl, tp, InpComment);
   uint rc = g_trade.ResultRetcode();
   if(sent && (rc == TRADE_RETCODE_DONE || rc == TRADE_RETCODE_PLACED || rc == TRADE_RETCODE_DONE_PARTIAL))
     {
      g_status  = StringFormat("aperto %s %.2f @ %s", isBuy ? "BUY" : "SELL", lots, DoubleToString(price, _Digits));
      g_pending = 0;
      PrintFormat("%s %.2f lotti  SL %s  TP %s  rating %+.3f  filtro %+.3f", isBuy ? "BUY" : "SELL", lots,
                  DoubleToString(sl, _Digits), DoubleToString(tp, _Digits),
                  Pick(g_sigCur, InpSignalSrc), InpUseFilter ? Pick(g_flt, InpFilterSrc) : 0.0);
     }
   else
     {
      g_status = StringFormat("ordine rifiutato: %u %s", rc, g_trade.ResultRetcodeDescription());
      Print(g_status);
      if(rc != TRADE_RETCODE_REQUOTE && rc != TRADE_RETCODE_PRICE_CHANGED && rc != TRADE_RETCODE_PRICE_OFF)
         g_pending = 0;               // errori non temporanei: non ritenta in questa candela
     }
  }

//+------------------------------------------------------------------+
//| Uscita sul rating (a ogni candela chiusa del TF segnale)          |
//+------------------------------------------------------------------+
void ManageExit()
  {
   if(InpExitMode == EXIT_SLTP || !g_sigCur.ok) return;
   double v = Pick(g_sigCur, InpSignalSrc);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0 || !IsMine()) continue;
      bool isBuy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      bool close;
      if(InpExitMode == EXIT_NEUTRAL)
         close = isBuy ? (v <= InpNeutralBand) : (v >= -InpNeutralBand);
      else
         close = isBuy ? (v < -InpNeutralBand) : (v > InpNeutralBand);
      if(close)
        {
         if(g_trade.PositionClose(ticket))
           {
            g_status = StringFormat("chiuso %s: rating %+.2f (%s)", isBuy ? "BUY" : "SELL", v, RatingText(v));
            Print(g_status);
           }
         else
            Print("Chiusura fallita: ", g_trade.ResultRetcode(), " ", g_trade.ResultRetcodeDescription());
        }
     }
  }

//+------------------------------------------------------------------+
//| Posizioni, lotti, prezzi                                         |
//+------------------------------------------------------------------+
bool IsMine()
  {
   return PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagic;
  }

bool HasPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionGetTicket(i) > 0 && IsMine()) return true;
   return false;
  }

double CalcLots(const bool isBuy, const double price, const double slDist)
  {
   double lots = InpFixedLots;
   if(InpLotMode == LOT_RISK)
     {
      if(slDist <= 0)
         Print("Rischio %: serve uno SL, uso il lotto fisso");
      else
        {
         double profit = 0;
         ENUM_ORDER_TYPE type = isBuy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
         double slPrice = isBuy ? price - slDist : price + slDist;
         if(!OrderCalcProfit(type, _Symbol, 1.0, price, slPrice, profit) || profit >= 0)
            return 0;
         double risk = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0;
         lots = risk / (-profit);
        }
     }
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step > 0) lots = MathFloor(lots / step + 1e-9) * step;
   if(lots < vmin) lots = vmin;
   if(lots > vmax) lots = vmax;
   return NormalizeDouble(lots, 2);
  }

double NormPrice(const double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0) ts = _Point;
   return NormalizeDouble(MathRound(p / ts) * ts, _Digits);
  }

bool InHours()
  {
   MqlDateTime t;
   TimeToStruct(TimeCurrent(), t);
   int h = t.hour;
   if(InpStartHour == InpEndHour) return true;
   if(InpStartHour < InpEndHour) return (h >= InpStartHour && h < InpEndHour);
   return (h >= InpStartHour || h < InpEndHour);   // fascia a cavallo della mezzanotte
  }

double Pick(const Rating &r, const RatingSource s)
  {
   if(s == SRC_MA)  return r.ma;
   if(s == SRC_OSC) return r.osc;
   return r.total;
  }

//+------------------------------------------------------------------+
//| Fasce di TradingView                                             |
//+------------------------------------------------------------------+
string RatingText(const double v)
  {
   if(v == NA)   return "n.d.";
   if(v > 0.5)   return "FORTE ACQUISTO";
   if(v > 0.1)   return "ACQUISTO";
   if(v >= -0.1) return "NEUTRALE";
   if(v >= -0.5) return "VENDITA";
   return "FORTE VENDITA";
  }

color RatingColor(const double v)
  {
   if(v == NA)   return clrGray;
   if(v > 0.5)   return clrDodgerBlue;
   if(v > 0.1)   return clrDeepSkyBlue;
   if(v >= -0.1) return clrSilver;
   if(v >= -0.5) return clrTomato;
   return clrRed;
  }

//+------------------------------------------------------------------+
//| Calcolo dei rating su un timeframe                               |
//| cur = ultima candela chiusa, prv = quella prima                  |
//+------------------------------------------------------------------+
int MaxMALen()
  {
   int m = 0;
   for(int k = 0; k < 6; k++) m = MathMax(m, g_maLen[k]);
   return m;
  }

int MinBars()
  {
   int m = MaxMALen();
   m = MathMax(m, InpIchiSpanB + InpIchiShift);
   m = MathMax(m, InpMACDSlow + InpMACDSig);
   m = MathMax(m, InpSRSIRsi + InpSRSIStoch + InpSRSIK + InpSRSID);
   m = MathMax(m, InpTrendLen);
   m = MathMax(m, 3 * InpADXLen);
   m = MathMax(m, InpAOSlow + 3);
   m = MathMax(m, InpUO3 + 1);
   return m + 5;
  }

bool CalcRatings(const ENUM_TIMEFRAMES tf, Rating &cur, Rating &prv, double &atr, datetime &closedTime)
  {
   cur.ok = false; prv.ok = false; atr = NA;
   int need  = MinBars();
   int avail = Bars(_Symbol, tf);
   int cnt   = MathMin(InpHistoryBars, avail - 1);
   if(cnt < need) return false;

   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, tf, 1, cnt, r);     // solo candele chiuse
   if(n < need) return false;
   closedTime = r[n - 1].time;

   ArrayResize(g_c, n);   ArrayResize(g_h, n);   ArrayResize(g_l, n);
   ArrayResize(g_vol, n); ArrayResize(g_hl2, n); ArrayResize(g_cciSrc, n);
   for(int i = 0; i < n; i++)
     {
      g_c[i]   = r[i].close;
      g_h[i]   = r[i].high;
      g_l[i]   = r[i].low;
      g_vol[i] = (r[i].real_volume > 0) ? (double)r[i].real_volume : (double)r[i].tick_volume;
      g_hl2[i] = (r[i].high + r[i].low) / 2.0;
      g_cciSrc[i] = InpCCITypical ? (r[i].high + r[i].low + r[i].close) / 3.0 : r[i].close;
     }

   //--- medie mobili
   for(int k = 0; k < 6; k++)
     {
      SMA(g_c, g_maLen[k], g_sma[k].v);
      EMA(g_c, g_maLen[k], g_ema[k].v);
     }
   HMA(g_c, InpHullLen, g_hma);
   VWMA(g_c, g_vol, InpVWMALen, g_vwma);
   Donchian(InpIchiConv, g_conv);
   Donchian(InpIchiBase, g_base);
   Donchian(InpIchiSpanB, g_spanB);

   //--- oscillatori
   RSI(g_c, InpRSILen, g_rsi);
   double raw[];
   Stoch(g_c, g_h, g_l, InpStochK, raw);
   SMA(raw, InpStochSm, g_stK);
   SMA(g_stK, InpStochD, g_stD);
   CCI(g_cciSrc, InpCCILen, g_cci);
   DMI(InpADXLen, g_pdi, g_mdi, g_adx);

   double f[], s[];
   SMA(g_hl2, InpAOFast, f);
   SMA(g_hl2, InpAOSlow, s);
   Diff(f, s, g_ao);

   ArrayResize(g_mom, n);
   for(int i = 0; i < n; i++)
      g_mom[i] = (i >= InpMomLen) ? g_c[i] - g_c[i - InpMomLen] : NA;

   EMA(g_c, InpMACDFast, f);
   EMA(g_c, InpMACDSlow, s);
   Diff(f, s, g_macd);
   EMA(g_macd, InpMACDSig, g_macdSig);

   double rsi2[];
   RSI(g_c, InpSRSIRsi, rsi2);
   Stoch(rsi2, rsi2, rsi2, InpSRSIStoch, raw);
   SMA(raw, InpSRSIK, g_srK);
   SMA(g_srK, InpSRSID, g_srD);

   WPR(InpWPRLen, g_wpr);

   EMA(g_c, InpBBPLen, f);
   ArrayResize(g_bull, n); ArrayResize(g_bear, n);
   for(int i = 0; i < n; i++)
     {
      g_bull[i] = (f[i] != NA) ? g_h[i] - f[i] : NA;
      g_bear[i] = (f[i] != NA) ? g_l[i] - f[i] : NA;
     }

   UO(g_uo);

   if(InpTrendEMA) EMA(g_c, InpTrendLen, g_trend);
   else            SMA(g_c, InpTrendLen, g_trend);

   //--- ATR (RMA del true range, come TradingView)
   double tr[];
   TrueRange(tr);
   RMA(tr, InpATRPeriod, g_atr);
   atr = g_atr[n - 1];

   Evaluate(n - 1, cur);
   Evaluate(n - 2, prv);
   return cur.ok;
  }

//+------------------------------------------------------------------+
//| Voti delle 26 componenti sulla candela i                          |
//+------------------------------------------------------------------+
void Vote(const int v, double &sum, int &cnt, int &nb, int &ns)
  {
   sum += v; cnt++;
   if(v > 0) nb++;
   if(v < 0) ns++;
  }

int MAVote(const double ma, const double price)
  {
   if(ma == NA) return 99;           // non disponibile
   if(ma < price) return 1;
   if(ma > price) return -1;
   return 0;
  }

bool Ok(const double a)                                 { return a != NA; }
bool Ok(const double a, const double b)                 { return a != NA && b != NA; }
bool Ok(const double a, const double b, const double c) { return a != NA && b != NA && c != NA; }

void Evaluate(const int i, Rating &R)
  {
   R.ok = false; R.ma = NA; R.osc = NA; R.total = NA;
   R.nMA = 0; R.nOsc = 0; R.bMA = 0; R.sMA = 0; R.bOsc = 0; R.sOsc = 0;
   if(i < 2) return;

   double c = g_c[i];
   double sM = 0, sO = 0;
   int v;

   //=== medie mobili (15) ============================================
   for(int k = 0; k < 6; k++)
     {
      v = MAVote(g_sma[k].v[i], c); if(v != 99) Vote(v, sM, R.nMA, R.bMA, R.sMA);
      v = MAVote(g_ema[k].v[i], c); if(v != 99) Vote(v, sM, R.nMA, R.bMA, R.sMA);
     }
   v = MAVote(g_hma[i], c);  if(v != 99) Vote(v, sM, R.nMA, R.bMA, R.sMA);
   v = MAVote(g_vwma[i], c); if(v != 99) Vote(v, sM, R.nMA, R.bMA, R.sMA);

   // Ichimoku: Span A > Span B, Kijun > Span A, Tenkan > Kijun, prezzo > Tenkan.
   // La nuvola e' quella disegnata sotto la candela corrente, cioe' calcolata
   // InpIchiShift candele fa (con spostamento 0 la regola non scatta mai,
   // perche' Tenkan > Kijun implica Span A > Kijun).
   int j = i - InpIchiShift;
   if(j >= 0 && Ok(g_conv[i], g_base[i]) && Ok(g_conv[j], g_base[j], g_spanB[j]))
     {
      double tenkan = g_conv[i], kijun = g_base[i];
      double spanA  = (g_conv[j] + g_base[j]) / 2.0, spanB = g_spanB[j];
      v = 0;
      if(spanA > spanB && kijun > spanA && tenkan > kijun && c > tenkan) v = 1;
      else if(spanA < spanB && kijun < spanA && tenkan < kijun && c < tenkan) v = -1;
      Vote(v, sM, R.nMA, R.bMA, R.sMA);
     }

   //=== oscillatori (11) =============================================
   bool up   = Ok(g_trend[i]) && c > g_trend[i];
   bool down = Ok(g_trend[i]) && c < g_trend[i];

   // RSI
   if(Ok(g_rsi[i], g_rsi[i - 1]))
     {
      v = 0;
      if(g_rsi[i] < 30 && g_rsi[i] > g_rsi[i - 1]) v = 1;
      else if(g_rsi[i] > 70 && g_rsi[i] < g_rsi[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Stocastico
   if(Ok(g_stK[i], g_stD[i]))
     {
      double k = g_stK[i], d = g_stD[i];
      v = 0;
      if(k < 20 && d < 20 && k > d) v = 1;
      else if(k > 80 && d > 80 && k < d) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // CCI
   if(Ok(g_cci[i], g_cci[i - 1]))
     {
      v = 0;
      if(g_cci[i] < -100 && g_cci[i] > g_cci[i - 1]) v = 1;
      else if(g_cci[i] > 100 && g_cci[i] < g_cci[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // ADX
   if(Ok(g_adx[i], g_adx[i - 1]) && Ok(g_pdi[i], g_mdi[i]))
     {
      v = 0;
      if(g_pdi[i] > g_mdi[i] && g_adx[i] > 20 && g_adx[i] > g_adx[i - 1]) v = 1;
      else if(g_mdi[i] > g_pdi[i] && g_adx[i] > 20 && g_adx[i] < g_adx[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Awesome Oscillator: incrocio dello zero, oppure "piattino" sopra/sotto zero
   if(Ok(g_ao[i], g_ao[i - 1], g_ao[i - 2]))
     {
      double a0 = g_ao[i], a1 = g_ao[i - 1], a2 = g_ao[i - 2];
      v = 0;
      if((a0 > 0 && a1 <= 0) || (a0 > 0 && a1 > 0 && a0 > a1 && a1 < a2)) v = 1;
      else if((a0 < 0 && a1 >= 0) || (a0 < 0 && a1 < 0 && a0 < a1 && a1 > a2)) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Momentum
   if(Ok(g_mom[i], g_mom[i - 1]))
     {
      v = 0;
      if(g_mom[i] > g_mom[i - 1]) v = 1;
      else if(g_mom[i] < g_mom[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // MACD
   if(Ok(g_macd[i], g_macdSig[i]))
     {
      v = 0;
      if(g_macd[i] > g_macdSig[i]) v = 1;
      else if(g_macd[i] < g_macdSig[i]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Stochastic RSI (con trend)
   if(Ok(g_srK[i], g_srD[i]) && Ok(g_trend[i]))
     {
      double k = g_srK[i], d = g_srD[i];
      v = 0;
      if(down && k < 20 && d < 20 && k > d) v = 1;
      else if(up && k > 80 && d > 80 && k < d) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Williams %R
   if(Ok(g_wpr[i], g_wpr[i - 1]))
     {
      v = 0;
      if(g_wpr[i] < -80 && g_wpr[i] > g_wpr[i - 1]) v = 1;
      else if(g_wpr[i] > -20 && g_wpr[i] < g_wpr[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Bull Bear Power (con trend)
   if(Ok(g_bear[i], g_bear[i - 1]) && Ok(g_bull[i], g_bull[i - 1]) && Ok(g_trend[i]))
     {
      v = 0;
      if(up && g_bear[i] < 0 && g_bear[i] > g_bear[i - 1]) v = 1;
      else if(down && g_bull[i] > 0 && g_bull[i] < g_bull[i - 1]) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }
   // Ultimate Oscillator
   if(Ok(g_uo[i]))
     {
      v = 0;
      if(g_uo[i] > 70) v = 1;
      else if(g_uo[i] < 30) v = -1;
      Vote(v, sO, R.nOsc, R.bOsc, R.sOsc);
     }

   //=== rating ======================================================
   if(R.nMA > 0)  R.ma  = sM / R.nMA;
   if(R.nOsc > 0) R.osc = sO / R.nOsc;
   if(R.nMA > 0 && R.nOsc > 0) R.total = (R.ma + R.osc) / 2.0;
   else if(R.nMA > 0)          R.total = R.ma;
   else if(R.nOsc > 0)         R.total = R.osc;
   R.ok = (R.total != NA);
  }

//+------------------------------------------------------------------+
//| Indicatori con le formule di TradingView (Pine)                   |
//| Tutte le serie: indice 0 = piu' vecchia, NA = non disponibile     |
//+------------------------------------------------------------------+
void SMA(const double &src[], const int len, double &out[])
  {
   int n = ArraySize(src);
   ArrayResize(out, n);
   double sum = 0;
   int bad = 0;
   for(int i = 0; i < n; i++)
     {
      if(src[i] == NA) bad++; else sum += src[i];
      if(i >= len) { if(src[i - len] == NA) bad--; else sum -= src[i - len]; }
      out[i] = (len > 0 && i >= len - 1 && bad == 0) ? sum / len : NA;
     }
  }

// media esponenziale con seme SMA (come ta.ema / ta.rma di Pine)
void ExpMA(const double &src[], const int len, const double alpha, double &out[])
  {
   int n = ArraySize(src);
   ArrayResize(out, n);
   ArrayInitialize(out, NA);
   int f = 0;
   while(f < n && src[f] == NA) f++;
   if(len < 1 || f + len > n) return;
   double sum = 0;
   for(int i = f; i < f + len; i++)
     {
      if(src[i] == NA) return;
      sum += src[i];
     }
   double prev = sum / len;
   out[f + len - 1] = prev;
   for(int i = f + len; i < n; i++)
     {
      if(src[i] == NA) continue;
      prev = alpha * src[i] + (1.0 - alpha) * prev;
      out[i] = prev;
     }
  }

void EMA(const double &src[], const int len, double &out[]) { ExpMA(src, len, 2.0 / (len + 1.0), out); }
void RMA(const double &src[], const int len, double &out[]) { ExpMA(src, len, 1.0 / len, out); }

void WMA(const double &src[], const int len, double &out[])
  {
   int n = ArraySize(src);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      out[i] = NA;
      if(len < 1 || i < len - 1) continue;
      double s = 0, w = 0;
      bool ok = true;
      for(int k = 0; k < len; k++)
        {
         double x = src[i - k];
         if(x == NA) { ok = false; break; }
         s += x * (len - k);
         w += (len - k);
        }
      if(ok) out[i] = s / w;
     }
  }

void HMA(const double &src[], const int len, double &out[])
  {
   double half[], full[], d[];
   WMA(src, MathMax(1, len / 2), half);
   WMA(src, len, full);
   int n = ArraySize(src);
   ArrayResize(d, n);
   for(int i = 0; i < n; i++)
      d[i] = (half[i] != NA && full[i] != NA) ? 2.0 * half[i] - full[i] : NA;
   WMA(d, MathMax(1, (int)MathFloor(MathSqrt(len))), out);
  }

void VWMA(const double &src[], const double &vol[], const int len, double &out[])
  {
   int n = ArraySize(src);
   double pv[], a[], b[];
   ArrayResize(pv, n);
   for(int i = 0; i < n; i++) pv[i] = src[i] * vol[i];
   SMA(pv, len, a);
   SMA(vol, len, b);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = (a[i] != NA && b[i] != NA && b[i] > 0) ? a[i] / b[i] : NA;
  }

void Highest(const double &src[], const int len, double &out[])
  {
   int n = ArraySize(src);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      out[i] = NA;
      if(len < 1 || i < len - 1) continue;
      double m = -DBL_MAX;
      bool ok = true;
      for(int k = 0; k < len; k++)
        {
         if(src[i - k] == NA) { ok = false; break; }
         if(src[i - k] > m) m = src[i - k];
        }
      if(ok) out[i] = m;
     }
  }

void Lowest(const double &src[], const int len, double &out[])
  {
   int n = ArraySize(src);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      out[i] = NA;
      if(len < 1 || i < len - 1) continue;
      double m = DBL_MAX;
      bool ok = true;
      for(int k = 0; k < len; k++)
        {
         if(src[i - k] == NA) { ok = false; break; }
         if(src[i - k] < m) m = src[i - k];
        }
      if(ok) out[i] = m;
     }
  }

void Donchian(const int len, double &out[])
  {
   double hh[], ll[];
   Highest(g_h, len, hh);
   Lowest(g_l, len, ll);
   int n = ArraySize(g_h);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = (hh[i] != NA && ll[i] != NA) ? (hh[i] + ll[i]) / 2.0 : NA;
  }

void Diff(const double &a[], const double &b[], double &out[])
  {
   int n = ArraySize(a);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = (a[i] != NA && b[i] != NA) ? a[i] - b[i] : NA;
  }

void RSI(const double &src[], const int len, double &out[])
  {
   int n = ArraySize(src);
   double u[], d[], ru[], rd[];
   ArrayResize(u, n); ArrayResize(d, n);
   u[0] = NA; d[0] = NA;
   for(int i = 1; i < n; i++)
     {
      double ch = src[i] - src[i - 1];
      u[i] = MathMax(ch, 0.0);
      d[i] = MathMax(-ch, 0.0);
     }
   RMA(u, len, ru);
   RMA(d, len, rd);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      if(ru[i] == NA || rd[i] == NA) { out[i] = NA; continue; }
      if(rd[i] == 0)      out[i] = 100;
      else if(ru[i] == 0) out[i] = 0;
      else                out[i] = 100.0 - 100.0 / (1.0 + ru[i] / rd[i]);
     }
  }

// stocastico grezzo: 100 * (src - minimo) / (massimo - minimo)
void Stoch(const double &src[], const double &hi[], const double &lo[], const int len, double &out[])
  {
   double hh[], ll[];
   Highest(hi, len, hh);
   Lowest(lo, len, ll);
   int n = ArraySize(src);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = (src[i] != NA && hh[i] != NA && ll[i] != NA && hh[i] > ll[i])
               ? 100.0 * (src[i] - ll[i]) / (hh[i] - ll[i]) : NA;
  }

void CCI(const double &src[], const int len, double &out[])
  {
   double ma[];
   SMA(src, len, ma);
   int n = ArraySize(src);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      out[i] = NA;
      if(ma[i] == NA) continue;
      double md = 0;
      for(int k = 0; k < len; k++) md += MathAbs(src[i - k] - ma[i]);
      md /= len;
      out[i] = (md == 0) ? 0 : (src[i] - ma[i]) / (0.015 * md);
     }
  }

void TrueRange(double &out[])
  {
   int n = ArraySize(g_c);
   ArrayResize(out, n);
   out[0] = g_h[0] - g_l[0];
   for(int i = 1; i < n; i++)
      out[i] = MathMax(g_h[i] - g_l[i], MathMax(MathAbs(g_h[i] - g_c[i - 1]), MathAbs(g_l[i] - g_c[i - 1])));
  }

// ta.dmi di Pine: +DI, -DI e ADX con smussamento di Wilder
void DMI(const int len, double &plus[], double &minus[], double &adx[])
  {
   int n = ArraySize(g_c);
   double pdm[], mdm[], tr[], rp[], rm[], rt[], dx[];
   ArrayResize(pdm, n); ArrayResize(mdm, n);
   pdm[0] = NA; mdm[0] = NA;
   for(int i = 1; i < n; i++)
     {
      double up = g_h[i] - g_h[i - 1];
      double dn = g_l[i - 1] - g_l[i];
      pdm[i] = (up > dn && up > 0) ? up : 0;
      mdm[i] = (dn > up && dn > 0) ? dn : 0;
     }
   TrueRange(tr);
   tr[0] = NA;
   RMA(tr, len, rt);
   RMA(pdm, len, rp);
   RMA(mdm, len, rm);
   ArrayResize(plus, n); ArrayResize(minus, n); ArrayResize(dx, n);
   for(int i = 0; i < n; i++)
     {
      if(rt[i] == NA || rp[i] == NA || rm[i] == NA || rt[i] == 0)
        { plus[i] = NA; minus[i] = NA; dx[i] = NA; continue; }
      plus[i]  = 100.0 * rp[i] / rt[i];
      minus[i] = 100.0 * rm[i] / rt[i];
      double sum = plus[i] + minus[i];
      dx[i] = MathAbs(plus[i] - minus[i]) / (sum == 0 ? 1.0 : sum);
     }
   RMA(dx, len, adx);
   for(int i = 0; i < n; i++)
      if(adx[i] != NA) adx[i] *= 100.0;
  }

void WPR(const int len, double &out[])
  {
   double hh[], ll[];
   Highest(g_h, len, hh);
   Lowest(g_l, len, ll);
   int n = ArraySize(g_c);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
      out[i] = (hh[i] != NA && ll[i] != NA && hh[i] > ll[i])
               ? 100.0 * (g_c[i] - hh[i]) / (hh[i] - ll[i]) : NA;
  }

void UO(double &out[])
  {
   int n = ArraySize(g_c);
   double bp[], tr[], b1[], t1[], b2[], t2[], b3[], t3[];
   ArrayResize(bp, n); ArrayResize(tr, n);
   bp[0] = NA; tr[0] = NA;
   for(int i = 1; i < n; i++)
     {
      double lo = MathMin(g_l[i], g_c[i - 1]);
      double hi = MathMax(g_h[i], g_c[i - 1]);
      bp[i] = g_c[i] - lo;
      tr[i] = hi - lo;
     }
   SMA(bp, InpUO1, b1); SMA(tr, InpUO1, t1);
   SMA(bp, InpUO2, b2); SMA(tr, InpUO2, t2);
   SMA(bp, InpUO3, b3); SMA(tr, InpUO3, t3);
   ArrayResize(out, n);
   for(int i = 0; i < n; i++)
     {
      if(b3[i] == NA || t1[i] == NA || t2[i] == NA || t3[i] == NA || t1[i] == 0 || t2[i] == 0 || t3[i] == 0)
        { out[i] = NA; continue; }
      out[i] = 100.0 * (4.0 * b1[i] / t1[i] + 2.0 * b2[i] / t2[i] + b3[i] / t3[i]) / 7.0;
     }
  }

//+------------------------------------------------------------------+
//| Pannello sul grafico                                             |
//+------------------------------------------------------------------+
string TFName(const ENUM_TIMEFRAMES tf)
  {
   string s = EnumToString(tf);
   return StringSubstr(s, 7);        // "PERIOD_H1" -> "H1"
  }

void Label(const int row, const string text, const color clr)
  {
   string name = g_pfx + IntegerToString(row);
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 10);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, 20 + row * 16);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
  }

string Num(const double v) { return (v == NA) ? "  n.d." : StringFormat("%+6.2f", v); }

int RatingRows(int row, const string title, const Rating &r, const datetime t)
  {
   Label(row++, StringFormat("%s  (candela chiusa %s)", title, TimeToString(t, TIME_DATE | TIME_MINUTES)), clrWhite);
   if(!r.ok) { Label(row++, "  dati non disponibili", clrGray); Label(row++, " ", clrGray); Label(row++, " ", clrGray); return row; }
   Label(row++, StringFormat("  Medie mobili %s  %-15s B %2d  S %2d  su %d", Num(r.ma), RatingText(r.ma), r.bMA, r.sMA, r.nMA), RatingColor(r.ma));
   Label(row++, StringFormat("  Oscillatori  %s  %-15s B %2d  S %2d  su %d", Num(r.osc), RatingText(r.osc), r.bOsc, r.sOsc, r.nOsc), RatingColor(r.osc));
   Label(row++, StringFormat("  TOTALE       %s  %s", Num(r.total), RatingText(r.total)), RatingColor(r.total));
   return row;
  }

void DrawPanel()
  {
   if(!g_draw) return;
   int row = 0;
   Label(row++, "TV Technical Ratings  " + _Symbol, clrGold);
   row = RatingRows(row, "Segnale " + TFName(g_sigTF), g_sigCur, g_sigClosed);
   if(InpUseFilter)
      row = RatingRows(row, "Filtro " + TFName(g_fltTF), g_flt, g_fltClosed);

   string pos = "nessuna";
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(PositionGetTicket(i) == 0 || !IsMine()) continue;
      pos = StringFormat("%s %.2f @ %s  P/L %.2f",
                         PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "BUY" : "SELL",
                         PositionGetDouble(POSITION_VOLUME),
                         DoubleToString(PositionGetDouble(POSITION_PRICE_OPEN), _Digits),
                         PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP));
      break;
     }
   Label(row++, "Posizione: " + pos, clrWhite);
   Label(row++, "Stato: " + g_status, clrSilver);
   ChartRedraw();
  }
//+------------------------------------------------------------------+
