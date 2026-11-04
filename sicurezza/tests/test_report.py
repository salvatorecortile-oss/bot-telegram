"""Test del report CSV. Avvio: python tests/test_report.py"""
import csv
import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analisi  # noqa: E402
import report  # noqa: E402


def riga(uid, chat=("Sala Elite",), **kw):
    info = {"id": uid, "nome": f"Utente{uid}", "cognome": "", "username": f"utente{uid}",
            "foto": True, "ultimo_accesso": "recente"}
    info.update(kw)
    return {"info": info, "valutazione": analisi.valuta(info), "chat": list(chat),
            "entrato": datetime(2026, 10, 1, tzinfo=timezone.utc)}


righe = [
    riga(1),                                                       # BASSO
    riga(2, bot=True),                                             # ALTO
    riga(3, foto=False, username="", ultimo_accesso="tempo_fa", chat_con_me=True),  # CONOSCIUTO
    riga(4, foto=False, username=""),                              # MEDIO
    riga(5, eliminato=True, nome="", username="", foto=False, chat=("Sala Elite", "Canale")),  # ALTO
]

ordinate = [r["info"]["id"] for r in report.ordina(righe)]
assert ordinate == [2, 5, 4, 1, 3], ordinate  # sospetti prima, conosciuti in fondo

conteggi = report.conta_livelli(righe)
assert conteggi == {"ALTO": 2, "MEDIO": 1, "BASSO": 1, "CONOSCIUTO": 1}, conteggi

percorso = os.path.join(tempfile.mkdtemp(), "r.csv")
report.scrivi_csv(righe, percorso)
with open(percorso, encoding="utf-8-sig", newline="") as f:
    dati = list(csv.reader(f, delimiter=";"))
assert dati[0] == report.COLONNE
assert len(dati) == 6
prima = dict(zip(dati[0], dati[1]))
assert prima["Livello"] == "ALTO" and prima["ID"] == "2" and prima["Username"] == "@utente2"
assert prima["Link profilo"] == "https://t.me/utente2" and prima["Entrato il"] == "01/10/2026"
eliminato = dict(zip(dati[0], dati[2]))
assert eliminato["Nome"] == "(senza nome)" and eliminato["Link profilo"] == "tg://user?id=5"
assert eliminato["Dove e' iscritto"] == "Sala Elite, Canale"
conosciuto = dict(zip(dati[0], dati[5]))
assert conosciuto["Livello"] == "CONOSCIUTO" and "chat privata" in conosciuto["Conosciuto perche'"]
assert conosciuto["Ultimo accesso"] == "molto tempo fa / nascosto"

testo = report.riepilogo(righe)
assert "Iscritti controllati: 5" in testo and "CONOSCIUTI (chat/contatti): 1" in testo
assert "Utente2" in testo and "Utente3" not in testo  # nel riepilogo solo gli ALTO

print("test_report: OK")
