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

- Apre al primo tick della candela (entro `InpMaxEntryDelaySeconds` secondi).
- Chiude `InpCloseSecondsBeforeEnd` secondi prima della fine della stessa candela.
- Il minuto dopo riapre, sempre, finché l'RSI resta nella zona. Quando l'RSI passa
  dall'altra parte del 50, cambia direzione.

Tutti i valori si cambiano dagli input: periodo RSI, livelli 70/50/30, timeframe,
lotto, SL/TP, spread massimo, orari.

## Installazione

1. In MT5: **File → Apri cartella dati → MQL5 → Experts**, copia `RSI_M1_Bot.mq5`.
2. Fai doppio clic sul file per aprirlo in MetaEditor e premi **F7** per compilarlo.
3. Trascinalo su un grafico M1 e abilita **Algo Trading**.
