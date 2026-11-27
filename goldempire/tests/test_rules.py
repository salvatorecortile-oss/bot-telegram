"""
Test delle regole di apertura, della protezione del conto e delle copie che
aprono solo quello che apre il conto principale. Avvio: python tests/test_rules.py
"""
import asyncio
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

SYNC_FILE = os.environ.setdefault("SYNC_TEST_FILE", os.path.join(tempfile.gettempdir(), f"rules_test_{os.getpid()}.db"))


def entra(no, direction, entry, sl, tp=None):
    return (f"🟢 ENTRA ORA · SIGNAL {no} · XAUUSD {direction}\nIngresso: {entry}\nSL da mettere nell'ordine: {sl}"
            + (f"\nObiettivo: {tp}" if tp else "\nTP: NON metterlo"))


def setup(role):
    os.environ.update({"SYNC_FILE": SYNC_FILE, "SYNC_ROLE": role, "MAX_PER_DIRECTION": "2",
                       "ONE_PER_FAMILY": "true", "LOW_PRIORITY_SIGNALS": "4", "MAX_ENTRY_DISTANCE": "2",
                       "RISK_DAILY_LOSS_PCT": "6", "RISK_MONTHLY_LOSS_PCT": "20", "FOLLOW_WAIT_SECONDS": "1"})
    if role == "follower":
        os.environ["PUBLISH_TO_CHANNEL"] = "false"
    import test_flow as F
    tg, mt5 = F.install_fakes(True)
    import database as db
    db.set_db_path(os.path.join(tempfile.mkdtemp(), f"{role}.db"))
    import main
    db.init_database()
    main.MT5_READY = True
    return F, tg, mt5, db, main


async def master():
    F, tg, mt5, db, main = setup("master")
    import sync
    status = lambda mid: db.get_signal(mid)["status"]
    mt5.bid, mt5.ask = 4100.00, 4100.30

    async def send(mid, text):
        await main.source_message_handler(F.event(F.msg(mid, text)))

    # BUY: 5.6 aperto; 4 BUY saltato (priorita' bassa, c'e' gia' un BUY)
    await send(1, entra("5.6", "BUY", "4100,30", "4060,00"))
    await send(2, entra(4, "BUY", "4100,30", "4060,00", "4300,00"))
    assert status(1) == "OPENED" and status(2) == "SKIPPED_LIMIT", (status(1), status(2))
    # 5.3 BUY saltato (famiglia 5 gia' BUY); 6 BUY aperto (secondo); 7 BUY saltato (max 2)
    await send(3, entra("5.3", "BUY", "4100,30", "4060,00"))
    await send(4, entra(6, "BUY", "4100,30", "4060,00", "4200,00"))
    await send(5, entra(7, "BUY", "4100,30", "4060,00"))
    assert [status(i) for i in (3, 4, 5)] == ["SKIPPED_LIMIT", "OPENED", "SKIPPED_LIMIT"]
    # SELL: famiglia 5 puo' avere anche un SELL; 5.2 SELL saltato (stessa famiglia e direzione)
    await send(6, entra("5.3", "SELL", "4100,00", "4140,00"))
    await send(7, entra("5.2", "SELL", "4100,00", "4140,00"))
    assert status(6) == "OPENED" and status(7) == "SKIPPED_LIMIT"
    # Nel canale escono solo le 3 operazioni aperte
    assert len(tg.sent) == 3, [m.text for m in tg.sent]

    # SIGNAL 4 per primo su una direzione vuota: si apre, e il 5 dopo si apre lo stesso (2 insieme)
    for mid in (1, 4, 6):
        mt5.broker_close(db.get_signal(mid)["position_ticket"], 4100.0, mt5.DEAL_REASON_EXPERT)
    task = asyncio.create_task(main.monitor_closures()); await asyncio.sleep(0.3); task.cancel()
    await send(8, entra(4, "BUY", "4100,30", "4060,00", "4300,00"))
    await send(9, entra("5.8", "BUY", "4100,30", "4060,00"))
    assert status(8) == "OPENED" and status(9) == "OPENED"

    # Prezzo a piu' di 2 $ dall'ingresso: non aperto
    await send(10, entra(6, "SELL", "4110,00", "4150,00", "4000,00"))
    assert status(10) == "SKIPPED", status(10)

    # Protezione: conta solo il saldo (operazioni chiuse). Equity -7% con operazioni aperte: niente pausa
    mt5.balance, mt5.equity = 1000.0, 1000.0
    await main.check_account_risk()
    mt5.equity = 930.0
    await main.check_account_risk()
    assert main.risk_pause_reason() is None
    # Prelievo di 200 $: il saldo scende a 800 ma non e' una perdita -> niente pausa
    from types import SimpleNamespace as NS
    mt5.deals.append(NS(ticket=1, order=0, position_id=0, entry=0, price=0, reason=0, time_msc=0, volume=0,
                        type=2, profit=-200.0))
    mt5.balance = mt5.equity = 800.0
    await main.check_account_risk()
    assert main.risk_pause_reason() is None
    # Operazioni chiuse in perdita: -7% del saldo rimasto dopo il prelievo (800 -> 744) -> pausa
    mt5.balance = 744.0
    n = len(tg.sent)
    await main.check_account_risk()
    channel = [m.text for m in tg.sent[n:] if "Le operazioni già aperte" in m.text]
    assert len(channel) == 1 and "perdita giornaliera del 6%" in channel[0] and "domani" in channel[0], tg.sent[n:]
    assert main.risk_pause_reason() and "giornaliera" in main.risk_pause_reason()
    await send(11, entra(7, "SELL", "4100,00", "4140,00"))
    assert status(11) == "PAUSED_RISK"
    assert "PROTEZIONE CONTO" in main.status_text()

    class Ev:
        raw_text = "bot3_play"
        async def reply(self, *a, **k): pass
    await main.saved_messages_handler(Ev())
    await main.check_account_risk()                          # stesso giorno: non riscatta
    assert main.risk_pause_reason() is None
    await send(12, entra(7, "SELL", "4100,00", "4140,00"))
    assert status(12) == "OPENED"

    decisions = {e["source_message_id"]: e["kind"] for e in sync.read_after(0) if e["kind"] in ("OPEN", "SKIP")}
    assert decisions == {1: "OPEN", 2: "SKIP", 3: "SKIP", 4: "OPEN", 5: "SKIP", 6: "OPEN", 7: "SKIP",
                         8: "OPEN", 9: "OPEN", 10: "SKIP", 11: "SKIP", 12: "OPEN"}, decisions
    # CHIUDI ORA in risposta a un SIGNAL 4 che il bot NON ha (VPS spenta): non chiude l'altro SIGNAL 4 aperto
    open4 = [r for r in db.get_open_signals() if r["signal_no"] == 4]
    assert open4, db.get_open_signals()
    missed = F.msg(900, entra(4, "BUY", "4100,30", "4060,00", "4300,00"))
    tg.history = [missed]
    close_txt = "🔴 CHIUDI ORA · SIGNAL 4 · BUY\n\n🏁 Uscita: 4105,00"
    await main.source_message_handler(F.event(F.msg(901, close_txt, reply_to=900)))
    assert db.get_signal(open4[0]["source_message_id"])["status"] == "OPENED"
    # Senza reply (o in reply a un messaggio che non e' un segnale) la riserva vale ancora
    tg.history = [F.msg(902, "Ragazzi attenzione")]
    await main.source_message_handler(F.event(F.msg(903, close_txt, reply_to=902)))
    assert db.get_signal(open4[0]["source_message_id"])["status"] == "CLOSED_MANUAL"

    # EXCLUDED_SIGNALS: 5.6 blocca solo il 5.6 (gli altri 5.x si aprono), 7 blocca tutta la famiglia 7
    main.EXCLUDED_SIGNALS = {5.6, 7.0}
    assert main.excluded_reason(5.6) and main.excluded_reason(7) and main.excluded_reason(7.1)
    assert main.excluded_reason(5.2) is None and main.excluded_reason(5) is None and main.excluded_reason(None) is None
    for mid in [r["source_message_id"] for r in db.get_open_signals()]:
        mt5.broker_close(db.get_signal(mid)["position_ticket"], 4100.0, mt5.DEAL_REASON_EXPERT)
    task = asyncio.create_task(main.monitor_closures()); await asyncio.sleep(0.3); task.cancel()
    await send(13, entra("5.6", "BUY", "4100,30", "4060,00"))
    await send(14, entra("5.2", "BUY", "4100,30", "4060,00"))
    assert status(13) == "SKIPPED_LIMIT" and status(14) == "OPENED", (status(13), status(14))
    main.EXCLUDED_SIGNALS = set()
    print("OK - principale: limiti per direzione/famiglia, priorita' SIGNAL 4, distanza 2 $, "
          "protezione -6% e conferme scritte per le copie.")


async def follower():
    F, tg, mt5, db, main = setup("follower")
    mt5.bid, mt5.ask = 4100.00, 4100.30
    # La copia non applica i limiti: apre esattamente cio' che ha aperto il principale
    for mid, text in ((1, entra("5.6", "BUY", "4100,30", "4060,00")),
                      (2, entra(4, "BUY", "4100,30", "4060,00", "4300,00")),
                      (12, entra(7, "SELL", "4100,00", "4140,00")),
                      (99, entra(6, "SELL", "4100,00", "4140,00", "4000,00"))):   # 99: nessuna conferma
        await main.source_message_handler(F.event(F.msg(mid, text)))
    st = {mid: db.get_signal(mid)["status"] for mid in (1, 2, 12, 99)}
    assert st == {1: "OPENED", 2: "NOT_OPENED_BY_MASTER", 12: "OPENED", 99: "NOT_OPENED_BY_MASTER"}, st
    assert tg.sent == []
    print("OK - copia: apre solo i segnali aperti dal principale (SKIP e nessuna conferma = non aperti).")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(master() if sys.argv[1] == "master" else follower())
    else:
        if os.path.exists(SYNC_FILE):
            os.remove(SYNC_FILE)
        subprocess.run([sys.executable, __file__, "master"], check=True)
        subprocess.run([sys.executable, __file__, "follower"], check=True)
        os.remove(SYNC_FILE)
