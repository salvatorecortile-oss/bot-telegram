# Bot Notizie — canale Community

Bot **solo notizie**: niente MT5, niente trade.
Pubblica nel canale Community, con il tuo account Telegram (Telethon, **non** BotFather):

- ☀️ **ogni mattina alle 6:00** il messaggio di buongiorno con il riepilogo delle notizie più importanti delle ultime 24 ore;
- 🚨 **subito**, durante il giorno, ogni notizia davvero importante, tradotta in italiano;
- 🌙 la sera **nessun** riepilogo.

## Da dove arrivano le notizie

Il bot legge direttamente le **stesse fonti RSS di [World Monitor](https://www.worldmonitor.app)**,
prese dal suo codice open source: Reuters, AP, BBC, Al Jazeera, CNBC, Financial Times,
Federal Reserve, IAEA, OMS, Kitco, più le ricerche di Google News su oro, banche centrali,
inflazione, dazi, dollaro e petrolio.
Le fonti sono in `feeds.py`, divise in 4 categorie: 🥇 Oro · 🏦 Macro · 🌍 Geopolitica · 📰 Mondo.

## Come sceglie le notizie importanti

World Monitor ha un filtro a parole chiave che dà a ogni titolo un livello
(critical / high / medium / low / info). Il bot usa lo stesso filtro, convertito in Python (`classifier.py`),
con in più le parole chiave su oro e macro (Fed, tassi, CPI, payrolls, record dell'oro...).

Ogni notizia riceve un **punteggio**:

| Elemento | Punti |
|---|---|
| Livello: critical / high / medium / low | 100 / 60 / 35 / 15 |
| Fonte: tier 1 (Reuters, AP, Fed) / tier 2 (BBC, CNBC...) / tier 3 / tier 4 | +20 / +5 / 0 / −10 |
| Ogni fonte in più che riporta la stessa notizia | +10 (max +30) |
| Parla di oro | +10 |

- punteggio ≥ `INSTANT_THRESHOLD` (75) → inviata **subito**
- punteggio ≥ `RECAP_THRESHOLD` (60) → entra nel **riepilogo delle 6:00**
- sotto → **scartata**

La stessa notizia riportata da più fonti viene inviata **una volta sola**.
Gossip, sport, articoli "previsioni prezzo" e simili vengono sempre scartati.
Anti-spam: al massimo `MAX_ALERTS_PER_HOUR` notizie istantanee all'ora.

## Installazione (Windows)

Dentro la cartella `news_bot`:

```bat
pip install -r requirements.txt
copy .env.example .env
```

Apri `.env` e inserisci `TELEGRAM_API_ID` e `TELEGRAM_API_HASH` (gli stessi del bot MT5).

1. Collega il tuo account (una sola volta):
   ```bat
   python login.py
   ```
2. Trova l'ID del canale Community e mettilo in `NEWS_CHANNEL` nel `.env`:
   ```bat
   python trova_canale.py
   ```
   Il tuo account deve essere **admin del canale** con il permesso di pubblicare.
3. (Consigliato) Guarda quali notizie passerebbero il filtro, senza pubblicare nulla:
   ```bat
   python prova_filtro.py
   ```
4. Avvia il bot:
   ```bat
   python main.py
   ```

Per le prove puoi mettere `DRY_RUN=true` nel `.env`: il bot scrive i messaggi solo nel log
(`logs/news_bot.log`) senza pubblicarli.

Al **primo avvio** il bot memorizza le notizie già uscite senza inviarle (per non riempire il canale):
da quel momento invia solo quelle nuove.

## Regolazioni utili (`.env`)

- Troppe notizie istantanee? Alza `INSTANT_THRESHOLD` (es. 85) o abbassa `MAX_ALERTS_PER_HOUR`.
- Troppo poche? Abbassa `INSTANT_THRESHOLD` (es. 70).
- Vuoi silenzio di notte? `QUIET_HOURS=23-6`.
- Orario del buongiorno: `MORNING_HOUR` e `MORNING_MINUTE`.
- Testi del buongiorno e formato dei messaggi: `messages.py`.

## Test senza internet

```bat
python test_news.py
```

## Note

- La traduzione usa Google Translate gratuito (nessuna chiave). Se non funziona, il bot pubblica il titolo originale in inglese.
- Il bot notizie usa una sessione Telegram separata (`news_bot.session`), quindi può girare insieme al bot MT5.
- **Non condividere mai** `.env` e `*.session`.
