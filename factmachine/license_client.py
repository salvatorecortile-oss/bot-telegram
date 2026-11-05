"""
Controllo licenza FactMachine (lato cliente, dentro il bot).

All'avvio il bot chiama il server di licenze del venditore con:
  - la chiave di licenza (dal file license.key accanto al bot)
  - l'impronta del PC (machine_id)
  - un nonce casuale
Il server risponde con lo stato, firmato (HMAC). Il bot verifica la firma e
procede solo se la licenza e' valida e non scaduta.

======================================================================
 CONFIG - il VENDITORE imposta questi due valori prima di distribuire
======================================================================
"""
import hashlib
import hmac
import json
import platform
import secrets
import sys
import urllib.request
import uuid
from pathlib import Path

# --- Le impostazioni del server stanno nel file separato license_config.py,
#     cosi' NON le perdi quando aggiorni questo file. Modifica license_config.py,
#     non queste righe. ---
try:
    from license_config import SERVER_URL, SIGNING_SECRET
except Exception:
    SERVER_URL = "http://LA-TUA-VPS:8000"
    SIGNING_SECRET = "CAMBIA-QUESTO-segreto-di-firma-lungo-a-caso"
# ----------------------------------------------------------------------

# license.key sta accanto al bot/exe (anche quando e' compilato con PyInstaller)
if getattr(sys, "frozen", False):
    _APP_DIR = Path(sys.executable).resolve().parent
else:
    _APP_DIR = Path(__file__).resolve().parent
KEY_FILE = _APP_DIR / "license.key"


def machine_id() -> str:
    """Impronta stabile del PC (MAC + hostname + sistema)."""
    raw = f"{uuid.getnode()}|{platform.node()}|{platform.system()}|{platform.machine()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def read_key() -> str:
    try:
        return KEY_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def save_key(key: str):
    KEY_FILE.write_text(key.strip().upper(), encoding="utf-8")


def _sig(fields: dict) -> str:
    canonical = "|".join(str(fields.get(k, "")) for k in
                         ("status", "key", "machine_id", "expires_at", "nonce"))
    return hmac.new(SIGNING_SECRET.encode(), canonical.encode(), hashlib.sha256).hexdigest()


# readable messages per status (English; the UI may override via its own labels)
MESSAGGI = {
    "ok": "License valid.",
    "invalid": "Invalid license key.",
    "revoked": "License revoked. Contact the seller.",
    "expired": "License expired. Renew to continue.",
    "wrong_machine": "This license is already active on another PC.",
}


def check(key: str = None) -> dict:
    """Verifica la licenza col server.
    Ritorna: {ok: bool, status: str, message: str, expires_at, days_left}."""
    key = (key if key is not None else read_key()).strip().upper()
    if not key:
        return {"ok": False, "status": "no_key", "message": "No key entered."}

    nonce = secrets.token_hex(8)
    payload = {"key": key, "machine_id": machine_id(), "nonce": nonce}
    try:
        req = urllib.request.Request(
            SERVER_URL.rstrip("/") + "/validate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read())
    except Exception as e:
        return {"ok": False, "status": "offline",
                "message": f"Cannot reach the license server: {e}"}

    # verify signature and nonce (anti-tamper / anti-replay)
    if res.get("nonce") != nonce or not hmac.compare_digest(res.get("sig", ""), _sig(res)):
        return {"ok": False, "status": "bad_sig",
                "message": "Invalid server response (bad signature)."}

    status = res.get("status", "invalid")
    return {
        "ok": status == "ok",
        "status": status,
        "message": MESSAGGI.get(status, f"Stato licenza: {status}"),
        "expires_at": res.get("expires_at", ""),
        "days_left": res.get("days_left"),
    }
