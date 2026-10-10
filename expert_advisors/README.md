# IndexORB_Long — EA MT5 per indici USA

Expert Advisor **intraday, solo long** per CFD su indici americani (su FPG: USTEC, US500, US30).
Nessuna posizione overnight. Nessun segnale Telegram (verrà aggiunto più avanti).

## La strategia: Opening Range Breakout (ORB)

1. Alle **09:30 New York** apre la borsa cash. L'EA registra il massimo e il minimo
   dei primi **15 minuti** (l'"opening range").
2. Se i filtri sono ok, piazza un **buy stop** poco sopra il massimo del range.
3. **Stop loss** sul minimo del range. **Take profit** a 2R (2 volte il rischio).
4. Se l'ordine non scatta entro le **12:00 NY** viene cancellato.
5. Alle **15:45 NY** chiude tutto, sempre: nessuna posizione la notte.
6. Massimo **1 trade al giorno** per simbolo.

### Filtri (servono a saltare i giorni peggiori)

| Filtro | Cosa fa |
|---|---|
| Trend D1 | Opera solo se la chiusura di ieri è sopra la SMA 50 giornaliera |
| Range rialzista | Opera solo se il range dei 15 minuti chiude sopra la sua apertura |
| Ampiezza range | Salta se il range è troppo piccolo (< 5% ATR D1) o troppo grande (> 40% ATR D1) |
| Spread | Opzionale: salta se lo spread supera un massimo |
| Giorni | Puoi escludere singoli giorni della settimana |
| Festività USA | Salta le festività della borsa USA e le mezze giornate (`InpSkipUSHolidays`, da mettere a `false` sugli indici europei) |

### Gestione del rischio

- **Rischio per trade:** 1% dell'equity. Il lotto si calcola dalla distanza dello stop.
- **Conti piccoli:** se anche il lotto minimo rischia più del 2%, il trade viene **saltato**
  invece di rischiare troppo.
- **Stop giornaliero:** -2% nella giornata, poi si chiude tutto fino a domani.
- **Kill switch:** con un drawdown del **12% dal picco** di equity l'EA si ferma da solo.
  Per riattivarlo imposta `InpResetPeak = true` una volta.

## Simboli FPG e impostazioni

| Simbolo FPG | Indice | Priorità | `InpSessionOpen` | `InpLastEntryTime` | `InpCloseTime` |
|---|---|---|---|---|---|
| `USTEC` | Nasdaq 100 | 1 — il più adatto | 16:30 | 19:00 | 22:45 |
| `US500` | S&P 500 | 2 | 16:30 | 19:00 | 22:45 |
| `DE40` | DAX 40 | 3 — da testare a parte | 10:00 | 13:00 | 18:15 |
| `US30` | Dow Jones | 4 | 16:30 | 19:00 | 22:45 |
| `EU50` | Euro Stoxx 50 | 5 — da testare a parte | 10:00 | 13:00 | 18:15 |
| `UK100` | FTSE 100 | 6 — poco adatto (poco volatile) | 10:00 | 13:00 | 18:15 |

Gli orari europei presuppongono un server GMT+2/GMT+3 allineato all'ora legale USA.
Nelle 2–3 settimane l'anno in cui Europa e USA cambiano ora in date diverse (marzo e fine
ottobre/inizio novembre) l'apertura europea cade alle **11:00** del server: in quelle settimane
il range verrebbe calcolato un'ora prima, quindi conviene non operare sugli indici europei.

Per usare più simboli insieme: un grafico per simbolo, ognuno con l'EA. Ricorda che gli
indici sono molto correlati: tre EA attivi possono voler dire tre trade persi nello stesso giorno.

## ⚠️ Prima cosa da verificare: l'orario del server FPG

Gli orari negli input sono in **ora del server**, non in ora italiana.
Il default `16:30` presuppone un server GMT+2/GMT+3 allineato all'ora legale americana,
dove le 09:30 di New York corrispondono sempre alle 16:30 del server.

**Come verificarlo:** apri il grafico M1 di NAS100 su un giorno qualsiasi e cerca la candela
dove volume e volatilità esplodono di colpo. Quella è l'apertura di New York.
Se non è alle 16:30, sposta di conseguenza tutti e tre gli orari (`InpSessionOpen`,
`InpLastEntryTime`, `InpCloseTime`).

Festività USA e giorni a orario ridotto (venerdì dopo il Thanksgiving, vigilia di Natale,
3 luglio) vengono saltati in automatico (`InpSkipUSHolidays = true`): in quei giorni il CFD
chiude prima delle 22:45 del server e la posizione resterebbe aperta fino al giorno dopo.

## Installazione

1. In MT5: **File → Apri cartella dati → MQL5 → Experts**. Copia lì `IndexORB_Long.mq5`.
2. Aprilo con MetaEditor (F4) e compila (F7). Non devono esserci errori.
3. Trascina l'EA sul grafico del simbolo (il timeframe non conta, i dati li legge da M1 e D1).
4. Attiva **Algo Trading**.

## Backtest nello Strategy Tester

- **Modello:** "Ogni tick basato su tick reali" (oppure "OHLC 1 minuto" per i test veloci).
- **Periodo:** almeno dal 2019 a oggi. Deve includere il crollo del 2020 e il ribasso del 2022.
- **Deposito:** usa il capitale reale che pensi di usare (100 / 500 / 1000), così vedi
  quanti trade vengono saltati per il lotto minimo.
- **Simboli:** testa NAS100 per primo (è il più adatto all'ORB), poi US500 e US30.

### Cosa guardare nei risultati

| Metrica | Obiettivo minimo |
|---|---|
| Numero di trade | > 150 |
| Profit factor | > 1.3 |
| Drawdown relativo su equity | < 15% |
| Recovery factor | > 3 |
| Andamento | Curva in crescita in quasi tutti gli anni, non solo in uno |

### Ottimizzazione (senza esagerare)

Ottimizza **pochi parametri alla volta**, con criterio **"Custom max"**: l'EA restituisce il
recovery factor e scarta le combinazioni con meno di 50 trade.

| Parametro | Range da provare |
|---|---|
| `InpORMinutes` | 5, 15, 30 |
| `InpTP_R` | 0 (solo fine giornata), 1.5, 2, 3 |
| `InpSLFrac` | 0.5, 0.75, 1.0 |
| `InpBreakEven_R` | 0, 1 |
| `InpUseTrendFilter` / `InpRequireBullOR` | true / false |

**Regola d'oro:** ottimizza su 2019–2023 e poi verifica **senza toccare nulla** su
2024–oggi (forward test). Se i risultati crollano fuori campione, la combinazione è
sovra-ottimizzata. Scegli zone di parametri stabili, non il singolo picco migliore.

## Note sui conti piccoli (100–1000)

Con 100 il vincolo vero è il **lotto minimo** del broker. Esempio: su NAS100 con 0.01 lotti
a 0.01 $/punto e uno stop di 120 punti il rischio è 1.20 $, cioè l'1.2% su 100 $: va bene.
Su US500 o US30 il lotto minimo potrebbe valere di più e molti trade verranno saltati.
Il log ("Lotto minimo ... trade saltato") te lo dice. Con 100 $ parti da NAS100.

## Percorso consigliato

1. Backtest su NAS100 con i parametri di default.
2. Ottimizzazione leggera e verifica fuori campione.
3. **2–3 mesi su conto demo FPG**, confrontando i risultati con il backtest dello stesso periodo.
4. Solo dopo: conto reale con il capitale minimo.
5. Poi: notifiche Telegram di ingresso e uscita, sfruttando il bot già presente in questo repo.
