"""Invio dei messaggi nel canale di destinazione."""
from config import DESTINATION_CHAT
from messages import format_be_applied_message, format_close_message, format_open_message
from telegram_client import client


async def send_open_message(direction, entry, sl, tp):
    return await client.send_message(
        DESTINATION_CHAT,
        format_open_message(direction, entry, sl, tp),
        parse_mode="html",
    )


async def send_be_applied_message(sl, reply_to=None):
    return await client.send_message(
        DESTINATION_CHAT,
        format_be_applied_message(sl),
        parse_mode="html",
        silent=True,
        reply_to=reply_to,
    )


async def send_close_message(close_status, pips, close_price, reply_to=None):
    return await client.send_message(
        DESTINATION_CHAT,
        format_close_message(close_status, pips, close_price),
        parse_mode="html",
        silent=True,
        reply_to=reply_to,
    )


async def send_text(text):
    """Report e buongiorno."""
    return await client.send_message(DESTINATION_CHAT, text, parse_mode="html", silent=True)
