# RSI M1 Reversal (Expert Advisor MT5)

È un bot separato dal copier Telegram e gira direttamente dentro MetaTrader 5.
Funziona su qualsiasi grafico a cui lo attacchi (EURUSD, GBPUSD, XAUUSD, ...).

## Logica

| RSI(28) sull'ultima candela chiusa | Cosa può fare il bot |
|---|---|
| sopra 70 | niente |
| tra 50 e 70 | solo **BUY**: dopo 4 candele **rosse** consecutive apre un BUY |
| tra 30 e 50 | solo **SELL**: dopo 4 candele **verdi/blu** consecutive apre un SELL |
| sotto 30 | niente |

- L'ingresso avviene al primo tick della 5ª candela (entro `InpMaxEntryDelaySeconds`).
- L'uscita avviene `InpCloseSecondsBeforeEnd` secondi prima che la stessa candela finisca,
  quindi il trade dura meno di un minuto su M1. C'è un timer, così chiude anche se non arrivano tick.
- Le candele doji (apertura = chiusura) interrompono la serie.
- Con `InpOnlyFirstOfStreak = true` si fa un solo trade per serie: se la 5ª candela
  è di nuovo dello stesso colore, alla 6ª non rientra.
- Ogni grafico gestisce solo le proprie posizioni (stesso simbolo e stesso `InpMagic`).

Tutti i valori si cambiano dagli input: periodo RSI, livelli 70/50/30, numero di candele,
timeframe, lotto, SL di emergenza, spread massimo e orari.

## Installazione

1. In MT5: **File → Apri cartella dati → MQL5 → Experts**, copia `RSI_M1_Reversal.mq5`.
2. Aprilo con MetaEditor e compila (F7).
3. Trascinalo su un grafico M1 e abilita **Algo Trading**.

## Consigli

- Su M1 lo spread pesa molto: lascia il filtro `InpMaxSpreadPoints` attivo
  (20 points = 2 pips su EURUSD a 5 decimali; per l'oro va alzato).
- Prima di usarlo sul conto reale provalo nello Strategy Tester con
  "Ogni tick basato su tick reali" e poi su un conto demo.
- `InpStreakCandles = 4` dà meno segnali ma più selezionati; con 3 ne dà di più ma è più rumoroso.
