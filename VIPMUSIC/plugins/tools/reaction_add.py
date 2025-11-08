import asyncio
import random
import time
from typing import Set, Tuple, Optional

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from VIPMUSIC import app
from config import BANNED_USERS, MENTION_USERNAMES, START_REACTIONS, OWNER_ID
from VIPMUSIC.utils.database import mongodb, get_sudoers


# ---------------- DATABASE ----------------
COLLECTION = mongodb["reaction_mentions"]

# ---------------- CACHE ----------------
custom_mentions: Set[str] = set(x.lower().lstrip("@") for x in MENTION_USERNAMES)


# ---------------- LOAD ON STARTUP ----------------
async def load_custom_mentions():
    try:
        docs = await COLLECTION.find().to_list(None)
        for doc in docs:
            name = doc.get("name")
            if name:
                custom_mentions.add(str(name).lower().lstrip("@"))
        print(f"[Reaction Manager] Loaded {len(custom_mentions)} mention triggers.")
    except Exception as e:
        print(f"[Reaction Manager] DB load error: {e}")

asyncio.get_event_loop().create_task(load_custom_mentions())


# ---------------- ADMIN CHECK ----------------
async def is_admin_or_sudo(client, message: Message) -> Tuple[bool, Optional[str]]:
    """
    Robust admin check that works in normal groups, supergroups, and linked channels.
    Returns (is_admin_bool, debug_string_or_None)
    """
    user_id = getattr(message.from_user, "id", None)
    chat_id = message.chat.id
    chat_type = getattr(message.chat, "type", "").lower()

    # Check sudoers or owner
    try:
        sudoers = await get_sudoers()
    except Exception:
        sudoers = set()

    if user_id and (user_id == OWNER_ID or user_id in sudoers):
        return True, None

    # Allow messages sent as channel (linked chat)
    sender_chat_id = getattr(message.sender_chat, "id", None)
    if sender_chat_id:
        try:
            chat = await client.get_chat(chat_id)
            if getattr(chat, "linked_chat_id", None) == sender_chat_id:
                return True, None  # Linked channel admin
        except Exception:
            pass

    # If not in a group, reject
    if chat_type not in ("group", "supergroup", "channel"):
        return False, f"chat_type={chat_type}"

    # If user_id missing, fail
    if not user_id:
        return False, "no from_user and not linked"

    # Normal admin check
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
            return True, None
        else:
            return False, f"user_status={member.status}"
    except Exception as e:
        return False, f"get_chat_member_error={e}"


# ---------------- /addreact ----------------
@app.on_message(filters.command("addreact") & ~BANNED_USERS)
async def add_reaction_name(client, message: Message):
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        await message.reply_text(
            "⚠️ Only admins or sudo users can add reaction names.\n\nDebug info:\n" + (debug or "unknown"),
            quote=True,
        )
        print("[addreact fail]", debug)
        return

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/addreact <keyword_or_username>`", quote=True)

    raw = message.text.split(None, 1)[1].strip()
    if not raw:
        return await message.reply_text("Usage: `/addreact <keyword_or_username>`", quote=True)

    name = raw.lower().lstrip("@")

    # Try resolving username to user ID
    resolved_id = None
    try:
        user = await client.get_users(name)
        if getattr(user, "id", None):
            resolved_id = user.id
    except Exception:
        pass

    await COLLECTION.insert_one({"name": name})
    custom_mentions.add(name)
    if resolved_id:
        id_key = f"id:{resolved_id}"
        await COLLECTION.insert_one({"name": id_key})
        custom_mentions.add(id_key)

    msg = f"✨ Added `{name}`"
    if resolved_id:
        msg += f" (id: `{resolved_id}`)"
    await message.reply_text(msg, quote=True)


# ---------------- /delreact ----------------
@app.on_message(filters.command("delreact") & ~BANNED_USERS)
async def delete_reaction_name(client, message: Message):
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        await message.reply_text(
            "⚠️ Only admins or sudo users can delete reaction names.\n\nDebug info:\n" + (debug or "unknown"),
            quote=True,
        )
        print("[delreact fail]", debug)
        return

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/delreact <keyword_or_username>`", quote=True)

    raw = message.text.split(None, 1)[1].strip().lower().lstrip("@")
    if not raw:
        return await message.reply_text("Usage: `/delreact <keyword_or_username>`", quote=True)

    removed = False

    if raw in custom_mentions:
        custom_mentions.remove(raw)
        await COLLECTION.delete_one({"name": raw})
        removed = True

    try:
        user = await client.get_users(raw)
        if getattr(user, "id", None):
            id_key = f"id:{user.id}"
            if id_key in custom_mentions:
                custom_mentions.remove(id_key)
                await COLLECTION.delete_one({"name": id_key})
                removed = True
    except Exception:
        pass

    if removed:
        await message.reply_text(f"🗑 Removed `{raw}` from mention list.", quote=True)
    else:
        await message.reply_text(f"❌ `{raw}` not found in mention list.", quote=True)


# ---------------- /reactlist ----------------
@app.on_message(filters.command("reactlist") & ~BANNED_USERS)
async def list_reactions(client, message: Message):
    if not custom_mentions:
        return await message.reply_text("ℹ️ No mention triggers found.", quote=True)

    lines = []
    for it in sorted(custom_mentions):
        if it.startswith("id:"):
            lines.append(f"(user id) `{it}`")
        else:
            lines.append(f"`{it}`")

    await message.reply_text("**🧠 Reaction Trigger List:**\n" + "\n".join(f"• {x}" for x in lines), quote=True)


# ---------------- /clearreact ----------------
@app.on_message(filters.command("clearreact") & ~BANNED_USERS)
async def clear_reactions(client, message: Message):
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        await message.reply_text(
            "⚠️ Only admins or sudo users can clear reactions.\n\nDebug info:\n" + (debug or "unknown"),
            quote=True,
        )
        print("[clearreact fail]", debug)
        return

    await COLLECTION.delete_many({})
    custom_mentions.clear()
    await message.reply_text("🧹 Cleared all custom reaction mentions.", quote=True)


# ---------------- REACT LOGIC ----------------
@app.on_message((filters.text | filters.caption) & ~BANNED_USERS)
async def react_on_mentions(client, message: Message):
    """Automatically react when trigger keyword or username is mentioned."""
    try:
        text = (message.text or message.caption or "").lower()
        entities = (message.entities or []) + (message.caption_entities or [])
        usernames, user_ids = set(), set()

        # Extract usernames and user IDs from message entities
        for ent in entities:
            if ent.type == "mention":
                uname = text[ent.offset : ent.offset + ent.length].lstrip("@").lower()
                usernames.add(uname)
            elif ent.type == "text_mention" and ent.user:
                user_ids.add(ent.user.id)
                if ent.user.username:
                    usernames.add(ent.user.username.lower())

        # Check entity usernames
        for uname in usernames:
            if uname in custom_mentions or f"@{uname}" in text:
                await message.react(random.choice(START_REACTIONS))
                return

        # Check user-id triggers
        for uid in user_ids:
            if f"id:{uid}" in custom_mentions:
                await message.react(random.choice(START_REACTIONS))
                return

        # Check raw text for triggers
        for trig in custom_mentions:
            if trig.startswith("id:"):
                continue
            if trig in text or f"@{trig}" in text:
                await message.react(random.choice(START_REACTIONS))
                return

    except Exception as e:
        print(f"[react_on_mentions] error: {e}")
