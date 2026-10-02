# RSI M1 Bot (Expert Advisor MT5)

Test su EURUSD M1. Serve un conto **hedging** (più posizioni aperte sullo stesso simbolo).
Tutti i livelli RSI sono letti sulla **candela chiusa**; chiusure e aperture avvengono sul
primo tick della candela successiva.

## Logica

| RSI(14) | Cosa fa |
|---|---|
| tocca **30** (≤ 30) | apre un ciclo **BUY** da 0.01 |
| tra 30 e 70 | non apre nuovi cicli (gestisce quello aperto) |
| tocca **70** (≥ 70) | apre un ciclo **SELL** da 0.01 |
| tocca **50** | **chiude tutto** il ciclo |

Durante il ciclo:
1. A ogni candela chiusa contro la direzione apre un'altra operazione con +0.01
   (0.02, 0.03, 0.04, …), senza limite di numero.
2. Le operazioni vecchie si chiudono **in pari** quando il prezzo torna al loro ingresso;
   l'ultima resta aperta.
3. Quando resta solo l'ultima, le mette lo **SL a break even** e non aggiunge più operazioni.
4. Quando l'RSI tocca **50** chiude tutto.
5. **Stop**: se la perdita totale del ciclo arriva a `-InpMaxLossMoney` (−20 €) chiude tutto.

## Installazione

1. In MT5: **File → Apri cartella dati → MQL5 → Experts**, copia `RSI_M1_Bot.mq5`.
2. Doppio clic sul file per aprirlo in MetaEditor e premi **F7** per compilarlo.
3. Togli la versione vecchia dal grafico, trascina quella nuova su EURUSD M1 e abilita **Algo Trading**.
