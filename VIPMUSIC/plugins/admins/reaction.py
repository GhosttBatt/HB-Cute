import asyncio
import random
from typing import Set, Dict, Optional, Tuple

from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus, ChatType
from VIPMUSIC import app
from config import BANNED_USERS, MENTION_USERNAMES, OWNER_ID
from VIPMUSIC.utils.database import mongodb, get_sudoers

print("[reaction] addreact, delreact, reactlist, clearreact")

# ---------------- DB ----------------
COLLECTION = mongodb["reaction_mentions"]

# ---------------- CACHE ----------------
custom_mentions: Set[str] = set(
    x.lower().lstrip("@") for x in (MENTION_USERNAMES or [])
)

# ---------------- TELEGRAM SAFE EMOJIS ----------------
VALID_REACTIONS = {
    "👍", "👎", "❤️", "🔥", "👏",
    "😁", "🤔", "😢", "🤯", "😍",
    "🤬", "😱", "🎉", "🤩", "🙏"
}

SAFE_REACTIONS = list(VALID_REACTIONS)

# ---------------- ROTATION STORAGE ----------------
chat_used_reactions: Dict[int, Set[str]] = {}


def next_emoji(chat_id: int) -> str:
    if chat_id not in chat_used_reactions:
        chat_used_reactions[chat_id] = set()

    used = chat_used_reactions[chat_id]
    if len(used) == len(SAFE_REACTIONS):
        used.clear()

    remaining = [e for e in SAFE_REACTIONS if e not in used]
    emoji = random.choice(remaining)
    used.add(emoji)
    chat_used_reactions[chat_id] = used

    return emoji


# ---------------- LOAD TRIGGERS ----------------
async def load_custom_mentions():
    try:
        docs = await COLLECTION.find({}).to_list(length=None)
        for doc in docs:
            name = doc.get("name")
            if name:
                custom_mentions.add(name.lower().lstrip("@"))
        print(f"[Reaction Manager] Loaded {len(custom_mentions)} triggers.")
    except Exception as e:
        print(f"[Reaction Manager] DB load error: {e}")


asyncio.get_event_loop().create_task(load_custom_mentions())


# ---------------- ADMIN CHECK ----------------
async def is_admin_or_sudo(client, message: Message) -> Tuple[bool, Optional[str]]:
    user = message.from_user
    chat = message.chat

    if not chat or not user:
        return False, "invalid message"

    user_id = user.id
    chat_id = chat.id

    # Owner / Sudoer
    try:
        sudoers = await get_sudoers()
    except Exception:
        sudoers = set()

    if user_id == OWNER_ID or user_id in sudoers:
        return True, None

    # Only admins allowed beyond this point
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL):
        return False, f"chat_type={chat.type}"

    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
            return True, None
        return False, f"user_status={member.status}"
    except Exception as e:
        return False, f"get_chat_member_error={e}"


# ---------------- ADD REACT ----------------
@app.on_message(filters.command("addreact") & ~BANNED_USERS)
async def add_reaction_name(client, message: Message):
    ok, reason = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            f"⚠️ Admins only.\nDebug: `{reason}`"
        )

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/addreact <username_or_keyword>`")

    raw = message.text.split(None, 1)[1].strip().lower().lstrip("@")

    # Avoid duplicates
    if raw in custom_mentions:
        return await message.reply_text(f"ℹ️ `{raw}` is already in the list.")

    resolved_id = None
    try:
        user = await client.get_users(raw)
        resolved_id = user.id
    except:
        pass

    await COLLECTION.update_one(
        {"name": raw},
        {"$setOnInsert": {"name": raw}},
        upsert=True
    )
    custom_mentions.add(raw)

    if resolved_id:
        id_key = f"id:{resolved_id}"
        if id_key not in custom_mentions:
            await COLLECTION.update_one(
                {"name": id_key},
                {"$setOnInsert": {"name": id_key}},
                upsert=True
            )
            custom_mentions.add(id_key)

    msg = f"✨ Added `{raw}`"
    if resolved_id:
        msg += f" (id: `{resolved_id}`)"
    await message.reply_text(msg)


# ---------------- DELETE REACT ----------------
@app.on_message(filters.command("delreact") & ~BANNED_USERS)
async def delete_reaction_name(client, message: Message):
    ok, reason = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(f"⚠️ Admins only.\nDebug: `{reason}`")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/delreact <keyword_or_username>`")

    raw = message.text.split(None, 1)[1].strip().lower().lstrip("@")

    removed = False

    if raw in custom_mentions:
        custom_mentions.remove(raw)
        await COLLECTION.delete_one({"name": raw})
        removed = True

    # Remove ID if user exists
    try:
        user = await client.get_users(raw)
        id_key = f"id:{user.id}"
        if id_key in custom_mentions:
            custom_mentions.remove(id_key)
            await COLLECTION.delete_one({"name": id_key})
            removed = True
    except:
        pass

    if removed:
        return await message.reply_text(f"🗑 Removed `{raw}`.")
    return await message.reply_text(f"❌ `{raw}` not found.")


# ---------------- REACT LIST ----------------
@app.on_message(filters.command("reactlist") & ~BANNED_USERS)
async def list_reactions(client, message: Message):
    if not custom_mentions:
        return await message.reply_text("No reaction triggers found.")

    text = "\n".join(f"• `{m}`" for m in sorted(custom_mentions))
    await message.reply_text(f"**🧠 Reaction Triggers:**\n{text}")


# ---------------- CLEAR REACT ----------------
@app.on_message(filters.command("clearreact") & ~BANNED_USERS)
async def clear_reactions(client, message: Message):
    ok, reason = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(f"⚠️ Admins only.\nDebug: `{reason}`")

    await COLLECTION.delete_many({})
    custom_mentions.clear()
    await message.reply_text("🧹 Cleared all reaction triggers.")


# ---------------- REACT TO MENTIONS (NO COMMANDS) ----------------
@app.on_message(
    (filters.text | filters.caption)
    & ~filters.regex(r"^/")        # IMPORTANT: Ignore ALL commands (Pyrogram v1 safe)
    & ~BANNED_USERS
)
async def react_on_mentions(client, message: Message):
    try:
        raw = message.text or message.caption or ""
        if not raw:
            return

        text = raw.lower()

        # Extra safeguard to ignore command-like prefixes
        if text.startswith(("/", "!", "$", ".", "#")):
            return

        chat_id = message.chat.id

        # Word splitting
        words = set(text.replace("@", " @").split())

        # Collect entities
        entities = (message.entities or []) + (message.caption_entities or [])
        mentioned_usernames = set()
        mentioned_ids = set()

        for ent in entities:
            try:
                if ent.type == "mention":
                    src = message.text or message.caption
                    username = src[ent.offset:ent.offset + ent.length]
                    mentioned_usernames.add(username.lstrip("@").lower())

                elif ent.type == "text_mention" and ent.user:
                    mentioned_ids.add(ent.user.id)
                    if ent.user.username:
                        mentioned_usernames.add(ent.user.username.lower())
            except:
                continue

        # Username triggers
        for uname in mentioned_usernames:
            if uname in custom_mentions:
                return await message.react(next_emoji(chat_id))

        # ID triggers
        for uid in mentioned_ids:
            if f"id:{uid}" in custom_mentions:
                return await message.react(next_emoji(chat_id))

        # Keyword triggers
        for trig in custom_mentions:
            if trig.startswith("id:"):
                continue
            if trig in words or f"@{trig}" in words:
                return await message.react(next_emoji(chat_id))

    except Exception as e:
        print(f"[react_on_mentions] error: {e}")
