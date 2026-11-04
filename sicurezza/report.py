"""
Crea il report degli iscritti sospetti: file CSV (si apre con Excel) + riepilogo.

Non usa Telegram: riceve le righe gia' valutate.
"""
import csv

from analisi import ULTIMO_ACCESSO_TESTO

ORDINE_LIVELLI = {"ALTO": 0, "MEDIO": 1, "BASSO": 2, "CONOSCIUTO": 3}

COLONNE = [
    "Livello", "Punteggio", "Motivi", "Conosciuto perche'", "Nome", "Username",
    "ID", "Dove e' iscritto", "Ultimo accesso", "Entrato il", "Link profilo",
]


def ordina(righe):
    """Prima i piu' sospetti; i CONOSCIUTI in fondo."""
    return sorted(righe, key=lambda r: (ORDINE_LIVELLI.get(r["valutazione"].livello, 9),
                                        -r["valutazione"].punteggio, r["info"]["id"]))


def riga_csv(riga):
    info = riga["info"]
    val = riga["valutazione"]
    nome = " ".join(x for x in (info.get("nome"), info.get("cognome")) if x) or "(senza nome)"
    username = f"@{info['username']}" if info.get("username") else ""
    entrato = riga.get("entrato")
    return [
        val.livello,
        val.punteggio,
        " | ".join(val.motivi),
        ", ".join(val.motivi_conosciuto),
        nome,
        username,
        info["id"],
        ", ".join(riga.get("chat", [])),
        ULTIMO_ACCESSO_TESTO.get(info.get("ultimo_accesso") or "", ""),
        entrato.strftime("%d/%m/%Y") if entrato else "",
        f"https://t.me/{info['username']}" if info.get("username") else f"tg://user?id={info['id']}",
    ]


def scrivi_csv(righe, percorso):
    # utf-8-sig e ';' = Excel italiano lo apre bene con un doppio clic.
    with open(percorso, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(COLONNE)
        for riga in ordina(righe):
            w.writerow(riga_csv(riga))


def conta_livelli(righe):
    conteggi = {k: 0 for k in ORDINE_LIVELLI}
    for r in righe:
        conteggi[r["valutazione"].livello] = conteggi.get(r["valutazione"].livello, 0) + 1
    return conteggi


def riepilogo(righe, max_righe=20):
    c = conta_livelli(righe)
    testo = [
        f"Iscritti controllati: {len(righe)}",
        f"  ALTO (molto sospetti):   {c['ALTO']}",
        f"  MEDIO (da guardare):     {c['MEDIO']}",
        f"  BASSO (sembrano ok):     {c['BASSO']}",
        f"  CONOSCIUTI (chat/contatti): {c['CONOSCIUTO']}",
    ]
    alti = [r for r in ordina(righe) if r["valutazione"].livello == "ALTO"]
    if alti:
        testo.append("")
        testo.append(f"I piu' sospetti (max {max_righe}):")
        for r in alti[:max_righe]:
            riga = riga_csv(r)
            testo.append(f"  [{riga[1]:>3}] {riga[4]} {riga[5]} (ID {riga[6]}) -> {riga[2]}")
    return "\n".join(testo)
