"""
Test del flusso completo senza Telegram e senza MT5 veri (entrambi simulati).
Avvio: python tests/test_flow.py
"""
import asyncio
import os
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timezone
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)


# ------------------------------------------------------------------
# MT5 finto
# ------------------------------------------------------------------
class FakeMT5(types.ModuleType):
    POSITION_TYPE_BUY, POSITION_TYPE_SELL = 0, 1
    ORDER_TYPE_BUY, ORDER_TYPE_SELL = 0, 1
    TRADE_ACTION_DEAL, TRADE_ACTION_SLTP = 1, 6
    ORDER_TIME_GTC = 0
    ORDER_FILLING_FOK, ORDER_FILLING_IOC, ORDER_FILLING_RETURN = 0, 1, 2
    SYMBOL_FILLING_FOK, SYMBOL_FILLING_IOC = 1, 2
    TRADE_RETCODE_DONE = 10009
    DEAL_ENTRY_IN, DEAL_ENTRY_OUT = 0, 1
    DEAL_REASON_SL, DEAL_REASON_TP, DEAL_REASON_EXPERT = 4, 5, 3
    ACCOUNT_MARGIN_MODE_RETAIL_HEDGING = 2

    def __init__(self):
        super().__init__("MetaTrader5")
        self.bid, self.ask = 4204.00, 4204.30
        self.positions = {}
        self.deals = []
        self.next_ticket = 1000

    def initialize(self, **kw): return True
    def last_error(self): return (0, "ok")
    def account_info(self): return SimpleNamespace(login=0, server="X", balance=1000.0, margin_mode=2)
    def symbol_select(self, *a): return True

    def symbol_info(self, symbol):
        return SimpleNamespace(visible=True, digits=2, point=0.01, volume_min=0.01, volume_max=100,
                               volume_step=0.01, filling_mode=2, trade_stops_level=0, trade_freeze_level=0,
                               trade_exemode=2)

    def symbol_info_tick(self, symbol): return SimpleNamespace(bid=self.bid, ask=self.ask)

    def positions_get(self, ticket=None, symbol=None):
        if ticket is not None:
            p = self.positions.get(int(ticket))
            return (p,) if p else ()
        return tuple(self.positions.values())

    def history_deals_get(self, ticket=None, position=None):
        if ticket is not None:
            return tuple(d for d in self.deals if d.ticket == ticket)
        return tuple(d for d in self.deals if d.position_id == position)

    def _deal(self, position_id, entry, price, reason):
        self.next_ticket += 1
        d = SimpleNamespace(ticket=self.next_ticket, position_id=position_id, entry=entry, price=price,
                            reason=reason, time_msc=self.next_ticket)
        self.deals.append(d)
        return d

    def order_send(self, req):
        if req["action"] == self.TRADE_ACTION_SLTP:
            self.positions[req["position"]].sl = req["sl"]
            return SimpleNamespace(retcode=10009, order=0, deal=0, price=0, volume=0)
        if "position" in req:  # chiusura
            p = self.positions.pop(req["position"])
            d = self._deal(p.ticket, self.DEAL_ENTRY_OUT, req["price"], self.DEAL_REASON_EXPERT)
            return SimpleNamespace(retcode=10009, order=d.ticket, deal=d.ticket, price=req["price"], volume=p.volume)
        self.next_ticket += 1
        t = self.next_ticket
        self.positions[t] = SimpleNamespace(ticket=t, magic=req["magic"], symbol=req["symbol"], type=req["type"],
                                            volume=req["volume"], price_open=req["price"], price_current=req["price"],
                                            sl=req["sl"], tp=req["tp"], profit=0.0, time=t, time_msc=t)
        d = self._deal(t, self.DEAL_ENTRY_IN, req["price"], self.DEAL_REASON_EXPERT)
        return SimpleNamespace(retcode=10009, order=t, deal=d.ticket, price=req["price"], volume=req["volume"])

    def broker_close(self, ticket, price, reason):
        self.positions.pop(ticket)
        self._deal(ticket, self.DEAL_ENTRY_OUT, price, reason)


# ------------------------------------------------------------------
# Telegram finto
# ------------------------------------------------------------------
class FakeClient:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat, text, parse_mode=None, silent=None, reply_to=None):
        msg = SimpleNamespace(id=500 + len(self.sent), text=text, reply_to=reply_to)
        self.sent.append(msg)
        return msg


def install_fakes(trading):
    os.environ.update({
        "TELEGRAM_API_ID": "1", "TELEGRAM_API_HASH": "x", "TELEGRAM_SOURCE_CHAT": "-100",
        "TELEGRAM_DESTINATION_CHAT": "-200", "TRADING_ENABLED": "true" if trading else "false",
        "MT5_LOGIN": "0", "MAGIC_NUMBER": "26090110",
    })
    telethon = types.ModuleType("telethon")
    telethon.events = SimpleNamespace(NewMessage=lambda **kw: None)
    sys.modules["telethon"] = telethon
    tc = types.ModuleType("telegram_client")
    tc.client = FakeClient()
    sys.modules["telegram_client"] = tc
    fake_mt5 = FakeMT5()
    sys.modules["MetaTrader5"] = fake_mt5
    return tc.client, fake_mt5


def msg(mid, text, reply_to=None):
    return SimpleNamespace(id=mid, raw_text=text, reply_to_msg_id=reply_to, date=datetime.now(timezone.utc))


def event(m):
    return SimpleNamespace(message=m)


async def scenario(trading):
    import test_parser as T
    tg, mt5 = install_fakes(trading)
    import database as db
    db.set_db_path(os.path.join(tempfile.mkdtemp(), "t.db"))
    import main
    db.init_database()
    main.MT5_READY = trading

    # 1) SIGNAL 2 VENDI (multi-obiettivo): TP = obiettivo 1
    await main.source_message_handler(event(msg(10, T.SIGNAL_2_SELL)))
    row = db.get_signal(10)
    assert row["status"] == "OPENED" and row["tp"] == 4169.15, row
    assert "XAUUSD — SELL" in tg.sent[-1].text and "4169.15" in tg.sent[-1].text
    if trading:
        assert row["open_price"] == 4204.00  # entry reale = BID
        pos = mt5.positions[row["position_ticket"]]
        assert (pos.sl, pos.tp) == (4214.33, 4169.15)

    # 2) SIGNAL 4 COMPRA in contemporanea (BUY + SELL aperti insieme)
    mt5.bid, mt5.ask = 4155.00, 4155.30
    await main.source_message_handler(event(msg(11, T.SIGNAL_4_BUY)))
    assert db.get_signal(11)["status"] == "OPENED"
    if trading:
        assert len(mt5.positions) == 2

    # 3) Duplicato dello stesso messaggio: nessun secondo trade
    n = len(tg.sent)
    await main.source_message_handler(event(msg(11, T.SIGNAL_4_BUY)))
    assert len(tg.sent) == n

    # 4) OBIETTIVO RAGGIUNTO su SIGNAL 2
    if trading:
        # MT5 ha gia' chiuso al TP: il messaggio del canale non deve chiudere altro
        mt5.broker_close(row["position_ticket"], 4169.15, mt5.DEAL_REASON_TP)
    await main.source_message_handler(event(msg(12, T.SIGNAL_2_TP, reply_to=10)))
    r = db.get_signal(10)
    assert r["status"] == "CLOSED_TP", r
    assert "TAKE PROFIT RAGGIUNTO" in tg.sent[-1].text and tg.sent[-1].reply_to == row["destination_message_id"]
    print("   TP  ->", tg.sent[-1].text.replace("\n", " | "))

    # 5) Il monitor non deve mandare un secondo messaggio per la stessa chiusura
    n = len(tg.sent)
    await asyncio.wait_for(_one_monitor_pass(main), 5)
    assert len(tg.sent) == n

    # 6) STOP A PAREGGIO dopo il TP: posizione gia' chiusa -> ignorato
    await main.source_message_handler(event(msg(13, T.SIGNAL_2_BE, reply_to=10)))
    assert len(tg.sent) == n

    # 7) BE su SIGNAL 4 (aperto) quando il prezzo e' in profitto
    mt5.bid, mt5.ask = 4180.00, 4180.30
    await main.source_message_handler(event(msg(14, T.SIGNAL_2_BE.replace("SIGNAL 2", "SIGNAL 4"), reply_to=11)))
    r4 = db.get_signal(11)
    assert r4["be_applied"] == 1 and r4["sl"] == r4["open_price"], r4
    assert "BE ATTIVATO" in tg.sent[-1].text
    print("   BE  ->", tg.sent[-1].text.replace("\n", " | "))
    if trading:
        assert mt5.positions[r4["position_ticket"]].sl == r4["open_price"]

    # 7b) BE con prezzo gia' sotto l'ingresso: impossibile su MT5 -> nessun messaggio
    if trading:
        n_be = len(tg.sent)
        mt5.bid, mt5.ask = 4150.00, 4150.30
        await main.source_message_handler(event(msg(16, T.SIGNAL_2_BE.replace("SIGNAL 2", "SIGNAL 4"), reply_to=11)))
        assert len(tg.sent) == n_be

    # 8) STOP dopo il BE: chiusura a pareggio -> "BE PRESO"
    mt5.bid, mt5.ask = 4155.00, 4155.30
    stop_be = T.SIGNAL_3_STOP.replace("SIGNAL 3", "SIGNAL 4").replace("4135,92", "4155,30")
    if trading:
        mt5.broker_close(r4["position_ticket"], r4["open_price"], mt5.DEAL_REASON_SL)
    await main.source_message_handler(event(msg(15, stop_be, reply_to=11)))
    assert db.get_signal(11)["status"] == "CLOSED_BE", db.get_signal(11)
    print("   BE preso ->", tg.sent[-1].text.replace("\n", " | "))

    # 9) SIGNAL 3 COMPRA -> STOP (MT5 ancora aperta: la chiude il bot)
    mt5.bid, mt5.ask = 4160.00, 4160.30
    await main.source_message_handler(event(msg(20, T.SIGNAL_3_BUY)))
    mt5.bid, mt5.ask = 4135.92, 4136.20
    await main.source_message_handler(event(msg(21, T.SIGNAL_3_STOP, reply_to=20)))
    r3 = db.get_signal(20)
    assert r3["status"] == "CLOSED_SL" and r3["pips"] < 0, r3
    print("   SL  ->", tg.sent[-1].text.replace("\n", " | "))

    # 10) SIGNAL 4 VENDI -> CHIUSA (senza reply: riserva per numero SIGNAL)
    mt5.bid, mt5.ask = 4117.69, 4118.00
    await main.source_message_handler(event(msg(30, T.SIGNAL_4_SELL)))
    mt5.bid, mt5.ask = 4086.60, 4086.87
    await main.source_message_handler(event(msg(31, T.SIGNAL_4_CLOSED)))
    r5 = db.get_signal(30)
    assert r5["status"] == "CLOSED_MANUAL" and r5["pips"] > 300, r5
    assert "CHIUSA IN PROFITTO" in tg.sent[-1].text
    print("   CHIUSA ->", tg.sent[-1].text.replace("\n", " | "))

    if trading:
        assert not mt5.positions, mt5.positions
        # 11) TP preso da MT5 senza alcun messaggio: lo rileva il monitor
        await main.source_message_handler(event(msg(40, T.SIGNAL_4_SELL)))
        r6 = db.get_signal(40)
        mt5.broker_close(r6["position_ticket"], 3806.75, mt5.DEAL_REASON_TP)
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert db.get_signal(40)["status"] == "CLOSED_TP"
        print("   Monitor TP ->", tg.sent[-1].text.replace("\n", " | "))

    # 12) Segnale troppo vecchio: ignorato
    old = msg(50, T.SIGNAL_3_BUY)
    old.date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    await main.source_message_handler(event(old))
    assert db.get_signal(50) is None

    print(f"OK - flusso {'MT5 REALE (simulato)' if trading else 'TEST senza MT5'}: {len(tg.sent)} messaggi nel canale.")


async def _one_monitor_pass(main):
    task = asyncio.create_task(main.monitor_closures())
    await asyncio.sleep(0.2)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(scenario(sys.argv[1] == "live"))
    else:
        for mode in ("test", "live"):
            subprocess.run([sys.executable, __file__, mode], check=True)
