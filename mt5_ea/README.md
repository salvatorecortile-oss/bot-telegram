# RSI M1 Bot (Expert Advisor MT5)

Gira dentro MetaTrader 5 sul grafico a cui lo attacchi (test su EURUSD M1).
Serve un conto **hedging** (più posizioni aperte sullo stesso simbolo).

## Logica

RSI(28) dell'ultima candela chiusa:

| RSI | Direzione |
|---|---|
| sopra 70 | nessuna nuova operazione (gestisce solo quelle aperte) |
| tra 50 e 70 | **SELL** |
| tra 30 e 50 | **BUY** |
| sotto 30 | nessuna nuova operazione (gestisce solo quelle aperte) |

Tutte le decisioni si prendono sul **primo tick di ogni nuova candela**: chiusure e aperture
avvengono una dopo l'altra nello stesso istante.

1. Apre **0.01**.
2. Candela chiusa in profitto → chiude e riapre subito 0.01.
3. Candela chiusa in perdita → tiene aperta e apre subito un'altra operazione con +0.01
   (0.02, 0.03, 0.04, 0.05). Con più operazioni aperte ne aggiunge una solo se la candela
   appena chiusa è andata contro. Massimo `InpMaxTrades` (5).
4. Le operazioni vecchie si chiudono **in pari** quando il prezzo torna al loro ingresso;
   l'ultima resta aperta.
5. Quando la **somma del ciclo** (chiuse + aperte) arriva a `InpTargetMoney` (+1 €) chiude tutto
   e riparte da 0.01.
6. **Stop**: se la somma arriva a `-InpMaxLossMoney` (−20 €) chiude tutto e riparte.
7. Se l'RSI passa nella zona opposta chiude tutto e apre subito 0.01 nell'altra direzione.

## Installazione

1. In MT5: **File → Apri cartella dati → MQL5 → Experts**, copia `RSI_M1_Bot.mq5`.
2. Doppio clic sul file per aprirlo in MetaEditor e premi **F7** per compilarlo.
3. Togli la versione vecchia dal grafico, trascina quella nuova su EURUSD M1 e abilita **Algo Trading**.
