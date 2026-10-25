"""Test della sala segnali con un finto MT5 (nessun Telegram, nessun MT5 vero)."""
import asyncio
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import database as db  # noqa: E402
import reports  # noqa: E402
from tracker import MAX_CLOSE_ATTEMPTS, Tracker, display_symbol  # noqa: E402

NOW = 1_800_000_000


class FakeReader:
    def __init__(self):
        self.positions = {}
        self.closed = {}
        self.fail = False

    def add(self, ticket, direction="BUY", price=4000.0, sl=3990.0, tp=4020.0, magic=61800, age=0):
        self.positions[ticket] = {
            "ticket": ticket, "magic": magic, "symbol": "XAUUSD-P", "direction": direction,
            "open_price": price, "sl": sl, "tp": tp, "volume": 0.01, "time": NOW - age, "profit": 0.0,
        }

    def close(self, ticket, price, reason, profit=0.0):
        self.positions.pop(ticket)
        self.closed[ticket] = {"price": price, "reason": reason, "profit": profit}

    def get_positions(self):
        return None if self.fail else list(self.positions.values())

    def server_now(self, symbol):
        return NOW

    def get_close_info(self, ticket):
        return self.closed.get(ticket)


class FakeTelegram:
    def __init__(self):
        self.sent = []

    async def send(self, text, reply_to=None):
        self.sent.append((text, reply_to))
        return 100 + len(self.sent)


class TrackerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db.set_db_path(Path(self.tmp.name) / "test.db")
        db.init_database()
        self.mt5 = FakeReader()
        self.tg = FakeTelegram()
        self.tracker = Tracker(self.mt5, self.tg.send)
        self.sync()  # primo giro a conto vuoto

    def tearDown(self):
        self.tmp.cleanup()

    def sync(self):
        asyncio.run(self.tracker.sync())

    def test_apertura_e_chiusura_al_tp(self):
        self.mt5.add(1, "BUY", 4000.0, 3990.0, 4020.0)
        self.sync()
        self.assertEqual(len(self.tg.sent), 1)
        text, reply = self.tg.sent[0]
        self.assertIn("XAUUSD — BUY", text)
        self.assertNotIn("XAUUSD-P", text)
        self.assertIn("4000.00", text)
        self.assertIn("3990.00", text)
        self.assertIn("4020.00", text)
        self.assertIsNone(reply)

        self.sync()  # niente di nuovo: nessun messaggio
        self.assertEqual(len(self.tg.sent), 1)

        self.mt5.close(1, 4020.0, "TP", 20.0)
        self.sync()
        self.sync()
        self.assertEqual(len(self.tg.sent), 2)
        text, reply = self.tg.sent[1]
        self.assertIn("TAKE PROFIT RAGGIUNTO", text)
        self.assertIn("+200", text)
        self.assertEqual(reply, 101)

    def test_sell_senza_tp_chiusa_dal_bot(self):
        self.mt5.add(2, "SELL", 4000.0, 4010.0, 0.0, magic=54001)
        self.sync()
        self.assertIn("chiusura a segnale", self.tg.sent[0][0])
        self.mt5.close(2, 3995.5, "OTHER", 4.5)
        self.sync()
        self.assertIn("CHIUSA IN PROFITTO", self.tg.sent[1][0])
        self.assertIn("+45", self.tg.sent[1][0])

    def test_stop_loss(self):
        self.mt5.add(3, "BUY", 4000.0, 3990.0, 4030.0)
        self.sync()
        self.mt5.close(3, 3990.0, "SL", -10.0)
        self.sync()
        self.assertIn("STOP LOSS PRESO", self.tg.sent[1][0])
        self.assertIn("-100", self.tg.sent[1][0])

    def test_break_even_e_be_preso(self):
        self.mt5.add(4, "BUY", 4000.0, 3990.0, 4030.0)
        self.sync()
        self.mt5.positions[4]["sl"] = 4000.0
        self.sync()
        self.assertIn("BE ATTIVATO", self.tg.sent[1][0])
        self.assertEqual(self.tg.sent[1][1], 101)
        self.mt5.close(4, 4000.0, "SL", 0.0)
        self.sync()
        self.assertIn("BE PRESO", self.tg.sent[2][0])

    def test_tp_cambiato(self):
        self.mt5.add(5, "SELL", 4000.0, 4010.0, 3980.0)
        self.sync()
        self.mt5.positions[5]["tp"] = 3970.0
        self.sync()
        self.assertIn("TP IMPOSTATO A 3970.00", self.tg.sent[1][0])

    def test_altri_magic_ignorati_dal_lettore(self):
        # il filtro sui magic sta in mt5_reader: qui basta che il tracker pubblichi solo cio' che riceve
        self.sync()
        self.assertEqual(self.tg.sent, [])

    def test_mt5_non_risponde_non_chiude_niente(self):
        self.mt5.add(6)
        self.sync()
        self.mt5.fail = True
        self.sync()
        self.assertEqual(len(self.tg.sent), 1)
        self.assertEqual(len(db.get_open_trades()), 1)

    def test_storico_in_ritardo(self):
        self.mt5.add(7)
        self.sync()
        self.mt5.positions.pop(7)
        self.sync()  # non ancora nello storico: aspetta
        self.assertEqual(len(self.tg.sent), 1)
        self.mt5.closed[7] = {"price": 4010.0, "reason": "OTHER", "profit": 10.0}
        self.sync()
        self.assertIn("CHIUSA IN PROFITTO", self.tg.sent[1][0])

    def test_storico_mai_arrivato(self):
        self.mt5.add(8)
        self.sync()
        self.mt5.positions.pop(8)
        for _ in range(MAX_CLOSE_ATTEMPTS):
            self.sync()
        self.assertEqual(db.get_open_trades(), [])
        self.assertEqual(len(self.tg.sent), 1)

    def test_pausa(self):
        self.tracker.publishing = False
        self.mt5.add(9)
        self.sync()
        self.assertEqual(self.tg.sent, [])
        self.tracker.publishing = True
        self.mt5.close(9, 4020.0, "TP")
        self.sync()
        self.assertEqual(self.tg.sent, [])  # mai pubblicata: niente chiusura

    def test_report_conta_solo_le_pubblicate(self):
        self.mt5.add(10, "BUY", 4000.0, 3990.0, 4020.0)
        self.sync()
        self.mt5.close(10, 4020.0, "TP")
        self.tracker.publishing = False
        self.mt5.add(11, "BUY", 4000.0, 3990.0, 4020.0)
        self.sync()
        self.mt5.close(11, 3990.0, "SL")
        self.sync()
        now = datetime.now(timezone.utc)
        rows = db.get_closed_between(now - timedelta(hours=1), now + timedelta(hours=1))
        self.assertEqual([r["ticket"] for r in rows], [10])
        text = reports.daily_report_text(reports.now_italy().date())
        self.assertIn("Operazioni chiuse: 1", text)
        self.assertIn("TOT +200 PIPS", text)


class AvvioTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db.set_db_path(Path(self.tmp.name) / "test.db")
        db.init_database()

    def tearDown(self):
        self.tmp.cleanup()

    def test_posizioni_gia_aperte_all_avvio(self):
        mt5, tg = FakeReader(), FakeTelegram()
        mt5.add(1, age=60)      # aperta da 1 minuto: pubblicata
        mt5.add(2, age=3600)    # aperta da 1 ora: seguita in silenzio
        tracker = Tracker(mt5, tg.send)
        asyncio.run(tracker.sync())
        self.assertEqual(len(tg.sent), 1)
        mt5.close(2, 4020.0, "TP")
        asyncio.run(tracker.sync())
        self.assertEqual(len(tg.sent), 1)

    def test_riavvio_non_ripubblica(self):
        mt5, tg = FakeReader(), FakeTelegram()
        mt5.add(1)
        asyncio.run(Tracker(mt5, tg.send).sync())
        asyncio.run(Tracker(mt5, tg.send).sync())  # nuovo processo, stesso database
        self.assertEqual(len(tg.sent), 1)
        mt5.close(1, 4020.0, "TP")
        asyncio.run(Tracker(mt5, tg.send).sync())
        self.assertEqual(tg.sent[1][1], 101)


class SimboloTest(unittest.TestCase):
    def test_display_symbol(self):
        self.assertEqual(display_symbol("XAUUSD-P"), "XAUUSD")
        self.assertEqual(display_symbol("XAUUSD.r"), "XAUUSD")
        self.assertEqual(display_symbol("XAUUSDm"), "XAUUSD")
        self.assertEqual(display_symbol("XAUUSD"), "XAUUSD")


if __name__ == "__main__":
    unittest.main()
