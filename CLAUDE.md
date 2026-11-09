# Istruzioni per Claude — repository bot-telegram

Leggi questo file all'inizio di ogni sessione. Contiene il contesto del progetto e le regole di lavoro.

## Chi sono e come lavoro

- Parlo **italiano**: rispondi sempre in italiano, in modo semplice e pratico.
- Non sono un programmatore esperto: spiega i passaggi uno alla volta e dammi i comandi pronti da copiare.
- I bot girano sul **mio PC Windows** (CMD, `python main.py`), con MetaTrader 5 aperto. Le sessioni di Claude Code girano in cloud: qui MT5 e Telegram veri **non ci sono**, quindi si testa solo con i test simulati.

## I progetti in questo repository

| Cartella | Cosa fa |
|---|---|
| radice (`main.py`, `signal_parser.py`, `bltech_parser.py`, `mt5_executor.py`, `telegram_sender.py`, `database.py`) | **TelegramMT5Bot1**: copia i messaggi da canali sorgente (anche BL Tech Pro) al mio canale e apre gli ordini XAUUSD su MT5. Regole in `README.md`. |
| `goldempire/` | **Bot Gold Empire** (indipendente: suo `.env`, sua sessione, suo DB `data/goldempire.db`, suo MAGIC NUMBER). Legge il canale "Gold empire signals room", apre/gestisce le operazioni su MT5 e pubblica nel mio canale. Testi dei messaggi in `messages.py`, report in `reports.py`. Regole in `goldempire/README.md`. |
| `ea/` | Expert Advisor MT5 in MQL5 (`ScalperM1_XAU`, `StraddleM1`) e i loro file `.set`. |
| `factmachine/` | Bot per alpha.factmachine.com (Playwright): vota e apre l'operazione. |
| `contenuti/` | **Video social YardFX** (@yard.fx): guida di stile `GUIDA_STILE_YARDFX.md` e kit di montaggio `yardfx_video/` (leggi il suo `README.md` prima di montare un video del calendario). |

## Regole importanti

- **Mai** committare o mostrare credenziali: `.env`, file `*.session`, API hash Telegram, password MT5. Solo `.env.example` con valori finti.
- È codice che apre **ordini con soldi veri**: ogni modifica alla logica di trading va spiegata chiaramente (cosa cambia nel comportamento del bot) prima di considerarla finita.
- Una modifica a un bot non deve rompere gli altri: i bot sono separati, non condividere file tra loro.
- Quando cambia un comportamento visibile, aggiorna anche il README del bot interessato.

## Test (senza Telegram né MT5)

Bot principale (dalla radice):

```
python test_parser.py
python test_database.py
python test_mt5_logic.py
```

Gold Empire (dalla cartella `goldempire`):

```
python tests/test_parser.py
python tests/test_flow.py
python tests/test_reports.py
```

Lancia i test del bot che hai modificato prima di fare commit.

## Commit

- Messaggi in italiano, con il nome del bot davanti, es.: `Gold Empire: chiude le operazioni opposte del SIGNAL 5`, `FactMachine: ...`.
