//+------------------------------------------------------------------+
//|                                              IndexORB_Long.mq5   |
//|  Opening Range Breakout LONG-ONLY intraday per indici USA        |
//|  (US500 / NAS100 / US30 CFD). Nessuna posizione overnight.       |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "1.10"
#property description "ORB long-only intraday su indici USA: range dei primi minuti di New York,"
#property description "ingresso sulla rottura del massimo, chiusura forzata a fine giornata."

#include <Trade/Trade.mqh>

//--- input -----------------------------------------------------------
input group "=== Sessione (ora del SERVER del broker) ==="
input string InpSessionOpen    = "16:30";  // Apertura cash New York (09:30 NY) in ora server
input int    InpORMinutes      = 15;       // Durata opening range (minuti)
input string InpLastEntryTime  = "19:00";  // Ultimo orario utile per l'ingresso
input string InpCloseTime      = "22:45";  // Chiusura forzata di tutto (15:45 NY)

input group "=== Filtri ==="
input bool   InpUseTrendFilter  = true;    // Solo se chiusura D1 di ieri > SMA D1
input int    InpTrendMAPeriod   = 50;      // Periodo SMA giornaliera
input bool   InpRequireBullOR   = true;    // Solo se il range chiude sopra la sua apertura
input int    InpATRPeriod       = 14;      // Periodo ATR giornaliero
input double InpMinORtoATR      = 0.05;    // Range minimo (frazione ATR D1)
input double InpMaxORtoATR      = 0.40;    // Range massimo (frazione ATR D1)
input int    InpMaxSpreadPoints = 0;       // Spread massimo in punti (0 = disattivato)
input bool   InpMonday          = true;    // Opera il lunedi
input bool   InpTuesday         = true;    // Opera il martedi
input bool   InpWednesday       = true;    // Opera il mercoledi
input bool   InpThursday        = true;    // Opera il giovedi
input bool   InpFriday          = true;    // Opera il venerdi
input bool   InpSkipUSHolidays  = true;    // Salta festivita USA e mezze giornate (solo indici USA)

input group "=== Gestione trade ==="
input double InpEntryBufferFrac = 0.05;    // Buffer sopra il massimo del range (frazione del range)
input double InpSLFrac          = 1.0;     // SL = max range - X*range (1.0 = minimo, 0.5 = meta)
input double InpTP_R            = 2.0;     // Take profit in multipli di R (0 = solo uscita a fine giornata)
input double InpBreakEven_R     = 0.0;     // Stop a pareggio dopo X R di profitto (0 = disattivato)

input group "=== Rischio ==="
input double InpRiskPct          = 1.0;    // Rischio per trade (% equity)
input double InpMaxRiskPctMinLot = 2.0;    // Se serve il lotto minimo, rischio massimo accettato (%)
input double InpMaxLots          = 5.0;    // Lotto massimo
input double InpDailyLossPct     = 2.0;    // Perdita giornaliera massima (% equity, 0 = off)
input double InpMaxDDPct         = 12.0;   // Drawdown massimo dal picco: EA si ferma (0 = off)
input bool   InpResetPeak        = false;  // Azzera il picco di equity salvato (riattiva l'EA)
input ulong  InpMagic            = 20261010; // Magic number

//--- stato -----------------------------------------------------------
CTrade   trade;
int      g_hMA  = INVALID_HANDLE;
int      g_hATR = INVALID_HANDLE;
int      g_secOpen, g_secLast, g_secClose;
datetime g_day           = 0;
bool     g_orReady       = false;
bool     g_noTradeToday  = false;
bool     g_halted        = false;
double   g_orHigh = 0, g_orLow = 0;
double   g_slDist        = 0;
double   g_dayStartEquity = 0;
double   g_peakEquity    = 0;
string   g_gvPeak;
string   g_status        = "";

//+------------------------------------------------------------------+
int ParseHHMM(const string s)
  {
   string parts[];
   if(StringSplit(s, ':', parts) != 2)
      return -1;
   int h = (int)StringToInteger(parts[0]);
   int m = (int)StringToInteger(parts[1]);
   if(h < 0 || h > 23 || m < 0 || m > 59)
      return -1;
   return h * 3600 + m * 60;
  }

double NormPrice(const double p)
  {
   double ts = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0)
      ts = _Point;
   return NormalizeDouble(MathRound(p / ts) * ts, _Digits);
  }

double StopsLevel()
  {
   return (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * _Point;
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   g_secOpen  = ParseHHMM(InpSessionOpen);
   g_secLast  = ParseHHMM(InpLastEntryTime);
   g_secClose = ParseHHMM(InpCloseTime);
   if(g_secOpen < 0 || g_secLast < 0 || g_secClose < 0)
     {
      Print("Orari non validi: usa il formato HH:MM");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpORMinutes < 1 || g_secOpen + InpORMinutes * 60 >= g_secLast || g_secLast >= g_secClose)
     {
      Print("Orari incoerenti: serve apertura + range < ultimo ingresso < chiusura");
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpRiskPct <= 0 || InpSLFrac <= 0)
      return INIT_PARAMETERS_INCORRECT;

   g_hMA  = iMA(_Symbol, PERIOD_D1, InpTrendMAPeriod, 0, MODE_SMA, PRICE_CLOSE);
   g_hATR = iATR(_Symbol, PERIOD_D1, InpATRPeriod);
   if(g_hMA == INVALID_HANDLE || g_hATR == INVALID_HANDLE)
     {
      Print("Impossibile creare gli indicatori");
      return INIT_FAILED;
     }

   trade.SetExpertMagicNumber(InpMagic);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(50);

   g_gvPeak = "IORB_peak_" + _Symbol + "_" + IntegerToString((long)InpMagic);
   if(InpResetPeak)
      GlobalVariableDel(g_gvPeak);
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   g_peakEquity = GlobalVariableCheck(g_gvPeak) ? GlobalVariableGet(g_gvPeak) : eq;
   if(eq > g_peakEquity)
      g_peakEquity = eq;
   GlobalVariableSet(g_gvPeak, g_peakEquity);

   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(g_hMA != INVALID_HANDLE)
      IndicatorRelease(g_hMA);
   if(g_hATR != INVALID_HANDLE)
      IndicatorRelease(g_hATR);
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   datetime now = TimeCurrent();
   datetime day = now - (now % 86400);
   int      sec = (int)(now - day);

   if(day != g_day)
      NewDay(day);

   UpdateEquityGuards();
   ManagePositions();

   if(sec >= g_secClose)
     {
      CloseAll("fine giornata");
      ShowStatus();
      return;
     }
   if(sec >= g_secLast)
     {
      DeletePendings();
      ShowStatus();
      return;
     }
   if(!g_halted && !g_noTradeToday && !g_orReady && sec >= g_secOpen + InpORMinutes * 60)
      BuildRangeAndPlace(day);

   ShowStatus();
  }

//+------------------------------------------------------------------+
void NewDay(const datetime day)
  {
   g_day            = day;
   g_orReady        = false;
   g_orHigh         = 0;
   g_orLow          = 0;
   g_slDist         = 0;
   g_dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_status         = "in attesa del range";

   // Sicurezza: nessuna posizione deve sopravvivere alla notte.
   CloseAll("nuovo giorno");

   MqlDateTime dt;
   TimeToStruct(day, dt);
   bool allowed = (dt.day_of_week == 1 && InpMonday)    ||
                  (dt.day_of_week == 2 && InpTuesday)   ||
                  (dt.day_of_week == 3 && InpWednesday) ||
                  (dt.day_of_week == 4 && InpThursday)  ||
                  (dt.day_of_week == 5 && InpFriday);
   g_noTradeToday = !allowed;
   if(!allowed)
      g_status = "giorno escluso";
   else if(InpSkipUSHolidays && (IsUSHoliday(day) || IsUSHalfDay(day)))
     {
      // Borsa USA chiusa o a orario ridotto: il CFD chiude prima e la
      // posizione resterebbe aperta fino al giorno dopo.
      g_noTradeToday = true;
      g_status = "festivita USA";
     }
  }

//+------------------------------------------------------------------+
//| Calendario borsa USA (NYSE)                                      |
//+------------------------------------------------------------------+
datetime MakeDate(const int y, const int m, const int d)
  {
   MqlDateTime t;
   ZeroMemory(t);
   t.year = y;
   t.mon  = m;
   t.day  = d;
   return StructToTime(t);
  }

int DayOfWeek(const datetime t)
  {
   MqlDateTime s;
   TimeToStruct(t, s);
   return s.day_of_week;
  }

// Giorno del mese dell'n-esimo giorno 'dow' (0=domenica) del mese.
int NthWeekday(const int y, const int m, const int dow, const int n)
  {
   int first = 1 + ((dow - DayOfWeek(MakeDate(y, m, 1)) + 7) % 7);
   return first + (n - 1) * 7;
  }

// Giorno del mese dell'ultimo giorno 'dow' del mese.
int LastWeekday(const int y, const int m, const int dow)
  {
   datetime last = (m == 12) ? MakeDate(y + 1, 1, 1) - 86400 : MakeDate(y, m + 1, 1) - 86400;
   MqlDateTime s;
   TimeToStruct(last, s);
   return s.day - ((s.day_of_week - dow + 7) % 7);
  }

// Festivita a data fissa con spostamento: sabato -> venerdi, domenica -> lunedi.
bool IsObservedFixed(const datetime day, const int y, const int m, const int d, const bool satToFri)
  {
   datetime h = MakeDate(y, m, d);
   int dow = DayOfWeek(h);
   if(dow == 6)
      return satToFri && day == h - 86400;
   if(dow == 0)
      return day == h + 86400;
   return day == h;
  }

datetime EasterSunday(const int y)
  {
   int a = y % 19, b = y / 100, c = y % 100, d = b / 4, e = b % 4;
   int f = (b + 8) / 25, g = (b - f + 1) / 3;
   int h = (19 * a + b - d - g + 15) % 30;
   int i = c / 4, k = c % 4;
   int l = (32 + 2 * e + 2 * i - h - k) % 7;
   int m = (a + 11 * h + 22 * l) / 451;
   int month = (h + l - 7 * m + 114) / 31;
   int dd    = ((h + l - 7 * m + 114) % 31) + 1;
   return MakeDate(y, month, dd);
  }

bool IsUSHoliday(const datetime day)
  {
   MqlDateTime s;
   TimeToStruct(day, s);
   int y = s.year, m = s.mon, d = s.day;

   if(IsObservedFixed(day, y, 1, 1, false))                return true; // Capodanno
   if(m == 1 && d == NthWeekday(y, 1, 1, 3))              return true; // Martin Luther King
   if(m == 2 && d == NthWeekday(y, 2, 1, 3))              return true; // Presidents Day
   if(day == EasterSunday(y) - 2 * 86400)                 return true; // Venerdi Santo
   if(m == 5 && d == LastWeekday(y, 5, 1))                return true; // Memorial Day
   if(y >= 2022 && IsObservedFixed(day, y, 6, 19, true))  return true; // Juneteenth
   if(IsObservedFixed(day, y, 7, 4, true))                return true; // Indipendenza
   if(m == 9 && d == NthWeekday(y, 9, 1, 1))              return true; // Labor Day
   if(m == 11 && d == NthWeekday(y, 11, 4, 4))            return true; // Thanksgiving
   if(IsObservedFixed(day, y, 12, 25, true))              return true; // Natale
   // Chiusure straordinarie (lutto nazionale)
   if(day == MakeDate(2018, 12, 5) || day == MakeDate(2025, 1, 9))
      return true;
   return false;
  }

// Giorni con chiusura anticipata alle 13:00 di New York.
bool IsUSHalfDay(const datetime day)
  {
   MqlDateTime s;
   TimeToStruct(day, s);
   if(s.day_of_week == 0 || s.day_of_week == 6 || IsUSHoliday(day))
      return false;
   if(s.mon == 11 && s.day == NthWeekday(s.year, 11, 4, 4) + 1) return true; // venerdi dopo Thanksgiving
   if(s.mon == 12 && s.day == 24)                               return true; // vigilia di Natale
   if(s.mon == 7 && s.day == 3)                                 return true; // vigilia dell'Indipendenza
   return false;
  }

//+------------------------------------------------------------------+
void UpdateEquityGuards()
  {
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_peakEquity)
     {
      g_peakEquity = eq;
      GlobalVariableSet(g_gvPeak, g_peakEquity);
     }

   if(InpMaxDDPct > 0 && !g_halted && eq <= g_peakEquity * (1.0 - InpMaxDDPct / 100.0))
     {
      g_halted = true;
      g_status = "FERMO: drawdown massimo raggiunto";
      CloseAll("drawdown massimo");
      PrintFormat("EA fermato: equity %.2f sotto il %.1f%% dal picco %.2f. Riattiva con InpResetPeak=true.",
                  eq, InpMaxDDPct, g_peakEquity);
     }

   if(InpDailyLossPct > 0 && !g_noTradeToday && g_dayStartEquity > 0 &&
      eq <= g_dayStartEquity * (1.0 - InpDailyLossPct / 100.0))
     {
      g_noTradeToday = true;
      g_status = "stop giornaliero";
      CloseAll("perdita giornaliera massima");
     }
  }

//+------------------------------------------------------------------+
bool AlreadyTradedToday(const datetime day)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
         return true;
     }
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t > 0 && OrderGetInteger(ORDER_MAGIC) == (long)InpMagic &&
         OrderGetString(ORDER_SYMBOL) == _Symbol)
         return true;
     }
   if(HistorySelect(day, TimeCurrent() + 60))
     {
      for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
        {
         ulong t = HistoryDealGetTicket(i);
         if(t > 0 && HistoryDealGetInteger(t, DEAL_MAGIC) == (long)InpMagic &&
            HistoryDealGetString(t, DEAL_SYMBOL) == _Symbol &&
            HistoryDealGetInteger(t, DEAL_ENTRY) == DEAL_ENTRY_IN)
            return true;
        }
     }
   return false;
  }

//+------------------------------------------------------------------+
void SkipDay(const string why)
  {
   g_noTradeToday = true;
   g_status = "nessun trade: " + why;
   Print("Nessun trade oggi: ", why);
  }

void BuildRangeAndPlace(const datetime day)
  {
   if(AlreadyTradedToday(day))
     {
      g_orReady = true;
      g_status = "trade di oggi gia eseguito";
      return;
     }

   datetime from = day + g_secOpen;
   datetime to   = from + InpORMinutes * 60 - 1;
   MqlRates r[];
   int n = CopyRates(_Symbol, PERIOD_M1, from, to, r);
   if(n <= 0)
      return; // dati non ancora pronti: riprova al prossimo tick
   g_orReady = true;
   if(n < InpORMinutes / 2)
     {
      SkipDay("dati M1 del range incompleti (" + IntegerToString(n) + " barre)");
      return;
     }

   double hi = r[0].high, lo = r[0].low;
   for(int i = 1; i < n; i++)
     {
      hi = MathMax(hi, r[i].high);
      lo = MathMin(lo, r[i].low);
     }
   double orOpen  = r[0].open;
   double orClose = r[n - 1].close;
   double range   = hi - lo;
   g_orHigh = hi;
   g_orLow  = lo;
   if(range <= 0)
     {
      SkipDay("range nullo");
      return;
     }

   if(InpRequireBullOR && orClose <= orOpen)
     {
      SkipDay("range ribassista");
      return;
     }

   if(InpUseTrendFilter)
     {
      double ma[1];
      double prevClose = iClose(_Symbol, PERIOD_D1, 1);
      if(CopyBuffer(g_hMA, 0, 1, 1, ma) != 1 || prevClose <= 0)
        {
         SkipDay("SMA D1 non disponibile");
         return;
        }
      if(prevClose <= ma[0])
        {
         SkipDay("trend D1 negativo");
         return;
        }
     }

   double atr[1];
   if(CopyBuffer(g_hATR, 0, 1, 1, atr) != 1 || atr[0] <= 0)
     {
      SkipDay("ATR D1 non disponibile");
      return;
     }
   double ratio = range / atr[0];
   if(ratio < InpMinORtoATR || ratio > InpMaxORtoATR)
     {
      SkipDay(StringFormat("range/ATR %.2f fuori da [%.2f, %.2f]", ratio, InpMinORtoATR, InpMaxORtoATR));
      return;
     }

   if(InpMaxSpreadPoints > 0 && SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPoints)
     {
      SkipDay("spread troppo alto");
      return;
     }

   double entry  = NormPrice(hi + InpEntryBufferFrac * range);
   double sl     = NormPrice(hi - InpSLFrac * range);
   double slDist = entry - sl;
   if(slDist <= StopsLevel() || slDist <= 0)
     {
      SkipDay("stop troppo vicino");
      return;
     }
   double tp = (InpTP_R > 0) ? NormPrice(entry + InpTP_R * slDist) : 0.0;

   double lots = CalcLots(entry, sl);
   if(lots <= 0)
     {
      SkipDay("lotto non compatibile con il rischio o il margine");
      return;
     }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   bool ok = false;
   if(entry > ask + StopsLevel())
      ok = trade.BuyStop(lots, entry, _Symbol, sl, tp, ORDER_TIME_GTC, 0, "IORB");
   else if(ask <= entry + 0.1 * range)
      ok = trade.Buy(lots, _Symbol, ask, sl, tp, "IORB mkt");
   else
     {
      SkipDay("prezzo gia troppo sopra il range");
      return;
     }

   if(ok)
     {
      g_slDist = slDist;
      g_status = StringFormat("buy stop %.2f lotti @ %s  SL %s  TP %s", lots,
                              DoubleToString(entry, _Digits), DoubleToString(sl, _Digits),
                              tp > 0 ? DoubleToString(tp, _Digits) : "-");
      Print("Ordine inviato: ", g_status);
     }
   else
      SkipDay("ordine rifiutato (" + IntegerToString((int)trade.ResultRetcode()) + " " +
              trade.ResultRetcodeDescription() + ")");
  }

//+------------------------------------------------------------------+
double CalcLots(const double entry, const double sl)
  {
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double lossPerLot = 0;
   if(!OrderCalcProfit(ORDER_TYPE_BUY, _Symbol, 1.0, entry, sl, lossPerLot))
      return 0;
   lossPerLot = MathAbs(lossPerLot);
   if(lossPerLot <= 0 || eq <= 0)
      return 0;

   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minL = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxL = MathMin(SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX), InpMaxLots);
   if(step <= 0)
      step = minL;

   double lots = eq * InpRiskPct / 100.0 / lossPerLot;
   lots = MathFloor(lots / step + 1e-9) * step;
   lots = MathMin(lots, maxL);

   if(lots < minL)
     {
      double riskAtMin = lossPerLot * minL / eq * 100.0;
      if(riskAtMin > InpMaxRiskPctMinLot)
        {
         PrintFormat("Lotto minimo %.2f rischierebbe il %.2f%% (> %.2f%%): trade saltato",
                     minL, riskAtMin, InpMaxRiskPctMinLot);
         return 0;
        }
      lots = minL;
     }

   double margin = 0;
   if(OrderCalcMargin(ORDER_TYPE_BUY, _Symbol, lots, entry, margin) &&
      margin > AccountInfoDouble(ACCOUNT_MARGIN_FREE))
     {
      PrintFormat("Margine insufficiente: servono %.2f", margin);
      return 0;
     }
   return NormalizeDouble(lots, 2);
  }

//+------------------------------------------------------------------+
void ManagePositions()
  {
   if(InpBreakEven_R <= 0)
      return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0 || PositionGetInteger(POSITION_MAGIC) != (long)InpMagic ||
         PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);
      if(sl >= open)
         continue; // gia a pareggio
      double risk = (g_slDist > 0) ? g_slDist : (sl > 0 ? open - sl : 0);
      if(risk <= 0)
         continue;
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double newSL = NormPrice(open);
      if(bid - open >= InpBreakEven_R * risk && bid - newSL > StopsLevel())
         trade.PositionModify(t, newSL, tp);
     }
  }

void DeletePendings()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong t = OrderGetTicket(i);
      if(t > 0 && OrderGetInteger(ORDER_MAGIC) == (long)InpMagic &&
         OrderGetString(ORDER_SYMBOL) == _Symbol)
         trade.OrderDelete(t);
     }
  }

void CloseAll(const string why)
  {
   DeletePendings();
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t > 0 && PositionGetInteger(POSITION_MAGIC) == (long)InpMagic &&
         PositionGetString(POSITION_SYMBOL) == _Symbol)
        {
         if(trade.PositionClose(t))
            Print("Posizione chiusa: ", why);
        }
     }
  }

//+------------------------------------------------------------------+
void ShowStatus()
  {
   if(MQLInfoInteger(MQL_TESTER) && !MQLInfoInteger(MQL_VISUAL_MODE))
      return;
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   double dd = (g_peakEquity > 0) ? (1.0 - eq / g_peakEquity) * 100.0 : 0;
   Comment(StringFormat("IndexORB Long  |  %s\nRange: %s - %s\nEquity %.2f  picco %.2f  DD %.1f%%%s",
                        g_status,
                        g_orHigh > 0 ? DoubleToString(g_orLow, _Digits) : "-",
                        g_orHigh > 0 ? DoubleToString(g_orHigh, _Digits) : "-",
                        eq, g_peakEquity, dd, g_halted ? "  [FERMO]" : ""));
  }

//+------------------------------------------------------------------+
// Criterio "Custom max" per l'ottimizzazione: recovery factor,
// scartando le combinazioni con troppo pochi trade.
double OnTester()
  {
   if(TesterStatistics(STAT_TRADES) < 50 || TesterStatistics(STAT_PROFIT) <= 0)
      return 0;
   return TesterStatistics(STAT_RECOVERY_FACTOR);
  }
//+------------------------------------------------------------------+
