import asyncio
import random
from typing import Dict, Set
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatMemberStatus

from VIPMUSIC import app
from config import BANNED_USERS, START_REACTIONS, OWNER_ID
from VIPMUSIC.utils.database import mongodb, get_sudoers

print("[reaction_bot] reaction system loaded")

# ---------------- DATABASE ----------------
SETTINGS = mongodb["reaction_settings"]

# ---------------- STATE ----------------
REACTION_ENABLED = True  # default ON

# ---------------- VALID REACTIONS ----------------
VALID_REACTIONS = {
    "❤️", "💖", "💘", "💞", "💓", "✨", "🔥", "💫",
    "💥", "🌸", "😍", "🥰", "💎", "🌙", "🌹", "😂",
    "😎", "🤩", "😘", "😉", "🤭", "💐", "😻", "🥳"
}

SAFE_REACTIONS = [e for e in START_REACTIONS if e in VALID_REACTIONS]
if not SAFE_REACTIONS:
    SAFE_REACTIONS = list(VALID_REACTIONS)

# ---------------- ROTATION STORAGE ----------------
chat_used_reactions: Dict[int, Set[str]] = {}


def next_emoji(chat_id: int) -> str:
    if chat_id not in chat_used_reactions:
        chat_used_reactions[chat_id] = set()

    used = chat_used_reactions[chat_id]
    if len(used) >= len(SAFE_REACTIONS):
        used.clear()

    remaining = [e for e in SAFE_REACTIONS if e not in used]
    emoji = random.choice(remaining)
    used.add(emoji)
    chat_used_reactions[chat_id] = used
    return emoji

# ---------------- LOAD SWITCH STATE ----------------
async def load_reaction_state():
    global REACTION_ENABLED
    doc = await SETTINGS.find_one({"_id": "switch"})
    if doc:
        REACTION_ENABLED = doc.get("enabled", True)
    print(f"[Reaction Switch] Loaded => {REACTION_ENABLED}")

asyncio.get_event_loop().create_task(load_reaction_state())

# ---------------- ADMIN CHECK ----------------
async def is_admin_or_sudo(client, message: Message):
    user_id = getattr(message.from_user, "id", None)
    chat_id = message.chat.id

    try:
        sudoers = await get_sudoers()
    except Exception:
        sudoers = set()

    if user_id and (user_id == OWNER_ID or user_id in sudoers):
        return True, None

    if not user_id:
        return False, "no from_user"

    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
            return True, None
        return False, f"user_status={member.status}"
    except Exception as e:
        return False, f"error={e}"

# ---------------- ADMIN COMMAND PANEL ----------------
@app.on_message(filters.command("reaction") & ~BANNED_USERS)
async def react_command(client, message: Message):
    global REACTION_ENABLED
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(f"⚠️ Only admins/sudo users.\nDebug: {debug}")

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Enable", callback_data="react_on"),
             InlineKeyboardButton("🛑 Disable", callback_data="react_off")],
            [InlineKeyboardButton("🔍 Status", callback_data="react_status")]
        ]
    )
    await message.reply_text(
        f"**Reaction System Control**\n\nCurrent state: {'🟢 ON' if REACTION_ENABLED else '🔴 OFF'}",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex("^react_"))
async def reaction_callback(client, query: CallbackQuery):
    global REACTION_ENABLED
    ok, debug = await is_admin_or_sudo(client, query.message)
    if not ok:
        return await query.answer("Only admins/sudo users can do this.", show_alert=True)

    action = query.data
    if action == "react_on":
        REACTION_ENABLED = True
        await SETTINGS.update_one({"_id": "switch"}, {"$set": {"enabled": True}}, upsert=True)
        return await query.edit_message_text("✅ **Reactions Enabled**")
    elif action == "react_off":
        REACTION_ENABLED = False
        await SETTINGS.update_one({"_id": "switch"}, {"$set": {"enabled": False}}, upsert=True)
        return await query.edit_message_text("🛑 **Reactions Disabled**")
    elif action == "react_status":
        return await query.answer(f"Reactions are {'ON' if REACTION_ENABLED else 'OFF'}", show_alert=True)

# ---------------- AUTO REACTION SYSTEM ----------------
@app.on_message(
    ~filters.command([]) &  # Ignore all commands
    ~BANNED_USERS
)
async def auto_react(client, message: Message):
    if not REACTION_ENABLED:
        return
    try:
        chat_id = message.chat.id
        emoji = next_emoji(chat_id)
        # React to any message type safely
        try:
            await message.react(emoji)
        except:
            # fallback to ❤️ if some type can't be reacted
            await message.react("❤️")
    except Exception as e:
        print(f"[auto_react] error: {e}")
