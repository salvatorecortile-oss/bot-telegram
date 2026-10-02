# RSI M1 Bot (Expert Advisor MT5)

Gira dentro MetaTrader 5 su qualsiasi grafico a cui lo attacchi (EURUSD, GBPUSD, XAUUSD, ...).

## Logica

A ogni nuova candela (ogni minuto su M1) guarda l'RSI(28) dell'ultima candela chiusa:

| RSI | Trade |
|---|---|
| sopra 70 | niente |
| tra 50 e 70 | **BUY** |
| tra 30 e 50 | **SELL** |
| sotto 30 | niente |

- Tutto avviene sul **primo tick della nuova candela**: chiude la posizione precedente
  e subito dopo apre la nuova, allo stesso prezzo di mercato.
- Se la direzione resta la stessa e `InpKeepSameDirection = true` (default) la posizione
  resta aperta: è come chiudere e riaprire allo stesso prezzo, ma senza pagare di nuovo lo spread.
  Con `false` chiude e riapre a ogni candela.
- Quando l'RSI passa dall'altra parte del 50 chiude e apre subito nella direzione opposta.
  Se l'RSI esce sopra 70 o sotto 30 chiude e resta fuori.

Tutti i valori si cambiano dagli input: periodo RSI, livelli 70/50/30, timeframe,
lotto, SL/TP, spread massimo, orari.

## Installazione

1. In MT5: **File → Apri cartella dati → MQL5 → Experts**, copia `RSI_M1_Bot.mq5`.
2. Fai doppio clic sul file per aprirlo in MetaEditor e premi **F7** per compilarlo.
3. Trascinalo su un grafico M1 e abilita **Algo Trading**.
