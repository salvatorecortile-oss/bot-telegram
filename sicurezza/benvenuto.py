"""
Messaggio di benvenuto personale, mandato in privato dopo il captcha superato.

Il testo si scrive nel file benvenuto.txt (in questa cartella), come un
messaggio normale: a capo, emoji e link funzionano. Si puo' cambiare anche
con il guardiano acceso: viene riletto ogni volta.

Segnaposto (facoltativi):
    {nome}  -> nome della persona
    {chat}  -> nome della community / canale

File mancante o vuoto = nessun messaggio di benvenuto.
"""
from pathlib import Path


def testo_benvenuto(percorso, nome="", chat=""):
    percorso = Path(percorso)
    if not percorso.exists():
        return None
    righe = []
    for riga in percorso.read_text(encoding="utf-8-sig").splitlines():
        if riga.lstrip().startswith("#"):
            continue  # le righe che iniziano con # sono note, non vengono mandate
        righe.append(riga.rstrip())
    testo = "\n".join(righe).strip()
    if not testo:
        return None
    return testo.replace("{nome}", nome or "").replace("{chat}", chat or "")
