//+------------------------------------------------------------------+
//|                                                RSI_Alert_M15.mq5 |
//|  EA solo avvisi (non apre operazioni)                            |
//|                                                                  |
//|  A ogni candela chiusa controlla l'RSI e invia una notifica push |
//|  all'app MetaTrader 5 del telefono quando:                       |
//|  - l'RSI chiude a 30 o sotto (prima era sopra 30)                |
//|  - l'RSI chiude a 70 o sopra (prima era sotto 70)                |
//|  Un solo avviso per tocco: il successivo arriva solo dopo che    |
//|  l'RSI e' uscito dalla zona ed e' tornato a toccare il livello.  |
//|                                                                  |
//|  Requisito: Strumenti -> Opzioni -> Notifiche -> abilitare le    |
//|  notifiche push e inserire il MetaQuotes ID del telefono.        |
//+------------------------------------------------------------------+
#property copyright "RSI Alert M15"
#property version   "1.00"

input ENUM_TIMEFRAMES InpTimeframe  = PERIOD_M15; // Timeframe RSI
input int             InpRsiPeriod  = 14;         // Periodo RSI
input double          InpLowLevel   = 30.0;       // Livello basso
input double          InpHighLevel  = 70.0;       // Livello alto
input bool            InpPush       = true;       // Notifica push sul telefono
input bool            InpPopup      = true;       // Avviso a schermo su MT5
input bool            InpTestOnStart= true;       // Invia notifica di prova all'avvio

int      hRsi    = INVALID_HANDLE;
datetime lastBar = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   hRsi = iRSI(_Symbol, InpTimeframe, InpRsiPeriod, PRICE_CLOSE);
   if(hRsi == INVALID_HANDLE)
     {
      Print("Errore creazione RSI: ", GetLastError());
      return(INIT_FAILED);
     }

   if(InpPush && !TerminalInfoInteger(TERMINAL_NOTIFICATIONS_ENABLED))
      Alert("Notifiche push disattivate: Strumenti -> Opzioni -> Notifiche, ",
            "abilitale e inserisci il MetaQuotes ID del telefono.");
   else if(InpPush && InpTestOnStart)
      Notify(StringFormat("RSI Alert attivo su %s %s - livelli %.0f / %.0f",
                          _Symbol, TfName(), InpLowLevel, InpHighLevel));

   // non avvisare per la candela gia' chiusa al momento dell'avvio
   lastBar = iTime(_Symbol, InpTimeframe, 0);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   IndicatorRelease(hRsi);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   //--- controlla solo all'apertura di una nuova candela (= candela precedente chiusa)
   datetime barTime = iTime(_Symbol, InpTimeframe, 0);
   if(barTime == 0 || barTime == lastBar)
      return;

   double rsi[];
   ArraySetAsSeries(rsi, true);
   if(CopyBuffer(hRsi, 0, 1, 2, rsi) != 2)
      return; // dati non pronti, riprova al prossimo tick

   lastBar = barTime;

   double rsiLast = rsi[0]; // candela appena chiusa
   double rsiPrev = rsi[1]; // candela precedente

   if(rsiLast <= InpLowLevel && rsiPrev > InpLowLevel)
      SendRsiAlert(InpLowLevel, rsiLast);
   else if(rsiLast >= InpHighLevel && rsiPrev < InpHighLevel)
      SendRsiAlert(InpHighLevel, rsiLast);
  }

//+------------------------------------------------------------------+
void SendRsiAlert(const double level, const double rsiValue)
  {
   double   closePrice = iClose(_Symbol, InpTimeframe, 1);
   datetime closedBar  = iTime(_Symbol, InpTimeframe, 1);
   string msg = StringFormat("%s %s - RSI(%d) ha toccato %.0f: %.2f - chiusura %s (candela %s)",
                             _Symbol, TfName(), InpRsiPeriod, level, rsiValue,
                             DoubleToString(closePrice, _Digits),
                             TimeToString(closedBar, TIME_DATE | TIME_MINUTES));
   Notify(msg);
  }

//+------------------------------------------------------------------+
void Notify(const string msg)
  {
   Print(msg);
   if(InpPopup)
      Alert(msg);
   if(InpPush && !MQLInfoInteger(MQL_TESTER))
     {
      if(!SendNotification(msg))
         Print("Invio notifica push fallito: ", GetLastError());
     }
  }

//+------------------------------------------------------------------+
string TfName()
  {
   string s = EnumToString(InpTimeframe); // es. "PERIOD_M15"
   StringReplace(s, "PERIOD_", "");
   return(s);
  }
//+------------------------------------------------------------------+
