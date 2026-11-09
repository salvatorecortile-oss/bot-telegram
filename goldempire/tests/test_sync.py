"""
Test dell'allineamento tra conto principale (master) e copia (follower).
Avvio: python tests/test_sync.py
"""
import asyncio
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

SYNC_FILE = os.environ.setdefault("SYNC_TEST_FILE", os.path.join(tempfile.gettempdir(), f"sync_test_{os.getpid()}.db"))


async def _pass(coro_fn, seconds=0.3):
    task = asyncio.create_task(coro_fn())
    await asyncio.sleep(seconds)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def master():
    os.environ.update({"SYNC_FILE": SYNC_FILE, "SYNC_ROLE": "master"})
    import test_flow as F
    tg, mt5 = F.install_fakes(True)
    import database as db
    db.set_db_path(os.path.join(tempfile.mkdtemp(), "m.db"))
    import main
    import sync
    db.init_database()
    main.MT5_READY = True
    T = __import__("test_parser")

    mt5.bid, mt5.ask = 4100.00, 4100.30
    await main.source_message_handler(F.event(F.msg(10, T.ENTRA_53_SELL)))
    mt5.bid, mt5.ask = 4155.00, 4155.30
    await main.source_message_handler(F.event(F.msg(11, T.SIGNAL_4_BUY)))
    r10, r11 = db.get_signal(10), db.get_signal(11)
    mt5.bid, mt5.ask = 4100.00, 4100.30
    # SL spostato a mano, poi BE a mano (SL all'ingresso), TP messo a mano, poi chiusura a mano
    mt5.positions[r10["position_ticket"]].sl = 4200.00
    await _pass(main.monitor_closures)
    mt5.positions[r10["position_ticket"]].sl = r10["open_price"]
    await _pass(main.monitor_closures)
    mt5.positions[r10["position_ticket"]].tp = 4000.00
    await _pass(main.monitor_closures)
    mt5.broker_close(r11["position_ticket"], 4110.00, mt5.DEAL_REASON_EXPERT)   # chiusa a mano su MT5
    await _pass(main.monitor_closures)
    events = [(e["source_message_id"], e["kind"], e["value"]) for e in sync.read_after(0)]
    assert events == [(10, "OPEN", None), (11, "OPEN", None), (10, "SL", 4200.0), (10, "BE", None),
                      (10, "TP", 4000.0), (11, "CLOSE", None)], events
    print("OK - master: scrive", events)


async def follower():
    os.environ.update({"SYNC_FILE": SYNC_FILE, "SYNC_ROLE": "follower", "PUBLISH_TO_CHANNEL": "false"})
    import test_flow as F
    tg, mt5 = F.install_fakes(True)
    import database as db
    db.set_db_path(os.path.join(tempfile.mkdtemp(), "f.db"))
    import main
    db.init_database()
    main.MT5_READY = True
    T = __import__("test_parser")

    # Stessi segnali (stessi id del canale sorgente), prezzi del broker un po' diversi
    mt5.bid, mt5.ask = 4100.40, 4100.70
    await main.source_message_handler(F.event(F.msg(10, T.ENTRA_53_SELL)))
    mt5.bid, mt5.ask = 4155.40, 4155.70
    await main.source_message_handler(F.event(F.msg(11, T.SIGNAL_4_BUY)))
    r10, r11 = db.get_signal(10), db.get_signal(11)
    mt5.bid, mt5.ask = 4090.00, 4090.30
    p10 = mt5.positions[r10["position_ticket"]]

    await _pass(main.sync_follower_loop, 2.5)
    assert db.get_signal(11)["status"] == "CLOSED_MANUAL" and r11["position_ticket"] not in mt5.positions
    assert p10.sl == r10["open_price"] == 4100.40, (p10.sl, r10["open_price"])   # BE al SUO ingresso
    assert p10.tp == 4000.00
    assert db.get_signal(10)["be_applied"] == 1 and db.get_signal(10)["tp"] == 4000.00
    assert tg.sent == []                                                       # la copia non scrive nel canale
    # Gli eventi gia' applicati non vengono riapplicati
    p10.sl = 4300.00
    await _pass(main.sync_follower_loop, 2.5)
    assert p10.sl == 4300.00
    print("OK - follower: chiusura, SL, BE (al proprio ingresso) e TP copiati; 0 messaggi nel canale.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(master() if sys.argv[1] == "master" else follower())
    else:
        if os.path.exists(SYNC_FILE):
            os.remove(SYNC_FILE)
        subprocess.run([sys.executable, __file__, "master"], check=True)
        subprocess.run([sys.executable, __file__, "follower"], check=True)
        os.remove(SYNC_FILE)
