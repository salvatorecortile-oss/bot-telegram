"""Invio dei messaggi nel canale di destinazione."""
from config import DESTINATION_CHAT, PUBLISH_TO_CHANNEL
from messages import (
    format_be_applied_message,
    format_close_message,
    format_open_message,
    format_sl_updated_message,
    format_tp_updated_message,
)
from telegram_client import client


async def _send(text, silent=True, reply_to=None):
    """Con PUBLISH_TO_CHANNEL=false non scrive niente nel canale e restituisce None."""
    if not PUBLISH_TO_CHANNEL:
        return None
    return await client.send_message(
        DESTINATION_CHAT,
        text,
        parse_mode="html",
        silent=silent,
        reply_to=reply_to,
    )


async def send_open_message(direction, entry, sl, tp):
    return await _send(format_open_message(direction, entry, sl, tp), silent=False)


async def send_be_applied_message(sl, reply_to=None):
    return await _send(format_be_applied_message(sl), reply_to=reply_to)


async def send_tp_updated_message(tp, reply_to=None):
    return await _send(format_tp_updated_message(tp), reply_to=reply_to)


async def send_sl_updated_message(sl, in_profit, reply_to=None):
    return await _send(format_sl_updated_message(sl, in_profit), reply_to=reply_to)


async def send_close_message(close_status, pips, close_price, reply_to=None):
    return await _send(format_close_message(close_status, pips, close_price), reply_to=reply_to)


async def send_text(text):
    """Report e buongiorno."""
    return await _send(text)
