//+------------------------------------------------------------------+
//|                                                BuySellGrid.mq5   |
//|  Griglia buy + sell (conto hedging), ricostruita dai parametri   |
//|  del file buysell2.set e dagli ordini del report di Buysell 2.0: |
//|  - a inizio ciclo apre un BUY e un SELL insieme                  |
//|  - ogni volta che il prezzo si sposta di un passo (MinStep) dal  |
//|    livello dell'ultima apertura, apre un'altra coppia buy + sell |
//|  - ogni posizione che arriva a +MinPosProfit si chiude da sola   |
//|  - quando la somma di tutte le posizioni arriva a +MinPosProfit  |
//|    chiude tutto il ciclo (anche le perdenti) e riparte           |
//|  - Stoploss (valuta conto) chiude tutto se la perdita del ciclo  |
//|    arriva a quel valore (0 = nessuno stop, come nell'originale)  |
//|  I nomi dei parametri sono gli stessi dell'originale, quindi il  |
//|  file .set dell'originale si carica direttamente.                |
//+------------------------------------------------------------------+
#property copyright "bot-telegram"
#property version   "1.00"
#property description "Griglia buy+sell su conto hedging (ricostruzione di Buysell 2.0 dai suoi parametri)"

#include <Trade\Trade.mqh>

enum TradingModeType
  {
   TM_BOTH        = 0, // Buy + Sell insieme a ogni livello
   TM_DIRECTIONAL = 1  // Solo nella direzione dell'ultimo passo (sale = buy, scende = sell)
  };

enum LotCalcType
  {
   LCM_FIXED   = 0, // Lotto fisso (Lots)
   LCM_GRID    = 1, // Lots + LotsizeIncrement ogni LotsizeIncrementMultiple posizioni gia' aperte nella stessa direzione
   LCM_BALANCE = 2  // Come 1, ma Lots vale per ogni 1000 di saldo
  };

enum StepType
  {
   STP_POINTS  = 0, // Passo in punti (MinStep)
   STP_PERCENT = 1  // Passo in % del prezzo (MinStepPerc)
  };

enum ProfitCalcType
  {
   PCM_POSITION = 0, // Chiude ogni posizione a +MinPosProfit
   PCM_BASKET   = 1, // Chiude tutto il ciclo quando la somma arriva a +MinPosProfit
   PCM_BOTH     = 2  // Tutte e due
  };

//--- parametri (stessi nomi del .set originale) ---------------------
input group "=== Impostazioni Generali ==="
input long            MagicNumber    = 123456;            // Magic number
input ENUM_TIMEFRAMES Timeframe      = PERIOD_CURRENT;    // Timeframe per newBarOnly
input bool            newBarOnly     = false;             // Apre nuove posizioni solo a inizio candela
input bool            PrintAllowed   = false;             // Scrive ogni operazione nel journal
input bool            ShowPanelChart = true;              // Pannello sul grafico
input int             MaxSpread      = 9999;              // Spread massimo per aprire (punti)
input int             MaxSlippage    = 9999;              // Slippage massimo (punti)
input string          TradeComment   = "BuySellGrid";     // Commento degli ordini

input group "=== Modalita' Direzionale ==="
input TradingModeType TradingMode    = TM_BOTH;           // Modalita'

input group "========= Range Parameters ========="
input int             StartHour      = 0;                 // Ora di inizio (ora del server)
input int             time           = 1140;              // Durata della finestra in minuti (1140 = fino alle 19:00)

input group "=== Gestione Lotti ==="
input double          Lots                     = 0.01;      // Lotto base
input double          LotsizeIncrement         = 0.01;      // Aumento del lotto (solo LotCalcMode 1 e 2)
input int             LotsizeIncrementMultiple = 1;         // Ogni quante posizioni aperte nella stessa direzione
input double          MaxLotsize               = 0;         // Lotto massimo (0 = nessun limite)
input LotCalcType     LotCalcMode              = LCM_FIXED; // Calcolo del lotto

input group "=== Logica della griglia ==="
input StepType        SType          = STP_POINTS;        // Tipo di passo
input int             MinStep        = 200;               // Passo in punti (200 punti = 2 $ sull'oro a 2 decimali)
input double          MinStepPerc    = 0.09;              // Passo in % del prezzo

input group "=== Gestione Profitto e Stop Loss ==="
input double          MinPosProfit   = 2;                 // Profitto di chiusura (valuta conto)
input ProfitCalcType  ProfitCalcMode = PCM_BOTH;          // Come si chiude
input double          Stoploss       = 0;                 // Perdita del ciclo che chiude tutto (valuta conto, 0 = off)

input group "=== Esportazione Dati ==="
input bool            ExportHistory  = false;             // Salva i deal in MQL5/Files/BuySellGrid_<simbolo>.csv all'uscita

//--- stato ------------------------------------------------------------
CTrade   g_trade;
double   g_lastPx   = 0;   // livello dell'ultima apertura (bid)
datetime g_lastBar  = 0;
double   g_maxDD    = 0;   // peggior perdita del ciclo vista da quando e' attaccato
int      g_cycles   = 0;   // cicli chiusi in profitto
string   g_status   = "";

//+------------------------------------------------------------------+
int OnInit()
  {
   if(AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
     {
      Print("BuySellGrid: serve un conto HEDGING (buy e sell aperti insieme sullo stesso simbolo)");
      return INIT_FAILED;
     }
   if(Lots <= 0 || MinPosProfit <= 0 || (SType == STP_POINTS && MinStep <= 0) || (SType == STP_PERCENT && MinStepPerc <= 0))
     {
      Print("BuySellGrid: Lots, MinPosProfit e il passo devono essere maggiori di zero");
      return INIT_PARAMETERS_INCORRECT;
     }

   g_trade.SetExpertMagicNumber(MagicNumber);
   g_trade.SetTypeFillingBySymbol(_Symbol);
   g_trade.SetDeviationInPoints(MaxSlippage);
   g_trade.LogLevel(PrintAllowed ? LOG_LEVEL_ALL : LOG_LEVEL_ERRORS);

   PrintFormat("BuySellGrid su %s: modo=%s passo=%s profitto=%.2f calcolo=%d lotto=%.2f calcolo lotto=%d stop=%.2f",
               _Symbol, TradingMode == TM_BOTH ? "buy+sell" : "direzionale",
               SType == STP_POINTS ? IntegerToString(MinStep) + " punti" : DoubleToString(MinStepPerc, 3) + "%",
               MinPosProfit, (int)ProfitCalcMode, Lots, (int)LotCalcMode, Stoploss);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(ExportHistory)
      ExportDeals();
   Comment("");
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid <= 0)
      return;

   ManageExits();

   bool canOpen = true;
   if(newBarOnly)
     {
      datetime bar = iTime(_Symbol, Timeframe, 0);
      if(bar == g_lastBar)
         canOpen = false;
      else
         g_lastBar = bar;
     }
   if(canOpen)
      ManageEntries(bid);

   if(ShowPanelChart)
      UpdatePanel(bid);
  }

//+------------------------------------------------------------------+
//| Uscite: stop del ciclo, chiusura del ciclo, chiusura singola     |
//+------------------------------------------------------------------+
void ManageExits()
  {
   int n = 0;
   double total = CycleProfit(n);
   if(n == 0)
      return;
   if(-total > g_maxDD)
      g_maxDD = -total;

   if(Stoploss > 0 && total <= -Stoploss)
     {
      Log(StringFormat("STOP ciclo: %d posizioni, %.2f", n, total));
      CloseAll();
      g_lastPx = 0;
      return;
     }

   if((ProfitCalcMode == PCM_BASKET || ProfitCalcMode == PCM_BOTH) && total >= MinPosProfit)
     {
      Log(StringFormat("Ciclo chiuso: %d posizioni, %.2f", n, total));
      CloseAll();
      g_cycles++;
      g_lastPx = 0;
      return;
     }

   if(ProfitCalcMode == PCM_POSITION || ProfitCalcMode == PCM_BOTH)
     {
      for(int i = PositionsTotal() - 1; i >= 0; i--)
        {
         ulong t = PositionGetTicket(i);
         if(!IsMine(t))
            continue;
         double p = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
         if(p >= MinPosProfit && g_trade.PositionClose(t))
            Log(StringFormat("Chiusa #%I64u a %.2f", t, p));
        }
     }
  }

//+------------------------------------------------------------------+
//| Ingressi: coppia iniziale e nuovi livelli a ogni passo           |
//+------------------------------------------------------------------+
void ManageEntries(double bid)
  {
   int nBuy = 0, nSell = 0;
   CountPositions(nBuy, nSell);
   int n = nBuy + nSell;

   bool window = InWindow();
   g_status = window ? "attivo" : "fuori orario";
   if(!window)
      return;
   if(SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > MaxSpread)
     {
      g_status = "spread alto";
      return;
     }

   if(n > 0 && g_lastPx == 0)
      g_lastPx = LastOpenPrice();   // dopo un riavvio riparte dall'ultima apertura

   if(n == 0 && TradingMode == TM_BOTH)
     {
      OpenLevel(bid, true, true, nBuy, nSell);
      return;
     }
   if(g_lastPx == 0)
     {
      g_lastPx = bid;               // direzionale: aspetta il primo passo da qui
      return;
     }

   double move = bid - g_lastPx;
   if(MathAbs(move) < StepPrice(bid))
      return;

   if(TradingMode == TM_BOTH)
      OpenLevel(bid, true, true, nBuy, nSell);
   else
      OpenLevel(bid, move > 0, move < 0, nBuy, nSell);
  }

void OpenLevel(double bid, bool buy, bool sell, int nBuy, int nSell)
  {
   bool ok = false;
   if(buy)
     {
      double lot = LotFor(nBuy);
      if(g_trade.Buy(lot, _Symbol, 0, 0, 0, TradeComment))
        { ok = true; Log(StringFormat("BUY %.2f a %s", lot, DoubleToString(g_trade.ResultPrice(), _Digits))); }
     }
   if(sell)
     {
      double lot = LotFor(nSell);
      if(g_trade.Sell(lot, _Symbol, 0, 0, 0, TradeComment))
        { ok = true; Log(StringFormat("SELL %.2f a %s", lot, DoubleToString(g_trade.ResultPrice(), _Digits))); }
     }
   // se l'apertura fallisce (margine, mercato chiuso) riprova al tick dopo
   if(ok)
      g_lastPx = bid;
  }

//+------------------------------------------------------------------+
//| Calcoli                                                          |
//+------------------------------------------------------------------+
double StepPrice(double bid)
  {
   if(SType == STP_PERCENT)
      return bid * MinStepPerc / 100.0;
   return MinStep * _Point;
  }

// already = posizioni gia' aperte nella stessa direzione
double LotFor(int already)
  {
   double lot = Lots;
   if(LotCalcMode == LCM_BALANCE)
      lot = Lots * AccountInfoDouble(ACCOUNT_BALANCE) / 1000.0;
   if(LotCalcMode != LCM_FIXED)
     {
      int every = LotsizeIncrementMultiple > 0 ? LotsizeIncrementMultiple : 1;
      lot += LotsizeIncrement * (already / every);
     }
   if(MaxLotsize > 0)
      lot = MathMin(lot, MaxLotsize);

   double vMin  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vMax  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double vStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(vStep > 0)
      lot = MathFloor(lot / vStep + 1e-9) * vStep;
   return NormalizeDouble(MathMax(vMin, MathMin(vMax, lot)), 2);
  }

// finestra oraria: da StartHour per "time" minuti (puo' passare la mezzanotte)
bool InWindow()
  {
   if(time <= 0 || time >= 1440)
      return true;
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int now   = dt.hour * 60 + dt.min;
   int start = StartHour * 60;
   int end   = start + time;
   if(end <= 1440)
      return now >= start && now < end;
   return now >= start || now < end - 1440;
  }

bool IsMine(ulong ticket)
  {
   return ticket > 0 && PositionSelectByTicket(ticket)
          && PositionGetString(POSITION_SYMBOL) == _Symbol
          && PositionGetInteger(POSITION_MAGIC) == MagicNumber;
  }

double CycleProfit(int &n)
  {
   double total = 0;
   n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(!IsMine(t))
         continue;
      total += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      n++;
     }
   return total;
  }

void CountPositions(int &nBuy, int &nSell)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(!IsMine(t))
         continue;
      if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
         nBuy++;
      else
         nSell++;
     }
  }

double LastOpenPrice()
  {
   long   newest = 0;
   double px     = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(!IsMine(t))
         continue;
      long tm = PositionGetInteger(POSITION_TIME_MSC);
      if(tm > newest)
        {
         newest = tm;
         px = PositionGetDouble(POSITION_PRICE_OPEN);
        }
     }
   return px;
  }

void CloseAll()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(IsMine(t))
         g_trade.PositionClose(t);
     }
  }

void Log(string s)
  {
   if(PrintAllowed)
      Print(s);
  }

//+------------------------------------------------------------------+
//| Pannello ed esportazione                                         |
//+------------------------------------------------------------------+
void UpdatePanel(double bid)
  {
   if((bool)MQLInfoInteger(MQL_TESTER) && !(bool)MQLInfoInteger(MQL_VISUAL_MODE))
      return;
   int nBuy = 0, nSell = 0, n = 0;
   CountPositions(nBuy, nSell);
   double total = CycleProfit(n);
   Comment(StringFormat("BuySellGrid  [%s]\n"
                        "Posizioni: %d buy / %d sell\n"
                        "Profitto ciclo: %.2f   (chiude a +%.2f)\n"
                        "Peggior perdita ciclo: %.2f\n"
                        "Passo: %s   ultimo livello: %s\n"
                        "Cicli chiusi: %d\n"
                        "Saldo: %.2f   Equity: %.2f",
                        g_status, nBuy, nSell, total, MinPosProfit, -g_maxDD,
                        DoubleToString(StepPrice(bid), _Digits),
                        g_lastPx > 0 ? DoubleToString(g_lastPx, _Digits) : "-",
                        g_cycles,
                        AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY)));
  }

void ExportDeals()
  {
   if(!HistorySelect(0, TimeCurrent() + 86400))
      return;
   string file = "BuySellGrid_" + _Symbol + ".csv";
   int h = FileOpen(file, FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(h == INVALID_HANDLE)
     {
      Print("Esportazione non riuscita: ", GetLastError());
      return;
     }
   FileWrite(h, "ora", "deal", "posizione", "tipo", "entrata", "volume", "prezzo", "profitto", "swap", "commissione");
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
     {
      ulong d = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(d, DEAL_MAGIC) != MagicNumber || HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol)
         continue;
      long type  = HistoryDealGetInteger(d, DEAL_TYPE);
      long entry = HistoryDealGetInteger(d, DEAL_ENTRY);
      FileWrite(h,
                TimeToString((datetime)HistoryDealGetInteger(d, DEAL_TIME), TIME_DATE | TIME_SECONDS),
                (long)d,
                HistoryDealGetInteger(d, DEAL_POSITION_ID),
                type == DEAL_TYPE_BUY ? "buy" : "sell",
                entry == DEAL_ENTRY_IN ? "in" : "out",
                DoubleToString(HistoryDealGetDouble(d, DEAL_VOLUME), 2),
                DoubleToString(HistoryDealGetDouble(d, DEAL_PRICE), _Digits),
                DoubleToString(HistoryDealGetDouble(d, DEAL_PROFIT), 2),
                DoubleToString(HistoryDealGetDouble(d, DEAL_SWAP), 2),
                DoubleToString(HistoryDealGetDouble(d, DEAL_COMMISSION), 2));
     }
   FileClose(h);
   Print("Deal salvati in MQL5/Files/", file);
  }
//+------------------------------------------------------------------+
