# RSI M1 Bot (Expert Advisor MT5)

Funziona su qualsiasi simbolo (test su EURUSD M1). Serve un conto **hedging**.
L'RSI(14) è letto sulle **candele chiuse**; aperture e chiusure avvengono sul primo tick
della candela successiva.

## Ingressi

| Ciclo | Livelli | Quando apre |
|---|---|---|
| BUY | 30, 20, 10, 5 | quando l'RSI scende sotto il livello partendo da sopra |
| SELL | 70, 80, 90, 95 | quando l'RSI sale sopra il livello partendo da sotto |

- Ogni livello apre **una sola operazione per ciclo**: se l'RSI balla attorno al livello non riapre.
- Se in una candela l'RSI attraversa più livelli, apre un'operazione **per ogni livello**.
- I livelli tornano validi solo quando il ciclo è chiuso del tutto.
- Lotti: 0.01, poi +0.01 a ogni nuova operazione del ciclo (massimo 0.01+0.02+0.03+0.04).

## Gestione

- L'**ultima** operazione aperta resta aperta fino al tocco del **50**.
- Le operazioni aperte prima si chiudono **in pari** quando il prezzo torna al loro ingresso.
- RSI tocca **50** → chiude tutto.
- **Stop per simbolo**: se la perdita del ciclo su quel simbolo arriva a −20 € chiude
  le operazioni di quel simbolo. Gli altri grafici non vengono toccati.

## Installazione

1. In MT5: **File → Apri cartella dati → MQL5 → Experts**, copia `RSI_M1_Bot.mq5`.
2. Doppio clic sul file per aprirlo in MetaEditor e premi **F7** per compilarlo.
3. Togli la versione vecchia dal grafico, trascina quella nuova sul grafico M1 e abilita **Algo Trading**.
