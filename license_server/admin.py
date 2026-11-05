"""
Pannello admin licenze FactMachine (per TE, il venditore).

Parla con il tuo server (server.py) per creare, elencare, revocare le chiavi.
Puoi lanciarlo sulla VPS (dove gira il server) o dal tuo PC.

CONFIG: imposta l'indirizzo del server e il token admin qui sotto, oppure
tramite variabili d'ambiente FM_SERVER_URL e FM_ADMIN_TOKEN.

ESEMPI:
    # crea 1 licenza mensile (30 giorni) con una nota
    python admin.py create --days 30 --note "cliente Mario"
    # crea 5 licenze settimanali in blocco
    python admin.py create --days 7 --count 5
    # licenza giornaliera
    python admin.py create --days 1
    # elenca tutte le licenze e il loro stato
    python admin.py list
    # revoca (disattiva) una licenza
    python admin.py revoke FM-ABCD-EFGH-JKLM
    # sblocca il PC legato a una licenza (il cliente cambia computer)
    python admin.py reset FM-ABCD-EFGH-JKLM
"""
import argparse
import json
import os
import urllib.request

# --- CONFIG (cambia qui oppure usa le variabili d'ambiente) ---
SERVER_URL = os.getenv("FM_SERVER_URL", "http://127.0.0.1:8000")
ADMIN_TOKEN = os.getenv("FM_ADMIN_TOKEN", "CAMBIA-QUESTO-admin-token-lungo-a-caso")
# --------------------------------------------------------------


def post(path, payload):
    payload["token"] = ADMIN_TOKEN
    req = urllib.request.Request(
        SERVER_URL.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def cmd_create(args):
    res = post("/admin/create", {"duration_days": args.days,
                                 "count": args.count, "note": args.note or ""})
    print(f"Create {len(res.get('created', []))} licenze da {res.get('duration_days')} giorni:")
    for k in res.get("created", []):
        print("  " + k)


def cmd_list(args):
    res = post("/admin/list", {})
    lic = res.get("licenze", [])
    if not lic:
        print("Nessuna licenza.")
        return
    print(f"{'CHIAVE':20} {'STATO':13} {'GG':>3} {'SCADE':20} {'PC':12} NOTA")
    for r in lic:
        print(f"{r['key']:20} {r['stato']:13} {r['durata_giorni']:>3} "
              f"{(r['scade'] or '-'):20} {(r['pc'] or '-'):12} {r['nota'] or ''}")


def cmd_revoke(args):
    post("/admin/revoke", {"key": args.key})
    print(f"Revocata: {args.key}")


def cmd_reset(args):
    post("/admin/reset", {"key": args.key})
    print(f"Machine-lock sbloccato: {args.key} (il cliente puo' riattivarla su un nuovo PC)")


def main():
    p = argparse.ArgumentParser(description="Admin licenze FactMachine")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="crea una o piu' licenze")
    c.add_argument("--days", type=int, required=True, help="durata in giorni (1=giorno, 7=settimana, 30=mese)")
    c.add_argument("--count", type=int, default=1, help="quante licenze creare")
    c.add_argument("--note", help="nota (es. nome cliente)")
    c.set_defaults(func=cmd_create)

    l = sub.add_parser("list", help="elenca le licenze")
    l.set_defaults(func=cmd_list)

    r = sub.add_parser("revoke", help="revoca una licenza")
    r.add_argument("key")
    r.set_defaults(func=cmd_revoke)

    rs = sub.add_parser("reset", help="sblocca il PC legato a una licenza")
    rs.add_argument("key")
    rs.set_defaults(func=cmd_reset)

    args = p.parse_args()
    try:
        args.func(args)
    except urllib.error.HTTPError as e:
        print(f"Errore server ({e.code}): {e.read().decode()[:200]}")
    except Exception as e:
        print(f"Errore: {e}")


if __name__ == "__main__":
    main()
