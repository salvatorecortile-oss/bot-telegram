import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from config import DATA_DIR

DB_PATH = Path(DATA_DIR) / "copier.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_database():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                source_chat_id INTEGER NOT NULL,
                source_message_id INTEGER NOT NULL,
                destination_message_id INTEGER,
                symbol TEXT,
                direction TEXT,
                entry REAL,
                entry_zone_low REAL,
                entry_zone_high REAL,
                sl REAL,
                tp1 REAL,
                tp2 REAL,
                tp3 REAL,
                tp4 REAL,
                tp_open_runner INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                mt5_ticket INTEGER,
                mt5_deal INTEGER,
                mt5_volume REAL,
                mt5_price REAL,
                mt5_ticket_2 INTEGER,
                mt5_deal_2 INTEGER,
                mt5_volume_2 REAL,
                mt5_price_2 REAL,
                sltp_applied INTEGER NOT NULL DEFAULT 0,
                breakeven_applied INTEGER NOT NULL DEFAULT 0,
                is_closed INTEGER NOT NULL DEFAULT 0,
                error TEXT,
                source_datetime TEXT,
                received_datetime TEXT,
                destination_datetime TEXT,
                trade_datetime TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source_chat_id, source_message_id)
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_open ON messages(source_chat_id, symbol, is_closed)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_reports (
                report_type TEXT NOT NULL,
                report_key TEXT NOT NULL,
                sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (report_type, report_key)
            )
            """
        )


def report_was_sent(report_type, report_key):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM sent_reports WHERE report_type = ? AND report_key = ?",
            (str(report_type), str(report_key)),
        ).fetchone()
        return row is not None


def mark_report_sent(report_type, report_key):
    """Ritorna True solo alla prima registrazione (evita invii duplicati)."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO sent_reports (report_type, report_key)
            VALUES (?, ?)
            ON CONFLICT(report_type, report_key) DO NOTHING
            """,
            (str(report_type), str(report_key)),
        )
        return cur.rowcount == 1


def get_message(source_chat_id, source_message_id):
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT * FROM messages WHERE source_chat_id = ? AND source_message_id = ?",
            (source_chat_id, source_message_id),
        )
        return cur.fetchone()


def insert_message(
    *,
    source_chat_id,
    source_message_id,
    symbol=None,
    direction=None,
    entry=None,
    entry_zone_low=None,
    entry_zone_high=None,
    status="RECEIVED",
    source_datetime=None,
    received_datetime=None,
):
    """Idempotente: ritorna True se la riga e' stata creata, False se esisteva gia'."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO messages (
                source_chat_id, source_message_id, symbol, direction,
                entry, entry_zone_low, entry_zone_high, status,
                source_datetime, received_datetime, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(source_chat_id, source_message_id) DO NOTHING
            """,
            (
                source_chat_id, source_message_id, symbol, direction,
                entry, entry_zone_low, entry_zone_high, status,
                source_datetime, received_datetime,
            ),
        )
        return cur.rowcount == 1


def update_copy(source_chat_id, source_message_id, destination_message_id, destination_datetime):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE messages
            SET destination_message_id = ?, destination_datetime = ?,
                status = CASE WHEN status = 'COPYING' THEN 'COPIED' ELSE status END,
                updated_at = CURRENT_TIMESTAMP
            WHERE source_chat_id = ? AND source_message_id = ?
            """,
            (destination_message_id, destination_datetime, source_chat_id, source_message_id),
        )


def update_status(
    source_chat_id, source_message_id, status, *,
    mt5_ticket=None, mt5_deal=None, mt5_volume=None, mt5_price=None,
    mt5_ticket_2=None, mt5_deal_2=None, mt5_volume_2=None, mt5_price_2=None,
    trade_datetime=None, error=None,
):
    fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
    params = [status]

    for column, value, caster in (
        ("mt5_ticket", mt5_ticket, int),
        ("mt5_deal", mt5_deal, int),
        ("mt5_volume", mt5_volume, float),
        ("mt5_price", mt5_price, float),
        ("mt5_ticket_2", mt5_ticket_2, int),
        ("mt5_deal_2", mt5_deal_2, int),
        ("mt5_volume_2", mt5_volume_2, float),
        ("mt5_price_2", mt5_price_2, float),
    ):
        if value is not None:
            fields.append(f"{column} = ?")
            params.append(caster(value))

    if trade_datetime is not None:
        fields.append("trade_datetime = ?")
        params.append(trade_datetime)
    if error is not None:
        fields.append("error = ?")
        params.append(str(error))

    params.extend([source_chat_id, source_message_id])

    with get_connection() as conn:
        cur = conn.execute(
            f"UPDATE messages SET {', '.join(fields)} WHERE source_chat_id = ? AND source_message_id = ?",
            params,
        )
        return cur.rowcount == 1


def get_latest_open_trade(source_chat_id, symbol="XAUUSD"):
    """
    Trade piu' recente aperto dal bot in questo canale, indipendentemente
    dal fatto che SL/TP siano gia' stati applicati. Usato sia per associare
    il messaggio SL/TP al trade giusto, sia dal monitor per BE/chiusura.
    """
    query = """
        SELECT
            source_message_id, destination_message_id, direction, entry,
            sl, tp1, tp2, tp3, tp4, tp_open_runner,
            mt5_ticket, mt5_price, mt5_ticket_2, mt5_price_2,
            sltp_applied, breakeven_applied
        FROM messages
        WHERE source_chat_id = ? AND symbol = ?
          AND status IN ('OPENED', 'SLTP_APPLIED')
          AND mt5_ticket IS NOT NULL
          AND is_closed = 0
        ORDER BY source_message_id DESC
        LIMIT 1
    """
    with get_connection() as conn:
        return conn.execute(query, (source_chat_id, symbol)).fetchone()


def get_latest_trade_awaiting_sltp(source_chat_id, symbol="XAUUSD"):
    """
    Trade aperto piu' recente che NON ha ancora ricevuto SL/TP.
    Usata per il primo messaggio SL/TP in arrivo: se ci sono piu' trade
    aperti in parallelo, evita di riassociare per errore un secondo
    messaggio SL/TP al trade sbagliato (quello gia' completato).
    """
    query = """
        SELECT
            source_message_id, destination_message_id, direction, entry,
            sl, tp1, tp2, tp3, tp4, tp_open_runner,
            mt5_ticket, mt5_price, mt5_ticket_2, mt5_price_2,
            sltp_applied, breakeven_applied
        FROM messages
        WHERE source_chat_id = ? AND symbol = ?
          AND status = 'OPENED'
          AND sltp_applied = 0
          AND mt5_ticket IS NOT NULL
          AND is_closed = 0
        ORDER BY source_message_id ASC
        LIMIT 1
    """
    with get_connection() as conn:
        return conn.execute(query, (source_chat_id, symbol)).fetchone()


def get_open_trades(source_chat_id, symbol="XAUUSD"):
    """Tutti i trade ancora aperti (per il monitor BE/chiusura)."""
    query = """
        SELECT
            source_message_id, destination_message_id, direction, entry,
            sl, tp1, tp2, tp3, tp4, tp_open_runner,
            mt5_ticket, mt5_price, mt5_ticket_2, mt5_price_2,
            sltp_applied, breakeven_applied
        FROM messages
        WHERE source_chat_id = ? AND symbol = ?
          AND status IN ('OPENED', 'SLTP_APPLIED')
          AND mt5_ticket IS NOT NULL
          AND is_closed = 0
        ORDER BY source_message_id ASC
    """
    with get_connection() as conn:
        return conn.execute(query, (source_chat_id, symbol)).fetchall()


def update_trade_sltp(source_chat_id, source_message_id, sl, tp1, tp2, tp3, tp4, tp_open_runner):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE messages
            SET sl = ?, tp1 = ?, tp2 = ?, tp3 = ?, tp4 = ?, tp_open_runner = ?,
                sltp_applied = 1, status = 'SLTP_APPLIED', updated_at = CURRENT_TIMESTAMP
            WHERE source_chat_id = ? AND source_message_id = ?
            """,
            (sl, tp1, tp2, tp3, tp4, 1 if tp_open_runner else 0, source_chat_id, source_message_id),
        )


def mark_breakeven_applied(source_chat_id, source_message_id, new_sl):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE messages
            SET sl = ?, breakeven_applied = 1, updated_at = CURRENT_TIMESTAMP
            WHERE source_chat_id = ? AND source_message_id = ?
            """,
            (float(new_sl), source_chat_id, source_message_id),
        )


def get_trade_by_primary_ticket(mt5_ticket):
    """Riga (source_chat_id, source_message_id, destination_message_id,
    breakeven_applied) del trade associato a un ticket del conto
    principale. Usata dal recovery all'avvio e dai report (per sapere
    se una posizione chiusa aveva ricevuto il Break Even)."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT source_chat_id, source_message_id, destination_message_id, breakeven_applied
            FROM messages
            WHERE mt5_ticket = ?
            ORDER BY source_message_id DESC
            LIMIT 1
            """,
            (int(mt5_ticket),),
        )
        return cur.fetchone()


def adopt_orphan_position(
    source_chat_id, source_message_id, *, direction, entry, sl, tp3,
    mt5_ticket, mt5_volume, mt5_price, status,
):
    """
    Crea una riga DB sintetica per una posizione MT5 trovata aperta al
    recovery senza alcuna riga corrispondente (es. crash tra l'apertura
    dell'ordine e la scrittura su DB). source_message_id e' negativo
    (-ticket) per non entrare mai in conflitto con id reali di Telegram.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO messages (
                source_chat_id, source_message_id, symbol, direction,
                entry, sl, tp3, sltp_applied, status,
                mt5_ticket, mt5_volume, mt5_price,
                created_at, updated_at
            )
            VALUES (?, ?, 'XAUUSD', ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(source_chat_id, source_message_id) DO NOTHING
            """,
            (
                source_chat_id, source_message_id, direction, entry, sl, tp3,
                1 if tp3 else 0, status, mt5_ticket, mt5_volume, mt5_price,
            ),
        )
        return cur.rowcount == 1


def mark_closed(source_chat_id, source_message_id):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE messages
            SET is_closed = 1, status = 'CLOSED', updated_at = CURRENT_TIMESTAMP
            WHERE source_chat_id = ? AND source_message_id = ?
            """,
            (source_chat_id, source_message_id),
        )
