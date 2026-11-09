"""
Captcha semplice per chi chiede di entrare: "Premi la MELA" e 6 pulsanti emoji.

La domanda e' scritta a parole e i pulsanti mostrano solo l'emoji: per
rispondere bisogna capire la parola, cosa che i bot automatici non fanno.

Non usa Telegram: si puo' testare senza connessione.
"""
import random
from dataclasses import dataclass, field

# (emoji, nome italiano, nome inglese)
OGGETTI = [
    ("🍎", "MELA", "APPLE"),
    ("🚗", "AUTO", "CAR"),
    ("🐶", "CANE", "DOG"),
    ("🐱", "GATTO", "CAT"),
    ("⚽", "PALLONE", "BALL"),
    ("🏠", "CASA", "HOUSE"),
    ("🌙", "LUNA", "MOON"),
    ("✈️", "AEREO", "PLANE"),
    ("🌳", "ALBERO", "TREE"),
    ("⭐", "STELLA", "STAR"),
    ("🔑", "CHIAVE", "KEY"),
    ("🐟", "PESCE", "FISH"),
]

NUM_OPZIONI = 6


@dataclass
class Sfida:
    opzioni: list            # indici in OGGETTI, nell'ordine dei pulsanti
    corretta: int            # posizione del pulsante giusto (0..NUM_OPZIONI-1)
    scadenza: float          # time.time() oltre il quale e' scaduta
    tentativi: int           # tentativi rimasti
    dati: dict = field(default_factory=dict)  # info extra (chat, nome, messaggio...)

    @property
    def oggetto(self):
        return OGGETTI[self.opzioni[self.corretta]]


def nuova_sfida(adesso, timeout, tentativi, rng=random):
    opzioni = rng.sample(range(len(OGGETTI)), NUM_OPZIONI)
    return Sfida(opzioni=opzioni, corretta=rng.randrange(NUM_OPZIONI),
                 scadenza=adesso + timeout, tentativi=max(1, tentativi))


def testo_domanda(sfida, titolo_chat="", secondi=0):
    emoji, it, en = sfida.oggetto
    dove = f" a <b>{titolo_chat}</b>" if titolo_chat else ""
    tempo = ""
    if secondi:
        if secondi < 120:
            tempo = f"\nHai {int(secondi)} secondi. / You have {int(secondi)} seconds."
        else:
            minuti = round(secondi / 60)
            tempo = f"\nHai {minuti} minuti. / You have {minuti} minutes."
    return (
        f"👋 Ciao! Hai chiesto di entrare{dove}.\n"
        f"Per confermare che sei una persona, premi: <b>{it}</b>\n\n"
        f"Hi! To confirm you are a person, press: <b>{en}</b>"
        f"{tempo}"
    )


def etichette_pulsanti(sfida):
    return [OGGETTI[i][0] for i in sfida.opzioni]


def rispondi(sfida, indice, adesso):
    """Ritorna 'ok', 'sbagliato' (puo' riprovare), 'fallito' o 'scaduto'."""
    if adesso > sfida.scadenza:
        return "scaduto"
    if indice == sfida.corretta:
        return "ok"
    sfida.tentativi -= 1
    if sfida.tentativi <= 0:
        return "fallito"
    return "sbagliato"


def scadute(sfide, adesso):
    """Chiavi delle sfide scadute (dict chiave -> Sfida)."""
    return [k for k, s in sfide.items() if adesso > s.scadenza]
