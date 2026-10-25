"""
Database SQLite della sala segnali: un record per ogni posizione MT5 seguita,
con il collegamento al messaggio pubblicato nel canale.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from config import DB_PATH

_db_path = str(DB_PATH)

OPEN_STATUS = "OPENED"
CLOSED_STATUSES = ("CLOSED_TP", "CLOSED_SL", "CLOSED_BE", "CLOSED_EXTERNAL")


def set_db_path(path):
    """Solo per i test: usa un database diverso."""
    global _db_path
    _db_path = str(path)


def _now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_connection():
    """Connessione con commit automatico, chiusa sempre all'uscita."""
    conn = sqlite3.connect(_db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_database():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                ticket                 INTEGER PRIMARY KEY,
                magic                  INTEGER,
                symbol                 TEXT,
                direction              TEXT NOT NULL,
                open_price             REAL NOT NULL,
                sl                     REAL,
                tp                     REAL,
                volume                 REAL,
                published              INTEGER NOT NULL DEFAULT 1,
                destination_message_id INTEGER,
                be_applied             INTEGER NOT NULL DEFAULT 0,
                status                 TEXT NOT NULL,
                close_price            REAL,
                pips                   REAL,
                profit                 REAL,
                close_attempts         INTEGER NOT NULL DEFAULT 0,
                opened_at              TEXT,
                closed_at              TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
        conn.execute("CREATE TABLE IF NOT EXISTS sent_messages (key TEXT PRIMARY KEY, sent_at TEXT)")


def _row(row):
    return dict(row) if row is not None else None


def get_trade(ticket):
    with get_connection() as conn:
        return _row(conn.execute("SELECT * FROM trades WHERE ticket = ?", (int(ticket),)).fetchone())


def insert_trade(position, published):
    """Inserimento idempotente: False se la posizione era gia' registrata."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO trades (
                ticket, magic, symbol, direction, open_price, sl, tp, volume,
                published, status, opened_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(position["ticket"]), int(position["magic"]), position["symbol"],
                position["direction"], float(position["open_price"]),
                float(position["sl"] or 0) or None, float(position["tp"] or 0) or None,
                float(position["volume"]), 1 if published else 0, OPEN_STATUS, _now(),
            ),
        )
        return cur.rowcount == 1


def set_destination_message(ticket, message_id):
    with get_connection() as conn:
        conn.execute("UPDATE trades SET destination_message_id = ? WHERE ticket = ?", (int(message_id), int(ticket)))


def get_open_trades():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM trades WHERE status = ? ORDER BY ticket", (OPEN_STATUS,)).fetchall()
        return [dict(r) for r in rows]


def update_levels(ticket, sl=None, tp=None, be_applied=None):
    with get_connection() as conn:
        if sl is not None:
            conn.execute("UPDATE trades SET sl = ? WHERE ticket = ?", (float(sl) or None, int(ticket)))
        if tp is not None:
            conn.execute("UPDATE trades SET tp = ? WHERE ticket = ?", (float(tp) or None, int(ticket)))
        if be_applied:
            conn.execute("UPDATE trades SET be_applied = 1 WHERE ticket = ?", (int(ticket),))


def add_close_attempt(ticket):
    with get_connection() as conn:
        conn.execute("UPDATE trades SET close_attempts = close_attempts + 1 WHERE ticket = ?", (int(ticket),))
        return conn.execute("SELECT close_attempts FROM trades WHERE ticket = ?", (int(ticket),)).fetchone()[0]


def claim_close(ticket, status, close_price, pips, profit):
    """OPENED -> chiusa. True solo la prima volta: il messaggio non parte mai due volte."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE trades SET status = ?, close_price = ?, pips = ?, profit = ?, closed_at = ?
            WHERE ticket = ? AND status = ?
            """,
            (
                status, None if close_price is None else float(close_price),
                None if pips is None else float(pips), None if profit is None else float(profit),
                _now(), int(ticket), OPEN_STATUS,
            ),
        )
        return cur.rowcount == 1


def get_closed_between(start_utc, end_utc):
    """Operazioni pubblicate e chiuse (con pips noti) tra due datetime UTC: [start, end)."""
    placeholders = ",".join("?" for _ in CLOSED_STATUSES)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM trades
            WHERE status IN ({placeholders}) AND published = 1 AND pips IS NOT NULL
              AND closed_at >= ? AND closed_at < ?
            ORDER BY closed_at
            """,
            (*CLOSED_STATUSES, start_utc.isoformat(), end_utc.isoformat()),
        ).fetchall()
        return [dict(r) for r in rows]


def was_sent(key):
    with get_connection() as conn:
        return conn.execute("SELECT 1 FROM sent_messages WHERE key = ?", (key,)).fetchone() is not None


def mark_sent(key):
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO sent_messages (key, sent_at) VALUES (?, ?)", (key, _now()))
