# reaction_bot.py
import asyncio
import random
from typing import Set, Dict, Tuple, Optional

from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ChatMemberStatus
from VIPMUSIC import app
from config import BANNED_USERS, MENTION_USERNAMES, START_REACTIONS, OWNER_ID
from VIPMUSIC.utils.database import mongodb, get_sudoers  # adapt if different in your project
from VIPMUSIC.utils.databases.reactiondb import is_reaction_on, reaction_on, reaction_off

# ---------------- DATABASE ----------------
COLLECTION = mongodb.get_collection("reaction_mentions")

# ---------------- CACHE ----------------
custom_mentions: Set[str] = set(x.lower().lstrip("@") for x in (MENTION_USERNAMES or []))

# ---------------- VALID REACTION EMOJIS ----------------
VALID_REACTIONS = {
    "❤️", "💖", "💘", "💞", "💓", "✨", "🔥", "💫",
    "💥", "🌸", "😍", "🥰", "💎", "🌙", "🌹", "😂",
    "😎", "🤩", "😘", "😉", "🤭", "💐", "😻", "🥳"
}

# Safely filter START_REACTIONS
SAFE_REACTIONS = [e for e in (START_REACTIONS or []) if e in VALID_REACTIONS]
if not SAFE_REACTIONS:
    SAFE_REACTIONS = list(VALID_REACTIONS)

# ---------------- PER-CHAT EMOJI ROTATION ----------------
chat_used_reactions: Dict[int, Set[str]] = {}

def next_emoji(chat_id: int) -> str:
    """Return a random, non-repeating emoji per chat."""
    if chat_id not in chat_used_reactions:
        chat_used_reactions[chat_id] = set()

    used = chat_used_reactions[chat_id]

    # Reset once all are used
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
        print(f"[Reaction Manager] Loaded {len(custom_mentions)} mention triggers.")
    except Exception as e:
        print(f"[Reaction Manager] DB load error: {e}")

# schedule startup load
asyncio.get_event_loop().create_task(load_custom_mentions())

# ---------------- ADMIN CHECK ----------------
async def is_admin_or_sudo(client, message: Message) -> Tuple[bool, Optional[str]]:
    user_id = getattr(message.from_user, "id", None)
    chat_id = message.chat.id
    chat_type = str(getattr(message.chat, "type", "")).lower()

    # Sudo or owner
    try:
        sudoers = await get_sudoers()
    except Exception:
        sudoers = set()

    if user_id and (user_id == OWNER_ID or user_id in sudoers):
        return True, None

    # Linked channel owner case
    sender_chat_id = getattr(message.sender_chat, "id", None)
    if sender_chat_id:
        try:
            chat = await client.get_chat(chat_id)
            if getattr(chat, "linked_chat_id", None) == sender_chat_id:
                return True, None
        except Exception:
            pass

    # Must be a group/supergroup/channel to check admin
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
            f"⚠️ Only admins or sudo users can add reaction names.\n\nDebug info:\n{debug or 'unknown'}"
        )

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/addreact <keyword_or_username>`")

    raw = message.text.split(None, 1)[1].strip()
    if not raw:
        return await message.reply_text("Usage: `/addreact <keyword_or_username>`")

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
        await COLLECTION.insert_one({"name": id_key})
        custom_mentions.add(id_key)

    msg = f"✨ Added `{name}`"
    if resolved_id:
        msg += f" (id: `{resolved_id}`)"
    await message.reply_text(msg)

# ---------------- /delreact ----------------
@app.on_message(filters.command("delreact") & ~BANNED_USERS)
async def delete_reaction_name(client, message: Message):
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            f"⚠️ Only admins or sudo users can delete reaction names.\n\nDebug info:\n{debug or 'unknown'}"
        )

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/delreact <keyword_or_username>`")

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
        await message.reply_text(f"🗑 Removed `{raw}` from mention list.")
    else:
        await message.reply_text(f"❌ `{raw}` not found in mention list.")

# ---------------- /reactlist ----------------
@app.on_message(filters.command("reactlist") & ~BANNED_USERS)
async def list_reactions(client, message: Message):
    if not custom_mentions:
        return await message.reply_text("ℹ️ No mention triggers found.")

    text = "\n".join(f"• `{m}`" for m in sorted(custom_mentions))
    await message.reply_text(f"**🧠 Reaction Triggers:**\n{text}")

# ---------------- /clearreact ----------------
@app.on_message(filters.command("clearreact") & ~BANNED_USERS)
async def clear_reactions(client, message: Message):
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            f"⚠️ Only admins or sudo users can clear reactions.\n\nDebug info:\n{debug or 'unknown'}"
        )

    await COLLECTION.delete_many({})
    custom_mentions.clear()
    await message.reply_text("🧹 Cleared all custom reaction mentions.")

# ---------------- /reaction (show buttons) ----------------
@app.on_message(filters.command("reaction") & ~BANNED_USERS)
async def reaction_menu(client, message: Message):
    # Only admins and sudoers can change per-chat setting
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            f"⚠️ Only admins or sudo users can toggle reactions.\n\nDebug info:\n{debug or 'unknown'}"
        )

    chat_id = message.chat.id
    enabled = await is_reaction_on(chat_id)
    status_text = "Enabled ✅" if enabled else "Disabled ❌"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Enable", callback_data=f"reaction_enable:{chat_id}"),
                InlineKeyboardButton("Disable", callback_data=f"reaction_disable:{chat_id}")
            ],
            [
                InlineKeyboardButton("Status", callback_data=f"reaction_status:{chat_id}")
            ]
        ]
    )
    await message.reply_text(f"Reactions are currently: **{status_text}**", reply_markup=keyboard)

# ---------------- CallbackQuery handlers for inline buttons ----------------
@app.on_callback_query(filters.regex(r"^reaction_(enable|disable|status):(-?\d+)$"))
async def reaction_callback(client: app.__class__, callback: CallbackQuery):
    # callback.data format: reaction_enable:<chat_id>
    data = callback.data or ""
    try:
        action, s_chat_id = data.split(":")
        chat_id = int(s_chat_id)
    except Exception:
        return await callback.answer("Invalid callback data.", show_alert=True)

    # Only allow the user who pressed to be admin/sudo in the chat where command is executed.
    # We'll build a fake message-like object for permission check
    class _FakeMsg:
        def __init__(self, from_user, chat):
            self.from_user = from_user
            self.chat = chat

    fake_msg = _FakeMsg(callback.from_user, await client.get_chat(chat_id))
    ok, debug = await is_admin_or_sudo(client, fake_msg)
    if not ok:
        await callback.answer("Only chat admins or sudo users can use this.", show_alert=True)
        return

    if action == "reaction_enable":
        await reaction_on(chat_id)
        await callback.answer("Reactions enabled for this chat.")
        try:
            await callback.edit_message_text("Reactions are currently: **Enabled ✅**", reply_markup=None)
        except Exception:
            pass
    elif action == "reaction_disable":
        await reaction_off(chat_id)
        await callback.answer("Reactions disabled for this chat.")
        try:
            await callback.edit_message_text("Reactions are currently: **Disabled ❌**", reply_markup=None)
        except Exception:
            pass
    else:  # status
        enabled = await is_reaction_on(chat_id)
        status_text = "Enabled ✅" if enabled else "Disabled ❌"
        await callback.answer(f"Current: {status_text}", show_alert=True)

# ---------------- /reactionon and /reactionoff (commands) ----------------
@app.on_message(filters.command("reactionon") & ~BANNED_USERS)
async def cmd_reaction_on(client, message: Message):
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            f"⚠️ Only admins or sudo users can enable reactions.\n\nDebug info:\n{debug or 'unknown'}"
        )

    chat_id = message.chat.id
    await reaction_on(chat_id)
    await message.reply_text("✅ Reactions enabled for this chat.")

@app.on_message(filters.command("reactionoff") & ~BANNED_USERS)
async def cmd_reaction_off(client, message: Message):
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            f"⚠️ Only admins or sudo users can disable reactions.\n\nDebug info:\n{debug or 'unknown'}"
        )

    chat_id = message.chat.id
    await reaction_off(chat_id)
    await message.reply_text("⛔ Reactions disabled for this chat.")

# ---------------- REACT ON MENTIONS (main runtime) ----------------
@app.on_message((filters.text | filters.caption) & ~BANNED_USERS)
async def react_on_mentions(client, message: Message):
    try:
        # Skip bot commands
        if message.text and message.text.startswith("/"):
            return

        chat_id = message.chat.id

        # Only react in groups/supergroups/channels where enabled
        # For private chats we can ignore or keep disabled (behavior: check is_reaction_on anyway)
        if not await is_reaction_on(chat_id):
            return

        text = (message.text or message.caption or "").lower()
        entities = (message.entities or []) + (message.caption_entities or [])
        usernames, user_ids = set(), set()

        # Parse entities
        for ent in entities:
            if ent.type == "mention":
                # extract exact substring from original text/caption, not lowercased
                src = message.text or message.caption or ""
                uname = src[ent.offset:ent.offset + ent.length].lstrip("@").lower()
                usernames.add(uname)
            elif ent.type == "text_mention" and ent.user:
                user_ids.add(ent.user.id)
                if ent.user.username:
                    usernames.add(ent.user.username.lower())

        reacted = False

        # 1️⃣ Username mentions
        for uname in usernames:
            if uname in custom_mentions or f"@{uname}" in text:
                emoji = next_emoji(chat_id)
                try:
                    await message.react(emoji)
                except Exception:
                    try:
                        await message.react("❤️")
                    except Exception:
                        pass
                reacted = True
                break

        # 2️⃣ ID-based
        if not reacted:
            for uid in user_ids:
                if f"id:{uid}" in custom_mentions:
                    emoji = next_emoji(chat_id)
                    try:
                        await message.react(emoji)
                    except Exception:
                        try:
                            await message.react("❤️")
                        except Exception:
                            pass
                    reacted = True
                    break

        # 3️⃣ Keyword trigger
        if not reacted:
            for trig in custom_mentions:
                if trig.startswith("id:"):
                    continue
                if trig in text or f"@{trig}" in text:
                    emoji = next_emoji(chat_id)
                    try:
                        await message.react(emoji)
                    except Exception:
                        try:
                            await message.react("❤️")
                        except Exception:
                            pass
                    break

    except Exception as e:
        print(f"[react_on_mentions] error: {e}")
