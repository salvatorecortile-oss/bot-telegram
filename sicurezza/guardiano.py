"""
BOT GUARDIANO: captcha per chi chiede di entrare nella sala elite / nel canale.

Funziona SOLO con i link d'invito che hanno "Richiedi approvazione admin"
attivo (vedi README). Chi usa quel link non entra subito: manda una richiesta.

1. Il bot scrive in privato a chi ha chiesto di entrare: "Premi la MELA".
2. Pulsante giusto       -> richiesta APPROVATA, la persona entra.
3. Sbagliato troppe volte o tempo scaduto -> richiesta RIFIUTATA
   (puo' riprovare cliccando di nuovo il link).
4. Se esiste benvenuto.txt, manda in privato il tuo messaggio di benvenuto.
5. Ti avvisa in privato (ADMIN_USER_ID) con il punteggio di sospetto.

Il bot deve essere ADMIN della chat con il permesso "Invita utenti / Aggiungi iscritti".

Avvio:  python guardiano.py
"""
import asyncio
import html
import logging
import time

from telethon import Button, TelegramClient, events, functions, types, utils
from telethon.errors import RPCError

import analisi
import benvenuto
import captcha
from config import (
    ADMIN_USER_ID, API_HASH, API_ID, BASE_DIR, BOT_SESSION_NAME, BOT_TOKEN,
    CAPTCHA_TENTATIVI, CAPTCHA_TIMEOUT_SECONDS, CHATS, ID_ACCOUNT_RECENTE,
    LOG_FILE, NOMI_PROTETTI,
)


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%d/%m/%Y %H:%M:%S")
    for handler in (logging.StreamHandler(), logging.FileHandler(LOG_FILE, encoding="utf-8")):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logging.getLogger("telethon").setLevel(logging.WARNING)
    return logger


logger = setup_logging()

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise RuntimeError("Manca TELEGRAM_API_ID, TELEGRAM_API_HASH o BOT_TOKEN nel file .env della cartella sicurezza.")

bot = TelegramClient(str(BASE_DIR / BOT_SESSION_NAME), API_ID, API_HASH,
                     connection_retries=5, retry_delay=1, auto_reconnect=True)

# Messaggio di benvenuto personale (vedi benvenuto.esempio.txt)
BENVENUTO_FILE = BASE_DIR / "benvenuto.txt"

# (user_id, chat_id) -> captcha.Sfida
SFIDE = {}


def nome_utente(user):
    nome = " ".join(x for x in (getattr(user, "first_name", ""), getattr(user, "last_name", "")) if x) or "(senza nome)"
    if getattr(user, "username", None):
        nome += f" @{user.username}"
    return nome


async def avvisa_admin(testo):
    if not ADMIN_USER_ID:
        return
    try:
        await bot.send_message(ADMIN_USER_ID, testo, parse_mode="html", link_preview=False)
    except Exception as exc:
        logger.warning("Non riesco ad avvisare l'admin (gli hai scritto /start?): %s", exc)


async def decidi(sfida, user_id, approva):
    """Approva o rifiuta la richiesta di entrata su Telegram."""
    try:
        await bot(functions.messages.HideChatJoinRequestRequest(
            peer=sfida.dati["peer"], user_id=sfida.dati["input_user"], approved=approva))
        return True
    except RPCError as exc:
        # Es. HIDE_REQUESTER_MISSING: richiesta gia' gestita a mano da te.
        logger.warning("Richiesta di %s non gestita (%s): forse gia' approvata/rifiutata a mano", user_id, exc)
        return False


def pulsanti(sfida, chat_id):
    etichette = captcha.etichette_pulsanti(sfida)
    tasti = [Button.inline(e, data=f"cap|{chat_id}|{i}".encode()) for i, e in enumerate(etichette)]
    return [tasti[:3], tasti[3:]]


@bot.on(events.Raw(types.UpdateBotChatInviteRequester))
async def nuova_richiesta(update):
    chat_id = utils.get_peer_id(update.peer)
    if CHATS and chat_id not in CHATS:
        return
    user_id = update.user_id
    try:
        user = await bot.get_entity(user_id)
        input_user = await bot.get_input_entity(user_id)
        peer = await bot.get_input_entity(update.peer)
        chat = await bot.get_entity(update.peer)
    except Exception as exc:
        logger.error("Richiesta di %s in %s: non riesco a leggere i dati (%s)", user_id, chat_id, exc)
        return

    titolo = getattr(chat, "title", str(chat_id))
    info = analisi.info_da_utente(user)
    val = analisi.valuta(info, NOMI_PROTETTI, ID_ACCOUNT_RECENTE)

    sfida = captcha.nuova_sfida(time.time(), CAPTCHA_TIMEOUT_SECONDS, CAPTCHA_TENTATIVI)
    sfida.dati.update(peer=peer, input_user=input_user, titolo=titolo, nome=nome_utente(user),
                      nome_breve=getattr(user, "first_name", "") or "",
                      punteggio=val.punteggio, livello=val.livello, motivi=val.motivi)
    SFIDE[(user_id, chat_id)] = sfida

    try:
        msg = await bot.send_message(user_id, captcha.testo_domanda(sfida, html.escape(titolo), CAPTCHA_TIMEOUT_SECONDS),
                                     buttons=pulsanti(sfida, chat_id), parse_mode="html")
        sfida.dati["msg_id"] = msg.id
    except Exception as exc:
        logger.error("Non riesco a scrivere a %s: %s (la richiesta resta in attesa, decidi tu a mano)", user_id, exc)
        SFIDE.pop((user_id, chat_id), None)
        await avvisa_admin(f"⚠️ Richiesta di <b>{html.escape(nome_utente(user))}</b> in {html.escape(titolo)}: "
                           f"non riesco a mandargli il captcha. Decidi tu a mano.")
        return

    logger.info("Richiesta: %s (ID %s) -> %s | sospetto %s (%s)", nome_utente(user), user_id, titolo,
                val.punteggio, val.livello)


def riassunto(sfida, user_id, esito):
    d = sfida.dati
    motivi = "\n".join(f"• {html.escape(m)}" for m in d["motivi"]) or "• nessuno"
    return (f"{esito}\n<b>{html.escape(d['nome'])}</b> (ID <code>{user_id}</code>)\n"
            f"Chat: {html.escape(d['titolo'])}\n"
            f"Sospetto: {d['punteggio']}/100 ({d['livello']})\n{motivi}\n"
            f"<a href=\"tg://user?id={user_id}\">Apri profilo</a>")


@bot.on(events.CallbackQuery(pattern=rb"cap\|"))
async def risposta(event):
    try:
        _, chat_s, idx_s = event.data.decode().split("|")
        chat_id, indice = int(chat_s), int(idx_s)
    except ValueError:
        return
    user_id = event.sender_id
    sfida = SFIDE.get((user_id, chat_id))
    if not sfida:
        await event.answer("Richiesta scaduta. Usa di nuovo il link per entrare.", alert=True)
        return

    esito = captcha.rispondi(sfida, indice, time.time())
    if esito == "sbagliato":
        await event.answer(f"❌ Sbagliato, riprova ({sfida.tentativi} tentativi rimasti)", alert=True)
        return

    SFIDE.pop((user_id, chat_id), None)
    if esito == "ok":
        await event.edit(f"✅ Fatto! Benvenuto in <b>{html.escape(sfida.dati['titolo'])}</b>.\n✅ Done, welcome!",
                         parse_mode="html")
        # Il messaggio di benvenuto parte PRIMA dell'approvazione: finche' la
        # richiesta e' aperta Telegram permette sempre al bot di scrivere.
        testo = benvenuto.testo_benvenuto(BENVENUTO_FILE, sfida.dati.get("nome_breve", ""), sfida.dati["titolo"])
        if testo:
            try:
                await bot.send_message(user_id, testo, link_preview=False)
            except Exception as exc:
                logger.warning("Messaggio di benvenuto non inviato a %s: %s", user_id, exc)
        await decidi(sfida, user_id, approva=True)
        logger.info("APPROVATO: %s (ID %s) in %s", sfida.dati["nome"], user_id, sfida.dati["titolo"])
        await avvisa_admin(riassunto(sfida, user_id, "✅ <b>Entrato</b> (captcha superato)"))
    else:  # fallito o scaduto
        await decidi(sfida, user_id, approva=False)
        await event.edit("❌ Captcha non superato. Puoi riprovare usando di nuovo il link d'invito.\n"
                         "❌ Captcha failed. You can try again with the invite link.")
        logger.info("RIFIUTATO (%s): %s (ID %s) in %s", esito, sfida.dati["nome"], user_id, sfida.dati["titolo"])
        await avvisa_admin(riassunto(sfida, user_id, f"⛔ <b>Rifiutato</b> (captcha {esito})"))


@bot.on(events.NewMessage(pattern=r"^/start", func=lambda e: e.is_private))
async def start(event):
    if event.sender_id == ADMIN_USER_ID:
        await event.respond(f"🛡 Guardiano attivo. Richieste in attesa di captcha: {len(SFIDE)}.\n"
                            "Ti avviso qui per ogni persona che entra o viene rifiutata.")
    else:
        await event.respond("🛡 Sono il bot di sicurezza. Per entrare usa il link d'invito.")


async def controlla_scadute():
    while True:
        await asyncio.sleep(15)
        for chiave in captcha.scadute(SFIDE, time.time()):
            sfida = SFIDE.pop(chiave, None)
            if not sfida:
                continue
            user_id, _ = chiave
            await decidi(sfida, user_id, approva=False)
            try:
                await bot.edit_message(user_id, sfida.dati.get("msg_id"),
                                       "⌛ Tempo scaduto. Puoi riprovare usando di nuovo il link d'invito.\n"
                                       "⌛ Time is up. You can try again with the invite link.")
            except Exception:
                pass
            logger.info("RIFIUTATO (tempo scaduto): %s (ID %s)", sfida.dati["nome"], user_id)
            await avvisa_admin(riassunto(sfida, user_id, "⌛ <b>Rifiutato</b> (non ha risposto in tempo)"))


async def main():
    await bot.start(bot_token=BOT_TOKEN)
    me = await bot.get_me()
    logger.info("Guardiano avviato come @%s. Chat controllate: %s", me.username, CHATS or "tutte quelle dove e' admin")
    await avvisa_admin("🛡 Guardiano avviato.")
    controllo = asyncio.create_task(controlla_scadute())
    try:
        await bot.run_until_disconnected()
    finally:
        controllo.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Guardiano fermato.")
