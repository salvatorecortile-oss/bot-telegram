# RSI M1 Bot (Expert Advisor MT5)

Funziona su qualsiasi simbolo (test su EURUSD M1). Serve un conto **hedging**.
Lavora **in tempo reale** sull'RSI(14) della candela in corso: apre e chiude nell'istante
del tocco, senza aspettare la chiusura della candela.

## Ingressi

| Ciclo | Livelli | Quando apre |
|---|---|---|
| BUY | 30, 25, 20, 15, 10, 5 | appena l'RSI scende sotto il livello partendo da sopra |
| SELL | 70, 75, 80, 85, 90, 95 | appena l'RSI sale sopra il livello partendo da sotto |

- Ogni livello apre **una sola operazione per ciclo**: se l'RSI balla attorno al livello non riapre.
- Se l'RSI attraversa più livelli insieme, apre un'operazione **per ogni livello**.
- I livelli tornano validi solo quando il ciclo è chiuso del tutto.
- Lotti: 0.01, poi +0.01 a ogni nuova operazione del ciclo (massimo 0.01 + … + 0.06 = 0.21).

## Chiusure

- RSI tocca **50** → chiude **tutto** subito.
- `InpCloseOldAtBE = true`: le operazioni vecchie si chiudono in pari quando il prezzo torna
  al loro ingresso e solo l'ultima aspetta il 50. Di default è `false`.
- **Stop per simbolo** (`InpMaxLossMoney`, 30 €): se la perdita del ciclo su quel simbolo
  arriva a −30 € chiude le operazioni di quel simbolo. Gli altri grafici non vengono toccati.

## Installazione

1. In MT5: **File → Apri cartella dati → MQL5 → Experts**, copia `RSI_M1_Bot.mq5`.
2. Doppio clic sul file per aprirlo in MetaEditor e premi **F7** per compilarlo.
3. Togli la versione vecchia dal grafico, trascina quella nuova sul grafico M1 e abilita **Algo Trading**.
