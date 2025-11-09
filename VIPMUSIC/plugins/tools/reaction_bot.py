# VIPMUSIC/plugins/tools/reaction_bot.py
import os
import importlib
import importlib.util
import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.enums import ChatMemberStatus

try:
    from VIPMUSIC import app
except Exception:
    raise RuntimeError("Failed to import app from VIPMUSIC.")

# import config values
try:
    from config import REACTION_BOT, START_REACTIONS, OWNER_ID, BANNED_USERS
except Exception:
    REACTION_BOT = True
    START_REACTIONS = []
    OWNER_ID = None
    BANNED_USERS = filters.user([])

# sudoers import
try:
    from VIPMUSIC.utils.database import get_sudoers
except Exception:
    async def get_sudoers():
        return set()

# --- ReactionDB Import Fallback ---
def import_reactiondb():
    try:
        from VIPMUSIC.utils.database.reactiondb import get_reaction_status, set_reaction_status
        return get_reaction_status, set_reaction_status
    except Exception:
        fallback_path = os.path.join(os.getcwd(), "VIPMUSIC", "utils", "database", "reactiondb.py")
        if os.path.exists(fallback_path):
            spec = importlib.util.spec_from_file_location("reactiondb_fallback", fallback_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            return getattr(mod, "get_reaction_status"), getattr(mod, "set_reaction_status")
        else:
            _mem = {}
            async def get_reaction_status_stub(cid: int) -> bool:
                return _mem.get(str(cid), False)
            async def set_reaction_status_stub(cid: int, status: bool):
                _mem[str(cid)] = bool(status)
            return get_reaction_status_stub, set_reaction_status_stub

get_reaction_status, set_reaction_status = import_reactiondb()

# --- Reactions ---
VALID_REACTIONS = [
    "❤️", "💖", "💘", "💞", "💓", "✨", "🔥", "💫",
    "💥", "🌸", "😍", "🥰", "💎", "🌙", "🌹", "😂",
    "😎", "🤩", "😘", "😉", "🤭", "💐", "😻", "🥳",
]
SAFE_REACTIONS = [e for e in (START_REACTIONS or []) if e in VALID_REACTIONS] or VALID_REACTIONS.copy()
chat_used_reactions = {}


def next_emoji_local(chat_id: int) -> str:
    if chat_id not in chat_used_reactions:
        chat_used_reactions[chat_id] = set()
    used = chat_used_reactions[chat_id]
    if len(used) >= len(SAFE_REACTIONS):
        used.clear()
    remaining = [e for e in SAFE_REACTIONS if e not in used]
    emoji = random.choice(remaining)
    used.add(emoji)
    return emoji


async def is_admin_or_sudo(client, user_id: int, chat_id: int) -> bool:
    try:
        if OWNER_ID and user_id == OWNER_ID:
            return True
        sudoers = await get_sudoers()
        if user_id in sudoers:
            return True
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


def reaction_buttons(chat_id: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Enable", callback_data=f"reaction_on:{chat_id}"),
                InlineKeyboardButton("🚫 Disable", callback_data=f"reaction_off:{chat_id}"),
            ]
        ]
    )


# ✅ Fixed command filters to work on all Pyrogram versions
@app.on_message(filters.command(["reaction"]) & ~BANNED_USERS & filters.group)
async def reaction_command(client, message: Message):
    chat = message.chat
    user = message.from_user

    if not user:
        return await message.reply_text("❌ User not found.")

    ok = await is_admin_or_sudo(client, user.id, chat.id)
    if not ok:
        return await message.reply_text("⚠️ Only admins, owner, or sudo users can use this command.")

    # show status if no args
    if len(message.command) == 1:
        status = await get_reaction_status(chat.id)
        status_text = "✅ Enabled" if status else "🚫 Disabled"
        return await message.reply_text(
            f"**Reaction Bot is currently:** {status_text}",
            reply_markup=reaction_buttons(chat.id),
        )

    arg = message.command[1].lower()
    if arg == "on":
        await set_reaction_status(chat.id, True)
        await message.reply_text("✅ Reaction Bot enabled for this chat.")
    elif arg == "off":
        await set_reaction_status(chat.id, False)
        await message.reply_text("🚫 Reaction Bot disabled for this chat.")
    else:
        await message.reply_text("Usage: `/reaction on` or `/reaction off`", quote=True)


# ✅ Callback Buttons
@app.on_callback_query(filters.regex(r"^reaction_on:(-?\d+)$"))
async def cb_reaction_on(client, callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    ok = await is_admin_or_sudo(client, user_id, chat_id)
    if not ok:
        return await callback.answer("Only admins/sudo can toggle.", show_alert=True)

    await set_reaction_status(chat_id, True)
    await callback.answer("✅ Enabled")
    try:
        await callback.message.edit_text(
            "✅ Reaction Bot enabled for this chat.",
            reply_markup=reaction_buttons(chat_id),
        )
    except Exception:
        pass


@app.on_callback_query(filters.regex(r"^reaction_off:(-?\d+)$"))
async def cb_reaction_off(client, callback: CallbackQuery):
    chat_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    ok = await is_admin_or_sudo(client, user_id, chat_id)
    if not ok:
        return await callback.answer("Only admins/sudo can toggle.", show_alert=True)

    await set_reaction_status(chat_id, False)
    await callback.answer("🚫 Disabled")
    try:
        await callback.message.edit_text(
            "🚫 Reaction Bot disabled for this chat.",
            reply_markup=reaction_buttons(chat_id),
        )
    except Exception:
        pass


# ✅ Auto reaction logic (unchanged from your working version)
@app.on_message(
    (filters.text | filters.sticker | filters.photo | filters.video | filters.document)
    & ~BANNED_USERS
    & filters.group
)
async def auto_react(client, message: Message):
    if not REACTION_BOT:
        return
    if message.text and message.text.startswith("/"):
        return
    if getattr(message.from_user, "is_bot", False):
        return

    chat_id = message.chat.id
    enabled = await get_reaction_status(chat_id)
    if not enabled:
        return

    emoji = next_emoji_local(chat_id)
    try:
        await message.react(emoji)
    except Exception:
        try:
            await message.react("❤️")
        except Exception:
            pass
