# RSI Bot (Expert Advisor MT5)

Funziona su qualsiasi simbolo. Serve un conto **hedging**.
Timeframe di lavoro **M15** (`InpTimeframe`: il bot usa questo input, non il timeframe del grafico).

## Ingressi

- **Filtro trend H1:** chiusura dell'ultima candela H1 sopra la EMA 200 → **solo BUY**, sotto → **solo SELL**.
- **BUY** ai livelli RSI **30, 25, 20**; **SELL** ai livelli **70, 75, 80**, confermati a candela M15 chiusa.
- Ogni livello apre una sola operazione per ciclo; lotti 1x, 2x, 3x.

## Novità della versione 7 (di base spente: con i valori di default si comporta come la v6)

| Input | Cosa fa | Valore da provare |
|---|---|---|
| `InpBuyExitRsi` | i BUY si chiudono quando l'RSI sale a questo livello | 60–70 |
| `InpSellExitRsi` | i SELL si chiudono quando l'RSI scende a questo livello | 40–30 |
| `InpUseAtrStop` | stop loss comune a tutto il ciclo, a ATR × moltiplicatore dal primo ingresso, messo sugli ordini | true |
| `InpAtrMultiplier` | distanza dello stop in ATR | 3 |
| `InpRiskPercent` | il lotto viene calcolato per rischiare questa % del capitale se tutti i livelli si aprono e lo stop viene colpito (richiede lo stop ATR) | 1 |

Con il rischio in %, se il capitale è troppo piccolo per rispettarlo anche con il lotto minimo,
il bot **non apre** il ciclo e lo scrive nel Diario.

`InpMaxLossMoney` (stop in denaro per simbolo) resta disponibile; con lo stop ATR puoi metterlo a 0.

## Installazione

1. In MT5: **File → Apri cartella dati → MQL5 → Experts**, copia `RSI_M1_Bot.mq5`.
2. Doppio clic sul file per aprirlo in MetaEditor e premi **F7** per compilarlo.
