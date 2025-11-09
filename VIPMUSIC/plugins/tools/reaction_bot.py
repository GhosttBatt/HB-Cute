# VIPMUSIC/plugins/tools/reaction_bot.py
import os
import importlib
import importlib.util
import asyncio
import random
from typing import Set, Dict, Optional, Tuple

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.types import CallbackQuery
from pyrogram.enums import ChatMemberStatus

# Prefer importing app and config as your project expects
# (adjust if your project exposes these differently)
try:
    from VIPMUSIC import app  # should be your bot client
except Exception:
    raise RuntimeError("Failed to import app from VIPMUSIC; ensure VIPMUSIC/__init__.py exposes 'app'.")

# import config values (must exist in your config)
try:
    from config import REACTION_BOT, START_REACTIONS, OWNER_ID, BANNED_USERS
except Exception:
    # fallback defaults if config missing keys
    REACTION_BOT = True
    START_REACTIONS = []
    OWNER_ID = None
    try:
        from config import BANNED_USERS as BANNED_USERS
    except Exception:
        BANNED_USERS = filters.user([])

# Try to import get_sudoers from your DB utils; fallback to empty function
try:
    from VIPMUSIC.utils.database import get_sudoers  # if this is a function
except Exception:
    async def get_sudoers():
        return set()

# Try to import reactiondb via normal package; if that fails, load by path
def import_reactiondb():
    # First try normal import
    try:
        from VIPMUSIC.utils.database.reactiondb import get_reaction_status, set_reaction_status
        return get_reaction_status, set_reaction_status
    except Exception:
        # fallback: construct file path relative to repo root
        fallback_path = os.path.join(os.getcwd(), "VIPMUSIC", "utils", "database", "reactiondb.py")
        if os.path.exists(fallback_path):
            spec = importlib.util.spec_from_file_location("reactiondb_fallback", fallback_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore
            return getattr(mod, "get_reaction_status"), getattr(mod, "set_reaction_status")
        else:
            # final fallback: memory-only stub
            print("[ReactionBot] reactiondb not found; using memory-only stub.")
            _mem = {}
            async def get_reaction_status_stub(cid: int) -> bool:
                return _mem.get(str(cid), False)
            async def set_reaction_status_stub(cid: int, status: bool):
                _mem[str(cid)] = bool(status)
                print(f"[ReactionDB-stub] Chat {cid} set to {'ON' if status else 'OFF'}")
            return get_reaction_status_stub, set_reaction_status_stub

get_reaction_status, set_reaction_status = import_reactiondb()

# -------------------- EMOJI CONFIG --------------------
VALID_REACTIONS = [
    "❤️","💖","💘","💞","💓","✨","🔥","💫",
    "💥","🌸","😍","🥰","💎","🌙","🌹","😂",
    "😎","🤩","😘","😉","🤭","💐","😻","🥳"
]
SAFE_REACTIONS = [e for e in (START_REACTIONS or []) if e in VALID_REACTIONS] or VALID_REACTIONS.copy()

# per-chat rotation memory
chat_used_reactions: Dict[int, Set[str]] = {}

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

# -------------------- HELPERS --------------------
async def is_admin_or_sudo(client, message: Message) -> Tuple[bool, Optional[str]]:
    user = getattr(message, "from_user", None)
    if not user:
        return False, "no from_user"
    user_id = getattr(user, "id", None)
    chat = message.chat
    chat_type = getattr(chat, "type", "").lower()
    # owner / sudo quick checks
    if OWNER_ID and user_id == OWNER_ID:
        return True, None
    try:
        sudoers = await get_sudoers()
        if user_id in sudoers:
            return True, None
    except Exception:
        pass
    # ensure group/supergroup
    if chat_type not in ("group", "supergroup"):
        return False, f"chat_type={chat_type}"
    try:
        member = await client.get_chat_member(chat.id, user_id)
        if member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
            return True, None
        return False, f"user_status={member.status}"
    except Exception as e:
        return False, str(e)

# -------------------- BUTTONS --------------------
def reaction_buttons(chat_id: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Enable", callback_data=f"reactionon:{chat_id}"),
                InlineKeyboardButton("🚫 Disable", callback_data=f"reactionoff:{chat_id}"),
            ]
        ]
    )

# -------------------- /reaction COMMAND --------------------
@app.on_message(filters.command("reaction") & ~BANNED_USERS & (filters.group | filters.channel))
async def reaction_command(client, message: Message):
    # Only groups/supergroups allowed
    chat = message.chat
    if getattr(chat, "type", "").lower() not in ("group", "supergroup"):
        return await message.reply_text("❌ This command works only in groups/supergroups.", quote=True)

    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(f"⚠️ Only admins/owner/sudoers. Debug: {debug or 'none'}", quote=True)

    # show status if no args
    if len(message.command) == 1:
        status = await get_reaction_status(chat.id)
        status_text = "✅ Enabled" if status else "❌ Disabled"
        return await message.reply_text(f"🤖 Reaction Bot is **{status_text}** in this chat.", 
                                        reply_markup=reaction_buttons(chat.id), quote=True)

    # /reaction on|off
    action = message.command[1].lower()
    if action == "on":
        await set_reaction_status(chat.id, True)
        await message.reply_text("✅ Reaction Bot enabled for this chat.", quote=True)
    elif action == "off":
        await set_reaction_status(chat.id, False)
        await message.reply_text("💤 Reaction Bot disabled for this chat.", quote=True)
    else:
        await message.reply_text("Usage: /reaction on or /reaction off", quote=True)

# -------------------- CALLBACK HANDLERS --------------------
@app.on_callback_query(filters.regex(r"^reactionon:(-?\d+)$"))
async def cb_reaction_on(client, callback: CallbackQuery):
    data = callback.data or ""
    parts = data.split(":")
    if len(parts) != 2:
        return await callback.answer("Invalid data", show_alert=True)
    chat_id = int(parts[1])
    # permission check using callback.message as context
    ok, debug = await is_admin_or_sudo(client, callback.message)
    if not ok:
        return await callback.answer("Only admins/owner/sudoers can toggle.", show_alert=True)
    await set_reaction_status(chat_id, True)
    try:
        await callback.message.edit_text("✅ Reaction Bot enabled for this chat.", reply_markup=reaction_buttons(chat_id))
    except Exception:
        pass
    await callback.answer("Enabled")

@app.on_callback_query(filters.regex(r"^reactionoff:(-?\d+)$"))
async def cb_reaction_off(client, callback: CallbackQuery):
    data = callback.data or ""
    parts = data.split(":")
    if len(parts) != 2:
        return await callback.answer("Invalid data", show_alert=True)
    chat_id = int(parts[1])
    ok, debug = await is_admin_or_sudo(client, callback.message)
    if not ok:
        return await callback.answer("Only admins/owner/sudoers can toggle.", show_alert=True)
    await set_reaction_status(chat_id, False)
    try:
        await callback.message.edit_text("💤 Reaction Bot disabled for this chat.", reply_markup=reaction_buttons(chat_id))
    except Exception:
        pass
    await callback.answer("Disabled")

# -------------------- AUTO-REACT HANDLER --------------------
@app.on_message((filters.text | filters.sticker | filters.photo | filters.video | filters.document) & ~BANNED_USERS & (filters.group | filters.channel))
async def auto_react(client, message: Message):
    # global config toggle
    if not REACTION_BOT:
        return
    # only groups/supergroups
    chat_type = getattr(message.chat, "type", "").lower()
    if chat_type not in ("group", "supergroup"):
        return
    # skip commands
    if message.text and message.text.startswith("/"):
        return
    # skip bots
    if getattr(message.from_user, "is_bot", False):
        return

    chat_id = message.chat.id
    try:
        enabled = await get_reaction_status(chat_id)
    except Exception:
        enabled = False
    if not enabled:
        return

    try:
        emoji = next_emoji_local(chat_id)
        await message.react(emoji)
        print(f"[ReactionBot] Reacted in {chat_id} with {emoji}")
    except Exception as e:
        # fallback single heart attempt
        try:
            await message.react("❤️")
        except Exception:
            print(f"[ReactionBot] Failed to react in {chat_id}: {e}")
