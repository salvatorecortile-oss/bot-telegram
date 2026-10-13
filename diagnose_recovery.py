"""
Script diagnostico: stampa lo stato del DB relativo al recovery.
Da eseguire con: py diagnose_recovery.py
(mettilo nella stessa cartella di main.py prima di lanciarlo)
"""
import database

database.init_database()

TICKET = 58434375231  # cambia qui se vuoi controllare un altro ticket

with database.get_connection() as conn:
    print("=" * 72)
    print("ULTIME 20 RIGHE DELLA TABELLA messages")
    print("=" * 72)
    rows = conn.execute(
        """
        SELECT source_chat_id, source_message_id, symbol, direction, entry,
               sl, tp1, status, mt5_ticket, created_at, updated_at
        FROM messages
        ORDER BY source_message_id DESC
        LIMIT 20
        """
    ).fetchall()
    for r in rows:
        print(r)

    print()
    print("=" * 72)
    print(f"RIGA CON source_message_id = -{TICKET} (eventuale adozione precedente)")
    print("=" * 72)
    row = conn.execute(
        "SELECT * FROM messages WHERE source_message_id = ?",
        (-TICKET,),
    ).fetchone()
    print(row)

    print()
    print("=" * 72)
    print("CANDIDATE BUY XAUUSD senza ticket (quello che vede il recovery)")
    print("=" * 72)
    candidates = conn.execute(
        """
        SELECT source_chat_id, source_message_id, symbol, direction, entry,
               sl, tp1, status, mt5_ticket, created_at
        FROM messages
        WHERE symbol = 'XAUUSD'
          AND direction = 'BUY'
          AND mt5_ticket IS NULL
          AND status IN ('OPENING_IMMEDIATE', 'OPENED', 'TP_SET', 'PARAMS_APPLIED', 'COPIED')
        ORDER BY source_message_id DESC
        LIMIT 20
        """
    ).fetchall()
    for c in candidates:
        print(c)
    print(f"\nTOTALE CANDIDATE: {len(candidates)}")

    print()
    print("=" * 72)
    print(f"RIGA CON mt5_ticket = {TICKET} (qualsiasi status)")
    print("=" * 72)
    row2 = conn.execute(
        "SELECT * FROM messages WHERE mt5_ticket = ?",
        (TICKET,),
    ).fetchone()
    print(row2)
