"""
Coordina l'esecuzione delle operazioni sul conto principale (in-process,
vedi mt5_executor.py) e sul secondo conto (processo separato, vedi
mt5_worker.py), quando SECOND_ACCOUNT_ENABLED e' attivo.

Se il secondo conto non e' configurato, tutte le funzioni *_dual si
comportano esattamente come il solo conto principale: nessuna differenza
di comportamento finche' non vengono fornite le credenziali del secondo
conto.
"""
import asyncio
import logging
import multiprocessing as mp
import queue
import threading
import time
import uuid

import mt5_executor
import mt5_worker

from config import (
    DEVIATION,
    LOT_SIZE,
    MAGIC_NUMBER_2,
    MT5_LOGIN_2,
    MT5_PASSWORD_2,
    MT5_PATH_2,
    MT5_SERVER_2,
    MT5_SYMBOL,
    ORDER_COMMENT,
    SECOND_ACCOUNT_ENABLED,
)

logger = logging.getLogger(__name__)

_process = None
_command_queue = None
_result_queue = None
_stop_event = None
_call_lock = threading.Lock()
_secondary_ready = False


def secondary_enabled():
    return bool(SECOND_ACCOUNT_ENABLED)


def start_secondary_worker(timeout=30):
    """Avvia il processo del secondo conto e attende la connessione MT5."""
    global _process, _command_queue, _result_queue, _stop_event, _secondary_ready

    if not SECOND_ACCOUNT_ENABLED:
        logger.info("ℹ️ Secondo conto MT5 disattivato (SECOND_ACCOUNT_ENABLED=false).")
        return False

    if not (MT5_PATH_2 and MT5_LOGIN_2 and MT5_PASSWORD_2 and MT5_SERVER_2):
        logger.error(
            "❌ SECOND_ACCOUNT_ENABLED=true ma mancano MT5_PATH_2/MT5_LOGIN_2/"
            "MT5_PASSWORD_2/MT5_SERVER_2 nel .env. Secondo conto NON avviato."
        )
        return False

    ctx = mp.get_context("spawn")
    _command_queue = ctx.Queue()
    _result_queue = ctx.Queue()
    _stop_event = ctx.Event()

    account_cfg = {
        "path": MT5_PATH_2,
        "login": MT5_LOGIN_2,
        "password": MT5_PASSWORD_2,
        "server": MT5_SERVER_2,
        "symbol": MT5_SYMBOL,
    }

    _process = ctx.Process(
        target=mt5_worker.worker_main,
        args=(account_cfg, _command_queue, _result_queue, _stop_event),
        daemon=True,
    )
    _process.start()

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            msg = _result_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        if msg.get("id") == "__ready__":
            _secondary_ready = bool(msg.get("ok"))
            if _secondary_ready:
                logger.info("✅ Secondo conto MT5 connesso.")
            else:
                logger.error("❌ Secondo conto MT5 NON connesso: verranno usati solo i risultati del conto principale.")
            return _secondary_ready

    logger.error("❌ Timeout avvio worker secondo conto MT5.")
    return False


def stop_secondary_worker():
    if _stop_event is not None:
        _stop_event.set()
    if _process is not None and _process.is_alive():
        _process.join(timeout=5)


def _call_secondary_sync(fn_name, args, kwargs, timeout):
    request_id = str(uuid.uuid4())
    with _call_lock:
        _command_queue.put({"id": request_id, "fn": fn_name, "args": args, "kwargs": kwargs})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                msg = _result_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if msg.get("id") == request_id:
                return msg
    raise TimeoutError(f"Timeout risposta dal secondo conto MT5 ({fn_name}).")


async def _call_secondary(fn_name, *args, timeout=15, **kwargs):
    if not _secondary_ready or _command_queue is None:
        raise RuntimeError("Secondo conto MT5 non connesso.")
    return await asyncio.to_thread(_call_secondary_sync, fn_name, args, kwargs, timeout)


async def open_market_order_dual(direction, sl=0.0, tp=0.0):
    """
    Apre a mercato sul conto principale (sempre) e, se attivo e connesso,
    anche sul secondo conto. Un errore sul secondo conto NON blocca ne'
    annulla l'apertura gia' avvenuta sul conto principale: viene solo
    loggato, cosi' il segnale resta comunque operativo.
    """
    primary = await asyncio.to_thread(mt5_executor.open_market_order, direction, sl, tp)

    secondary = None
    if secondary_enabled() and _secondary_ready:
        try:
            response = await _call_secondary(
                "open_market_order", MT5_SYMBOL, direction, LOT_SIZE, MAGIC_NUMBER_2,
                ORDER_COMMENT, DEVIATION, sl, tp,
            )
            if response["ok"]:
                secondary = response["result"]
            else:
                logger.error("❌ Apertura FALLITA sul secondo conto: %s", response["error"])
        except Exception:
            logger.exception("❌ Errore comunicazione con il secondo conto (apertura).")

    return primary, secondary


async def apply_sltp_dual(primary_ticket, secondary_ticket, sl, tp):
    primary_result = await asyncio.to_thread(mt5_executor.modify_position_sl_tp, primary_ticket, sl, tp)

    secondary_result = None
    if secondary_enabled() and _secondary_ready and secondary_ticket:
        try:
            response = await _call_secondary(
                "modify_position_sl_tp", MT5_SYMBOL, MAGIC_NUMBER_2, ORDER_COMMENT,
                secondary_ticket, sl, tp,
            )
            if response["ok"]:
                secondary_result = response["result"]
            else:
                logger.error("❌ Modifica SL/TP FALLITA sul secondo conto: %s", response["error"])
        except Exception:
            logger.exception("❌ Errore comunicazione con il secondo conto (SL/TP).")

    return primary_result, secondary_result


async def move_to_breakeven_dual(primary_ticket, secondary_ticket):
    primary_sl = await asyncio.to_thread(mt5_executor.move_position_to_breakeven, primary_ticket)

    secondary_sl = None
    if secondary_enabled() and _secondary_ready and secondary_ticket:
        try:
            response = await _call_secondary(
                "move_position_to_breakeven", MT5_SYMBOL, MAGIC_NUMBER_2, ORDER_COMMENT, secondary_ticket,
            )
            if response["ok"]:
                secondary_sl = response["result"]
            else:
                logger.error("❌ Break Even FALLITO sul secondo conto: %s", response["error"])
        except Exception:
            logger.exception("❌ Errore comunicazione con il secondo conto (BE).")

    return primary_sl, secondary_sl


def primary_position_is_open(ticket):
    return mt5_executor.position_is_open(ticket)


def primary_closed_position_info(ticket):
    return mt5_executor.get_closed_position_info(ticket)


async def secondary_open_positions():
    if not (secondary_enabled() and _secondary_ready):
        return None
    try:
        response = await _call_secondary("list_open_positions", MT5_SYMBOL, MAGIC_NUMBER_2)
        if response["ok"]:
            return response["result"]
        logger.error("❌ Lettura posizioni FALLITA sul secondo conto: %s", response["error"])
    except Exception:
        logger.exception("❌ Errore comunicazione con il secondo conto (lista posizioni).")
    return None


async def close_all_dual():
    """
    Chiude a mercato TUTTE le posizioni del bot su entrambi i conti
    (usata dai comandi remoti stop/riavvio e dalla chiusura automatica
    di fine giornata). Ritorna (primary_closed, primary_errors,
    secondary_closed, secondary_errors).
    """
    primary_closed, primary_errors = await asyncio.to_thread(mt5_executor.close_all_positions)

    secondary_closed, secondary_errors = [], []
    if secondary_enabled() and _secondary_ready:
        try:
            response = await _call_secondary(
                "close_all_positions", MT5_SYMBOL, MAGIC_NUMBER_2, ORDER_COMMENT, DEVIATION,
            )
            if response["ok"]:
                secondary_closed, secondary_errors = response["result"]
            else:
                logger.error("❌ Chiusura totale FALLITA sul secondo conto: %s", response["error"])
        except Exception:
            logger.exception("❌ Errore comunicazione con il secondo conto (chiusura totale).")

    return primary_closed, primary_errors, secondary_closed, secondary_errors


async def secondary_closed_position_info(ticket):
    if not (secondary_enabled() and _secondary_ready and ticket):
        return None
    try:
        response = await _call_secondary("get_closed_position_info", ticket)
        if response["ok"]:
            return response["result"]
        logger.error("❌ Lettura chiusura FALLITA sul secondo conto: %s", response["error"])
    except Exception:
        logger.exception("❌ Errore comunicazione con il secondo conto (storico chiusura).")
    return None
