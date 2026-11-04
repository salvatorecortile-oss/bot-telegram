"""Test del punteggio di sospetto. Avvio: python tests/test_analisi.py"""
import os
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analisi  # noqa: E402


def info(**kw):
    base = {"id": 123456789, "nome": "Mario", "cognome": "Rossi", "username": "mariorossi",
            "foto": True, "bot": False, "eliminato": False, "scam": False, "fake": False,
            "limitato": False, "premium": False, "verificato": False, "contatto": False,
            "chat_con_me": False, "ultimo_accesso": "recente"}
    base.update(kw)
    return base


# Persona normale: foto, username, attiva -> BASSO, nessun motivo
v = analisi.valuta(info())
assert v.livello == "BASSO" and v.punteggio == 0 and v.motivi == [], v

# Account eliminato e bot -> ALTO
assert analisi.valuta(info(eliminato=True, nome="", cognome="", username="", foto=False)).livello == "ALTO"
assert analisi.valuta(info(bot=True)).livello == "ALTO"
assert analisi.valuta(info(scam=True)).livello == "ALTO"

# Profilo vuoto + account recente + mai online -> ALTO
v = analisi.valuta(info(id=7_500_000_000, username="", foto=False, ultimo_accesso="tempo_fa"),
                   id_account_recente=7_000_000_000)
assert v.livello == "ALTO", v
assert any("recente" in m for m in v.motivi)

# Solo senza foto -> BASSO (non basta per essere sospetto)
assert analisi.valuta(info(foto=False)).livello == "BASSO"

# Profilo vuoto ma attivo -> MEDIO
assert analisi.valuta(info(username="", foto=False)).livello == "MEDIO"

# Inattivo da tempo ma ha una chat con me -> CONOSCIUTO (non va eliminato per sbaglio)
v = analisi.valuta(info(username="", foto=False, ultimo_accesso="tempo_fa", chat_con_me=True))
assert v.livello == "CONOSCIUTO" and v.conosciuto, v
assert v.punteggio >= 30  # il punteggio resta visibile
v = analisi.valuta(info(username="", foto=False, contatto=True))
assert v.livello == "CONOSCIUTO"

# Account eliminato resta ALTO anche se c'era una chat
assert analisi.valuta(info(eliminato=True, chat_con_me=True)).livello == "ALTO"

# Imitazione del nome protetto
v = analisi.valuta(info(nome="Sala Elite", cognome="Support", username="salaelite_help"), ["Sala Elite"])
assert v.livello == "ALTO", v
assert any("imitazione" in m for m in v.motivi)
assert any("support" in m for m in v.motivi)
# Nome protetto troppo corto -> ignorato
assert not any("imitazione" in m for m in analisi.valuta(info(nome="Leo"), ["Leo"]).motivi)

# Link nel nome
assert any("Link" in m for m in analisi.valuta(info(nome="Guadagna su t.me/xyz")).motivi)

# Parole spam: parola intera, non pezzi di parola ("Bettina" non e' spam)
assert analisi.valuta(info(nome="Bettina", cognome="Invernizzi")).motivi == []
assert any("crypto" in m for m in analisi.valuta(info(nome="Crypto", cognome="King")).motivi)

# Nome solo emoji
assert any("emoji" in m for m in analisi.valuta(info(nome="🔥🔥", cognome="")).motivi)

# Username con tanti numeri
assert any("numeri" in m for m in analisi.valuta(info(username="user8473625")).motivi)

# Premium e verificato abbassano il punteggio
assert analisi.valuta(info(foto=False, username="", premium=True)).livello == "BASSO"

# Punteggio sempre tra 0 e 100
v = analisi.valuta(info(bot=True, scam=True, fake=True, foto=False, username=""))
assert v.punteggio == 100
assert analisi.valuta(info(verificato=True)).punteggio == 0

# --- Ultimo accesso da status Telethon (simulato con classi dal nome giusto) ---
adesso = datetime(2026, 11, 4, tzinfo=timezone.utc)


def status(nome, **kw):
    return type(nome, (), {})() if not kw else type(nome, (), kw)()


assert analisi.ultimo_accesso_da_status(None) == "tempo_fa"
assert analisi.ultimo_accesso_da_status(status("UserStatusOnline")) == "online"
assert analisi.ultimo_accesso_da_status(status("UserStatusRecently")) == "recente"
assert analisi.ultimo_accesso_da_status(status("UserStatusLastWeek")) == "settimana"
assert analisi.ultimo_accesso_da_status(status("UserStatusLastMonth")) == "mese"
assert analisi.ultimo_accesso_da_status(status("UserStatusEmpty")) == "tempo_fa"
for giorni, atteso in ((1, "recente"), (5, "settimana"), (20, "mese"), (90, "tempo_fa")):
    st = status("UserStatusOffline", was_online=adesso - timedelta(days=giorni))
    assert analisi.ultimo_accesso_da_status(st, adesso) == atteso, (giorni, atteso)

# --- Dati da un utente Telethon (simulato) ---
utente = SimpleNamespace(id=42, first_name="Anna", last_name=None, username=None,
                         usernames=[SimpleNamespace(username="anna_x", active=True)],
                         photo=object(), bot=False, deleted=False, scam=False, fake=False,
                         restricted=False, premium=True, verified=False, contact=False,
                         mutual_contact=True, status=None)
d = analisi.info_da_utente(utente, chat_con_me=True)
assert d["username"] == "anna_x" and d["foto"] and d["contatto"] and d["chat_con_me"]
assert d["cognome"] == "" and d["ultimo_accesso"] == "tempo_fa" and d["premium"]

print("test_analisi: OK")
