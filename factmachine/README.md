# FactMachine bot

Bot che vota l'opzione scelta da te e apre subito l'operazione su
`alpha.factmachine.com`, per entrare a un prezzo migliore prima che il prezzo
salga. Gira sul TUO PC, avviato da te.

Login solo via web (niente app, niente API ufficiale), codice via SMS.
Si usa l'automazione del browser con Playwright.

## Setup (una volta)

```bash
pip install playwright
playwright install chromium
```

## Passo 1 - login (una volta sola)

```bash
python factmachine/login.py
```

Si apre un browser: fai login a mano con numero + codice SMS. Quando sei dentro,
premi INVIO nel terminale. La sessione viene salvata in `browser_profile/`, cosi'
non serve rifare il login/SMS ogni volta.

## Passo 2 - ricognizione (una volta, per capire il sito)

```bash
python factmachine/recon.py
```

Nella finestra fai UN voto + UNA operazione a mano. Lo script registra tutte le
chiamate di rete in `recon_capture.json`. Manda quel file per costruire il
passo 3.

## Passo 3 - il bot

```bash
python factmachine/bot.py
```

Il flusso sono DUE chiamate in sequenza (verificato dalla ricognizione):
1. VOTO:     POST /api/v1/vote/market/cast
             {marketId, optionId, consensusGuess}   <- la rotellina = consensusGuess (la %)
2. ACQUISTO: POST /api/v1/order/transactions/buy
             {marketId, optionId, usdcInD6String, maxPriceD6String, maxSlippageBps}

Quindi: la PERCENTUALE che scrivi e' il voto (consensusGuess); l'IMPORTO e'
l'acquisto. Le opzioni cambiano ad ogni round: si vota con `1` o `2` (o col nome).

Flusso per un round:
1. `load <url|id>`  carica il mercato, mostra le opzioni e i prezzi
2. quando il gruppo dice la risposta:  `buy 1`  (spara subito: 100$ al 77%)
   - oppure pre-arma con `arm 1` e poi premi INVIO al momento giusto

Default modificabili in cima a `bot.py` (`DEFAULT_USDC`, `DEFAULT_PCT`,
`DEFAULT_SLIPPAGE_BPS`) o a runtime (`usdc 100`, `pct 77`, `slippage 10000`).

## Nota

`browser_profile/`, `storage_state.json` e `recon_capture.json` contengono la
tua sessione: sono gia' ignorati da git. Non condividerli.

Controlla i Termini di servizio del sito: alcune piattaforme vietano i bot.
