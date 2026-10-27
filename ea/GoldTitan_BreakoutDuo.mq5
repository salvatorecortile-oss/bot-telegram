//+------------------------------------------------------------------+
//|                                       GoldTitan_BreakoutDuo.mq5  |
//|  Due bot in uno sulla strategia ROTTURA di GoldTitan Trio:       |
//|   - ORIGINALE : rottura in alto -> BUY, in basso -> SELL         |
//|   - INVERTITA : rottura in alto -> SELL, in basso -> BUY         |
//|  Stesso segnale per entrambe (chiusura M15 fuori dal canale di   |
//|  24 candele, filtro trend H1 e ADX), stessi filtri (ATR, spread, |
//|  notizie USD). Ogni versione ha magic number, pausa e risultati  |
//|  suoi: e' come far girare due bot separati nello stesso test.    |
//|  Con InpMirror l'invertita usa SL e TP scambiati rispetto        |
//|  all'originale (SL inv = TP orig, TP inv = SL orig).             |
//|  In ottimizzazione scrive in Common\Files il file                |
//|  GoldTitan_BreakoutDuo_opt.csv con il confronto delle due        |
//|  versioni per ogni combinazione provata.                         |
//|  Serve un conto HEDGING (le due versioni aprono in direzioni     |
//|  opposte nello stesso momento).                                  |
//+------------------------------------------------------------------+
#property version   "1.00"
#property description "GoldTitan Breakout Duo - Rottura M15 su XAUUSD, versione originale e invertita insieme, con confronto dei risultati."

#include <Trade\Trade.mqh>

enum OptTarget
  {
   OPT_TOTAL = 0,  // Totale delle due versioni
   OPT_ORIG  = 1,  // Solo ORIGINALE
   OPT_INV   = 2,  // Solo INVERTITA
   OPT_DIFF  = 3   // INVERTITA meno ORIGINALE
  };

//--- Lotto
input double InpLots          = 0.01;      // Lotto (uguale per le due versioni)
input double InpBalancePerLot = 0.0;       // Lotto progressivo: un lotto ogni X $ di saldo (0 = lotto fisso)

//--- Versioni (1 pip = 0.10 di prezzo = 10 points)
input bool   InpUseOrig       = true;      // ORIGINALE: attiva
input int    InpSlPips        = 200;       // ORIGINALE: stop loss (pips)
input int    InpTpPips        = 300;       // ORIGINALE: take profit (pips)
input bool   InpUseInv        = true;      // INVERTITA: attiva
input bool   InpMirror        = true;      // INVERTITA: SL e TP scambiati rispetto all'originale
input int    InpInvSlPips     = 300;       // INVERTITA: stop loss (pips, usato solo se Mirror = false)
input int    InpInvTpPips     = 200;       // INVERTITA: take profit (pips, usato solo se Mirror = false)

//--- Filtri (uguali per le due versioni)
input double InpAdxMin        = 30.0;      // Opera solo se ADX M15 e' sopra questo valore (0 = filtro spento)
input bool   InpH1Filter      = true;      // Filtro trend H1 (EMA 50/200 nella direzione della rottura)
input double InpMinAtrUsd     = 60.0;      // Opera solo se l'ATR giornaliero e' sopra X $ (0 = filtro spento)
input int    InpMaxSpreadPts  = 70;        // Opera solo se lo spread e' inferiore a (points, 0 = off)

//--- Protezioni (contatore separato per ogni versione)
input int    InpPauseLosses   = 4;         // Pausa dopo N stop loss consecutivi (0 = off)
input int    InpPauseHours    = 24;        // Durata della pausa (ore)

//--- Tester e identificativi
input OptTarget InpOptTarget  = OPT_TOTAL; // Ottimizzazione: cosa massimizzare con "Custom max"
input double InpSimSlipPerLot = 10.0;      // Slippage simulato nel tester ($ per lotto, 0 = off)
input ulong  InpOrigMagic     = 20261010;  // ORIGINALE: magic number
input ulong  InpInvMagic      = 20261011;  // INVERTITA: magic number

//--- Filtro notizie (USD)
input bool   InpNewsFilter    = true;      // NOTIZIE: niente nuove operazioni vicino alle notizie USD
input int    InpNewsBeforeMin = 0;         // NOTIZIE: minuti prima della notizia
input int    InpNewsAfterMin  = 90;        // NOTIZIE: minuti dopo la notizia
input bool   InpNewsMedium    = false;     // NOTIZIE: includi anche quelle di media importanza
input bool   InpNewsClose     = false;     // NOTIZIE: chiudi le posizioni aperte durante la finestra

//--- Pannello sul grafico (solo informativo, non cambia il trading)
input bool   InpShowPanel     = true;      // PANNELLO: mostra il pannello sul grafico

//--- Valori fissi, uguali a GoldTitan Trio
#define BRK_TF            PERIOD_M15   // timeframe della rottura
#define CHANNEL_BARS      24           // candele del canale
#define ADX_PERIOD        14
#define ATR_PERIOD        14           // giorni
#define EMA_FAST_PERIOD   50
#define EMA_SLOW_PERIOD   200
#define PIP_SIZE          0.10         // valore di 1 pip in prezzo
#define NO_SLIPPAGE_LIMIT 100000       // points: in pratica nessun limite allo slippage
#define OPT_FILE          "GoldTitan_BreakoutDuo_opt.csv"

// indice delle versioni: 0 = ORIGINALE, 1 = INVERTITA
CTrade   trade;
int      h1FastHandle  = INVALID_HANDLE;
int      h1SlowHandle  = INVALID_HANDLE;
int      adxHandle     = INVALID_HANDLE;
int      atrHandle     = INVALID_HANDLE;
datetime atrWarnDay    = 0;
datetime brkLastBar    = 0;
datetime lastWarnBar   = 0;
ulong    vMagic[2];
bool     vOn[2];
int      vSl[2], vTp[2];
double   slipSim[2]    = {0.0, 0.0};       // slippage simulato accumulato ($)
int      consLosses[2] = {0, 0};
datetime pauseUntil[2] = {0, 0};
int      pauseCount[2] = {0, 0};
int      signalCount   = 0;                // segnali che hanno passato i filtri del segnale
string   lastSignal    = "";

#define  NEWS_FILE "GoldTitan_news.csv"
datetime newsTimes[];
int      newsCount     = 0;
int      newsPtr       = 0;
datetime newsLoadedAt  = 0;
int      newsSkips     = 0;
int      newsCloses    = 0;

//--- ottimizzazione: parametri ottimizzati e file del confronto
string   optNames[];
int      optFile = INVALID_HANDLE;
int      optRows = 0;

//--- pannello
bool     panelOn        = false;
bool     panelHistDirty = true;
datetime panelHistAt    = 0;
int      panelLines     = 0;
double   hsTodayNet[2], hsAllNet[2], hsGrossWin[2], hsGrossLoss[2];
int      hsTodayN[2], hsAllN[2], hsAllW[2];

color    PNL_TXT  = clrWhite;
color    PNL_DIM  = C'150,150,150';
color    PNL_HEAD = C'212,175,55';
color    PNL_OK   = C'60,200,90';
color    PNL_WARN = C'255,170,40';
color    PNL_BAD  = C'240,80,80';

//+------------------------------------------------------------------+
string VName(const int k)
  {
   return(k == 0 ? "ORIGINALE" : "INVERTITA");
  }

//+------------------------------------------------------------------+
int VIndex(const ulong magic)
  {
   if(magic == vMagic[0]) return(0);
   if(magic == vMagic[1]) return(1);
   return(-1);
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   if(StringFind(_Symbol, "XAU") < 0 && StringFind(_Symbol, "GOLD") < 0)
      Print("ATTENZIONE: l'EA e' pensato per XAUUSD, simbolo attuale: ", _Symbol);

   if(InpOrigMagic == InpInvMagic)
     {
      Print("I magic number devono essere diversi tra loro");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(!InpUseOrig && !InpUseInv)
     {
      Print("Attiva almeno una delle due versioni");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(InpLots <= 0.0 || InpBalancePerLot < 0.0 || InpAdxMin < 0.0 || InpMinAtrUsd < 0.0 ||
      InpPauseLosses < 0 || InpPauseHours < 1)
     {
      Print("Parametri di lotto o dei filtri non validi");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(InpUseOrig && InpUseInv &&
      AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
     {
      Print("Le due versioni aprono in direzioni opposte: serve un conto HEDGING (oppure attivane una sola)");
      return(INIT_FAILED);
     }

   vMagic[0] = InpOrigMagic;
   vMagic[1] = InpInvMagic;
   vOn[0]    = InpUseOrig;
   vOn[1]    = InpUseInv;
   vSl[0]    = InpSlPips;
   vTp[0]    = InpTpPips;
   vSl[1]    = InpMirror ? InpTpPips : InpInvSlPips;
   vTp[1]    = InpMirror ? InpSlPips : InpInvTpPips;

   double point   = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   for(int k = 0; k < 2; k++)
     {
      if(!vOn[k])
         continue;
      if(vSl[k] <= 0 || vTp[k] <= 0 || vSl[k] * PIP_SIZE < minDist || vTp[k] * PIP_SIZE < minDist)
        {
         PrintFormat("%s: SL/TP non validi o sotto lo stop level del broker", VName(k));
         return(INIT_PARAMETERS_INCORRECT);
        }
     }

   h1FastHandle = iMA(_Symbol, PERIOD_H1, EMA_FAST_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
   h1SlowHandle = iMA(_Symbol, PERIOD_H1, EMA_SLOW_PERIOD, 0, MODE_EMA, PRICE_CLOSE);
   adxHandle    = iADX(_Symbol, BRK_TF, ADX_PERIOD);
   atrHandle    = iATR(_Symbol, PERIOD_D1, ATR_PERIOD);
   if(h1FastHandle == INVALID_HANDLE || h1SlowHandle == INVALID_HANDLE ||
      adxHandle == INVALID_HANDLE || atrHandle == INVALID_HANDLE)
     {
      Print("Impossibile creare gli indicatori, errore ", GetLastError());
      return(INIT_FAILED);
     }

   trade.SetDeviationInPoints(NO_SLIPPAGE_LIMIT);
   trade.SetTypeFillingBySymbol(_Symbol);

   if(InpNewsFilter)
     {
      if(InpNewsBeforeMin < 0 || InpNewsAfterMin < 0)
        {
         Print("Minuti del filtro notizie non validi");
         return(INIT_PARAMETERS_INCORRECT);
        }
      if(!LoadNews())
        {
         if(MQLInfoInteger(MQL_TESTER))
           {
            Print("Filtro notizie: file ", NEWS_FILE, " non trovato in Common\\Files. Esegui prima lo script GoldTitan_ExportNews.");
            return(INIT_FAILED);
           }
         Print("Filtro notizie: calendario non ancora disponibile, riprovo tra poco");
        }
     }

   PrintFormat("GoldTitan Breakout Duo 1.00 avviato su %s | ORIGINALE %s SL %d TP %d | INVERTITA %s SL %d TP %d | ADX min %.0f | ATR min %.0f $ | lotto %.2f",
               _Symbol, vOn[0] ? "on" : "off", vSl[0], vTp[0], vOn[1] ? "on" : "off", vSl[1], vTp[1],
               InpAdxMin, InpMinAtrUsd, InpLots);
   PanelInit();
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(h1FastHandle != INVALID_HANDLE) IndicatorRelease(h1FastHandle);
   if(h1SlowHandle != INVALID_HANDLE) IndicatorRelease(h1SlowHandle);
   if(adxHandle    != INVALID_HANDLE) IndicatorRelease(adxHandle);
   if(atrHandle    != INVALID_HANDLE) IndicatorRelease(atrHandle);
   PanelDeinit();
  }

//+------------------------------------------------------------------+
void OnTimer()
  {
   PanelUpdate();
  }

//+------------------------------------------------------------------+
//| Risultati di una versione dalle operazioni chiuse: trade, vinti, |
//| netto (meno lo slippage simulato), profit factor e drawdown      |
//| massimo sulle chiusure.                                          |
//+------------------------------------------------------------------+
void VersionStats(const int k, int &n, int &win, double &net, double &pf, double &dd)
  {
   n = 0; win = 0; net = 0.0; pf = 0.0; dd = 0.0;
   double gw = 0.0, gl = 0.0, cum = 0.0, peak = 0.0;
   double slipPerTrade = 0.0;
   if(!HistorySelect(0, TimeCurrent()))
      return;
   int total = HistoryDealsTotal();
   // lo slippage simulato si spalma sulle chiusure, per includerlo anche nel drawdown
   int closes = 0;
   for(int i = 0; i < total; i++)
     {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0 || (ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != vMagic[k])
         continue;
      long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
      if(entry == DEAL_ENTRY_OUT || entry == DEAL_ENTRY_OUT_BY || entry == DEAL_ENTRY_INOUT)
         closes++;
     }
   if(closes > 0)
      slipPerTrade = slipSim[k] / closes;

   for(int i = 0; i < total; i++)
     {
      ulong deal = HistoryDealGetTicket(i);
      if(deal == 0 || (ulong)HistoryDealGetInteger(deal, DEAL_MAGIC) != vMagic[k])
         continue;
      long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY && entry != DEAL_ENTRY_INOUT)
         continue;
      double p = HistoryDealGetDouble(deal, DEAL_PROFIT) +
                 HistoryDealGetDouble(deal, DEAL_SWAP) +
                 HistoryDealGetDouble(deal, DEAL_COMMISSION) - slipPerTrade;
      n++;
      if(p > 0.0) { win++; gw += p; }
      else        gl -= p;
      cum += p;
      if(cum > peak)
         peak = cum;
      if(peak - cum > dd)
         dd = peak - cum;
     }
   net = cum;
   pf  = gl > 0.0 ? gw / gl : (gw > 0.0 ? 99.0 : 0.0);
  }

//+------------------------------------------------------------------+
//| Fine del test: confronto nel Journal e valore per "Custom max".  |
//| In ottimizzazione manda i risultati al terminale (frame) per il  |
//| file CSV del confronto.                                          |
//+------------------------------------------------------------------+
double OnTester()
  {
   int    n[2], w[2];
   double net[2], pf[2], dd[2];
   for(int k = 0; k < 2; k++)
      VersionStats(k, n[k], w[k], net[k], pf[k], dd[k]);

   for(int k = 0; k < 2; k++)
      PrintFormat("%-9s: %s | SL %d TP %d | %d trade, %d vinti (%.0f%%), netto %.2f $, PF %.2f, DD %.2f $, slippage %.2f $, pause %d",
                  VName(k), vOn[k] ? "on " : "off", vSl[k], vTp[k], n[k], w[k],
                  n[k] > 0 ? 100.0 * w[k] / n[k] : 0.0, net[k], pf[k], dd[k], slipSim[k], pauseCount[k]);
   PrintFormat("SEGNALI  : %d | notizie: segnali scartati %d, posizioni chiuse %d", signalCount, newsSkips, newsCloses);
   string best = net[1] > net[0] ? "INVERTITA" : (net[0] > net[1] ? "ORIGINALE" : "PARI");
   PrintFormat("CONFRONTO: INVERTITA - ORIGINALE = %.2f $ | migliore: %s | totale %.2f $",
               net[1] - net[0], best, net[0] + net[1]);

   double value = net[0] + net[1];
   if(InpOptTarget == OPT_ORIG)      value = net[0];
   else if(InpOptTarget == OPT_INV)  value = net[1];
   else if(InpOptTarget == OPT_DIFF) value = net[1] - net[0];

   double data[12];
   for(int k = 0; k < 2; k++)
     {
      data[k * 5 + 0] = n[k];
      data[k * 5 + 1] = w[k];
      data[k * 5 + 2] = net[k];
      data[k * 5 + 3] = pf[k];
      data[k * 5 + 4] = dd[k];
     }
   data[10] = vSl[1];
   data[11] = vTp[1];
   FrameAdd("duo", 0, value, data);
   return(NormalizeDouble(value, 2));
  }

//+------------------------------------------------------------------+
//| Ottimizzazione: apre il CSV e annota quali parametri variano.    |
//+------------------------------------------------------------------+
void OnTesterInit()
  {
   string cand[] = {"InpSlPips", "InpTpPips", "InpMirror", "InpInvSlPips", "InpInvTpPips",
                    "InpAdxMin", "InpH1Filter", "InpMinAtrUsd", "InpMaxSpreadPts",
                    "InpPauseLosses", "InpPauseHours", "InpNewsAfterMin", "InpNewsBeforeMin", "InpNewsMedium"};
   ArrayResize(optNames, 0);
   for(int i = 0; i < ArraySize(cand); i++)
     {
      // interi e bool con la versione long, i double con quella double
      bool   enable = false;
      long   lv, lstart, lstep, lstop;
      double dv, dstart, dstep, dstop;
      bool   found = ParameterGetRange(cand[i], enable, lv, lstart, lstep, lstop);
      if(!found)
         found = ParameterGetRange(cand[i], enable, dv, dstart, dstep, dstop);
      if(found && enable)
        {
         int s = ArraySize(optNames);
         ArrayResize(optNames, s + 1);
         optNames[s] = cand[i];
        }
     }

   optRows = 0;
   optFile = FileOpen(OPT_FILE, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(optFile == INVALID_HANDLE)
     {
      Print("Impossibile creare ", OPT_FILE, ", errore ", GetLastError());
      return;
     }
   string head = "Passaggio";
   for(int i = 0; i < ArraySize(optNames); i++)
      head += ";" + optNames[i];
   head += ";ORIG SL;ORIG TP;ORIG trade;ORIG vinti;ORIG % vinti;ORIG netto;ORIG PF;ORIG DD"
           ";INV SL;INV TP;INV trade;INV vinti;INV % vinti;INV netto;INV PF;INV DD"
           ";INV - ORIG;Totale;Migliore";
   FileWriteString(optFile, head + "\r\n");
  }

//+------------------------------------------------------------------+
//| Numero con la virgola decimale (Excel in italiano).              |
//+------------------------------------------------------------------+
string Num(const double v, const int digits)
  {
   string s = DoubleToString(v, digits);
   StringReplace(s, ".", ",");
   return(s);
  }

//+------------------------------------------------------------------+
//| Ottimizzazione: una riga del CSV per ogni passaggio finito.      |
//+------------------------------------------------------------------+
void OnTesterPass()
  {
   ulong  pass;
   string name;
   long   id;
   double value;
   double data[];
   while(FrameNext(pass, name, id, value, data))
     {
      if(name != "duo" || ArraySize(data) < 12 || optFile == INVALID_HANDLE)
         continue;

      string params[];
      uint   pcount = 0;
      string line = IntegerToString((long)pass);
      string origSl = "", origTp = "";
      if(FrameInputs(pass, params, pcount))
        {
         for(int i = 0; i < ArraySize(optNames); i++)
           {
            string val = "";
            for(uint j = 0; j < pcount; j++)
              {
               int eq = StringFind(params[j], "=");
               if(eq > 0 && StringSubstr(params[j], 0, eq) == optNames[i])
                 {
                  val = StringSubstr(params[j], eq + 1);
                  break;
                 }
              }
            StringReplace(val, ".", ",");
            line += ";" + val;
           }
         for(uint j = 0; j < pcount; j++)
           {
            if(StringFind(params[j], "InpSlPips=") == 0) origSl = StringSubstr(params[j], 10);
            if(StringFind(params[j], "InpTpPips=") == 0) origTp = StringSubstr(params[j], 10);
           }
        }
      else
         for(int i = 0; i < ArraySize(optNames); i++)
            line += ";";

      double nO = data[0], wO = data[1], netO = data[2], pfO = data[3], ddO = data[4];
      double nI = data[5], wI = data[6], netI = data[7], pfI = data[8], ddI = data[9];
      string best = netI > netO ? "INVERTITA" : (netO > netI ? "ORIGINALE" : "PARI");
      line += ";" + origSl + ";" + origTp +
              ";" + Num(nO, 0) + ";" + Num(wO, 0) + ";" + Num(nO > 0 ? 100.0 * wO / nO : 0.0, 1) +
              ";" + Num(netO, 2) + ";" + Num(pfO, 2) + ";" + Num(ddO, 2) +
              ";" + Num(data[10], 0) + ";" + Num(data[11], 0) +
              ";" + Num(nI, 0) + ";" + Num(wI, 0) + ";" + Num(nI > 0 ? 100.0 * wI / nI : 0.0, 1) +
              ";" + Num(netI, 2) + ";" + Num(pfI, 2) + ";" + Num(ddI, 2) +
              ";" + Num(netI - netO, 2) + ";" + Num(netO + netI, 2) + ";" + best;
      FileWriteString(optFile, line + "\r\n");
      FileFlush(optFile);
      optRows++;
     }
  }

//+------------------------------------------------------------------+
void OnTesterDeinit()
  {
   OnTesterPass();   // eventuali frame rimasti
   if(optFile != INVALID_HANDLE)
     {
      FileClose(optFile);
      optFile = INVALID_HANDLE;
     }
   PrintFormat("Confronto salvato: %d combinazioni in %s\\Files\\%s",
               optRows, TerminalInfoString(TERMINAL_COMMONDATA_PATH), OPT_FILE);
  }

//+------------------------------------------------------------------+
//| Conta gli stop consecutivi (pausa, separata per versione) e,     |
//| solo nel tester, lo slippage simulato a ogni apertura.           |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
   panelHistDirty = true;
   if(!HistoryDealSelect(trans.deal))
      return;
   if(HistoryDealGetString(trans.deal, DEAL_SYMBOL) != _Symbol)
      return;
   int k = VIndex((ulong)HistoryDealGetInteger(trans.deal, DEAL_MAGIC));
   if(k < 0)
      return;
   long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);

   if(entry == DEAL_ENTRY_OUT)
     {
      double p = HistoryDealGetDouble(trans.deal, DEAL_PROFIT) +
                 HistoryDealGetDouble(trans.deal, DEAL_SWAP) +
                 HistoryDealGetDouble(trans.deal, DEAL_COMMISSION);
      if(p < 0.0)
        {
         consLosses[k]++;
         if(InpPauseLosses > 0 && consLosses[k] >= InpPauseLosses)
           {
            pauseUntil[k] = TimeCurrent() + (datetime)(InpPauseHours * 3600);
            consLosses[k] = 0;
            pauseCount[k]++;
            PrintFormat("%s: pausa di %d ore dopo %d stop consecutivi", VName(k), InpPauseHours, InpPauseLosses);
           }
        }
      else
         consLosses[k] = 0;
      return;
     }

   if(entry != DEAL_ENTRY_IN)
      return;
   if(InpSimSlipPerLot <= 0.0 || !MQLInfoInteger(MQL_TESTER))
      return;
   slipSim[k] += NormalizeDouble(InpSimSlipPerLot * HistoryDealGetDouble(trans.deal, DEAL_VOLUME), 2);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   if(InpNewsFilter)
     {
      if(!MQLInfoInteger(MQL_TESTER) && TimeCurrent() - newsLoadedAt > (newsCount > 0 ? 3600 : 60))
         LoadNews();
      if(InpNewsClose && NewsBlocked(TimeCurrent()))
         CloseAllForNews();
     }

   // Il segnale si valuta alla chiusura di ogni candela M15.
   // La candela e' segnata come valutata solo se i dati erano pronti (altrimenti si riprova).
   datetime brkBar = iTime(_Symbol, BRK_TF, 0);
   if(brkBar != 0 && brkBar != brkLastBar)
     {
      if(CheckBreakout(brkBar))
         brkLastBar = brkBar;
     }
  }

//+------------------------------------------------------------------+
//| Segnale identico alla Rottura di GoldTitan Trio: l'ultima        |
//| candela M15 chiude sopra il massimo (rottura in alto) o sotto il |
//| minimo (rottura in basso) delle 24 candele precedenti, a favore  |
//| del trend H1 e con ADX sopra il minimo.                          |
//| ORIGINALE entra nella direzione della rottura, INVERTITA contro. |
//| Ritorna false solo se i dati non sono pronti.                    |
//+------------------------------------------------------------------+
bool CheckBreakout(const datetime barTime)
  {
   double hi[], lo[], cl[];
   int n = CHANNEL_BARS;
   if(CopyHigh(_Symbol, BRK_TF, 2, n, hi) != n ||
      CopyLow(_Symbol, BRK_TF, 2, n, lo) != n ||
      CopyClose(_Symbol, BRK_TF, 1, 1, cl) != 1)
      return(NotReady(barTime, "canale"));

   double upper = hi[ArrayMaximum(hi)];
   double lower = lo[ArrayMinimum(lo)];

   bool breakUp   = (cl[0] > upper);
   bool breakDown = (cl[0] < lower);
   if(!breakUp && !breakDown)
      return(true);

   // I filtri guardano la direzione della rottura, come nella versione originale.
   if(InpH1Filter)
     {
      bool ready = true;
      if(!H1TrendOk(breakUp, ready))
         return(ready ? true : NotReady(barTime, "EMA H1"));
     }

   if(InpAdxMin > 0.0)
     {
      double adx[];
      if(BarsCalculated(adxHandle) < 2 * ADX_PERIOD + 2 ||
         CopyBuffer(adxHandle, 0, 1, 1, adx) != 1 ||
         adx[0] == EMPTY_VALUE)
         return(NotReady(barTime, "ADX"));
      if(adx[0] < InpAdxMin)
         return(true);
     }

   signalCount++;
   lastSignal = StringFormat("%s rottura in %s", TimeToString(barTime, TIME_DATE | TIME_MINUTES),
                             breakUp ? "alto" : "basso");
   if(vOn[0])
      OpenTrade(0, breakUp);
   if(vOn[1])
      OpenTrade(1, !breakUp);
   return(true);
  }

//+------------------------------------------------------------------+
//| Filtro trend H1 sull'ultima candela H1 chiusa: rialzo se         |
//| EMA 50 > EMA 200, ribasso se sotto.                              |
//| ready = false se le EMA H1 non sono ancora disponibili.          |
//+------------------------------------------------------------------+
bool H1TrendOk(const bool isUp, bool &ready)
  {
   ready = true;
   double h1Fast[], h1Slow[];
   if(BarsCalculated(h1FastHandle) < EMA_SLOW_PERIOD + 2 ||
      BarsCalculated(h1SlowHandle) < EMA_SLOW_PERIOD + 2 ||
      CopyBuffer(h1FastHandle, 0, 1, 1, h1Fast) != 1 ||
      CopyBuffer(h1SlowHandle, 0, 1, 1, h1Slow) != 1 ||
      h1Fast[0] == EMPTY_VALUE || h1Slow[0] == EMPTY_VALUE)
     {
      ready = false;
      return(false);
     }
   return(isUp ? (h1Fast[0] > h1Slow[0]) : (h1Fast[0] < h1Slow[0]));
  }

//+------------------------------------------------------------------+
bool NotReady(const datetime barTime, const string what)
  {
   if(lastWarnBar != barTime)
     {
      lastWarnBar = barTime;
      Print(what, " non ancora disponibile, riprovo al prossimo tick");
     }
   return(false);
  }

//+------------------------------------------------------------------+
//| Apre il trade della versione k. Al massimo una posizione aperta  |
//| per versione.                                                    |
//+------------------------------------------------------------------+
void OpenTrade(const int k, const bool isBuy)
  {
   string side = isBuy ? "BUY" : "SELL";
   string tag  = k == 0 ? "ROT" : "ROTINV";

   if(CountPositions(vMagic[k]) > 0)
      return;
   if(InpNewsFilter && NewsBlocked(TimeCurrent()))
     {
      newsSkips++;
      return;
     }
   if(pauseUntil[k] > 0 && TimeCurrent() < pauseUntil[k])
      return;

   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int    digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   long spread = (long)MathRound((ask - bid) / point);
   if(InpMaxSpreadPts > 0 && spread >= InpMaxSpreadPts)
     {
      PrintFormat("%s %s ignorato: spread %I64d points >= %d", tag, side, spread, InpMaxSpreadPts);
      return;
     }

   // ATR giornaliero dell'ultimo giorno chiuso (in $ di prezzo).
   double atrBuf[];
   double atr = 0.0;
   if(BarsCalculated(atrHandle) >= ATR_PERIOD + 2 &&
      CopyBuffer(atrHandle, 0, 1, 1, atrBuf) == 1 && atrBuf[0] != EMPTY_VALUE)
      atr = atrBuf[0];
   if(atr <= 0.0 && InpMinAtrUsd > 0.0)
     {
      datetime day = iTime(_Symbol, PERIOD_D1, 0);
      if(atrWarnDay != day)
        {
         atrWarnDay = day;
         Print("ATR giornaliero non ancora disponibile: segnale ignorato");
        }
      return;
     }
   if(InpMinAtrUsd > 0.0 && atr < InpMinAtrUsd)
      return;

   double lots = InpLots;
   if(InpBalancePerLot > 0.0)
     {
      double steps = MathFloor(AccountInfoDouble(ACCOUNT_BALANCE) / InpBalancePerLot);
      lots = InpLots * MathMax(1.0, steps);
     }
   lots = NormalizeLots(lots);

   double slDist = vSl[k] * PIP_SIZE;
   double tpDist = vTp[k] * PIP_SIZE;
   double sl = 0.0, tp = 0.0;
   if(isBuy)
     {
      sl = NormalizeDouble(ask - slDist, digits);
      tp = NormalizeDouble(ask + tpDist, digits);
     }
   else
     {
      sl = NormalizeDouble(bid + slDist, digits);
      tp = NormalizeDouble(bid - tpDist, digits);
     }

   if(!StopsAllowed(isBuy, ask, bid, sl, tp, point))
     {
      PrintFormat("%s %s ignorato: SL/TP sotto lo stop level del broker", tag, side);
      return;
     }

   trade.SetExpertMagicNumber(vMagic[k]);
   string comment = tag + " " + side;
   bool ok = isBuy ? trade.Buy(lots, _Symbol, ask, sl, tp, comment)
                   : trade.Sell(lots, _Symbol, bid, sl, tp, comment);
   if(!ok)
      PrintFormat("%s %s fallito: %d %s", tag, side, trade.ResultRetcode(), trade.ResultRetcodeDescription());
  }

//+------------------------------------------------------------------+
//| Verifica la distanza minima degli stop richiesta dal broker.     |
//| BUY:  SL e TP si misurano dal Bid.  SELL: SL e TP dall'Ask.      |
//+------------------------------------------------------------------+
bool StopsAllowed(const bool isBuy, const double ask, const double bid,
                  const double sl, const double tp, const double point)
  {
   double minDist = (double)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) * point;
   if(minDist <= 0.0)
      return(true);

   double eps = point * 0.5;
   if(isBuy)
     {
      if((bid - sl) < minDist - eps) return(false);
      if((tp - bid) < minDist - eps) return(false);
     }
   else
     {
      if((sl - ask) < minDist - eps) return(false);
      if((ask - tp) < minDist - eps) return(false);
     }
   return(true);
  }

//+------------------------------------------------------------------+
int CountPositions(const ulong magic)
  {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         (ulong)PositionGetInteger(POSITION_MAGIC) == magic)
         count++;
     }
   return(count);
  }

//+------------------------------------------------------------------+
double NormalizeLots(double lots)
  {
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(step > 0.0)
      lots = MathFloor(lots / step + 1e-9) * step;
   lots = MathMax(minLot, MathMin(maxLot, lots));
   return(NormalizeDouble(lots, 2));
  }

//+------------------------------------------------------------------+
//| Carica le notizie USD. Nel tester dal file in Common\Files       |
//| (creato dallo script GoldTitan_ExportNews), dal vivo dal         |
//| calendario di MT5 (da ieri a 7 giorni avanti).                   |
//+------------------------------------------------------------------+
bool LoadNews()
  {
   newsLoadedAt = TimeCurrent();
   datetime tmp[];
   int n = 0;

   if(MQLInfoInteger(MQL_TESTER))
     {
      int h = FileOpen(NEWS_FILE, FILE_READ | FILE_SHARE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON, ';');
      if(h == INVALID_HANDLE)
         return(false);
      while(!FileIsEnding(h))
        {
         string ts  = FileReadString(h);
         if(FileIsEnding(h) && ts == "")
            break;
         string imp = FileReadString(h);
         while(!FileIsLineEnding(h) && !FileIsEnding(h))
            FileReadString(h);   // nome della notizia: non serve
         long t = StringToInteger(ts);
         int  i = (int)StringToInteger(imp);
         if(t <= 0)
            continue;
         if(i == (int)CALENDAR_IMPORTANCE_HIGH || (InpNewsMedium && i == (int)CALENDAR_IMPORTANCE_MODERATE))
           {
            ArrayResize(tmp, n + 1, 1000);
            tmp[n++] = (datetime)t;
           }
        }
      FileClose(h);
     }
   else
     {
      MqlCalendarValue values[];
      datetime from = TimeTradeServer() - 86400;
      datetime to   = TimeTradeServer() + 7 * 86400;
      if(CalendarValueHistory(values, from, to, NULL, "USD") <= 0)
         return(false);
      for(int k = 0; k < ArraySize(values); k++)
        {
         MqlCalendarEvent ev;
         if(!CalendarEventById(values[k].event_id, ev))
            continue;
         if(ev.importance == CALENDAR_IMPORTANCE_HIGH || (InpNewsMedium && ev.importance == CALENDAR_IMPORTANCE_MODERATE))
           {
            ArrayResize(tmp, n + 1, 100);
            tmp[n++] = values[k].time;
           }
        }
     }

   ArraySort(tmp);
   ArrayResize(newsTimes, n);
   for(int k = 0; k < n; k++)
      newsTimes[k] = tmp[k];
   newsCount = n;
   newsPtr   = 0;
   if(MQLInfoInteger(MQL_TESTER))
      PrintFormat("Filtro notizie: %d notizie caricate dal file", n);
   else
      PrintFormat("Filtro notizie: %d notizie USD importanti nei prossimi 7 giorni (finestra -%d / +%d min)",
                  n, InpNewsBeforeMin, InpNewsAfterMin);
   return(true);
  }

//+------------------------------------------------------------------+
//| true se 'now' e' dentro la finestra di una notizia.              |
//+------------------------------------------------------------------+
bool NewsBlocked(const datetime now)
  {
   if(newsCount == 0)
      return(false);
   int after  = InpNewsAfterMin * 60;
   int before = InpNewsBeforeMin * 60;
   while(newsPtr < newsCount && newsTimes[newsPtr] + after < now)
      newsPtr++;
   if(newsPtr >= newsCount)
      return(false);
   return(now >= newsTimes[newsPtr] - before);
  }

//+------------------------------------------------------------------+
void CloseAllForNews()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(VIndex((ulong)PositionGetInteger(POSITION_MAGIC)) < 0)
         continue;
      if(trade.PositionClose(ticket))
         newsCloses++;
      else
         PrintFormat("Chiusura per notizia fallita: %d %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
     }
  }
//+------------------------------------------------------------------+

//+------------------------------------------------------------------+
//| PANNELLO INFORMATIVO                                             |
//| Solo lettura: le due versioni affiancate.                        |
//+------------------------------------------------------------------+
#define PNL_PFX   "GTBD_"
#define PNL_W     430
#define PNL_LINEH 15
#define PNL_MAXL  30

//+------------------------------------------------------------------+
void PanelInit()
  {
   panelOn = InpShowPanel && (!MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_VISUAL_MODE))
             && !MQLInfoInteger(MQL_OPTIMIZATION);
   if(!panelOn)
      return;
   string bg = PNL_PFX + "bg";
   if(ObjectFind(0, bg) < 0)
      ObjectCreate(0, bg, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, bg, OBJPROP_CORNER, CORNER_LEFT_UPPER);
   ObjectSetInteger(0, bg, OBJPROP_XDISTANCE, 8);
   ObjectSetInteger(0, bg, OBJPROP_YDISTANCE, 22);
   ObjectSetInteger(0, bg, OBJPROP_XSIZE, PNL_W);
   ObjectSetInteger(0, bg, OBJPROP_YSIZE, 100);
   ObjectSetInteger(0, bg, OBJPROP_BGCOLOR, C'18,18,22');
   ObjectSetInteger(0, bg, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, bg, OBJPROP_COLOR, C'70,70,80');
   ObjectSetInteger(0, bg, OBJPROP_BACK, false);
   ObjectSetInteger(0, bg, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, bg, OBJPROP_HIDDEN, true);
   EventSetTimer(1);
   panelHistDirty = true;
   PanelUpdate();
  }

//+------------------------------------------------------------------+
void PanelDeinit()
  {
   if(!panelOn)
      return;
   EventKillTimer();
   ObjectsDeleteAll(0, PNL_PFX);
   ChartRedraw();
  }

//+------------------------------------------------------------------+
void PanelLine(const int i, const string text, const color clr)
  {
   if(i >= PNL_MAXL)
      return;
   string name = PNL_PFX + "l" + IntegerToString(i);
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, 18);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
     }
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, 30 + i * PNL_LINEH);
   ObjectSetString(0, name, OBJPROP_TEXT, text == "" ? " " : text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
  }

//+------------------------------------------------------------------+
//| Rilegge lo storico (solo deal delle due versioni).               |
//+------------------------------------------------------------------+
void PanelReadHistory()
  {
   datetime now = TimeCurrent();
   datetime dayStart = now - (now % 86400);
   for(int k = 0; k < 2; k++)
     {
      hsTodayNet[k] = 0; hsAllNet[k] = 0; hsGrossWin[k] = 0; hsGrossLoss[k] = 0;
      hsTodayN[k] = 0; hsAllN[k] = 0; hsAllW[k] = 0;
     }
   if(!HistorySelect(0, now + 86400))
      return;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++)
     {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0 || HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol)
         continue;
      int k = VIndex((ulong)HistoryDealGetInteger(d, DEAL_MAGIC));
      if(k < 0)
         continue;
      datetime dt = (datetime)HistoryDealGetInteger(d, DEAL_TIME);
      double p = HistoryDealGetDouble(d, DEAL_PROFIT) + HistoryDealGetDouble(d, DEAL_SWAP) +
                 HistoryDealGetDouble(d, DEAL_COMMISSION);
      hsAllNet[k] += p;
      if(dt >= dayStart) hsTodayNet[k] += p;
      long entry = HistoryDealGetInteger(d, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY)
         continue;
      hsAllN[k]++;
      if(dt >= dayStart) hsTodayN[k]++;
      if(p > 0) { hsAllW[k]++; hsGrossWin[k] += p; }
      else      hsGrossLoss[k] -= p;
     }
   panelHistAt    = now;
   panelHistDirty = false;
  }

//+------------------------------------------------------------------+
string Money(const double v)
  {
   return(StringFormat("%+.2f", v));
  }

string Pct(const int w, const int n)
  {
   return(n > 0 ? StringFormat("%.0f%%", 100.0 * w / n) : "-");
  }

double ReadBuf(const int handle, const int buffer)
  {
   double b[];
   if(handle == INVALID_HANDLE || CopyBuffer(handle, buffer, 1, 1, b) != 1 || b[0] == EMPTY_VALUE)
      return(-1);
   return(b[0]);
  }

//+------------------------------------------------------------------+
void PanelUpdate()
  {
   if(!panelOn)
      return;
   datetime now = TimeCurrent();
   if(panelHistDirty || now - panelHistAt >= 60)
      PanelReadHistory();

   int    i = 0;
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   long   spread = (point > 0) ? (long)MathRound((ask - bid) / point) : 0;
   double atr    = ReadBuf(atrHandle, 0);
   double adx    = ReadBuf(adxHandle, 0);
   double h1f    = ReadBuf(h1FastHandle, 0);
   double h1s    = ReadBuf(h1SlowHandle, 0);
   bool   newsNow = InpNewsFilter && NewsBlocked(now);
   string cur    = AccountInfoString(ACCOUNT_CURRENCY);

   PanelLine(i++, "GoldTitan Breakout Duo 1.00   " + _Symbol, PNL_HEAD);
   string st; color sc;
   bool algoOk = TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && MQLInfoInteger(MQL_TRADE_ALLOWED);
   if(!algoOk)
     { st = "FERMO: Algo Trading disattivato"; sc = PNL_BAD; }
   else if(newsNow && newsPtr < newsCount)
     { st = "NOTIZIA: niente nuove entrate fino alle " + TimeToString(newsTimes[newsPtr] + InpNewsAfterMin * 60, TIME_MINUTES); sc = PNL_WARN; }
   else if(InpMinAtrUsd > 0 && atr >= 0 && atr < InpMinAtrUsd)
     { st = StringFormat("FERMO: volatilita' bassa (ATR %.0f < %.0f)", atr, InpMinAtrUsd); sc = PNL_WARN; }
   else if(InpMaxSpreadPts > 0 && spread >= InpMaxSpreadPts)
     { st = StringFormat("ATTESA: spread alto (%I64d >= %d)", spread, InpMaxSpreadPts); sc = PNL_WARN; }
   else
     { st = "ATTIVO: in attesa di segnali"; sc = PNL_OK; }
   PanelLine(i++, st, sc);
   PanelLine(i++, "Ultimo segnale: " + (lastSignal == "" ? "-" : lastSignal), PNL_TXT);
   PanelLine(i++, "", PNL_TXT);

   PanelLine(i++, StringFormat("%-12s %-20s %-20s", "", "ORIGINALE", "INVERTITA"), PNL_DIM);
   PanelLine(i++, StringFormat("%-12s %-20s %-20s", "Stato", vOn[0] ? "attiva" : "spenta", vOn[1] ? "attiva" : "spenta"), PNL_TXT);
   PanelLine(i++, StringFormat("%-12s %-20s %-20s", "SL / TP",
                               StringFormat("%d / %d", vSl[0], vTp[0]), StringFormat("%d / %d", vSl[1], vTp[1])), PNL_TXT);
   PanelLine(i++, StringFormat("%-12s %-20s %-20s", "Oggi " + cur,
                               StringFormat("%s (%d)", Money(hsTodayNet[0]), hsTodayN[0]),
                               StringFormat("%s (%d)", Money(hsTodayNet[1]), hsTodayN[1])), PNL_TXT);
   PanelLine(i++, StringFormat("%-12s %-20s %-20s", "Totale " + cur, Money(hsAllNet[0]), Money(hsAllNet[1])),
             hsAllNet[1] >= hsAllNet[0] ? PNL_OK : PNL_WARN);
   PanelLine(i++, StringFormat("%-12s %-20s %-20s", "Trade/vinti",
                               StringFormat("%d / %s", hsAllN[0], Pct(hsAllW[0], hsAllN[0])),
                               StringFormat("%d / %s", hsAllN[1], Pct(hsAllW[1], hsAllN[1]))), PNL_TXT);
   PanelLine(i++, StringFormat("%-12s %-20s %-20s", "Profit F.",
                               hsGrossLoss[0] > 0 ? StringFormat("%.2f", hsGrossWin[0] / hsGrossLoss[0]) : "-",
                               hsGrossLoss[1] > 0 ? StringFormat("%.2f", hsGrossWin[1] / hsGrossLoss[1]) : "-"), PNL_TXT);
   PanelLine(i++, StringFormat("%-12s %-20s %-20s", "Stop di fila",
                               StringFormat("%d / %d", consLosses[0], InpPauseLosses),
                               StringFormat("%d / %d", consLosses[1], InpPauseLosses)), PNL_TXT);
   string pz[2];
   for(int k = 0; k < 2; k++)
      pz[k] = (pauseUntil[k] > 0 && now < pauseUntil[k]) ? "pausa " + TimeToString(pauseUntil[k], TIME_MINUTES) : "no";
   PanelLine(i++, StringFormat("%-12s %-20s %-20s", "In pausa", pz[0], pz[1]),
             (pz[0] != "no" || pz[1] != "no") ? PNL_WARN : PNL_TXT);

   string pos[2] = {"nessuna", "nessuna"};
   for(int p = PositionsTotal() - 1; p >= 0; p--)
     {
      ulong tk = PositionGetTicket(p);
      if(tk == 0 || PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      int k = VIndex((ulong)PositionGetInteger(POSITION_MAGIC));
      if(k < 0)
         continue;
      bool buy = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY);
      pos[k] = StringFormat("%s %s", buy ? "BUY" : "SELL",
                            Money(PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP)));
     }
   PanelLine(i++, StringFormat("%-12s %-20s %-20s", "Posizione", pos[0], pos[1]), PNL_TXT);
   PanelLine(i++, StringFormat("Differenza INV - ORIG: %s %s", Money(hsAllNet[1] - hsAllNet[0]), cur),
             hsAllNet[1] >= hsAllNet[0] ? PNL_OK : PNL_WARN);
   PanelLine(i++, "", PNL_TXT);

   PanelLine(i++, "MERCATO", PNL_DIM);
   PanelLine(i++, StringFormat("ATR giornaliero %6.1f $  (min %.0f)  %s", atr, InpMinAtrUsd,
                               atr >= InpMinAtrUsd ? "OK" : "NO"), atr >= InpMinAtrUsd ? PNL_OK : PNL_WARN);
   PanelLine(i++, StringFormat("Spread %I64d points   (max %d)  %s", spread, InpMaxSpreadPts,
                               (InpMaxSpreadPts <= 0 || spread < InpMaxSpreadPts) ? "OK" : "NO"),
             (InpMaxSpreadPts <= 0 || spread < InpMaxSpreadPts) ? PNL_OK : PNL_WARN);
   string trend = (h1f < 0 || h1s < 0) ? "-" : (h1f > h1s ? "RIALZO (valide solo rotture in alto)" : "RIBASSO (valide solo rotture in basso)");
   PanelLine(i++, "Trend H1 " + (InpH1Filter ? trend : "filtro spento"), PNL_TXT);
   PanelLine(i++, StringFormat("ADX M15 %5.1f  (min %.0f)  %s", adx, InpAdxMin,
                               adx >= InpAdxMin ? "OK" : "NO"), adx >= InpAdxMin ? PNL_OK : PNL_TXT);

   string nx = "Notizie: filtro spento";
   if(InpNewsFilter)
     {
      nx = "Prossima notizia USD: nessuna nei prossimi giorni";
      for(int n = newsPtr; n < newsCount; n++)
         if(newsTimes[n] >= now)
           {
            nx = "Prossima notizia USD: " + TimeToString(newsTimes[n], TIME_DATE | TIME_MINUTES);
            break;
           }
     }
   PanelLine(i++, nx, PNL_TXT);
   PanelLine(i++, "Orari = ora del server", PNL_DIM);

   for(int j = i; j < panelLines; j++)
      ObjectDelete(0, PNL_PFX + "l" + IntegerToString(j));
   panelLines = i;
   ObjectSetInteger(0, PNL_PFX + "bg", OBJPROP_YSIZE, 16 + i * PNL_LINEH);
   ChartRedraw();
  }
//+------------------------------------------------------------------+
