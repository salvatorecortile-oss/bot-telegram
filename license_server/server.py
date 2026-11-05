"""
Server di licenze FactMachine (gira sulla TUA VPS).

Zero dipendenze: usa solo la libreria standard di Python (http.server + sqlite3).
Custodisce le chiavi di licenza, le scadenze e il blocco per PC (machine-lock).

AVVIO (sulla VPS):
    python server.py
Resta in ascolto su 0.0.0.0:8000 (apri quella porta nel firewall della VPS).

ENDPOINT:
    GET  /health                      -> {"ok": true}
    POST /validate   {key, machine_id, nonce}
         -> {status, expires_at, days_left, nonce, sig}
         status: ok | invalid | revoked | expired | wrong_machine
    POST /admin/create  {token, duration_days, count, note}
    POST /admin/list    {token}
    POST /admin/revoke  {token, key}
    POST /admin/reset   {token, key}   # sblocca il machine-lock (nuovo PC)

======================================================================
 CONFIG - CAMBIA QUESTI DUE VALORI PRIMA DI USARLO!
======================================================================
"""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import string
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- CAMBIA QUESTI DUE VALORI (devono restare segreti) ---
# Token per usare il pannello admin (scegli una password lunga a caso):
ADMIN_TOKEN = os.getenv("FM_ADMIN_TOKEN", "CAMBIA-QUESTO-admin-token-lungo-a-caso")
# Segreto per firmare le risposte: lo STESSO valore va messo nel bot
# (license_client.py -> SIGNING_SECRET). Scegli una stringa lunga a caso:
SIGNING_SECRET = os.getenv("FM_SIGNING_SECRET", "CAMBIA-QUESTO-segreto-di-firma-lungo-a-caso")
# ----------------------------------------------------------

HOST = os.getenv("FM_HOST", "0.0.0.0")
PORT = int(os.getenv("FM_PORT", "8000"))
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "licenses.db")


# --------------------------- Database ---------------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                key           TEXT PRIMARY KEY,
                duration_days INTEGER NOT NULL,
                note          TEXT,
                created_at    TEXT NOT NULL,
                activated_at  TEXT,
                expires_at    TEXT,
                machine_id    TEXT,
                revoked       INTEGER NOT NULL DEFAULT 0
            )
        """)


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.replace(microsecond=0).isoformat()


def new_key():
    """Chiave leggibile tipo FM-ABCD-EFGH-JKLM."""
    alphabet = string.ascii_uppercase + string.digits
    groups = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
    return "FM-" + "-".join(groups)


# --------------------------- Firma ---------------------------
def sign(fields: dict) -> str:
    """Firma HMAC-SHA256 dei campi della risposta (il bot la verifica)."""
    canonical = "|".join(str(fields.get(k, "")) for k in
                         ("status", "key", "machine_id", "expires_at", "nonce"))
    return hmac.new(SIGNING_SECRET.encode(), canonical.encode(), hashlib.sha256).hexdigest()


# --------------------------- Logica validate ---------------------------
def validate(key: str, machine_id: str) -> dict:
    key = (key or "").strip().upper()
    machine_id = (machine_id or "").strip()
    with db() as conn:
        row = conn.execute("SELECT * FROM licenses WHERE key=?", (key,)).fetchone()
        if not row:
            return {"status": "invalid"}
        if row["revoked"]:
            return {"status": "revoked"}

        activated_at = row["activated_at"]
        expires_at = row["expires_at"]
        bound = row["machine_id"]

        # prima attivazione: lega il PC e fa partire il conteggio della durata
        if not activated_at:
            start = now_utc()
            exp = start.timestamp() + row["duration_days"] * 86400
            activated_at = iso(start)
            expires_at = iso(datetime.fromtimestamp(exp, tz=timezone.utc))
            bound = machine_id
            conn.execute(
                "UPDATE licenses SET activated_at=?, expires_at=?, machine_id=? WHERE key=?",
                (activated_at, expires_at, bound, key))
        else:
            # gia' attivata: deve essere lo STESSO PC
            if bound and machine_id and bound != machine_id:
                return {"status": "wrong_machine", "expires_at": expires_at}

        # scadenza
        try:
            exp_dt = datetime.fromisoformat(expires_at)
        except Exception:
            exp_dt = now_utc()
        if now_utc() > exp_dt:
            return {"status": "expired", "expires_at": expires_at}

        days_left = max(0, int((exp_dt - now_utc()).total_seconds() // 86400))
        return {"status": "ok", "expires_at": expires_at, "days_left": days_left}


# --------------------------- HTTP ---------------------------
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _admin_ok(self, data):
        return hmac.compare_digest(str(data.get("token", "")), ADMIN_TOKEN)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        data = self._body()

        if self.path == "/validate":
            key = data.get("key", "")
            machine_id = data.get("machine_id", "")
            nonce = data.get("nonce", "")
            res = validate(key, machine_id)
            res["key"] = (key or "").strip().upper()
            res["machine_id"] = machine_id
            res["nonce"] = nonce
            res.setdefault("expires_at", "")
            res["sig"] = sign(res)
            self._send(200, res)
            return

        # ---- admin ----
        if self.path.startswith("/admin/"):
            if not self._admin_ok(data):
                self._send(403, {"error": "token non valido"})
                return

            if self.path == "/admin/create":
                duration = int(data.get("duration_days", 30))
                count = int(data.get("count", 1))
                note = data.get("note", "")
                created = []
                with db() as conn:
                    for _ in range(count):
                        k = new_key()
                        conn.execute(
                            "INSERT INTO licenses (key, duration_days, note, created_at) VALUES (?,?,?,?)",
                            (k, duration, note, iso(now_utc())))
                        created.append(k)
                self._send(200, {"created": created, "duration_days": duration})
                return

            if self.path == "/admin/list":
                with db() as conn:
                    rows = conn.execute("SELECT * FROM licenses ORDER BY created_at DESC").fetchall()
                out = []
                for r in rows:
                    status = "revocata" if r["revoked"] else (
                        "non attivata" if not r["activated_at"] else "attiva")
                    if status == "attiva" and r["expires_at"]:
                        try:
                            if now_utc() > datetime.fromisoformat(r["expires_at"]):
                                status = "scaduta"
                        except Exception:
                            pass
                    out.append({
                        "key": r["key"], "stato": status,
                        "durata_giorni": r["duration_days"],
                        "attivata": r["activated_at"], "scade": r["expires_at"],
                        "pc": (r["machine_id"] or "")[:12], "nota": r["note"],
                    })
                self._send(200, {"licenze": out})
                return

            if self.path == "/admin/revoke":
                with db() as conn:
                    conn.execute("UPDATE licenses SET revoked=1 WHERE key=?",
                                 ((data.get("key") or "").strip().upper(),))
                self._send(200, {"ok": True})
                return

            if self.path == "/admin/reset":
                with db() as conn:
                    conn.execute("UPDATE licenses SET machine_id=NULL WHERE key=?",
                                 ((data.get("key") or "").strip().upper(),))
                self._send(200, {"ok": True, "info": "machine-lock sbloccato"})
                return

        self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        print(f"{iso(now_utc())}  {self.address_string()}  {fmt % args}")


def main():
    init_db()
    print(f"Server licenze FactMachine su http://{HOST}:{PORT}  (DB: {DB_PATH})")
    if "CAMBIA" in ADMIN_TOKEN or "CAMBIA" in SIGNING_SECRET:
        print("!!! ATTENZIONE: cambia ADMIN_TOKEN e SIGNING_SECRET prima di usarlo in produzione !!!")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
