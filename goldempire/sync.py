"""
Allineamento tra due bot sulla stessa macchina (es. Fortune Prime -> PU Prime).

Il bot "master" scrive in un file SQLite condiviso (SYNC_FILE) cosa succede alle
sue operazioni: chiusura, SL spostato, BE, TP cambiato. Il bot "follower" legge
il file e fa lo stesso sulla sua operazione collegata allo STESSO segnale del
canale sorgente (stesso source_message_id: i due bot leggono lo stesso canale).
"""
import sqlite3
from datetime import datetime, timezone

from config import SYNC_FILE, SYNC_ROLE

IS_MASTER = bool(SYNC_FILE) and SYNC_ROLE == "master"
IS_FOLLOWER = bool(SYNC_FILE) and SYNC_ROLE == "follower"


def _connect():
    conn = sqlite3.connect(SYNC_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_events (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            source_message_id INTEGER NOT NULL,
            kind              TEXT NOT NULL,   -- CLOSE, SL, BE, TP
            value             REAL,
            created_at        TEXT
        )
        """
    )
    return conn


def publish(source_message_id, kind, value=None):
    """
    Solo il master scrive. kind: OPEN / SKIP (segnale aperto o no), CLOSE,
    SL (value=prezzo), BE, TP (value=prezzo, 0=nessuno).
    """
    if not IS_MASTER:
        return
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sync_events (source_message_id, kind, value, created_at) VALUES (?, ?, ?, ?)",
            (int(source_message_id), kind, None if value is None else float(value),
             datetime.now(timezone.utc).isoformat()),
        )


def find_decision(source_message_id):
    """Cosa ha deciso il principale su un segnale: 'OPEN', 'SKIP' o None (non ancora)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT kind FROM sync_events WHERE source_message_id = ? AND kind IN ('OPEN', 'SKIP') "
            "ORDER BY id DESC LIMIT 1",
            (int(source_message_id),),
        ).fetchone()
        return row["kind"] if row else None


def read_after(last_id):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM sync_events WHERE id > ? ORDER BY id", (int(last_id),)
        ).fetchall()
        return [dict(r) for r in rows]
