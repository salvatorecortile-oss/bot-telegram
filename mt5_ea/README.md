# RSI_XAUUSD_Trailing (Expert Advisor MT5)

EA indipendente dal bot Telegram, da usare in MetaTrader 5 (live o Strategy Tester).

## Regole
- Simbolo: XAUUSD (quello del grafico/tester), lotto 0.01
- RSI 14 periodi su M5, valutato alla chiusura della candela
- RSI sale a 70 → SELL, RSI scende a 30 → BUY (modalità `SIGNAL_CROSS_IN`)
- SL 100 pips, nessun TP, una sola posizione alla volta
- Trailing: ogni 20 pips di profitto lo SL sale di 20 pips (+20 → pareggio, +40 → SL +20, +60 → SL +40, ... senza limite)
- 1 pip = 10 points (con XAUUSD a 2 decimali: 1 pip = 0.10 $, 100 pips = 10 $)

## Installazione
1. MT5 → File → Apri cartella dati → `MQL5/Experts/`
2. Copia `RSI_XAUUSD_Trailing.mq5`, aprilo in MetaEditor e premi **Compila** (F7)

## Test nello Strategy Tester (Ctrl+R)
- Expert: `RSI_XAUUSD_Trailing`, Simbolo: `XAUUSD`, Periodo: `M5`
- Modello: **Ogni tick basato su tick reali** (serve per un trailing realistico)
- Tutti i parametri sono modificabili nella scheda *Parametri*.
