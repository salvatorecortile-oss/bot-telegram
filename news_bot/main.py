"""
BOT NOTIZIE - avvio:  python main.py

Cosa fa:
1. ogni POLL_SECONDS legge le fonti di World Monitor (oro, macro, geopolitica, mondo);
2. se esce una notizia davvero importante la pubblica SUBITO nel canale, tradotta in italiano;
3. ogni mattina alle 6:00 pubblica il buongiorno con il riepilogo delle notizie più importanti;
4. la sera non invia nessun riepilogo.

Nessun collegamento a MT5, nessun trade.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from telethon import TelegramClient, errors

import config
import messages
from news_engine import NewsEngine, fetch_all
from storage import Storage
from translator import to_italian

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("news_bot")

TZ = ZoneInfo(config.TIMEZONE)


def in_quiet_hours(now):
    """True se siamo nelle ore di silenzio (QUIET_HOURS, es. "23-6")."""
    if not config.QUIET_HOURS:
        return False
    try:
        start, end = (int(x) for x in config.QUIET_HOURS.split("-"))
    except ValueError:
        return False
    hour = now.hour
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end


class NewsBot:
    def __init__(self):
        self.storage = Storage()
        self.engine = NewsEngine(self.storage)
        self.client = TelegramClient(
            config.SESSION_NAME, config.API_ID, config.API_HASH,
            connection_retries=5, retry_delay=2, auto_reconnect=True,
        )
        self.channel = None

    async def send(self, text):
        if config.DRY_RUN:
            log.info("[DRY_RUN] Messaggio non inviato:\n%s", text)
            return
        for part in messages.split_message(text):
            while True:
                try:
                    await self.client.send_message(
                        self.channel, part, parse_mode="html", link_preview=False
                    )
                    break
                except errors.FloodWaitError as exc:
                    log.warning("Telegram chiede di aspettare %s secondi", exc.seconds)
                    await asyncio.sleep(exc.seconds + 1)

    # ---------- notizie istantanee ----------
    async def poll_news(self):
        first_run = self.storage.get_meta("initialized") is None
        items = await asyncio.to_thread(fetch_all)
        touched = self.engine.ingest(items)
        log.info("Lette %d notizie, %d nuove storie/aggiornamenti", len(items), len(touched))

        if first_run:
            # Primo avvio in assoluto: non inviamo tutto l'arretrato,
            # le notizie restano solo per il riepilogo del mattino.
            for sid in touched:
                self.storage.mark_sent(sid, 0)
            self.storage.set_meta("initialized", "1")
            log.info("Primo avvio: notizie attuali memorizzate senza inviarle.")
            return

        now_local = datetime.now(TZ)
        if in_quiet_hours(now_local):
            return

        # Controlliamo tutte le storie recenti non ancora inviate: così una notizia
        # rimandata per il limite orario, o confermata più tardi da altre fonti,
        # può partire al giro successivo.
        since = time.time() - config.MAX_INSTANT_AGE_HOURS * 3600
        recent_ids = [s["id"] for s in self.storage.stories_since(since)]
        midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        for info in self.engine.instant_candidates(recent_ids):
            if self.storage.alerts_sent_since(midnight) >= config.MAX_ALERTS_PER_DAY:
                log.info("Già inviate %d ultim'ora oggi: le altre vanno nel riepilogo di domani.",
                         config.MAX_ALERTS_PER_DAY)
                break
            gap = config.MIN_MINUTES_BETWEEN_ALERTS * 60
            if self.storage.alerts_sent_since(time.time() - gap) > 0:
                log.info("Ultima ultim'ora inviata da meno di %d minuti, attendo.",
                         config.MIN_MINUTES_BETWEEN_ALERTS)
                break
            title_it = await asyncio.to_thread(to_italian, info["title"])
            summary_it = await asyncio.to_thread(to_italian, info["summary"]) if info["summary"] else ""
            text = messages.format_alert(
                info["level"], info["category"], title_it, summary_it,
                info["source"], info["num_sources"], info["link"],
            )
            await self.send(text)
            self.storage.mark_sent(info["story_id"], time.time())
            log.info("Inviata (score %d): %s", info["score"], info["title"])

    async def news_loop(self):
        while True:
            try:
                await self.poll_news()
                self.storage.cleanup()
            except Exception:
                log.exception("Errore durante il controllo delle notizie")
            await asyncio.sleep(config.POLL_SECONDS)

    # ---------- buongiorno delle 6:00 ----------
    async def send_morning(self, now_local):
        recap = []
        for info in self.engine.recap():
            recap.append({
                "category": info["category"],
                "title_it": await asyncio.to_thread(to_italian, info["title"]),
                "source": info["source"],
                "link": info["link"],
            })
        await self.send(messages.format_morning(now_local, recap))
        log.info("Buongiorno inviato con %d notizie nel riepilogo.", len(recap))

    async def morning_loop(self):
        while True:
            try:
                now_local = datetime.now(TZ)
                start = now_local.replace(
                    hour=config.MORNING_HOUR, minute=config.MORNING_MINUTE,
                    second=0, microsecond=0,
                )
                today = now_local.date().isoformat()
                # Finestra di 1 ora: se il PC era spento alle 6:00 ma riparte
                # entro le 7:00, il buongiorno viene comunque inviato una volta.
                if (start <= now_local < start + timedelta(hours=1)
                        and self.storage.get_meta("last_morning") != today):
                    await self.send_morning(now_local)
                    self.storage.set_meta("last_morning", today)
            except Exception:
                log.exception("Errore durante l'invio del buongiorno")
            await asyncio.sleep(30)

    # ---------- avvio ----------
    async def run(self):
        if not config.API_ID or not config.API_HASH:
            raise SystemExit("Configura TELEGRAM_API_ID e TELEGRAM_API_HASH nel file .env")
        if not config.NEWS_CHANNEL:
            raise SystemExit("Configura NEWS_CHANNEL nel file .env (usa trova_canale.py)")

        await self.client.connect()
        if not await self.client.is_user_authorized():
            raise SystemExit("Account non collegato: esegui prima  python login.py")

        await self.client.get_dialogs()  # carica i canali per trovare l'ID
        self.channel = await self.client.get_entity(config.NEWS_CHANNEL)
        log.info("Bot notizie avviato. Canale: %s", getattr(self.channel, "title", config.NEWS_CHANNEL))
        if config.DRY_RUN:
            log.info("Modalità DRY_RUN attiva: nessun messaggio verrà pubblicato.")
        if config.DEEPL_API_KEY:
            log.info("Traduzione: DeepL API Free.")
        else:
            log.info("DEEPL_API_KEY non impostata: traduzione con Google Translate gratuito.")

        await asyncio.gather(self.news_loop(), self.morning_loop())


if __name__ == "__main__":
    try:
        asyncio.run(NewsBot().run())
    except KeyboardInterrupt:
        log.info("Bot fermato.")
