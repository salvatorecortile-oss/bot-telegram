# TRS Zones – indicatore MT5

Indicatore che traduce in **regole oggettive** i concetti del PDF "TRS – il vero metodo":
zone di reazione, zone forti, rifiuti, rimbalzi e breakout.

L'obiettivo non è "dare segnali da seguire alla cieca", ma **vedere su anni di storico
se questi setup funzionano davvero**, prima di costruirci sopra un EA.

---

## 1. Installazione

1. In MetaTrader 5: **File → Apri cartella dati**.
2. Entra in `MQL5/Indicators/` e copia lì `TRS_Zones.mq5`.
3. Apri **MetaEditor** (F4), apri il file e premi **Compila** (F7).
   Deve dire `0 errors`. Se ci sono errori, copiameli.
4. Torna su MT5, nel **Navigatore** (Ctrl+N) → Indicatori → trascina `TRS_Zones` sul grafico.
5. Grafico consigliato: **XAUUSD, M15 o M5** (quelli del PDF).

---

## 2. Cosa vedi sul grafico

| Elemento | Colore (default) | Concetto del PDF |
|---|---|---|
| Rettangolo giallo scuro | zona di reazione | "imposta massimo / imposta minimo" |
| Rettangolo verde | zona forte di supporto | "zona forte sell-buy" |
| Rettangolo rosso | zona forte di resistenza | "zona forte buy-sell" |
| Rettangolo blu / viola | zona di rifiuto (supp. / resist.) | "rifiuto sulle ombre" |
| Rettangolo grigio | zona già rotta o scaduta | storico |
| Freccia verde ↑ / rossa ↓ | segnale BUY / SELL | ingresso |

Sotto/sopra ogni freccia c'è una sigla:

- **RZ** = breakout di una **zona di reazione** (pag. 7–8 del PDF)
- **BO** = **breakout** di una zona forte o di rifiuto, con chiusura oltre la zona (pag. 11 e 17)
- **RB** = **rimbalzo**: il prezzo torna sulla zona e la rifiuta (pag. 12, 15, 16)

Passando il mouse su una zona vedi: tipo, stato (attiva/rotta/scaduta), prezzi e
numero di tocchi. Passando sulla sigla vedi il nome completo del segnale.

---

## 3. Le regole usate (cosa fa esattamente)

Tutto è misurato in **ATR** (volatilità media), così le regole valgono sia
su M5 che su M15 e su strumenti diversi.

### Zona di reazione
- Prima c'è un **movimento** di almeno `2.5 × ATR` nelle ultime 5 candele.
- Poi `3` candele con i **corpi compressi** (altezza tra `0.2` e `1 × ATR`).
- Massimo e minimo della zona = estremi dei **corpi** (come nelle slide, le ombre possono uscire).
- **Segnale**: la prima candela che **chiude** fuori dal range **nella direzione del movimento** (come a pag. 8 del PDF).
- Se entro 30 candele non rompe, la zona scade.

### Zona forte
- Uno **swing** (minimo/massimo più basso/alto delle 5 candele a sinistra e a destra).
- Dopo lo swing il prezzo si allontana di almeno `2.5 × ATR` ("inversione forte").
- La zona va dall'**estremo** (ombra) ai **corpi** delle candele dello swing.

### Zona di rifiuto
- Una candela con **ombra ≥ 3 volte il corpo** e ≥ `1.2 × ATR`.
- La zona è l'ombra stessa.

### Cosa succede quando il prezzo torna su una zona forte/rifiuto
- **Chiude oltre la zona** → **BO** (breakout), la zona muore.
- **Tocca la zona e chiude fuori dalla parte giusta** con candela di rifiuto → **RB** (rimbalzo).
  Solo il **primo** rimbalzo per zona viene segnalato.
- La zona diventa "testabile" solo dopo 3 candele dalla sua nascita.

### Filtri sui segnali
- Almeno **8 candele** tra un segnale e il successivo.
- Segnali solo tra le **8 e le 20 (ora server)**: fuori orario l'oro fa molto rumore.

> Le zone forti si disegnano a partire dallo swing, ma diventano attive **solo dopo**
> che lo swing è confermato (3 candele dopo). I segnali non usano mai candele future:
> **una freccia apparsa non sparisce più**.

---

## 4. Come usarlo (il metodo di lavoro)

### Fase A – Verifica visiva (ora)
1. Metti l'indicatore su XAUUSD M15.
2. Scorri **indietro nel grafico** di qualche settimana.
3. Per ogni freccia chiediti:
   - il prezzo è andato a favore di almeno 1× la dimensione dello stop prima di andare contro?
   - dove avresti messo lo stop? (lato opposto della zona è il candidato naturale)
4. Annota a parte, per **tipo** di segnale (RZ / BO / RB), quanti vincono e quanti perdono.
5. Prova a cambiare i parametri (vedi sotto) e guarda se le zone somigliano
   di più a quelle del PDF.

### Fase B – Backtest automatico (prossimo passo)
L'indicatore espone i segnali in 3 buffer, leggibili da un EA con `iCustom`:

| Buffer | Contenuto |
|---|---|
| 0 | prezzo della freccia BUY (o vuoto) |
| 1 | prezzo della freccia SELL (o vuoto) |
| 2 | codice: `±1` breakout zona reazione, `±2` breakout zona, `±3` rimbalzo (segno + = buy, − = sell) |

Il prossimo step è un EA per lo **Strategy Tester** che entra su questi segnali con
stop e target definiti e misura win rate, profit factor e drawdown.

---

## 5. Parametri principali

| Parametro | Default | Effetto se lo **aumenti** |
|---|---|---|
| `InpLookback` | 1500 | analizza più storico (più lento) |
| `InpRangeBars` | 3 | range di reazione più lunghi, meno zone |
| `InpRangeMaxATR` | 1.0 | accetta range più larghi, più zone |
| `InpImpulseATR` | 2.5 | richiede un movimento più forte prima del range, meno zone |
| `InpBreakOnClose` | true | `false` = segnale appena l'ombra esce (più aggressivo, più falsi) |
| `InpOnlyWithTrend` | true | `false` = segnala anche i breakout contro il movimento (più segnali) |
| `InpSwingBars` | 5 | swing più "importanti", meno zone forti |
| `InpStrongATR` | 2.5 | inversioni più forti, meno zone forti |
| `InpWickBodyRatio` | 3.0 | rifiuti più netti, meno zone di rifiuto |
| `InpMaxBounces` | 1 | più rimbalzi segnalati sulla stessa zona |
| `InpShowDeadZones` | false | `true` = mostra anche le zone già rotte (utile per studiare lo storico) |
| `InpCooldownBars` | 8 | meno segnali ravvicinati |
| `InpStartHour` / `InpEndHour` | 8 / 20 | fascia oraria dei segnali (ora del server del broker); uguali = sempre |
| `InpAlertPush` | false | `true` = notifica sul telefono (configura l'ID MetaQuotes in Strumenti → Opzioni → Notifiche) |

Se il grafico è troppo pieno: disattiva un tipo di zona alla volta
(`InpShowReaction`, `InpShowStrong`, `InpShowRejection`) e studiali separatamente.

---

## 6. EA di test: `TRS_Zones_EA.mq5`

Contiene **le stesse regole** dell'indicatore e apre i trade da solo, per misurare
nello **Strategy Tester** quale setup funziona.

1. Copia `TRS_Zones_EA.mq5` in `MQL5/Experts/` e compilalo (F7).
2. In MT5: **Visualizza → Tester strategia** (Ctrl+R).
3. Expert: `TRS_Zones_EA` · Simbolo: `XAUUSD` · Periodo: `M15` · Date: almeno 1–2 anni.
4. Modellazione: **"Ogni tick basato su tick reali"** (la più fedele).
5. Avvia. A fine test, nella scheda **Diario**, trovi le statistiche separate per setup:

```
RZ breakout zona reazione | trade: … | vinti: …% | netto: … | profit factor: …
BO breakout zona forte    | …
RB rimbalzo su zona       | …
```

Regole dei trade:
- **Ingresso** all'apertura della candela dopo il segnale.
- **Stop** oltre il lato opposto della zona (+ `0.1 × ATR` di margine), minimo `0.3 × ATR`;
  se lo stop supera `2 × ATR` il trade viene saltato.
- **Take profit** a `1.5 R` (`InpRR`).
- **Rischio** `0.5%` del saldo per trade (`InpRiskPercent`) o lotti fissi (`InpFixedLots`).
- Max 3 trade e max 2 perdite al giorno, una posizione alla volta, orario 8–20.

Come leggere i risultati: un setup interessa solo se ha **profit factor > 1.3**
su **almeno 100 trade**. Puoi disattivare i singoli setup (`InpTradeRZ`, `InpTradeBO`,
`InpTradeRB`) per testarli uno alla volta.
