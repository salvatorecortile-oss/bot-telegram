# RSI Bot (Expert Advisor MT5)

Funziona su qualsiasi simbolo. Serve un conto **hedging**.
Timeframe di lavoro **M15** (`InpTimeframe`: il bot usa questo input, non il timeframe del grafico).

## Ingressi

- **Filtro trend H1:** se la chiusura dell'ultima candela H1 è sopra la EMA 200 H1 fa **solo BUY**,
  se è sotto fa **solo SELL** (`InpUseTrendFilter`).
- **BUY** ai livelli RSI **30, 25, 20**; **SELL** ai livelli **70, 75, 80**.
- Il tocco è confermato a **candela M15 chiusa**: la candela deve chiudere con l'RSI ancora oltre il
  livello (la candela prima era dall'altra parte). L'ordine si apre al primo tick della candela successiva.
- Ogni livello apre **una sola operazione per ciclo**; lotti **0.01, 0.02, 0.03**.
- Le aggiunte (25/20, 75/80) si aprono solo se il trend H1 è ancora nella direzione del ciclo.

## Chiusure

- RSI tocca **50** (in tempo reale) → chiude **tutto**.
- `InpCloseOldAtBE = true`: le operazioni vecchie si chiudono in pari al ritorno sul loro ingresso.
- **Stop per simbolo** (`InpMaxLossMoney`, 50): chiude tutto il ciclo di quel simbolo se la perdita
  arriva a −50. Nel tester mettilo a 0 per vedere il drawdown reale della strategia.

## Installazione

1. In MT5: **File → Apri cartella dati → MQL5 → Experts**, copia `RSI_M1_Bot.mq5`.
2. Doppio clic sul file per aprirlo in MetaEditor e premi **F7** per compilarlo.
