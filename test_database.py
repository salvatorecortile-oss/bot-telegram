import tempfile
from pathlib import Path

import database


with tempfile.TemporaryDirectory() as tmp:
    old_path = database.DB_PATH
    database.DB_PATH = Path(tmp) / "test.db"

    try:
        database.init_database()

        assert database.insert_message(
            source_chat_id=1,
            source_message_id=10,
            status="COPYING",
        ) is True

        # Second insert: deve essere ignorato, non sostituire la riga.
        assert database.insert_message(
            source_chat_id=1,
            source_message_id=10,
            status="WAITING_ENTRY",
        ) is False

        row = database.get_message(1, 10)
        assert row is not None
        assert row[8] == "COPYING"

        database.update_copy(1, 10, 99, "2026-09-02T20:00:00+00:00")
        database.update_status(
            1,
            10,
            "OPENED",
            mt5_ticket=123,
            mt5_deal=456,
            mt5_volume=0.01,
            mt5_price=4372.15,
        )

        # Un update successivo NON deve cancellare ticket/deal.
        database.update_status(1, 10, "OPENED")

        row = database.get_message(1, 10)
        assert row[2] == 99
        assert row[8] == "OPENED"
        assert row[9] == 123
        assert row[10] == 456
        assert row[11] == 0.01
        assert row[12] == 4372.15

        print("OK - database idempotency/update test superato.")
    finally:
        database.DB_PATH = old_path
