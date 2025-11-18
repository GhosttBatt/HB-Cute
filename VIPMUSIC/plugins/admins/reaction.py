import asyncio
import random
from typing import Set, Tuple, Optional, Dict
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from VIPMUSIC import app
from config import BANNED_USERS, MENTION_USERNAMES, START_REACTIONS, OWNER_ID
from VIPMUSIC.utils.database import mongodb, get_sudoers

print("[reaction] addreact, delreact, reactlist, clearreact")

# ---------------- DATABASE ----------------
COLLECTION = mongodb["reaction_mentions"]

# ---------------- CACHE ----------------
custom_mentions: Set[str] = set(x.lower().lstrip("@") for x in MENTION_USERNAMES)

# ---------------- VALID TELEGRAM REACTIONS ONLY ----------------
VALID_REACTIONS = {
    "👍", "👎", "❤️", "🔥", "👏",
    "😁", "🤔", "😢", "🤯", "😍",
    "🤬", "😱", "🎉", "🤩", "🙏"
}

SAFE_REACTIONS = list(VALID_REACTIONS)

# ---------------- PER-CHAT EMOJI ROTATION ----------------
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

# ---------------- LOAD ON STARTUP ----------------
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
        return False, "no from_user and not linked"

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
        return await message.reply_text(
            f"⚠️ Only admins or sudo users can add reaction triggers.\n\nDebug: `{debug}`",
            parse_mode="markdown"
        )

    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/addreact <keyword_or_username>`",
            parse_mode="markdown"
        )

    raw = message.text.split(None, 1)[1].strip()
    name = raw.lower().lstrip("@")

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
        custom_mentions.add(id_key)
        await COLLECTION.insert_one({"name": id_key})

    msg = f"✨ Added `{name}`"
    if resolved_id:
        msg += f" (id: `{resolved_id}`)"

    await message.reply_text(msg, parse_mode="markdown")

# ---------------- /delreact ----------------
@app.on_message(filters.command("delreact") & ~BANNED_USERS)
async def delete_reaction_name(client, message: Message):
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            f"⚠️ Only admins or sudo users can delete reaction triggers.\n\nDebug: `{debug}`",
            parse_mode="markdown"
        )

    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/delreact <keyword_or_username>`",
            parse_mode="markdown"
        )

    raw = message.text.split(None, 1)[1].strip().lower().lstrip("@")
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
        return await message.reply_text(f"🗑 Removed `{raw}`.", parse_mode="markdown")
    else:
        return await message.reply_text(f"❌ `{raw}` not found.", parse_mode="markdown")

# ---------------- /reactlist ----------------
@app.on_message(filters.command("reactlist") & ~BANNED_USERS)
async def list_reactions(client, message: Message):
    if not custom_mentions:
        return await message.reply_text("ℹ️ No triggers found.")

    text = "\n".join(f"• `{m}`" for m in sorted(custom_mentions))
    await message.reply_text(f"**🧠 Reaction Triggers:**\n{text}", parse_mode="markdown")

# ---------------- /clearreact ----------------
@app.on_message(filters.command("clearreact") & ~BANNED_USERS)
async def clear_reactions(client, message: Message):
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            f"⚠️ Only admins or sudo users can clear reactions.\n\nDebug: `{debug}`",
            parse_mode="markdown"
        )

    await COLLECTION.delete_many({})
    custom_mentions.clear()
    await message.reply_text("🧹 Cleared all reaction triggers.")

# ---------------- REACT ON MENTIONS (STRICT MODE) ----------------
@app.on_message((filters.text | filters.caption) & ~BANNED_USERS)
async def react_on_mentions(client, message: Message):

    try:
        if message.text and message.text.startswith("/"):
            return

        chat_id = message.chat.id
        text = (message.text or message.caption or "").lower()

        # Exact-word split (prevents substring triggers)
        words = set(text.replace("@", " @").split())

        # Extract mentions
        entities = (message.entities or []) + (message.caption_entities or [])
        mentioned_usernames = set()
        mentioned_ids = set()

        for ent in entities:
            if ent.type == "mention":
                uname = (message.text or message.caption)[ent.offset:ent.offset + ent.length]
                mentioned_usernames.add(uname.lstrip("@").lower())

            elif ent.type == "text_mention" and ent.user:
                mentioned_ids.add(ent.user.id)
                if ent.user.username:
                    mentioned_usernames.add(ent.user.username.lower())

        # 1) Username triggers
        for uname in mentioned_usernames:
            if uname in custom_mentions:
                return await message.react(next_emoji(chat_id))

        # 2) ID triggers
        for uid in mentioned_ids:
            if f"id:{uid}" in custom_mentions:
                return await message.react(next_emoji(chat_id))

        # 3) Keyword triggers (EXACT match only)
        for trig in custom_mentions:
            if trig.startswith("id:"):
                continue

            if trig in words or f"@{trig}" in words:
                return await message.react(next_emoji(chat_id))

    except Exception as e:
        print(f"[react_on_mentions] error: {e}")
