# RSI_XAUUSD_Trailing (Expert Advisor MT5)

EA indipendente dal bot Telegram, da usare in MetaTrader 5 (live o Strategy Tester).

## Regole
- Simbolo: XAUUSD (quello del grafico/tester), lotto 0.01
- RSI 14 periodi su M1, valutato alla chiusura della candela
- RSI sale a 60 → SELL, RSI scende a 25 → BUY (modalità `SIGNAL_CROSS_IN`)
- Nessun limite di slippage massimo: gli ordini vengono sempre eseguiti
- Slippage simulato nel tester: 15 $ per lotto scalati dal saldo a ogni apertura (0.01 lotti = 0.15 $)
- Opera solo se lo spread è inferiore a 50 points
- SL 20 pips, nessun TP, una sola posizione alla volta
- Trailing: ogni 20 pips di profitto lo SL sale di 20 pips (+20 → pareggio, +40 → SL +20, +60 → SL +40, ... senza limite) — fisso, non modificabile dai parametri
- 1 pip = 10 points (con XAUUSD a 2 decimali: 1 pip = 0.10 $, 20 pips = 2 $)

## Installazione
1. MT5 → File → Apri cartella dati → `MQL5/Experts/`
2. Copia `RSI_XAUUSD_Trailing.mq5`, aprilo in MetaEditor e premi **Compila** (F7)

## Test nello Strategy Tester (Ctrl+R)
- Expert: `RSI_XAUUSD_Trailing`, Simbolo: `XAUUSD`, Periodo: `M1`
- Modello: **Ogni tick basato su tick reali** (serve per un trailing realistico)
- Tutti i parametri sono modificabili nella scheda *Parametri*.
