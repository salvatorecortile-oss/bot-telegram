"""
Database SQLite del bot Gold Empire: un record per ogni segnale di apertura
del canale sorgente, con il collegamento a posizione MT5 e messaggio copiato.
"""
import sqlite3
from datetime import datetime, timezone

from config import DB_PATH

_db_path = str(DB_PATH)

OPEN_STATUS = "OPENED"
PENDING_STATUS = "PENDING"

COLUMNS = (
    "source_message_id", "signal_no", "direction", "entry_signal", "sl", "tp",
    "targets_total", "status", "position_ticket", "open_price", "volume",
    "destination_message_id", "be_applied", "close_price", "pips",
    "created_at", "opened_at", "closed_at", "error",
)


def set_db_path(path):
    """Solo per i test: usa un database diverso."""
    global _db_path
    _db_path = str(path)


def _now():
    return datetime.now(timezone.utc).isoformat()


def get_connection():
    conn = sqlite3.connect(_db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_database():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                source_message_id      INTEGER PRIMARY KEY,
                signal_no              INTEGER,
                direction              TEXT NOT NULL,
                entry_signal           REAL,
                sl                     REAL,
                tp                     REAL,
                targets_total          INTEGER,
                status                 TEXT NOT NULL,
                position_ticket        INTEGER,
                open_price             REAL,
                volume                 REAL,
                destination_message_id INTEGER,
                be_applied             INTEGER NOT NULL DEFAULT 0,
                close_price            REAL,
                pips                   REAL,
                created_at             TEXT,
                opened_at              TEXT,
                closed_at              TEXT,
                error                  TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status)"
        )
        # Colonne aggiunte dopo la prima versione (database gia' esistenti).
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(signals)")}
        for column, ddl in (
            ("order_type", "TEXT"),
            ("order_ticket", "INTEGER"),
            ("pending_since", "TEXT"),
        ):
            if column not in existing:
                conn.execute(f"ALTER TABLE signals ADD COLUMN {column} {ddl}")


def _row(row):
    return dict(row) if row is not None else None


def insert_signal(source_message_id, signal):
    """Inserimento idempotente: False se il segnale era gia' registrato."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO signals (
                source_message_id, signal_no, direction, entry_signal, sl, tp,
                targets_total, status, created_at, order_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'RECEIVED', ?, ?)
            """,
            (
                int(source_message_id), signal.get("signal_no"), signal["direction"],
                signal["entry"], signal["sl"], signal["tp"],
                signal.get("targets_total", 1), _now(),
                signal.get("order_type", "MARKET"),
            ),
        )
        return cur.rowcount == 1


def get_signal(source_message_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM signals WHERE source_message_id = ?",
            (int(source_message_id),),
        ).fetchone()
        return _row(row)


def get_latest_open_by_signal_no(signal_no):
    """Riserva quando l'aggiornamento non e' una reply: ultimo SIGNAL N aperto."""
    if signal_no is None:
        return None
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT * FROM signals
            WHERE signal_no = ? AND status IN (?, ?)
            ORDER BY source_message_id DESC LIMIT 1
            """,
            (int(signal_no), OPEN_STATUS, PENDING_STATUS),
        ).fetchone()
        return _row(row)


def get_open_signals():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM signals WHERE status = ? ORDER BY source_message_id",
            (OPEN_STATUS,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_active_by_signal_no(signal_no, direction):
    """Operazioni aperte e ordini pendenti di un SIGNAL N in una direzione."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM signals
            WHERE signal_no = ? AND direction = ? AND status IN (?, ?)
            ORDER BY source_message_id
            """,
            (int(signal_no), direction, OPEN_STATUS, PENDING_STATUS),
        ).fetchall()
        return [dict(r) for r in rows]


def get_pending_signals():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM signals WHERE status = ? ORDER BY source_message_id",
            (PENDING_STATUS,),
        ).fetchall()
        return [dict(r) for r in rows]


def mark_pending(source_message_id, order_ticket):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE signals SET status = ?, order_ticket = ?, pending_since = ?
            WHERE source_message_id = ?
            """,
            (PENDING_STATUS, int(order_ticket), _now(), int(source_message_id)),
        )


def finish_pending(source_message_id, status):
    """PENDING -> CANCELED/EXPIRED. True solo se era ancora pendente."""
    with get_connection() as conn:
        cur = conn.execute(
            "UPDATE signals SET status = ? WHERE source_message_id = ? AND status = ?",
            (status, int(source_message_id), PENDING_STATUS),
        )
        return cur.rowcount == 1


def set_status(source_message_id, status, error=None):
    with get_connection() as conn:
        conn.execute(
            "UPDATE signals SET status = ?, error = COALESCE(?, error) WHERE source_message_id = ?",
            (status, error, int(source_message_id)),
        )


def mark_opened(source_message_id, position_ticket, open_price, volume, sl, tp):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE signals
            SET status = ?, position_ticket = ?, open_price = ?, volume = ?,
                sl = ?, tp = ?, opened_at = ?
            WHERE source_message_id = ?
            """,
            (
                OPEN_STATUS, position_ticket, float(open_price), volume,
                float(sl), float(tp) if tp else None, _now(), int(source_message_id),
            ),
        )


def set_destination_message(source_message_id, destination_message_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE signals SET destination_message_id = ? WHERE source_message_id = ?",
            (int(destination_message_id), int(source_message_id)),
        )


def mark_breakeven(source_message_id, new_sl):
    with get_connection() as conn:
        conn.execute(
            "UPDATE signals SET be_applied = 1, sl = ? WHERE source_message_id = ?",
            (float(new_sl), int(source_message_id)),
        )


def claim_close(source_message_id, close_status, close_price, pips):
    """
    Passa il segnale da OPENED allo stato di chiusura. Restituisce True solo
    al primo che lo fa: cosi' il messaggio di chiusura non parte mai due volte.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE signals
            SET status = ?, close_price = ?, pips = ?, closed_at = ?
            WHERE source_message_id = ? AND status = ?
            """,
            (
                close_status,
                None if close_price is None else float(close_price),
                None if pips is None else float(pips),
                _now(), int(source_message_id), OPEN_STATUS,
            ),
        )
        return cur.rowcount == 1


CLOSED_STATUSES = ("CLOSED_TP", "CLOSED_SL", "CLOSED_BE", "CLOSED_MANUAL", "CLOSED_EXTERNAL")


def get_closed_between(start_utc, end_utc):
    """Operazioni chiuse (con pips noti) tra due datetime UTC: [start, end)."""
    placeholders = ",".join("?" for _ in CLOSED_STATUSES)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM signals
            WHERE status IN ({placeholders}) AND pips IS NOT NULL
              AND closed_at >= ? AND closed_at < ?
            ORDER BY closed_at
            """,
            (*CLOSED_STATUSES, start_utc.isoformat(), end_utc.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]


def _init_sent_messages(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sent_messages (key TEXT PRIMARY KEY, sent_at TEXT)"
    )


def was_sent(key):
    with get_connection() as conn:
        _init_sent_messages(conn)
        return conn.execute("SELECT 1 FROM sent_messages WHERE key = ?", (key,)).fetchone() is not None


def mark_sent(key):
    with get_connection() as conn:
        _init_sent_messages(conn)
        conn.execute("INSERT OR IGNORE INTO sent_messages (key, sent_at) VALUES (?, ?)", (key, _now()))
