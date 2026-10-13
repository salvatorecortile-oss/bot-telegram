"""
Ripara la riga storica #3175, corrotta da un bug del vecchio recovery
(scriveva il ticket/prezzo della posizione ATTUALE su una riga che in
realta' era solo il messaggio di correzione SL/TP1 del trade #3174, gia'
chiuso il 9/9). Il bug e' stato corretto in database.py: questo script
ripara solo il dato gia' scritto in precedenza.

Da eseguire UNA SOLA VOLTA, con il bot FERMO, dalla cartella del bot:
    py fix_corrupted_row.py
"""
import database

database.init_database()

SOURCE_CHAT = -1003543239308
MESSAGE_ID = 3175

with database.get_connection() as conn:
    before = conn.execute(
        "SELECT * FROM messages WHERE source_chat_id = ? AND source_message_id = ?",
        (SOURCE_CHAT, MESSAGE_ID),
    ).fetchone()
    print("PRIMA:", before)

    if before is None:
        print("Riga non trovata: niente da riparare.")
    elif before[9] != 58434375231:
        print(
            "La riga non ha il ticket corrotto atteso (58434375231): "
            "non tocco nulla per sicurezza. Valore trovato:", before[9],
        )
    else:
        conn.execute(
            """
            UPDATE messages
            SET mt5_ticket = NULL,
                mt5_volume = NULL,
                mt5_price = NULL,
                trade_datetime = '2026-09-09T15:36:01.586361+00:00',
                updated_at = CURRENT_TIMESTAMP
            WHERE source_chat_id = ? AND source_message_id = ?
            """,
            (SOURCE_CHAT, MESSAGE_ID),
        )
        conn.commit()
        after = conn.execute(
            "SELECT * FROM messages WHERE source_chat_id = ? AND source_message_id = ?",
            (SOURCE_CHAT, MESSAGE_ID),
        ).fetchone()
        print("DOPO :", after)
        print("Riga ripristinata correttamente.")
