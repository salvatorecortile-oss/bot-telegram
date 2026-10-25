"""
Confronta le posizioni aperte su MT5 con quelle gia' seguite e pubblica i
messaggi: apertura, TP/SL cambiati, break-even e chiusura (in reply al
messaggio di apertura).

`reader` e' il modulo mt5_reader (o un finto lettore nei test), `send` una
coroutine send(text, reply_to=None) che restituisce l'id del messaggio.
"""
import asyncio
import logging

import database as db
from config import DISPLAY_SYMBOL, MAX_OPEN_AGE_SECONDS, PIP_SIZE
from messages import (
    calculate_pips,
    classify_stop_close,
    format_be_applied_message,
    format_close_message,
    format_open_message,
    format_sl_updated_message,
    format_tp_updated_message,
)

logger = logging.getLogger(__name__)

# Dopo quanti controlli senza uscita nello storico la posizione viene chiusa senza messaggio.
MAX_CLOSE_ATTEMPTS = 30


def display_symbol(symbol):
    """XAUUSD-P / XAUUSD.r / XAUUSDm -> XAUUSD (oppure DISPLAY_SYMBOL dal .env)."""
    if DISPLAY_SYMBOL:
        return DISPLAY_SYMBOL
    for sep in ("-", ".", "_"):
        symbol = symbol.split(sep)[0]
    if len(symbol) > 6 and symbol[:6].isupper() and symbol[6:].islower():
        symbol = symbol[:6]
    return symbol


class Tracker:
    def __init__(self, reader, send):
        self.reader = reader
        self.send = send
        self.publishing = True     # False = in pausa: le nuove operazioni non vengono pubblicate
        self.first_sync = True

    async def sync(self):
        positions = await asyncio.to_thread(self.reader.get_positions)
        if positions is None:
            return
        by_ticket = {p["ticket"]: p for p in positions}

        for position in positions:
            if db.get_trade(position["ticket"]) is None:
                await self._new_position(position)

        for row in db.get_open_trades():
            position = by_ticket.get(row["ticket"])
            if position is None:
                await self._closed(row)
            else:
                await self._check_levels(row, position)
        self.first_sync = False

    # ------------------------------------------------------------------
    async def _new_position(self, position):
        publish = self.publishing
        if publish and self.first_sync:
            # gia' aperta all'avvio: la pubblica solo se e' recente
            now = await asyncio.to_thread(self.reader.server_now, position["symbol"])
            publish = now is not None and now - position["time"] <= MAX_OPEN_AGE_SECONDS
        if not db.insert_trade(position, publish):
            return
        logger.info(
            "🆕 %s %s %s @ %.2f | SL %.2f | TP %.2f | magic %s | ticket %s%s",
            "PUBBLICO" if publish else "SEGUO IN SILENZIO", position["direction"], position["symbol"],
            position["open_price"], position["sl"], position["tp"], position["magic"], position["ticket"],
            "" if publish else " (aperta prima dell'avvio o sala in pausa)",
        )
        if not publish:
            return
        text = format_open_message(display_symbol(position["symbol"]), position["direction"],
                                   position["open_price"], position["sl"], position["tp"])
        try:
            message_id = await self.send(text)
            db.set_destination_message(position["ticket"], message_id)
        except Exception:
            logger.exception("❌ ERRORE INVIO APERTURA | ticket %s", position["ticket"])

    async def _check_levels(self, row, position):
        ticket = row["ticket"]
        reply_to = row["destination_message_id"]
        published = bool(row["published"])

        known_tp = float(row["tp"] or 0.0)
        if abs(position["tp"] - known_tp) >= 0.005:
            db.update_levels(ticket, tp=position["tp"])
            logger.info("🎯 TP CAMBIATO | ticket %s | %.2f -> %.2f", ticket, known_tp, position["tp"])
            if published:
                await self._send_reply(format_tp_updated_message(position["tp"]), reply_to, ticket)

        known_sl = float(row["sl"] or 0.0)
        new_sl = position["sl"]
        if abs(new_sl - known_sl) >= 0.005:
            open_price = float(row["open_price"])
            if row["direction"] == "BUY":
                in_profit = bool(new_sl) and new_sl >= open_price - 0.005
            else:
                in_profit = bool(new_sl) and new_sl <= open_price + 0.005
            first_be = in_profit and not row["be_applied"]
            db.update_levels(ticket, sl=new_sl, be_applied=first_be)
            logger.info("🛡️ SL CAMBIATO | ticket %s | %.2f -> %.2f%s", ticket, known_sl, new_sl,
                        " (BE)" if first_be else "")
            if published:
                text = format_be_applied_message(new_sl) if first_be else format_sl_updated_message(new_sl, in_profit)
                await self._send_reply(text, reply_to, ticket)

    async def _closed(self, row):
        ticket = row["ticket"]
        info = await asyncio.to_thread(self.reader.get_close_info, ticket)
        if info is None:
            # lo storico a volte arriva qualche secondo dopo
            if db.add_close_attempt(ticket) >= MAX_CLOSE_ATTEMPTS:
                db.claim_close(ticket, "CLOSED_EXTERNAL", None, None, None)
                logger.warning("⚠️ Ticket %s chiuso ma senza uscita nello storico: nessun messaggio", ticket)
            return

        pips = calculate_pips(row["open_price"], info["price"], row["direction"], PIP_SIZE)
        if info["reason"] == "TP":
            status = "CLOSED_TP"
        elif info["reason"] == "SL":
            status = classify_stop_close(pips, bool(row["be_applied"]))
        else:
            status = "CLOSED_EXTERNAL"
        if not db.claim_close(ticket, status, info["price"], pips, info["profit"]):
            return
        logger.info("🏁 %s | ticket %s %s | chiusura %.2f | %+.1f pips | %+.2f",
                    status, ticket, row["direction"], info["price"], pips, info["profit"])
        if row["published"]:
            await self._send_reply(format_close_message(status, pips, info["price"]),
                                   row["destination_message_id"], ticket)

    async def _send_reply(self, text, reply_to, ticket):
        try:
            await self.send(text, reply_to=reply_to)
        except Exception:
            logger.exception("❌ ERRORE INVIO AGGIORNAMENTO | ticket %s", ticket)
