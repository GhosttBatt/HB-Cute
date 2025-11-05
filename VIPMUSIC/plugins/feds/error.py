import traceback
import html
from pyrogram import Client, errors
from pyrogram.types import Message
from VIPMUSIC.plugins.admins.functions import log_exception
from VIPMUSIC import config


async def handle_error(client: Client, message: Message, err: Exception):
    """Handle and report errors gracefully."""
    if isinstance(err, errors.FloodWait):
        await message.reply_text(f"⏳ Flood wait of {err.value} seconds.")
        return
    if isinstance(err, errors.MessageNotModified):
        return
    if isinstance(err, errors.MessageDeleteForbidden):
        return
    if isinstance(err, errors.ChatWriteForbidden):
        return
    if isinstance(err, errors.UserNotParticipant):
        await message.reply_text("🚫 The user is not a participant in this chat.")
        return

    # General fallback
    try:
        tb = "".join(traceback.format_exception(None, err, err.__traceback__))
        text = (
            "<b>⚠️ Exception Caught</b>\n\n"
            f"<b>Chat:</b> {message.chat.title if message.chat else 'Private'}\n"
            f"<b>User:</b> {message.from_user.mention if message.from_user else 'Unknown'}\n"
            f"<b>Error:</b> <code>{html.escape(str(err))}</code>\n\n"
            f"<b>Traceback:</b>\n<code>{html.escape(tb[-3000:])}</code>"
        )
        await message.reply_text(text)
        await log_exception(client, message, err)
    except Exception:
        pass


async def safe_exec(func, client: Client, message: Message, *args, **kwargs):
    """Run a coroutine and auto-handle exceptions."""
    try:
        return await func(client, message, *args, **kwargs)
    except Exception as err:
        await handle_error(client, message, err)
