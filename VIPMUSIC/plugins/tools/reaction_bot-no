import asyncio
import random
from typing import Set, Tuple, Optional, Dict
from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pyrogram.enums import ChatMemberStatus

from VIPMUSIC import app
from config import BANNED_USERS, MENTION_USERNAMES, START_REACTIONS, OWNER_ID
from VIPMUSIC.utils.database import mongodb, get_sudoers

print("[reaction_bot] reaction")

# ---------------- DATABASE ----------------
COLLECTION = mongodb["reaction_mentions"]
SETTINGS = mongodb["reaction_settings"]  # reaction ON/OFF switch storage

# ---------------- STATE ----------------
REACTION_ENABLED = True  # default ON

# ---------------- CACHE ----------------
custom_mentions: Set[str] = set(x.lower().lstrip("@") for x in MENTION_USERNAMES)

# ---------------- VALID REACTION EMOJIS ----------------
VALID_REACTIONS = {
    "❤️", "💖", "💘", "💞", "💓", "✨", "🔥", "💫",
    "💥", "🌸", "😍", "🥰", "💎", "🌙", "🌹", "😂",
    "😎", "🤩", "😘", "😉", "🤭", "💐", "😻", "🥳"
}

SAFE_REACTIONS = [e for e in START_REACTIONS if e in VALID_REACTIONS]
if not SAFE_REACTIONS:
    SAFE_REACTIONS = list(VALID_REACTIONS)

# ---------------- PER-CHAT NON-REPEATING EMOJI ROTATION ----------------
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

# ---------------- LOAD CUSTOM MENTIONS ----------------
async def load_custom_mentions():
    try:
        docs = await COLLECTION.find().to_list(None)
        for doc in docs:
            name = doc.get("name")
            if name:
                custom_mentions.add(str(name).lower().lstrip("@"))
        print(f"[Reaction Manager] Loaded {len(custom_mentions)} triggers.")
    except Exception as e:
        print(f"[Reaction Manager] DB load error: {e}")

asyncio.get_event_loop().create_task(load_custom_mentions())

# ---------------- LOAD SWITCH STATE ----------------
async def load_reaction_state():
    global REACTION_ENABLED
    doc = await SETTINGS.find_one({"_id": "switch"})
    if doc:
        REACTION_ENABLED = doc.get("enabled", True)
    print(f"[Reaction Switch] Loaded => {REACTION_ENABLED}")

asyncio.get_event_loop().create_task(load_reaction_state())

# ---------------- ADMIN CHECK ----------------
async def is_admin_or_sudo(client, message: Message) -> Tuple[bool, Optional[str]]:
    user_id = getattr(message.from_user, "id", None)
    chat_id = message.chat.id
    chat_type = str(getattr(message.chat, "type", "")).lower()

    try:
        sudoers = await get_sudoers()
    except Exception:
        sudoers = set()

    if user_id and (user_id == OWNER_ID or user_id in sudoers):
        return True, None

    sender_chat_id = getattr(message.sender_chat, "id", None)
    if sender_chat_id:
        try:
            chat = await client.get_chat(chat_id)
            if getattr(chat, "linked_chat_id", None) == sender_chat_id:
                return True, None
        except Exception:
            pass

    if chat_type not in ("chattype.group", "chattype.supergroup", "chattype.channel"):
        return False, f"chat_type={chat_type}"

    if not user_id:
        return False, "no from_user"

    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
            return True, None
        else:
            return False, f"user_status={member.status}"
    except Exception as e:
        return False, f"error={e}"

# ---------------- INLINE BUTTON PANEL (/react COMMAND) ----------------
@app.on_message(filters.command("reaction") & ~BANNED_USERS)
async def react_command(client, message: Message):
    global REACTION_ENABLED

    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            "⚠️ Only admins/sudo users may control reaction system.\n\n"
            f"Debug: {debug}"
        )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Enable", callback_data="react_on"),
                InlineKeyboardButton("🛑 Disable", callback_data="react_off"),
            ],
            [
                InlineKeyboardButton("🔍 Status", callback_data="react_status")
            ]
        ]
    )

    await message.reply_text(
        f"**Reaction System Control**\n\n"
        f"Current state: {'🟢 ON' if REACTION_ENABLED else '🔴 OFF'}",
        reply_markup=keyboard
    )

# ---------------- CALLBACK HANDLER FOR BUTTONS ----------------
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
        return await query.answer(
            f"Reactions are {'ON' if REACTION_ENABLED else 'OFF'}",
            show_alert=True
        )

# ---------------- AUTO REACTION SYSTEM ----------------
@app.on_message(
    (filters.text | filters.caption)
    & ~filters.command([])
    & ~BANNED_USERS
)
async def react_on_mentions(client, message: Message):


    if not REACTION_ENABLED:
        return

    try:
        if message.text and message.text.startswith("/"):
            return

        chat_id = message.chat.id
        text = (message.text or message.caption or "").lower()
        entities = (message.entities or []) + (message.caption_entities or [])
        usernames, user_ids = set(), set()

        for ent in entities:
            if ent.type == "mention":
                uname = (message.text or message.caption)[ent.offset:ent.offset + ent.length].lstrip("@").lower()
                usernames.add(uname)
            elif ent.type == "text_mention" and ent.user:
                user_ids.add(ent.user.id)
                if ent.user.username:
                    usernames.add(ent.user.username.lower())

        reacted = False

        for uname in usernames:
            if uname in custom_mentions or f"@{uname}" in text:
                emoji = next_emoji(chat_id)
                try:
                    await message.react(emoji)
                except:
                    await message.react("❤️")
                reacted = True
                break

        if not reacted:
            for uid in user_ids:
                if f"id:{uid}" in custom_mentions:
                    emoji = next_emoji(chat_id)
                    try:
                        await message.react(emoji)
                    except:
                        await message.react("❤️")
                    reacted = True
                    break

        if not reacted:
            for trig in custom_mentions:
                if trig.startswith("id:"):
                    continue
                if trig in text or f"@{trig}" in text:
                    emoji = next_emoji(chat_id)
                    try:
                        await message.react(emoji)
                    except:
                        await message.react("❤️")
                    break

    except Exception as e:
        print(f"[react_on_mentions] error: {e}")
