# ScalperM1_XAU — EA MT5

Scalper sui tick per XAUUSD, costruito replicando la logica ricavata dagli screenshot analizzati:

| Regola | Valore di default |
|---|---|
| Take profit | 50 punti fissi (0,50 $) |
| Stop loss | 50 punti + spread corrente (≈ 57–60 punti) |
| Posizioni | una alla volta |
| Ingresso | il bid si è mosso di ≥ 30 punti negli ultimi 5000 ms ed è vicino al massimo/minimo della finestra → entra nella stessa direzione |
| Uscita anticipata | dopo +20 punti, se ritraccia di 20 punti dal massimo; oppure dopo 60 s |
| Filtro spread | massimo 18 punti |
| Filtro orario | 9–21 ora server |

## Installazione

1. In MT5: *File → Apri cartella dati → MQL5 → Experts*. Copia qui `ScalperM1_XAU.mq5`.
2. Apri MetaEditor, apri il file e premi **Compila** (F7).
3. Trascina l'EA sul grafico XAUUSD (il timeframe non conta, lavora sui tick; usa M1 per vederlo).
4. Attiva **Algo Trading**, poi premi **Start** sul pannello.

## Pannello

- **Start** — trading continuo.
- **Start One** — fa un solo trade e poi si ferma.
- **Finish** — nessun nuovo ingresso, si ferma quando il trade aperto si chiude.
- **Stop+Close** — si ferma subito e chiude la posizione aperta.

Mostra stato, spread (attuale/min/media/max), trade e win rate del giorno, P/L netto (commissioni incluse) e ultimo segnale.

## Test (obbligatorio prima del reale)

Strategy Tester → modello **"Every tick based on real ticks"** (gli altri modelli falsano completamente uno scalper di questo tipo). Nel tester l'EA parte da solo in RUNNING.

Range consigliati per l'ottimizzazione:

| Parametro | Range |
|---|---|
| InpMomentumPoints | 15 – 60, passo 5 |
| InpMomentumMs | 2000 – 15000, passo 1000 |
| InpReverseExitPoints | 0 – 40, passo 5 |
| InpMaxHoldSec | 0 – 180, passo 15 |
| InpStartHour / InpEndHour | sessioni Londra / New York |

Ottimizza su un periodo e verifica su un periodo diverso (forward), altrimenti i risultati sono sovra-adattati.

**Pareggio:** con vincita ≈ 50 punti, perdita ≈ 57 punti e commissione ≈ 7 $/lotto, il win rate minimo per non perdere è circa il **60%**. Controlla questo valore nel report prima di tutto il resto.

Poi prova almeno 2–4 settimane su un conto reale con 0,01 lotti: lo slippage reale su trade di pochi secondi può cambiare completamente i risultati.
