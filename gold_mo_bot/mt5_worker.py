"""
Processo separato per il SECONDO conto MT5.

Il modulo MetaTrader5 mantiene una sola connessione attiva per processo:
per aprire/gestire operazioni su due conti (magari due broker diversi)
in parallelo serve un secondo processo indipendente con la propria
connessione. Questo modulo e' l'entry point di quel processo: riceve
comandi da una Queue, li esegue con mt5_engine e rimanda i risultati su
un'altra Queue.
"""
import logging
import queue

import mt5_engine as engine

logger = logging.getLogger(__name__)


def worker_main(account_cfg, command_queue, result_queue, stop_event):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | WORKER2 | %(levelname)s | %(message)s",
    )

    connected = engine.connect_mt5(
        account_cfg["path"],
        account_cfg["login"],
        account_cfg["password"],
        account_cfg["server"],
        account_cfg["symbol"],
        label="MT5 SECONDO CONTO",
    )
    result_queue.put({"id": "__ready__", "ok": connected})

    if not connected:
        logger.error("❌ Secondo conto MT5 non disponibile: il worker resta inattivo.")

    while not stop_event.is_set():
        try:
            cmd = command_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if cmd is None:
            break

        request_id = cmd.get("id")
        fn_name = cmd.get("fn")
        args = cmd.get("args", ())
        kwargs = cmd.get("kwargs", {})

        try:
            fn = getattr(engine, fn_name)
            result = fn(*args, **kwargs)
            result_queue.put({"id": request_id, "ok": True, "result": result})
        except Exception as e:
            logger.exception("Errore comando %s sul secondo conto", fn_name)
            result_queue.put({"id": request_id, "ok": False, "error": str(e)})

    try:
        import MetaTrader5 as mt5
        mt5.shutdown()
    except Exception:
        pass
