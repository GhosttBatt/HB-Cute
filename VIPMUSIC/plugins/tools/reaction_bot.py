# reaction_bot.py
import asyncio
import random
from typing import Set, Dict, Optional, Tuple

from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ChatMemberStatus

from VIPMUSIC import app
from config import BANNED_USERS, MENTION_USERNAMES, START_REACTIONS, OWNER_ID
from VIPMUSIC.utils.database import mongodb, get_sudoers  # keep your project's get_sudoers
from VIPMUSIC.utils.databases.reactiondb import (
    is_reaction_on,
    reaction_on,
    reaction_off,
    load_all_statuses,
)

# ---------------- DATABASE ----------------
COLLECTION = mongodb["reaction_mentions"]

# ---------------- CACHE ----------------
# initial mentions from config + DB loaded ones
custom_mentions: Set[str] = set(x.lower().lstrip("@") for x in (MENTION_USERNAMES or []))

# ---------------- VALID REACTION EMOJIS ----------------
VALID_REACTIONS = {
    "❤️", "💖", "💘", "💞", "💓", "✨", "🔥", "💫",
    "💥", "🌸", "😍", "🥰", "💎", "🌙", "🌹", "😂",
    "😎", "🤩", "😘", "😉", "🤭", "💐", "😻", "🥳"
}

# Filter START_REACTIONS safely
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

    # Reset once all used
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

# Schedule DB loads at startup
asyncio.get_event_loop().create_task(load_custom_mentions())
asyncio.get_event_loop().create_task(load_all_statuses())

# ---------------- ADMIN CHECK ----------------
async def is_admin_or_sudo(client, message: Message) -> Tuple[bool, Optional[str]]:
    """
    Returns (True, None) if user is OWNER/IN SUDOERS or chat admin.
    Otherwise returns (False, debug_str).
    """
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

    # Linked channel owner check (mirrors your reference)
    sender_chat_id = getattr(message.sender_chat, "id", None)
    if sender_chat_id:
        try:
            chat = await client.get_chat(chat_id)
            if getattr(chat, "linked_chat_id", None) == sender_chat_id:
                return True, None
        except Exception:
            pass

    # only check in group/supergroup/channel context
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

# ---------------- /reaction (show buttons) & /reaction enable/disable ----------------
def reaction_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Enable ✅", callback_data=f"reaction_toggle:{chat_id}:on"),
                InlineKeyboardButton("Disable ⛔️", callback_data=f"reaction_toggle:{chat_id}:off"),
            ]
        ]
    )
    return kb

@app.on_message(filters.command("reaction") & ~BANNED_USERS)
async def reaction_command(client, message: Message):
    """
    /reaction -> shows enable/disable buttons
    /reaction enable -> enables immediately
    /reaction disable -> disables immediately
    """
    # admin check
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            f"⚠️ Only admins or sudo users can manage reactions.\n\nDebug info:\n{debug or 'unknown'}"
        )

    # Accept subcommands
    if len(message.command) == 2:
        sub = message.command[1].lower()
        if sub in ("enable", "on"):
            await reaction_on(message.chat.id)
            return await message.reply_text("✅ Reactions enabled for this chat.")
        if sub in ("disable", "off"):
            await reaction_off(message.chat.id)
            return await message.reply_text("⛔️ Reactions disabled for this chat.")

    # Default: show buttons
    await message.reply_text(
        "Manage reactions for this chat:",
        reply_markup=reaction_keyboard(message.chat.id)
    )

# ---------------- /reactionon and /reactionoff commands ----------------
@app.on_message(filters.command("reactionon") & ~BANNED_USERS)
async def cmd_reaction_on(client, message: Message):
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            f"⚠️ Only admins or sudo users can enable reactions.\n\nDebug info:\n{debug or 'unknown'}"
        )

    await reaction_on(message.chat.id)
    await message.reply_text("✅ Reactions turned ON for this chat.")

@app.on_message(filters.command("reactionoff") & ~BANNED_USERS)
async def cmd_reaction_off(client, message: Message):
    ok, debug = await is_admin_or_sudo(client, message)
    if not ok:
        return await message.reply_text(
            f"⚠️ Only admins or sudo users can disable reactions.\n\nDebug info:\n{debug or 'unknown'}"
        )

    await reaction_off(message.chat.id)
    await message.reply_text("⛔️ Reactions turned OFF for this chat.")

# ---------------- CallbackQuery handler for the inline buttons ----------------
@app.on_callback_query(filters.regex(r"^reaction_toggle:"))
async def reaction_toggle_cb(client: app.__class__, cb: CallbackQuery):
    data = cb.data or ""
    parts = data.split(":")
    if len(parts) != 3:
        return await cb.answer("Invalid data.", show_alert=True)

    _, chat_id_str, action = parts
    try:
        chat_id = int(chat_id_str)
    except ValueError:
        return await cb.answer("Invalid chat id.", show_alert=True)

    # Ensure only admins or sudoers can press the buttons
    # The callback query has 'from_user'
    class FakeMessage:
        # quick shim for is_admin_or_sudo (we only need chat.id and from_user)
        def __init__(self, chat_id, from_user):
            self.chat = type("c", (), {"id": chat_id, "type": "supergroup"})
            self.from_user = from_user
            self.sender_chat = None

    helper_msg = FakeMessage(chat_id, cb.from_user)
    ok, debug = await is_admin_or_sudo(client, helper_msg)
    if not ok:
        return await cb.answer("Only group admins or sudoers can use this.", show_alert=True)

    if action == "on":
        await reaction_on(chat_id)
        await cb.answer("Reactions enabled ✅")
        try:
            await cb.edit_message_text("Reactions enabled for this chat ✅", reply_markup=reaction_keyboard(chat_id))
        except Exception:
            pass
    elif action == "off":
        await reaction_off(chat_id)
        await cb.answer("Reactions disabled ⛔️")
        try:
            await cb.edit_message_text("Reactions disabled for this chat ⛔️", reply_markup=reaction_keyboard(chat_id))
        except Exception:
            pass
    else:
        await cb.answer("Unknown action.", show_alert=True)

# ---------------- REACT ON MENTIONS (main reaction logic) ----------------
@app.on_message((filters.text | filters.caption) & ~BANNED_USERS)
async def react_on_mentions(client, message: Message):
    try:
        # Skip bot commands
        if message.text and message.text.startswith("/"):
            return

        chat_id = message.chat.id

        # If reactions are OFF for this chat - skip
        try:
            enabled = await is_reaction_on(chat_id)
        except Exception:
            # safe default: on
            enabled = True

        if not enabled:
            return

        text = (message.text or message.caption or "").lower()
        entities = (message.entities or []) + (message.caption_entities or [])
        usernames, user_ids = set(), set()

        # Parse entities
        for ent in entities:
            if ent.type == "mention":
                raw = (message.text or message.caption)[ent.offset:ent.offset + ent.length].lstrip("@").lower()
                usernames.add(raw)
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

        # 2️⃣ ID-based mentions
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
        # never crash the bot on reaction errors
        print(f"[react_on_mentions] error: {e}")
