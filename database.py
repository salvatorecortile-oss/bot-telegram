import sqlite3
from pathlib import Path
from datetime import datetime, time as dt_time, timezone
from zoneinfo import ZoneInfo

from config import DATA_DIR

DB_PATH = Path(DATA_DIR) / "copier.db"


def get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False,
    )
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
                sl REAL,
                tp1 REAL,
                status TEXT NOT NULL,
                mt5_ticket INTEGER,
                mt5_deal INTEGER,
                mt5_volume REAL,
                mt5_price REAL,
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
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_status
            ON messages(status)
            """
        )


        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_trade_results (
                position_ticket INTEGER PRIMARY KEY,
                source_chat_id INTEGER NOT NULL,
                source_message_id INTEGER NOT NULL,
                symbol TEXT,
                direction TEXT,
                open_price REAL,
                close_price REAL,
                profit_pips REAL NOT NULL,
                close_status TEXT NOT NULL,
                close_datetime TEXT NOT NULL,
                breakeven_applied INTEGER NOT NULL DEFAULT 0,
                trailing_applied INTEGER NOT NULL DEFAULT 0,
                tp3_hit INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_daily_trade_results_close_datetime
            ON daily_trade_results(close_datetime)
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_reports (
                report_date TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_protections (
                position_ticket INTEGER PRIMARY KEY,
                source_chat_id INTEGER NOT NULL,
                source_message_id INTEGER NOT NULL,
                breakeven_applied INTEGER NOT NULL DEFAULT 0,
                breakeven_sl REAL,
                tp3_reached INTEGER NOT NULL DEFAULT 0,
                applied_at TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS weekly_reports (
                report_week TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Migrazione per database creati con la versione precedente.
        columns = {row[1] for row in conn.execute("PRAGMA table_info(trade_protections)").fetchall()}
        if "tp3_reached" not in columns:
            conn.execute("ALTER TABLE trade_protections ADD COLUMN tp3_reached INTEGER NOT NULL DEFAULT 0")


def get_latest_open_trade(source_chat_id, symbol="XAUUSD", direction=None):
    """
    Restituisce il trade più recente ancora aperto dal bot.

    Il campo mt5_ticket contiene il POSITION ticket usato da MT5 per
    modificare/chiudere la posizione.
    """
    query = """
        SELECT
            mt5_ticket,
            source_message_id,
            symbol,
            direction,
            entry,
            sl,
            tp1,
            status,
            mt5_deal,
            mt5_volume,
            mt5_price
        FROM messages
        WHERE source_chat_id = ?
          AND symbol = ?
          AND status IN ('OPENED', 'TP_SET')
          AND mt5_ticket IS NOT NULL
    """
    params = [source_chat_id, symbol]

    if direction is not None:
        query += " AND direction = ?"
        params.append(direction)

    query += " ORDER BY source_message_id DESC LIMIT 1"

    with get_connection() as conn:
        cur = conn.execute(query, params)
        return cur.fetchone()


def get_open_trades(source_chat_id, symbol="XAUUSD"):
    """Restituisce tutte le posizioni del bot ancora aperte nel DB."""
    query = """
        SELECT
            mt5_ticket,
            source_message_id,
            destination_message_id,
            symbol,
            direction,
            entry,
            sl,
            tp1,
            status,
            mt5_deal,
            mt5_volume,
            mt5_price
        FROM messages
        WHERE source_chat_id = ?
          AND symbol = ?
          AND status IN ('OPENED', 'TP_SET')
          AND mt5_ticket IS NOT NULL
        ORDER BY source_message_id ASC
    """
    with get_connection() as conn:
        cur = conn.execute(query, (source_chat_id, symbol))
        return cur.fetchall()


def get_open_trade_by_ticket_any_source(position_ticket, symbol="XAUUSD"):
    """Cerca una posizione aperta per ticket indipendentemente dal source_chat_id.

    Usata esclusivamente dal recovery: non modifica il database e permette di
    recuperare posizioni aperte quando il SOURCE_CHAT configurato e' cambiato.
    """
    query = """
        SELECT
            mt5_ticket,
            source_message_id,
            destination_message_id,
            symbol,
            direction,
            entry,
            sl,
            tp1,
            status,
            mt5_deal,
            mt5_volume,
            mt5_price,
            source_chat_id
        FROM messages
        WHERE mt5_ticket = ?
          AND symbol = ?
          AND status IN ('OPENED', 'TP_SET')
        ORDER BY source_message_id DESC
        LIMIT 1
    """
    with get_connection() as conn:
        return conn.execute(query, (int(position_ticket), symbol)).fetchone()

def get_recovery_candidates(direction, symbol="XAUUSD", limit=20):
    """Trova record DB senza ticket che possono essere associati a una posizione MT5.

    Usato solo dal recovery. Non modifica il database.

    NOTA: 'PARAMS_APPLIED' e' volutamente escluso. Non e' mai lo stato di una
    posizione a se stante: e' lo stato del messaggio di CORREZIONE (SL/TP1)
    applicato a una posizione gia' aperta su un'altra riga (vedi
    process_update_params). Il suo mt5_ticket e' sempre NULL per design, non
    perche' manchi un'associazione: includerlo qui fa si' che il recovery
    scriva il ticket sbagliato su un record storico che non rappresenta
    alcun trade aperto.
    """
    query = """
        SELECT
            source_chat_id, source_message_id, destination_message_id,
            symbol, direction, entry, sl, tp1, status,
            mt5_deal, mt5_volume, mt5_price, source_datetime,
            received_datetime, trade_datetime, created_at
        FROM messages
        WHERE symbol = ?
          AND direction = ?
          AND mt5_ticket IS NULL
          AND status IN ('OPENING_IMMEDIATE', 'OPENED', 'TP_SET', 'COPIED')
        ORDER BY source_message_id DESC
        LIMIT ?
    """
    with get_connection() as conn:
        return conn.execute(query, (symbol, direction, int(limit))).fetchall()


def associate_position_ticket(
    source_chat_id, source_message_id, position_ticket,
    *, mt5_deal=None, mt5_volume=None, mt5_price=None, trade_datetime=None
):
    """Associa un ticket MT5 a una riga DB gia' esistente, senza crearne una nuova.

    Porta anche lo status a 'OPENED' (se non gia' piu' avanzato): senza
    questo, la successiva verifica del recovery (che richiede status
    OPENED/TP_SET) fallirebbe sempre, facendo risultare "non associata"
    una posizione che invece e' stata appena associata correttamente.
    """
    fields = [
        "mt5_ticket = ?",
        "updated_at = CURRENT_TIMESTAMP",
        "status = CASE WHEN status IN ('OPENED', 'TP_SET') THEN status ELSE 'OPENED' END",
    ]
    params = [int(position_ticket)]
    if mt5_deal is not None:
        fields.append("mt5_deal = ?"); params.append(int(mt5_deal))
    if mt5_volume is not None:
        fields.append("mt5_volume = ?"); params.append(float(mt5_volume))
    if mt5_price is not None:
        fields.append("mt5_price = ?"); params.append(float(mt5_price))
    if trade_datetime is not None:
        fields.append("trade_datetime = ?"); params.append(trade_datetime)
    params.extend([source_chat_id, source_message_id])
    with get_connection() as conn:
        cur = conn.execute(
            f"UPDATE messages SET {', '.join(fields)} WHERE source_chat_id = ? AND source_message_id = ? AND mt5_ticket IS NULL",
            params,
        )
        return cur.rowcount == 1


def get_open_trade_for_signal(source_chat_id, symbol, direction, entry):
    """
    Restituisce il trade aperto più recente che corrisponde al segnale
    in arrivo. L'entry è quella indicativa del primo messaggio e serve
    solo ad associare il secondo messaggio alla posizione corretta.
    """
    query = """
        SELECT
            mt5_ticket,
            source_message_id,
            symbol,
            direction,
            entry,
            sl,
            tp1,
            status,
            mt5_deal,
            mt5_volume,
            mt5_price,
            destination_message_id
        FROM messages
        WHERE source_chat_id = ?
          AND symbol = ?
          AND direction = ?
          AND entry = ?
          AND status IN ('OPENED', 'TP_SET')
          AND mt5_ticket IS NOT NULL
        ORDER BY source_message_id DESC
        LIMIT 1
    """
    with get_connection() as conn:
        cur = conn.execute(query, (source_chat_id, symbol, direction, float(entry)))
        return cur.fetchone()


def adopt_orphan_position(
    source_chat_id, symbol, direction, entry, sl, mt5_ticket,
    *, mt5_volume=None, mt5_price=None, trade_datetime=None,
):
    """
    Crea una riga DB sintetica per una posizione MT5 del bot trovata aperta
    al recovery senza NESSUNA riga DB corrispondente (es. crash/riavvio tra
    l'apertura dell'ordine e la scrittura del ticket nel DB, oppure un
    segnale che non era stato riconosciuto dal parser). Usa un
    source_message_id sintetico negativo per non entrare mai in conflitto
    con id reali di Telegram.

    Il campo sl salvato è quello LIVE della posizione al momento del
    recovery: se l'utente ha già applicato manualmente un trailing/SL sulla
    posizione, viene preservato. Il monitor live non lo peggiora mai
    (vedi monitor_trailing_sl_closures in main.py).
    """
    synthetic_message_id = -abs(int(mt5_ticket))
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO messages (
                source_chat_id, source_message_id, symbol, direction,
                entry, sl, tp1, status, mt5_ticket, mt5_volume, mt5_price,
                trade_datetime, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL, 'OPENED', ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(source_chat_id, source_message_id) DO NOTHING
            """,
            (
                int(source_chat_id),
                synthetic_message_id,
                symbol,
                direction,
                float(entry),
                float(sl) if sl else None,
                int(mt5_ticket),
                float(mt5_volume) if mt5_volume is not None else None,
                float(mt5_price) if mt5_price is not None else None,
                trade_datetime,
            ),
        )
        return synthetic_message_id if cur.rowcount == 1 else None


def has_trailing_sl_update(source_chat_id, original_message_id):
    """True se il trade ha ricevuto almeno un trailing SL realmente applicato."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT 1
            FROM messages
            WHERE source_chat_id = ?
              AND source_message_id > ?
              AND status = 'PIPS_SL_APPLIED'
            ORDER BY source_message_id DESC
            LIMIT 1
            """,
            (source_chat_id, original_message_id),
        )
        return cur.fetchone() is not None


def mark_automatic_breakeven(position_ticket, source_chat_id, source_message_id, breakeven_sl):
    """Registra in modo persistente il BE automatico della posizione."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO trade_protections (
                position_ticket, source_chat_id, source_message_id,
                breakeven_applied, breakeven_sl, applied_at
            )
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(position_ticket) DO UPDATE SET
                breakeven_applied = 1,
                breakeven_sl = excluded.breakeven_sl,
                applied_at = excluded.applied_at
            """,
            (
                int(position_ticket),
                int(source_chat_id),
                int(source_message_id),
                float(breakeven_sl),
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def mark_tp3_reached(position_ticket, source_chat_id, source_message_id):
    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO trade_protections (
                position_ticket, source_chat_id, source_message_id,
                breakeven_applied, tp3_reached, applied_at
            ) VALUES (?, ?, ?, 0, 1, ?)
            ON CONFLICT(position_ticket) DO UPDATE SET
                tp3_reached = 1,
                applied_at = excluded.applied_at
            """,
            (int(position_ticket), int(source_chat_id), int(source_message_id), now),
        )


def has_tp3_reached(position_ticket):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT tp3_reached FROM trade_protections WHERE position_ticket = ?",
            (int(position_ticket),),
        ).fetchone()
    return bool(row and int(row[0] or 0))


def has_breakeven_applied(source_chat_id, original_message_id):
    """True se il trade ha ricevuto un Break Even realmente applicato."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT 1
            FROM trade_protections
            WHERE source_chat_id = ?
              AND source_message_id = ?
              AND breakeven_applied = 1
            LIMIT 1
            """,
            (source_chat_id, original_message_id),
        )
        if cur.fetchone() is not None:
            return True

        # Compatibilità con i BE registrati nelle vecchie versioni.
        cur = conn.execute(
            """
            SELECT 1
            FROM messages
            WHERE source_chat_id = ?
              AND source_message_id > ?
              AND status = 'BREAK_EVEN_APPLIED'
            ORDER BY source_message_id DESC
            LIMIT 1
            """,
            (source_chat_id, original_message_id),
        )
        return cur.fetchone() is not None


def get_message(source_chat_id, source_message_id):
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                source_chat_id,
                source_message_id,
                destination_message_id,
                symbol,
                direction,
                entry,
                sl,
                tp1,
                status,
                mt5_ticket,
                mt5_deal,
                mt5_volume,
                mt5_price,
                error,
                source_datetime,
                received_datetime,
                destination_datetime,
                trade_datetime,
                created_at,
                updated_at
            FROM messages
            WHERE source_chat_id = ? AND source_message_id = ?
            """,
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
    sl=None,
    tp1=None,
    status="RECEIVED",
    source_datetime=None,
    received_datetime=None,
):
    """
    Idempotente: non usa INSERT OR REPLACE.
    Restituisce True se la riga è stata creata, False se esiste già.
    """
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO messages (
                source_chat_id,
                source_message_id,
                symbol,
                direction,
                entry,
                sl,
                tp1,
                status,
                source_datetime,
                received_datetime,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(source_chat_id, source_message_id) DO NOTHING
            """,
            (
                source_chat_id,
                source_message_id,
                symbol,
                direction,
                entry,
                sl,
                tp1,
                status,
                source_datetime,
                received_datetime,
            ),
        )
        return cur.rowcount == 1


def update_copy(
    source_chat_id,
    source_message_id,
    destination_message_id,
    destination_datetime,
):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE messages
            SET destination_message_id = ?,
                destination_datetime = ?,
                status = CASE
                    WHEN status = 'COPYING' THEN 'COPIED'
                    ELSE status
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE source_chat_id = ? AND source_message_id = ?
            """,
            (
                destination_message_id,
                destination_datetime,
                source_chat_id,
                source_message_id,
            ),
        )


def update_status(
    source_chat_id,
    source_message_id,
    status,
    *,
    mt5_ticket=None,
    mt5_deal=None,
    mt5_volume=None,
    mt5_price=None,
    trade_datetime=None,
    error=None,
):
    """
    Aggiorna solo i campi passati. Non cancella accidentalmente il ticket
    quando un update successivo non lo specifica.
    """
    fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
    params = [status]

    if mt5_ticket is not None:
        fields.append("mt5_ticket = ?")
        params.append(int(mt5_ticket))

    if mt5_deal is not None:
        fields.append("mt5_deal = ?")
        params.append(int(mt5_deal))

    if mt5_volume is not None:
        fields.append("mt5_volume = ?")
        params.append(float(mt5_volume))

    if mt5_price is not None:
        fields.append("mt5_price = ?")
        params.append(float(mt5_price))

    if trade_datetime is not None:
        fields.append("trade_datetime = ?")
        params.append(trade_datetime)

    if error is not None:
        fields.append("error = ?")
        params.append(str(error))

    params.extend([source_chat_id, source_message_id])

    with get_connection() as conn:
        cur = conn.execute(
            f"""
            UPDATE messages
            SET {", ".join(fields)}
            WHERE source_chat_id = ? AND source_message_id = ?
            """,
            params,
        )
        return cur.rowcount == 1


def set_copying(source_chat_id, source_message_id):
    update_status(source_chat_id, source_message_id, "COPYING")


def set_error(source_chat_id, source_message_id, status, error):
    update_status(
        source_chat_id,
        source_message_id,
        status,
        error=error,
    )


def update_trade_params(source_chat_id, source_message_id, sl, tp1):
    """Salva SL/TP1 ricevuti nel messaggio parametri del trade originale."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE messages
            SET sl = ?,
                tp1 = ?,
                status = 'TP_SET',
                updated_at = CURRENT_TIMESTAMP
            WHERE source_chat_id = ? AND source_message_id = ?
            """,
            (float(sl), float(tp1), source_chat_id, source_message_id),
        )


def update_trade_sl(source_chat_id, source_message_id, new_sl, status="OPENED"):
    """Aggiorna lo SL del trade originale nel database."""
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE messages
            SET sl = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE source_chat_id = ? AND source_message_id = ?
            """,
            (float(new_sl), status, source_chat_id, source_message_id),
        )


def record_daily_trade_result(
    *,
    position_ticket,
    source_chat_id,
    source_message_id,
    symbol,
    direction,
    open_price,
    close_price,
    profit_pips,
    close_status,
    close_datetime,
    breakeven_applied=False,
    trailing_applied=False,
    tp3_hit=False,
):
    """Registra una chiusura reale MT5 una sola volta per position ticket."""
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO daily_trade_results (
                position_ticket,
                source_chat_id,
                source_message_id,
                symbol,
                direction,
                open_price,
                close_price,
                profit_pips,
                close_status,
                close_datetime,
                breakeven_applied,
                trailing_applied,
                tp3_hit
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(position_ticket),
                int(source_chat_id),
                int(source_message_id),
                symbol,
                direction,
                float(open_price),
                float(close_price),
                float(profit_pips),
                close_status,
                close_datetime,
                1 if breakeven_applied else 0,
                1 if trailing_applied else 0,
                1 if tp3_hit else 0,
            ),
        )
        return cur.rowcount == 1


def get_daily_trade_results(report_date, source_chat_id):
    """Restituisce le chiusure reali del giorno in Europe/Rome."""
    italy_tz = ZoneInfo("Europe/Rome")
    start_local = datetime.combine(
        report_date,
        dt_time.min,
        tzinfo=italy_tz,
    )
    end_local = start_local.replace(
        day=start_local.day,
    )
    # Il giorno successivo viene calcolato aggiungendo un giorno al calendario
    # locale; ZoneInfo applica automaticamente l'eventuale cambio DST.
    from datetime import timedelta
    end_local = start_local + timedelta(days=1)

    start_utc = start_local.astimezone(timezone.utc).isoformat()
    end_utc = end_local.astimezone(timezone.utc).isoformat()

    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                position_ticket,
                source_message_id,
                symbol,
                direction,
                open_price,
                close_price,
                profit_pips,
                close_status,
                close_datetime,
                breakeven_applied,
                trailing_applied,
                tp3_hit
            FROM daily_trade_results
            WHERE source_chat_id = ?
              AND close_datetime >= ?
              AND close_datetime < ?
            ORDER BY close_datetime ASC, position_ticket ASC
            """,
            (source_chat_id, start_utc, end_utc),
        )
        return cur.fetchall()


def get_weekly_trade_results(week_start, week_end, source_chat_id):
    """Restituisce le chiusure reali del lunedi-venerdi in Europe/Rome."""
    italy_tz = ZoneInfo("Europe/Rome")
    start_local = datetime.combine(week_start, dt_time.min, tzinfo=italy_tz)
    end_local = datetime.combine(week_end, dt_time.min, tzinfo=italy_tz)
    start_utc = start_local.astimezone(timezone.utc).isoformat()
    end_utc = end_local.astimezone(timezone.utc).isoformat()

    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT
                position_ticket, source_message_id, symbol, direction,
                open_price, close_price, profit_pips, close_status,
                close_datetime, breakeven_applied, trailing_applied, tp3_hit
            FROM daily_trade_results
            WHERE source_chat_id = ?
              AND close_datetime >= ?
              AND close_datetime < ?
            ORDER BY close_datetime ASC, position_ticket ASC
            """,
            (source_chat_id, start_utc, end_utc),
        )
        return cur.fetchall()


def has_weekly_report(report_week):
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT 1 FROM weekly_reports WHERE report_week = ? LIMIT 1",
            (str(report_week),),
        )
        return cur.fetchone() is not None


def mark_weekly_report_sent(report_week):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO weekly_reports (report_week, sent_at) VALUES (?, CURRENT_TIMESTAMP)",
            (str(report_week),),
        )


def has_daily_report(report_date):
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT 1 FROM daily_reports WHERE report_date = ? LIMIT 1",
            (str(report_date),),
        )
        return cur.fetchone() is not None


def mark_daily_report_sent(report_date):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO daily_reports (report_date, sent_at)
            VALUES (?, CURRENT_TIMESTAMP)
            """,
            (str(report_date),),
        )
