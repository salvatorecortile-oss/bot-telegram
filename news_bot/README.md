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

- punteggio ≥ `INSTANT_THRESHOLD` (85) → inviata **subito**
- punteggio ≥ `RECAP_THRESHOLD` (60) → entra nel **riepilogo delle 6:00**
- sotto → **scartata**

La stessa notizia riportata da più fonti viene inviata **una volta sola**.
Gossip, sport, articoli "previsioni prezzo", spiegoni ("How…?", "Why…"), trascrizioni,
risultati aziendali e necrologi vengono sempre scartati.
Quante notizie arrivano al massimo:
- **ULTIM'ORA**: al massimo `MAX_ALERTS_PER_DAY` (5) al giorno, inviate appena escono,
  anche a pochi minuti l'una dall'altra. Nelle giornate tranquille anche 0.
  Con `MAX_ALERTS_PER_DAY=0` non c'è nessun limite.
- **Riepilogo delle 6:00**: al massimo `RECAP_MAX_ITEMS` (5) notizie, le più importanti di ieri.

## Traduzione in italiano: DeepL API Free (gratis)

Il bot traduce **solo le notizie che pubblica** (titolo e, se c'è, il breve riassunto).

1. Vai su <https://www.deepl.com/pro-api> e scegli il piano **DeepL API Free** (0 €).
   DeepL chiede una carta solo per verificare l'identità: il piano Free **non addebita nulla**
   e quando finisce la quota mensile si ferma, non passa a pagamento.
2. Nel tuo account DeepL apri **API Keys** e copia la chiave (finisce con `:fx`).
3. Incollala nel `.env`: `DEEPL_API_KEY=...:fx`
4. Prova: `python prova_filtro.py --traduci`

La quota gratuita è di **500.000 caratteri al mese**. Il bot ne usa circa 1.000–3.000 al giorno,
quindi ne resta in abbondanza. Se la chiave manca o la quota finisce, il bot usa
Google Translate gratuito; se non funziona neanche quello, pubblica il titolo in inglese.

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
2. Trova l'ID del canale e mettilo in `NEWS_CHANNEL` nel `.env`
   (per ora il canale di test "news": `-1004400822982`):
   ```bat
   python trova_canale.py
   ```
   Il tuo account deve essere **admin del canale** con il permesso di pubblicare.
3. (Consigliato) Guarda quali notizie passerebbero il filtro, senza pubblicare nulla:
   ```bat
   python prova_filtro.py
   python prova_filtro.py --traduci
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

- Troppe notizie istantanee? Alza `INSTANT_THRESHOLD` (es. 95) o abbassa `MAX_ALERTS_PER_DAY`.
- Troppo poche? Abbassa `INSTANT_THRESHOLD` (es. 75).
- Vuoi silenzio di notte? `QUIET_HOURS=23-6`.
- Orario del buongiorno: `MORNING_HOUR` e `MORNING_MINUTE`.
- Testi del buongiorno e formato dei messaggi: `messages.py`.

## Test senza internet

```bat
python test_news.py
```

## Note

- Il bot notizie usa una sessione Telegram separata (`news_bot.session`), quindi può girare insieme al bot MT5.
- **Non condividere mai** `.env` e `*.session`.
