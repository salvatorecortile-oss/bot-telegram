"""
Valuta quanto un account Telegram sembra sospetto (bot, falso, spam).

Non usa Telegram: riceve i dati dell'account gia' letti e restituisce un
punteggio con i motivi. Cosi' si puo' testare senza connessione.

Il punteggio e' solo un AIUTO: non elimina nessuno. Chi ha una chat con te
o e' nei tuoi contatti viene segnato come CONOSCIUTO, anche se e' inattivo.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone

SOGLIA_ALTO = 60
SOGLIA_MEDIO = 30

# Parole tipiche di account spam / truffatori nei canali di trading.
PAROLE_SPAM = [
    "admin", "support", "supporto", "assistenza", "helpdesk", "help desk",
    "manager", "customer", "service", "official", "ufficiale",
    "crypto", "bitcoin", "btc", "usdt", "airdrop", "giveaway", "promo",
    "bonus", "casino", "scommesse", "recupero fondi", "recovery",
    "investimenti", "invest", "profit", "guadagna", "earn",
    "dm me", "scrivimi", "contattami", "whatsapp",
    "sex", "xxx", "onlyfans", "18+", "dating",
]

LINK_RE = re.compile(r"(https?://|www\.|t\.me/|\.com\b|\.io\b|\.net\b|@\w{4,})", re.IGNORECASE)

ULTIMO_ACCESSO_TESTO = {
    "online": "online ora",
    "recente": "di recente",
    "settimana": "nell'ultima settimana",
    "mese": "nell'ultimo mese",
    "tempo_fa": "molto tempo fa / nascosto",
    "": "sconosciuto",
}


@dataclass
class Valutazione:
    punteggio: int
    livello: str          # ALTO / MEDIO / BASSO / CONOSCIUTO
    motivi: list = field(default_factory=list)
    conosciuto: bool = False
    motivi_conosciuto: list = field(default_factory=list)


def normalizza(testo):
    """Minuscolo, senza accenti, solo lettere e numeri separati da spazio."""
    testo = unicodedata.normalize("NFKD", testo or "")
    testo = "".join(c for c in testo if not unicodedata.combining(c)).lower()
    testo = re.sub(r"[^a-z0-9]+", " ", testo)
    return " ".join(testo.split())


def _ha_lettere_o_numeri(testo):
    return any(c.isalnum() for c in testo or "")


def _parole_spam_trovate(nome):
    norm = f" {normalizza(nome)} "
    trovate = []
    for parola in PAROLE_SPAM:
        if parola == "18+":
            if "18+" in (nome or ""):
                trovate.append(parola)
        elif f" {normalizza(parola)} " in norm:
            trovate.append(parola)
    return trovate


def _imitazione(nome_completo, username, nomi_protetti):
    nome_norm = normalizza(nome_completo)
    user_norm = normalizza(username).replace(" ", "")
    for protetto in nomi_protetti:
        p = normalizza(protetto)
        if len(p) < 4:
            continue
        if f" {p} " in f" {nome_norm} " or (user_norm and p.replace(" ", "") in user_norm):
            return protetto
    return None


def livello_da_punteggio(punteggio):
    if punteggio >= SOGLIA_ALTO:
        return "ALTO"
    if punteggio >= SOGLIA_MEDIO:
        return "MEDIO"
    return "BASSO"


def valuta(info, nomi_protetti=(), id_account_recente=0):
    """
    info: dizionario con i dati dell'account (vedi info_da_utente):
        id, nome, cognome, username, foto, bot, eliminato, scam, fake,
        limitato, premium, verificato, ultimo_accesso, contatto,
        chat_con_me
    """
    punti = 0
    motivi = []

    def aggiungi(p, motivo):
        nonlocal punti
        punti += p
        motivi.append(motivo)

    nome_completo = " ".join(x for x in (info.get("nome"), info.get("cognome")) if x).strip()
    username = info.get("username") or ""

    # --- Segnali certi ---
    if info.get("eliminato"):
        aggiungi(100, "Account eliminato")
    if info.get("bot"):
        aggiungi(100, "E' un bot")
    if info.get("scam"):
        aggiungi(80, "Segnalato da Telegram come TRUFFA (scam)")
    if info.get("fake"):
        aggiungi(80, "Segnalato da Telegram come FALSO (fake)")
    if info.get("limitato"):
        aggiungi(40, "Account limitato da Telegram")

    if not info.get("eliminato"):
        # --- Imitazioni e nomi spam ---
        imitato = _imitazione(nome_completo, username, nomi_protetti)
        if imitato:
            aggiungi(50, f"Possibile imitazione di '{imitato}'")
        if LINK_RE.search(nome_completo):
            aggiungi(40, "Link o @ nel nome")
        spam = _parole_spam_trovate(f"{nome_completo} {username.replace('_', ' ')}")
        if spam:
            aggiungi(25, "Parole sospette nel nome: " + ", ".join(spam))
        if nome_completo and not _ha_lettere_o_numeri(nome_completo):
            aggiungi(15, "Nome fatto solo di simboli/emoji")

        # --- Profilo vuoto ---
        if not info.get("foto"):
            aggiungi(20, "Nessuna foto profilo")
        if not username:
            aggiungi(10, "Nessun username")
        if not info.get("foto") and not username:
            aggiungi(10, "Profilo vuoto (niente foto e niente username)")
        elif username and len(re.findall(r"\d", username)) >= 5:
            aggiungi(10, "Username con tanti numeri")

        # --- Eta' e attivita' ---
        if id_account_recente and int(info.get("id") or 0) >= id_account_recente:
            aggiungi(15, "Account creato di recente (stima dall'ID)")
        accesso = info.get("ultimo_accesso") or ""
        if accesso == "tempo_fa":
            aggiungi(15, "Non si collega da molto tempo (o lo nasconde)")
        elif accesso == "mese":
            aggiungi(5, "Ultimo accesso nell'ultimo mese")

        # --- Segnali positivi ---
        if info.get("premium"):
            aggiungi(-20, "Ha Telegram Premium (a pagamento, raro nei bot)")
        if info.get("verificato"):
            aggiungi(-50, "Account verificato da Telegram")

    punti = max(0, min(punti, 100))

    motivi_conosciuto = []
    if info.get("contatto"):
        motivi_conosciuto.append("nei tuoi contatti")
    if info.get("chat_con_me"):
        motivi_conosciuto.append("hai una chat privata con lui/lei")
    certo_falso = info.get("eliminato") or info.get("bot") or info.get("scam") or info.get("fake")
    conosciuto = bool(motivi_conosciuto) and not certo_falso

    livello = "CONOSCIUTO" if conosciuto else livello_da_punteggio(punti)
    return Valutazione(punti, livello, motivi, conosciuto, motivi_conosciuto)


def ultimo_accesso_da_status(status, adesso=None):
    """Converte lo 'status' Telethon in: online/recente/settimana/mese/tempo_fa."""
    if status is None:
        return "tempo_fa"
    nome = type(status).__name__
    if nome == "UserStatusOnline":
        return "online"
    if nome == "UserStatusRecently":
        return "recente"
    if nome == "UserStatusLastWeek":
        return "settimana"
    if nome == "UserStatusLastMonth":
        return "mese"
    if nome == "UserStatusOffline":
        quando = getattr(status, "was_online", None)
        if not quando:
            return "tempo_fa"
        adesso = adesso or datetime.now(timezone.utc)
        if quando.tzinfo is None:
            quando = quando.replace(tzinfo=timezone.utc)
        giorni = (adesso - quando).days
        if giorni <= 3:
            return "recente"
        if giorni <= 7:
            return "settimana"
        if giorni <= 30:
            return "mese"
        return "tempo_fa"
    return "tempo_fa"  # UserStatusEmpty = "visto molto tempo fa"


def info_da_utente(user, chat_con_me=False, adesso=None):
    """Estrae i dati che servono da un utente Telethon (types.User)."""
    username = getattr(user, "username", None)
    if not username:
        for u in getattr(user, "usernames", None) or []:
            if getattr(u, "active", False):
                username = u.username
                break
    return {
        "id": user.id,
        "nome": getattr(user, "first_name", None) or "",
        "cognome": getattr(user, "last_name", None) or "",
        "username": username or "",
        "foto": getattr(user, "photo", None) is not None,
        "bot": bool(getattr(user, "bot", False)),
        "eliminato": bool(getattr(user, "deleted", False)),
        "scam": bool(getattr(user, "scam", False)),
        "fake": bool(getattr(user, "fake", False)),
        "limitato": bool(getattr(user, "restricted", False)),
        "premium": bool(getattr(user, "premium", False)),
        "verificato": bool(getattr(user, "verified", False)),
        "contatto": bool(getattr(user, "contact", False) or getattr(user, "mutual_contact", False)),
        "chat_con_me": bool(chat_con_me),
        "ultimo_accesso": ultimo_accesso_da_status(getattr(user, "status", None), adesso),
    }
