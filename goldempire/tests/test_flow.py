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
    TRADE_ACTION_PENDING, TRADE_ACTION_REMOVE = 5, 8
    ORDER_TYPE_BUY_LIMIT, ORDER_TYPE_SELL_LIMIT, ORDER_TYPE_BUY_STOP, ORDER_TYPE_SELL_STOP = 2, 3, 4, 5
    ORDER_STATE_CANCELED, ORDER_STATE_FILLED = 2, 4
    TRADE_RETCODE_PLACED = 10008
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
        self.orders = {}
        self.history_orders = {}
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

    def orders_get(self, ticket=None):
        o = self.orders.get(int(ticket))
        return (o,) if o else ()

    def history_orders_get(self, ticket=None):
        o = self.history_orders.get(int(ticket))
        return (o,) if o else ()

    def history_deals_get(self, ticket=None, position=None):
        if ticket is not None:  # ticket = ordine che ha generato il deal
            return tuple(d for d in self.deals if d.order == ticket)
        return tuple(d for d in self.deals if d.position_id == position)

    def _deal(self, position_id, entry, price, reason):
        self.next_ticket += 1
        d = SimpleNamespace(ticket=self.next_ticket, order=position_id, position_id=position_id, entry=entry,
                            price=price, reason=reason, time_msc=self.next_ticket, volume=0.01)
        self.deals.append(d)
        return d

    def order_send(self, req):
        if req["action"] == self.TRADE_ACTION_PENDING:
            self.next_ticket += 1
            self.orders[self.next_ticket] = SimpleNamespace(ticket=self.next_ticket, **req)
            return SimpleNamespace(retcode=10008, order=self.next_ticket, deal=0, price=req["price"], volume=req["volume"])
        if req["action"] == self.TRADE_ACTION_REMOVE:
            o = self.orders.pop(req["order"])
            self.history_orders[o.ticket] = SimpleNamespace(ticket=o.ticket, state=self.ORDER_STATE_CANCELED)
            return SimpleNamespace(retcode=10009, order=o.ticket, deal=0, price=0, volume=0)
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

    def fill_pending(self, ticket):
        """Il prezzo raggiunge l'ordine pendente: diventa una posizione con lo stesso ticket."""
        o = self.orders.pop(ticket)
        is_buy = o.type in (self.ORDER_TYPE_BUY_LIMIT, self.ORDER_TYPE_BUY_STOP)
        self.positions[ticket] = SimpleNamespace(
            ticket=ticket, magic=o.magic, symbol=o.symbol, type=self.POSITION_TYPE_BUY if is_buy else self.POSITION_TYPE_SELL,
            volume=o.volume, price_open=o.price, price_current=o.price, sl=o.sl, tp=o.tp, profit=0.0,
            time=ticket, time_msc=ticket)
        self.history_orders[ticket] = SimpleNamespace(ticket=ticket, state=self.ORDER_STATE_FILLED)
        self._deal(ticket, self.DEAL_ENTRY_IN, o.price, self.DEAL_REASON_EXPERT)

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

    # 11b) Segnale senza TP: aperto con il solo SL, chiuso dal messaggio del canale
    mt5.bid, mt5.ask = 4118.50, 4118.78
    await main.source_message_handler(event(msg(60, T.SIGNAL_5_BUY_NO_TP)))
    r7 = db.get_signal(60)
    assert r7["status"] == "OPENED" and r7["tp"] is None, r7
    assert "chiusura a segnale" in tg.sent[-1].text, tg.sent[-1].text
    print("   Apertura senza TP ->", tg.sent[-1].text.replace("\n", " | "))
    if trading:
        pos = mt5.positions[r7["position_ticket"]]
        assert (pos.sl, pos.tp) == (3871.65, 0.0), (pos.sl, pos.tp)
    assert "a segnale" in main.status_text()
    mt5.bid, mt5.ask = 4150.00, 4150.30
    close5 = "🟠 SIGNAL 5 – CHIUSA\n\nUscita 4150,00\nRisultato +312,2 pips"
    await main.source_message_handler(event(msg(61, close5, reply_to=60)))
    assert db.get_signal(60)["status"] == "CLOSED_MANUAL", db.get_signal(60)
    print("   Chiusura a segnale ->", tg.sent[-1].text.replace("\n", " | "))

    if trading:
        # 13) BUY LIMIT sotto il prezzo: ordine pendente, nessun messaggio finche' non viene eseguito
        mt5.bid, mt5.ask = 4140.00, 4140.30
        n = len(tg.sent)
        limit_buy = T.SIGNAL_2_BUY_NEW.replace("XAUUSD BUY", "XAUUSD BUY LIMIT")
        await main.source_message_handler(event(msg(70, limit_buy)))
        r8 = db.get_signal(70)
        assert r8["status"] == "PENDING" and r8["order_ticket"] in mt5.orders, r8
        o = mt5.orders[r8["order_ticket"]]
        assert (o.type, o.price, o.sl, o.tp) == (mt5.ORDER_TYPE_BUY_LIMIT, 4137.44, 4131.13, 4163.40)
        assert len(tg.sent) == n and "pendenti (1)" in main.status_text()
        # Eseguito: il monitor lo registra e lo pubblica con l'entry reale
        mt5.fill_pending(r8["order_ticket"])
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        r8 = db.get_signal(70)
        assert r8["status"] == "OPENED" and r8["position_ticket"] == r8["order_ticket"], r8
        assert "XAUUSD — BUY" in tg.sent[-1].text and "4137.44" in tg.sent[-1].text
        print("   LIMIT eseguito ->", tg.sent[-1].text.replace("\n", " | "))
        # Poi TP dal canale: chiusura normale
        mt5.bid, mt5.ask = 4163.40, 4163.70
        await main.source_message_handler(event(msg(71, "🟣 SIGNAL 2 – TP1 RAGGIUNTO ✅", reply_to=70)))
        assert db.get_signal(70)["status"] == "CLOSED_TP"

        # 14) SELL LIMIT mai eseguito e annullato dal canale: nessun messaggio nel canale
        n = len(tg.sent)
        sell_limit = (T.SIGNAL_2_BUY_NEW.replace("XAUUSD BUY", "XAUUSD SELL LIMIT")
                      .replace("4137,44", "4180,00").replace("4163,40", "4150,00").replace("4131,13", "4195,00"))
        await main.source_message_handler(event(msg(80, sell_limit)))
        r9 = db.get_signal(80)
        assert r9["status"] == "PENDING", r9
        await main.source_message_handler(event(msg(81, "🟣 SIGNAL 2 – ORDINE ANNULLATO", reply_to=80)))
        assert db.get_signal(80)["status"] == "CANCELED" and r9["order_ticket"] not in mt5.orders
        assert len(tg.sent) == n

        # 15) BUY LIMIT con prezzo gia' sotto l'ingresso: aperto subito a mercato
        mt5.bid, mt5.ask = 4135.00, 4135.30
        await main.source_message_handler(event(msg(90, limit_buy)))
        r10 = db.get_signal(90)
        assert r10["status"] == "OPENED" and r10["open_price"] == 4135.30, r10

        # 16) Pendente scaduto: annullato dal monitor
        mt5.bid, mt5.ask = 4140.00, 4140.30
        await main.source_message_handler(event(msg(95, limit_buy)))
        with db.get_connection() as conn:
            conn.execute("UPDATE signals SET pending_since = '2020-01-01T00:00:00+00:00' WHERE source_message_id = 95")
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert db.get_signal(95)["status"] == "EXPIRED", db.get_signal(95)

    # 17) INVERSIONE SIGNAL 5 / 6
    def strat(no, direction, entry, sl):
        return (f"🟠 SIGNAL {no} – XAUUSD {direction}\n\n📥 Ingresso: {entry}\n\n"
                f"🎯 Uscita: al segnale della strategia\n\n🛑 SL: {sl} (stop d’emergenza)")
    mt5.bid, mt5.ask = 4100.00, 4100.30
    for mid in (100, 101, 102):                      # tre SELL del SIGNAL 5
        await main.source_message_handler(event(msg(mid, strat(5, "SELL", "4100,00", "4350,00"))))
    await main.source_message_handler(event(msg(103, strat(6, "SELL", "4100,00", "4350,00"))))  # SELL del 6
    assert all(db.get_signal(m)["status"] == "OPENED" for m in (100, 101, 102, 103))
    # SIGNAL 4 con TP/SL: non viene toccato dalle inversioni
    await main.source_message_handler(event(msg(104, T.SIGNAL_4_SELL.replace("4117,69", "4100,00"))))
    assert db.get_signal(104)["status"] == "OPENED"

    n = len(tg.sent)
    mt5.bid, mt5.ask = 4080.00, 4080.30
    await main.source_message_handler(event(msg(110, strat(5, "BUY", "4080,30", "3850,00"))))
    for m in (100, 101, 102):
        r = db.get_signal(m)
        assert r["status"] == "CLOSED_MANUAL" and r["pips"] > 0, r
    assert db.get_signal(103)["status"] == "OPENED"       # il SIGNAL 6 resta aperto
    assert db.get_signal(104)["status"] == "OPENED"       # il SIGNAL 4 resta aperto
    assert db.get_signal(110)["status"] == "OPENED" and db.get_signal(110)["direction"] == "BUY"
    new = tg.sent[n:]
    assert len(new) == 4, [m.text for m in new]           # 3 chiusure + 1 apertura
    assert all("CHIUSA IN PROFITTO" in m.text for m in new[:3]) and "XAUUSD — BUY" in new[3].text
    assert [m.reply_to for m in new[:3]] == [db.get_signal(x)["destination_message_id"] for x in (100, 101, 102)]
    print("   Inversione SIGNAL 5 ->", " || ".join(m.text.replace("\n", " | ") for m in new[:1] + new[3:]))
    if trading:
        assert not any(p.type == mt5.POSITION_TYPE_SELL and p.price_open == 4100.00 and p.tp == 0.0
                       and p.ticket in (db.get_signal(x)["position_ticket"] for x in (100, 101, 102))
                       for p in mt5.positions.values())

    # Il SIGNAL 6 BUY chiude solo il SELL del 6
    await main.source_message_handler(event(msg(111, strat(6, "BUY", "4080,30", "3850,00"))))
    assert db.get_signal(103)["status"] == "CLOSED_MANUAL" and db.get_signal(110)["status"] == "OPENED"

    # SIGNAL 4 opposto (non e' di inversione): il SELL del 4 resta aperto
    await main.source_message_handler(event(msg(112, T.SIGNAL_4_BUY.replace("4155,08", "4080,30"))))
    assert db.get_signal(104)["status"] == "OPENED"

    # Inversione in ritardo: chiude il BUY del 5 ma NON apre il nuovo SELL
    mt5.bid, mt5.ask = 4090.00, 4090.30
    late = msg(113, strat(5, "SELL", "4090,00", "4350,00"))
    late.date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    await main.source_message_handler(event(late))
    assert db.get_signal(110)["status"] == "CLOSED_MANUAL" and db.get_signal(113) is None

    # In pausa: chiude gli opposti ma non apre
    await main.source_message_handler(event(msg(114, strat(5, "BUY", "4090,30", "3850,00"))))
    main.BOT_STATE = "PAUSED"
    await main.source_message_handler(event(msg(115, strat(5, "SELL", "4090,00", "4350,00"))))
    assert db.get_signal(114)["status"] == "CLOSED_MANUAL"
    assert db.get_signal(115)["status"] == "PAUSED_NO_NEW_TRADE"
    main.BOT_STATE = "RUNNING"

    # 18) 3 SELL del SIGNAL 5: "CHIUSA" in reply chiude solo quella, il BUY chiude le restanti
    mt5.bid, mt5.ask = 4100.00, 4100.30
    for mid in (120, 121, 122):
        await main.source_message_handler(event(msg(mid, strat(5, "SELL", "4100,00", "4350,00"))))
    mt5.bid, mt5.ask = 4090.00, 4090.30
    close_reply = "🟠 SIGNAL 5 – OPERAZIONE CHIUSA"
    await main.source_message_handler(event(msg(123, close_reply, reply_to=122)))  # ultimo SELL
    assert [db.get_signal(m)["status"] for m in (120, 121, 122)] == ["OPENED", "OPENED", "CLOSED_MANUAL"]
    await main.source_message_handler(event(msg(124, close_reply, reply_to=120)))  # primo SELL
    assert [db.get_signal(m)["status"] for m in (120, 121, 122)] == ["CLOSED_MANUAL", "OPENED", "CLOSED_MANUAL"]
    # Il SIGNAL 6 non e' toccato dalle chiusure del 5
    await main.source_message_handler(event(msg(125, strat(6, "SELL", "4090,00", "4350,00"))))
    n = len(tg.sent)
    await main.source_message_handler(event(msg(126, strat(5, "BUY", "4090,30", "3850,00"))))
    assert db.get_signal(121)["status"] == "CLOSED_MANUAL" and db.get_signal(125)["status"] == "OPENED"
    assert len(tg.sent) - n == 2  # una sola chiusura (l'unico SELL rimasto) + apertura BUY
    # Messaggio di chiusura arrivato dopo il BUY: gia' chiusa, nessun doppione
    await main.source_message_handler(event(msg(127, close_reply, reply_to=121)))
    assert len(tg.sent) - n == 2

    if trading:
        # 19) TP impostato a mano su MT5: il bot lo comunica in reply al segnale, una volta sola
        mt5.bid, mt5.ask = 4100.00, 4100.30
        await main.source_message_handler(event(msg(130, strat(5, "SELL", "4100,00", "4350,00"))))
        r = db.get_signal(130)
        n = len(tg.sent)
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert len(tg.sent) == n                          # nessuna modifica: nessun messaggio
        mt5.positions[r["position_ticket"]].tp = 4050.00  # TP messo a mano
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert len(tg.sent) == n + 1 and "TP IMPOSTATO A 4050.00" in tg.sent[-1].text
        assert tg.sent[-1].reply_to == r["destination_message_id"] and db.get_signal(130)["tp"] == 4050.00
        print("   TP manuale ->", tg.sent[-1].text)
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert len(tg.sent) == n + 1                      # nessun doppione
        assert "TP 4050.00" in main.status_text()
        mt5.positions[r["position_ticket"]].tp = 0.0      # TP tolto a mano
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert "TP RIMOSSO" in tg.sent[-1].text and db.get_signal(130)["tp"] is None
        mt5.positions[r["position_ticket"]].tp = 4050.00
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        # TP preso da MT5: messaggio di TP raggiunto
        mt5.broker_close(r["position_ticket"], 4050.00, mt5.DEAL_REASON_TP)
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert db.get_signal(130)["status"] == "CLOSED_TP" and "TAKE PROFIT RAGGIUNTO" in tg.sent[-1].text

    if trading:
        # 20) SL modificato a mano: avvicinato -> "IMPOSTATO A", in profitto -> "BE ATTIVATO"
        mt5.bid, mt5.ask = 4100.00, 4100.30
        await main.source_message_handler(event(msg(140, strat(6, "SELL", "4100,00", "4350,00"))))
        r = db.get_signal(140)
        pos = mt5.positions[r["position_ticket"]]
        n = len(tg.sent)
        pos.sl = 4150.00                                   # avvicinato, ancora in perdita
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert len(tg.sent) == n + 1 and "STOP LOSS IMPOSTATO A 4150.00" in tg.sent[-1].text, tg.sent[-1].text
        assert tg.sent[-1].reply_to == r["destination_message_id"] and not db.get_signal(140)["be_applied"]
        print("   SL avvicinato ->", tg.sent[-1].text)
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert len(tg.sent) == n + 1                       # nessun doppione
        pos.sl = 4100.00                                   # all'ingresso (SELL) -> BE
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert "BE ATTIVATO" in tg.sent[-1].text and db.get_signal(140)["be_applied"] == 1
        print("   SL in profitto ->", tg.sent[-1].text.replace("\n", " | "))
        pos.sl = 4090.00                                   # ancora piu' in profitto
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert "STOP LOSS IN PROFITTO A 4090.00" in tg.sent[-1].text
        print("   SL spostato di nuovo ->", tg.sent[-1].text)
        assert len(tg.sent) == n + 3
        # Il BE fatto dal bot su messaggio del canale NON genera un secondo messaggio
        await main.source_message_handler(event(msg(141, strat(6, "SELL", "4100,00", "4350,00"))))
        r2 = db.get_signal(141)
        mt5.bid, mt5.ask = 4080.00, 4080.30
        await main.source_message_handler(event(msg(142, "🟠 SIGNAL 6 – STOP A PAREGGIO", reply_to=141)))
        m = len(tg.sent)
        await asyncio.wait_for(_one_monitor_pass(main), 5)
        assert len(tg.sent) == m and db.get_signal(141)["be_applied"] == 1

    # 21) Chiusure scritte a parole ("Chiudiamo...")
    mt5.bid, mt5.ask = 4155.00, 4155.30
    await main.source_message_handler(event(msg(150, T.SIGNAL_4_BUY)))                # SIGNAL 4
    await main.source_message_handler(event(msg(151, T.SIGNAL_3_BUY.replace("4160,08", "4155,30"))))  # SIGNAL 3, piu' recente
    await main.source_message_handler(event(msg(152, strat(5, "BUY", "4155,30", "3900,00"))))  # SIGNAL 5, ignorato
    main._last_free_close["at"] = 0.0
    mt5.bid, mt5.ask = 4158.00, 4158.30
    n = len(tg.sent)
    await main.source_message_handler(event(msg(153, "CHIUDIAMO UN SEGNALE SENZA IL TP SEGNATO...")))
    assert db.get_signal(151)["status"] == "CLOSED_MANUAL"          # la piu' recente (non 5/6)
    assert db.get_signal(150)["status"] == "OPENED" and db.get_signal(152)["status"] == "OPENED"
    assert len(tg.sent) == n + 1 and tg.sent[-1].reply_to == db.get_signal(151)["destination_message_id"]
    print("   Chiusura a parole ->", tg.sent[-1].text.replace("\n", " | "))
    # Secondo messaggio subito dopo ("Chiudiamo quindi 1 trade su 4"): stessa chiusura, ignorato
    await main.source_message_handler(event(msg(154, "Chiudiamo quindi 1 trade su 4")))
    assert db.get_signal(150)["status"] == "OPENED" and len(tg.sent) == n + 1
    # Il primo messaggio viene poi modificato: gia' gestito, ignorato
    await main.source_edited_handler(event(msg(153, "CHIUDIAMO UN SEGNALE SENZA IL TP SEGNATO... (modificato)")))
    assert db.get_signal(150)["status"] == "OPENED"
    # In reply a un SIGNAL 5: non viene toccato
    await main.source_message_handler(event(msg(155, "Chiudiamo", reply_to=152)))
    assert db.get_signal(152)["status"] == "OPENED"
    # In reply a un segnale preciso: chiude quello, anche subito dopo un'altra chiusura
    await main.source_message_handler(event(msg(156, "Chiudete questo", reply_to=150)))
    assert db.get_signal(150)["status"] == "CLOSED_MANUAL"
    # Frase che non e' una chiusura: niente
    m = len(tg.sent)
    main._last_free_close["at"] = 0.0
    await main.source_message_handler(event(msg(157, "Non chiudiamo ancora, lasciamo correre")))
    assert len(tg.sent) == m

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
