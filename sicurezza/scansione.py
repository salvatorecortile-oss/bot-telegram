"""
REPORT ISCRITTI SOSPETTI (sala elite + canale)

Legge gli iscritti delle chat in TELEGRAM_CHATS (serve essere admin), da' a
ognuno un punteggio di sospetto e salva il report in report/ (file CSV che
si apre con Excel).

NON elimina e NON blocca nessuno: decidi tu dopo aver guardato il report.
Chi ha una chat privata con te o e' nei tuoi contatti e' segnato CONOSCIUTO.

Avvio:
    python scansione.py                 (lettura normale)
    python scansione.py --approfondita  (cerca anche per lettera: piu' lento,
                                         serve se il canale e' grande)
"""
import argparse
import asyncio
import string
from datetime import datetime

from telethon import functions
from telethon.errors import ChatAdminRequiredError

import analisi
import report
from config import CHATS, ID_ACCOUNT_RECENTE, NOMI_PROTETTI, REPORT_DIR
from telegram_client import client

TIPI_ADMIN = {"ChannelParticipantAdmin", "ChannelParticipantCreator",
              "ChatParticipantAdmin", "ChatParticipantCreator"}


async def utenti_con_chat_privata():
    """ID delle persone con cui hai una chat privata (gente con cui hai parlato)."""
    ids = set()
    async for dialog in client.iter_dialogs():
        if dialog.is_user:
            ids.add(dialog.id)
    return ids


async def totale_iscritti(entity):
    try:
        full = await client(functions.channels.GetFullChannelRequest(entity))
        return full.full_chat.participants_count
    except Exception:
        return None


async def leggi_iscritti(entity, approfondita):
    trovati = {}

    async def leggi(search=""):
        async for u in client.iter_participants(entity, search=search):
            trovati.setdefault(u.id, u)

    await leggi()
    if approfondita:
        for lettera in string.ascii_lowercase + string.digits:
            await leggi(lettera)
            print(f"  ricerca '{lettera}': {len(trovati)} iscritti trovati", end="\r")
            await asyncio.sleep(1)
        print()
    return trovati


async def main(approfondita):
    if not CHATS:
        print("Manca TELEGRAM_CHATS nel file .env (usa: python get_chats.py)")
        return

    await client.start()
    me = await client.get_me()
    nomi_protetti = list(NOMI_PROTETTI)
    mio_nome = " ".join(x for x in (me.first_name, me.last_name) if x)
    if mio_nome:
        nomi_protetti.append(mio_nome)

    print("Leggo le tue chat private (per riconoscere chi conosci)...")
    con_chat = await utenti_con_chat_privata()
    print(f"  {len(con_chat)} chat private trovate")

    utenti = {}  # id -> {"user", "chat": [titoli], "entrato": data}
    for chat_id in CHATS:
        try:
            entity = await client.get_entity(chat_id)
        except Exception as exc:
            print(f"Chat {chat_id} non trovata: {exc}")
            continue
        titolo = getattr(entity, "title", str(chat_id))
        print(f"\nLeggo gli iscritti di: {titolo}")
        try:
            iscritti = await leggi_iscritti(entity, approfondita)
        except ChatAdminRequiredError:
            print("  Devi essere ADMIN di questa chat per vedere gli iscritti.")
            continue

        totale = await totale_iscritti(entity)
        if totale:
            print(f"  Letti {len(iscritti)} iscritti su {totale}")
            if len(iscritti) < totale * 0.9 and not approfondita:
                print("  Telegram ne ha dati solo una parte: riprova con  python scansione.py --approfondita")
        else:
            print(f"  Letti {len(iscritti)} iscritti")

        for u in iscritti.values():
            partecipante = getattr(u, "participant", None)
            if u.id == me.id or type(partecipante).__name__ in TIPI_ADMIN:
                continue  # tu e gli admin non entrano nel report
            voce = utenti.setdefault(u.id, {"user": u, "chat": [], "entrato": None})
            voce["chat"].append(titolo)
            data = getattr(partecipante, "date", None)
            if data and (voce["entrato"] is None or data < voce["entrato"]):
                voce["entrato"] = data

    await client.disconnect()

    righe = []
    for uid, voce in utenti.items():
        info = analisi.info_da_utente(voce["user"], chat_con_me=uid in con_chat)
        val = analisi.valuta(info, nomi_protetti, ID_ACCOUNT_RECENTE)
        righe.append({"info": info, "valutazione": val, "chat": voce["chat"], "entrato": voce["entrato"]})

    if not righe:
        print("\nNessun iscritto letto.")
        return

    percorso = REPORT_DIR / f"report_{datetime.now():%Y%m%d_%H%M}.csv"
    report.scrivi_csv(righe, percorso)
    print()
    print(report.riepilogo(righe))
    print(f"\nReport completo salvato in:\n  {percorso}")
    print("Aprilo con Excel. Il bot NON ha eliminato nessuno.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Report iscritti sospetti")
    parser.add_argument("--approfondita", action="store_true",
                        help="cerca anche lettera per lettera (canali grandi)")
    args = parser.parse_args()
    asyncio.run(main(args.approfondita))
