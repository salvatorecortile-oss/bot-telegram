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

---

# Donchian Trend (Expert Advisor MT5, multi-simbolo)

File: `Donchian_Trend.mq5`. **Un solo grafico gestisce tutte le 28 coppie forex** (input `InpSymbols`,
con il suffisso del broker `InpSuffix = -P`). Con `InpSymbols` vuoto lavora solo sul simbolo del grafico.

- **Ingresso:** BUY quando la candela D1 chiude sopra il massimo delle 20 candele precedenti,
  SELL sotto il minimo.
- **Stop iniziale:** ATR(20) × 2,5, messo sull'ordine.
- **Uscita a inseguimento:** lo stop segue il minimo (BUY) / massimo (SELL) delle ultime 10 candele;
  la posizione si chiude quando la candela chiude oltre quel livello. Nessun take profit.
- **Rischio:** 0,5 % del capitale per operazione. Se il lotto calcolato è sotto il minimo (0.01)
  usa il minimo solo se rischia al massimo il 2 % (`InpMaxRiskMinLot`), altrimenti salta.
- **Massimo 6 posizioni aperte insieme** (`InpMaxPositions`).
- Filtro opzionale con la SMA 200 (`InpUseTrendMa`).

---

# BB Gold M1 (Expert Advisor MT5)

File: `BB_Gold_M1.mq5`. Pensato per **XAUUSD M1**, Bande di Bollinger 20 / 2 (SMA).

- **Modalità SELL:** almeno 4 candele verdi di fila e una di esse (dalla 4ª in poi) tocca la banda
  superiore. Finisce quando il prezzo tocca la banda inferiore.
- **Modalità BUY:** almeno 4 candele rosse di fila e una di esse tocca la banda inferiore.
  Finisce quando il prezzo tocca la banda superiore.
- `InpOnePerCandle = false`: **un trade unico** per modalità, aperto alla candela successiva
  e chiuso al tocco della banda opposta.
- `InpOnePerCandle = true`: **un trade a ogni candela**, aperto all'apertura e chiuso alla chiusura,
  finché il prezzo tocca la banda opposta.
- Dopo la fine di una modalità serve una nuova serie di candele + tocco.
- Uscita a tempo (`InpMaxMinutes`, default 30): se la modalità dura più di N minuti senza toccare
  la banda opposta, chiude e la modalità finisce (0 = spenta).
- Lotto 0.01; stop di emergenza opzionale (`InpEmergencySl`, in dollari di prezzo, 0 = nessuno).
