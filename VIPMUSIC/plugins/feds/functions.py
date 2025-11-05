import asyncio
import html
import re
from datetime import datetime, timedelta
from pyrogram import Client, errors
from pyrogram.types import Message, ChatMember
from VIPMUSIC import config


# ─────────── GENERAL HELPERS ─────────── #

def time_formatter(milliseconds: int) -> str:
    """Converts milliseconds to human readable format."""
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    tmp = []
    if days:
        tmp.append(f"{days}d")
    if hours:
        tmp.append(f"{hours}h")
    if minutes:
        tmp.append(f"{minutes}m")
    if seconds:
        tmp.append(f"{seconds}s")
    return " ".join(tmp)


def get_readable_time(seconds: int) -> str:
    """Convert seconds to H:M:S string"""
    count = 0
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        remainder, result = divmod(seconds, 60) if count < 2 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
        count += 1

    compiled = [
        f"{time_list[x]}{time_suffix_list[x]}" for x in range(len(time_list)) if time_list[x] != 0
    ]
    compiled.reverse()
    return " ".join(compiled)


async def delete_after(message: Message, delay: int = 10):
    """Auto delete message after delay seconds."""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass


async def extract_user(message: Message):
    """Extract user id and name from a reply, mention or ID."""
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        return user.id, user.first_name

    args = message.text.split(None, 1)
    if len(args) < 2:
        return None, None
    user_ref = args[1]

    if user_ref.isdigit():
        return int(user_ref), None
    if user_ref.startswith("@"):
        try:
            user = await message._client.get_users(user_ref)
            return user.id, user.first_name
        except Exception:
            return None, None
    return None, None


# ─────────── ADMIN + PERMISSIONS ─────────── #

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if a user is admin in chat."""
    try:
        member: ChatMember = await client.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except errors.UserNotParticipant:
        return False
    except Exception:
        return False


def is_sudo(user_id: int) -> bool:
    """Check if user is in sudo or owner list."""
    try:
        return user_id in [int(x) for x in config.SUDOERS] or user_id == int(config.OWNER_ID)
    except Exception:
        return False


async def admin_filter(client: Client, message: Message) -> bool:
    """Filter function usable with Pyrogram filters for admin-only commands."""
    user_id = message.from_user.id if message.from_user else None
    chat_id = message.chat.id
    if not user_id:
        return False
    return await is_admin(client, chat_id, user_id)


async def mention_html(user):
    """Return a clickable HTML mention."""
    if not user:
        return "Unknown"
    return f"<a href='tg://user?id={user.id}'>{html.escape(user.first_name)}</a>"


async def mention_markdown(user):
    """Return a markdown mention."""
    if not user:
        return "Unknown"
    return f"[{user.first_name}](tg://user?id={user.id})"


# ─────────── TIME + LOGGING ─────────── #

def utcnow() -> datetime:
    """UTC timestamp."""
    return datetime.utcnow()


def pretty_datetime() -> str:
    """Formatted UTC datetime string."""
    return utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


async def log_exception(client: Client, message: Message, error: Exception):
    """Log error in logger group."""
    from VIPMUSIC import config
    try:
        err_text = f"<b>⚠️ Error Report</b>\n\n"
        err_text += f"<b>Chat:</b> {message.chat.title if message.chat else 'Private'}\n"
        err_text += f"<b>User:</b> {message.from_user.id if message.from_user else 'N/A'}\n"
        err_text += f"<b>Time:</b> {pretty_datetime()}\n\n"
        err_text += f"<code>{html.escape(str(error))}</code>"
        await client.send_message(int(config.LOG_GROUP_ID), err_text)
    except Exception:
        pass
