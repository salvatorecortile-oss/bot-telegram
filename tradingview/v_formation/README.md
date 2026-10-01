# V-Formation: strategia di backtest per TradingView

Traduzione in regole oggettive della strategia "impulso → ritraccio → V-Formation".
Lo scopo di questa prima versione è **verificare con i dati** se la strategia ha un vantaggio statistico,
e in quali condizioni. Non è pensata per il trading live.

File: [`v_formation_strategy.pine`](v_formation_strategy.pine) (Pine Script v6).

---

## 1. Come caricarla su TradingView

1. Apri un grafico (es. EURUSD, M5 o M15).
2. *Pine Editor* → incolla il contenuto del file `.pine` → **Salva** → **Aggiungi al grafico**.
3. Apri il pannello **Strategy Tester** per i risultati.
4. In *Impostazioni → Proprietà* imposta costi realistici. TradingView non simula lo spread e
   lo **slippage** si applica solo agli ordini market e stop, non ai limite. Il modo più semplice è una
   **commissione "per contratto"** pari a metà spread per ogni esecuzione.
   Esempio EURUSD con spread ~0,8 pips e quantità in unità: 0,00004 per contratto,
   più uno slippage di 2–3 tick per gli stop.

---

## 2. Regole formalizzate (esempio long, lo short è speculare)

### 2.1 Swing
Gli swing sono pivot confermati: un massimo (minimo) è uno swing se è il più alto (basso) di
`N` barre a sinistra e `N` a destra (`Lunghezza pivot`, default 3). Il pivot è noto solo `N`
barre dopo, quindi **niente repaint**. Gli swing formano una sequenza alternata high/low (zigzag).

### 2.2 Schema richiesto sugli ultimi 5 swing

```
            B (fine impulso)
           /\
          /  \      D (rimbalzo dei buyer, "mangiato")
         /    \    /\                    F (massimo gamba destra)
        /      \  /  \                  /
       /        \/    \                /
      /          C     \              /
     A                  \            /
 (inizio impulso)        \          /
                          \        /
                           \      /
                            \    /
                             \  /
                              \/
                              E (fondo della V)
```

| Regola | Condizione |
|---|---|
| Impulso | `B − A ≥ Impulso minimo × ATR` (default 2 ATR) |
| Ritraccio | `(B − E) / (B − A)` tra `Ritraccio minimo` e `Ritraccio massimo` (default 0,50–0,886) |
| Struttura | `D < B` (D è un massimo più basso, dentro il ritraccio) e `E > A` (impulso non invalidato) |
| Gamba sinistra | `E < C`: il rimbalzo C→D viene "mangiato" dai seller (attivabile/disattivabile) |
| Sweep (opzionale) | E rompe il minimo della sessione asiatica e/o del giorno precedente |

### 2.3 Gamba destra e rango
Dopo la conferma di E si segue il massimo successivo **F**. Con `tol = Tolleranza × ATR`:

| Rango | Condizione | Nei video |
|---|---|---|
| **S** | `F > D + tol` | gamba destra più alta della sinistra: la migliore |
| **A** | `D − tol ≤ F ≤ D + tol` | gambe uguali: valida |
| — | `F < D − tol` | gamba destra più corta: **non si entra** |

Se la gamba destra non raggiunge almeno il rango A entro `Barre max per completare la gamba destra`
dal minimo E, il setup viene scartato.

### 2.4 Entry, stop, target
- **Entry**: ordine limite al `50%` della gamba destra E→F (`Entry`, default 0,50). Il livello
  segue F finché la gamba destra fa nuovi massimi. La zona grafica arriva fino al 70%.
- **Stop loss**: `E − buffer × ATR` (default 0,1 ATR).
- **TP1** (default: massimo della gamba destra F, cioè "la prima liquidità") → si chiude il `50%`.
- **TP2** (default: massimo dell'impulso B, cioè la liquidità a sinistra). Se F ha già superato B,
  si usa un R:R fisso (default 2R).
- Dopo il TP1 lo stop va a **break-even** (opzionale).
- Il trade si prende solo se il R:R sul target finale è almeno `R:R minimo` (default 1).

### 2.5 Cancellazione dell'ordine
L'ordine limite (o il setup in formazione) viene cancellato se:
- il prezzo torna oltre E prima del fill (V invalidata);
- passano più di `Validità ordine limite` barre (default 30);
- un filtro di contesto non è più valido (fuori sessione, bias cambiato, limite di trade raggiunto, R:R insufficiente);
- si forma una nuova V valida nella stessa direzione, che sostituisce la precedente.

### 2.6 Filtri di contesto
| Filtro | Default | Dettagli |
|---|---|---|
| Bias TF superiore | Struttura H1 | **Struttura**: diventa long quando una candela HTF chiude sopra l'ultimo swing high, short quando chiude sotto l'ultimo swing low. **EMA**: close HTF sopra/sotto EMA 50. Si usa la candela HTF già chiusa (niente repaint). |
| Sessione | 09:00–17:00 Europe/Rome | Gli ordini si piazzano e restano attivi solo in sessione. La V può formarsi prima (es. fine sessione di Tokyo). |
| Sweep di liquidità | Off | Asia (01:00–08:00 Roma) e/o massimo/minimo del giorno precedente |
| Trade al giorno | max 2 | |

### 2.7 Rischio
- Rango S: `Rischio %` dell'equity (default 1%).
- Rango A: `Rischio % × Moltiplicatore` (default 0,5, quindi metà rischio), come nei video
  ("setup più sporco = rischio ridotto").
- La quantità è calcolata dalla distanza entry–stop, con conversione nella valuta del conto.

---

## 3. Piano di test consigliato

L'obiettivo è capire **quali filtri creano davvero il vantaggio**. Cambia una variabile alla volta.

1. **Base**: tutti i filtri attivi tranne lo sweep, rango minimo A. Simboli EURUSD, GBPUSD,
   USDCHF, EURGBP su M5 e M15, con il massimo storico disponibile.
2. **Rango**: confronta "solo S" con "S + A". Il rango S deve rendere di più, altrimenti la classificazione non serve.
3. **Bias**: Struttura vs EMA vs Off. Se con Off i risultati sono uguali, il bias non sta aiutando.
4. **Sweep**: Off vs Asia/giorno precedente. Meno trade, ma la qualità sale?
5. **Entry**: 0,50 vs 0,618 vs 0,70. Un'entry più profonda dà R:R migliore ma meno fill.
6. **Uscite**: TP1 al 50% + BE vs tutto al TP2 vs R:R fisso 2.
7. **Sessione**: Londra vs Londra+NY vs Off.

Per ogni prova annota: numero di trade, win rate, profit factor, max drawdown, R medio per trade.

**Come leggere i risultati**
- Servono **almeno 100–200 trade** perché i numeri abbiano senso.
- Profit factor stabilmente > 1,3 con costi realistici è un buon segnale. Sotto 1,1 il vantaggio non c'è.
- Il win rate da solo non conta: un 40% con R:R 1:2 è profittevole, un 70% con R:R 1:0,4 no.
- Attenzione all'**overfitting**: se trovi i parametri migliori su un periodo, verificali su un periodo
  diverso (es. ottimizza sul 2023–2024, verifica sul 2025–2026).

---

## 4. Limiti noti della versione 1

- **Zone di interesse** (order block, FVG) non implementate: troppo soggettive per la prima versione.
  Come liquidità si usano solo gli swing, la sessione asiatica e massimo/minimo del giorno precedente.
- Il **bias "ultimi 3–5 giorni"** dei video è approssimato dalla struttura del TF superiore.
- Il filtro **"zona raggiungibile nella sessione"** (distanza rispetto al range medio) non è ancora presente.
- Il backtester di TradingView è ottimista sui fill degli ordini limite (basta toccare il prezzo) e non
  simula lo spread variabile: imposta lo slippage.
- Il **pannello di stato** e gli alert mostrano solo l'ultimo setup per direzione.

---

## 5. Alert (per il futuro collegamento al bot)

La strategia emette alert con `alert()`, in formato JSON:

```json
{"evento":"ordine","simbolo":"EURUSD","tf":"5","lato":"buy","rango":"S",
 "entry":1.08345,"sl":1.08210,"tp1":1.08480,"tp2":1.08610}
```

- `evento = "ordine"`: ordine limite piazzato. I livelli possono ancora spostarsi finché la gamba destra sale.
- `evento = "eseguito"`: ordine eseguito.

Per attivarli: *Crea alert* → Condizione: questa strategia → **"Solo chiamate alert() function"**.
Con un webhook URL, questi messaggi potranno arrivare a un endpoint del bot (`mt5_executor.py`) in una fase successiva.

---

## 6. Prossimi passi

1. Eseguire il piano di test (sezione 3) e annotare i risultati.
2. In base ai dati: rifinire le regole, oppure abbandonare / modificare la strategia.
3. Se regge: versione **indicatore** (solo grafica + alert) da usare in manuale.
4. Poi: webhook TradingView → bot → MT5, prima in **demo**.
