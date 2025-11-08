import asyncio
import random
import time
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from VIPMUSIC import app
from config import BANNED_USERS, MENTION_USERNAMES, START_REACTIONS, OWNER_ID
from VIPMUSIC.utils.database import mongodb, get_sudoers

# =================== DATABASE COLLECTION ===================
COLLECTION = mongodb["reaction_mentions"]

# =================== CACHE ===================
custom_mentions = set(MENTION_USERNAMES)
admin_cache = {}  # {chat_id: {"admins": set(), "time": float}}


# =================== LOAD CUSTOM MENTIONS ===================
async def load_custom_mentions():
    docs = await COLLECTION.find().to_list(None)
    for doc in docs:
        custom_mentions.add(doc["name"].lower())
    print(f"[Reaction Manager] Loaded {len(custom_mentions)} mention triggers.")


# Auto-load on startup
asyncio.get_event_loop().create_task(load_custom_mentions())


# =================== ADMIN CACHE SYSTEM ===================
async def get_admins(client, chat_id: int):
    """Fetch or return cached admin list (cached for 10 minutes)."""
    now = time.time()
    if chat_id in admin_cache and (now - admin_cache[chat_id]["time"]) < 600:
        return admin_cache[chat_id]["admins"]

    admins = set()
    try:
        async for member in client.get_chat_members(chat_id, filter="administrators"):
            admins.add(member.user.id)
        admin_cache[chat_id] = {"admins": admins, "time": now}
    except Exception as e:
        print(f"[AdminCache] Error: {e}")
    return admins


# =================== PERMISSION CHECK ===================
async def is_admin_or_sudo(client, message: Message) -> bool:
    """Check if user is admin, owner, or sudo."""
    user_id = message.from_user.id
    chat_id = message.chat.id
    sudoers = await get_sudoers()

    # Owner or sudo
    if user_id == OWNER_ID or user_id in sudoers:
        return True

    # Private chat check
    if message.chat.type not in ["group", "supergroup"]:
        return False

    # Check admin cache first
    admins = await get_admins(client, chat_id)
    if user_id in admins:
        return True

    # Fallback — direct Telegram API call
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
            # Cache update (avoid future misses)
            admins.add(user_id)
            admin_cache[chat_id] = {"admins": admins, "time": time.time()}
            return True
    except Exception as e:
        print(f"[AdminCheckFallback] Error: {e}")

    return False


# =================== COMMAND: /addreact ===================
@app.on_message(filters.command("addreact") & ~BANNED_USERS)
async def add_reaction_name(client, message: Message):
    """Add a new reaction keyword."""
    if not await is_admin_or_sudo(client, message):
        return await message.reply_text("⚠️ Only admins or sudo users can add reaction names.")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/addreact <keyword>`", quote=True)

    name_to_add = message.text.split(None, 1)[1].strip().lower()

    if name_to_add in custom_mentions:
        return await message.reply_text(f"✅ `{name_to_add}` is already in the mention list!")

    await COLLECTION.insert_one({"name": name_to_add})
    custom_mentions.add(name_to_add)
    await message.reply_text(f"✨ Added `{name_to_add}` to the mention reaction list.")


# =================== COMMAND: /reactlist (Everyone) ===================
@app.on_message(filters.command("reactlist") & ~BANNED_USERS)
async def list_reactions(client, message: Message):
    """Show all active reaction trigger names."""
    if not custom_mentions:
        return await message.reply_text("ℹ️ No mention triggers found yet.")

    msg = "**🧠 Reaction Trigger List:**\n"
    msg += "\n".join([f"• `{x}`" for x in sorted(custom_mentions)])
    await message.reply_text(msg)


# =================== COMMAND: /delreact ===================
@app.on_message(filters.command("delreact") & ~BANNED_USERS)
async def delete_reaction_name(client, message: Message):
    """Remove a reaction trigger."""
    if not await is_admin_or_sudo(client, message):
        return await message.reply_text("⚠️ Only admins or sudo users can delete reaction names.")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/delreact <keyword>`")

    name_to_del = message.text.split(None, 1)[1].strip().lower()

    if name_to_del not in custom_mentions:
        return await message.reply_text(f"❌ `{name_to_del}` not found in mention list.")

    await COLLECTION.delete_one({"name": name_to_del})
    custom_mentions.remove(name_to_del)
    await message.reply_text(f"🗑 Removed `{name_to_del}` from mention list.")


# =================== COMMAND: /clearreact ===================
@app.on_message(filters.command("clearreact") & ~BANNED_USERS)
async def clear_reactions(client, message: Message):
    """Clear all reaction triggers."""
    if not await is_admin_or_sudo(client, message):
        return await message.reply_text("⚠️ Only admins or sudo users can clear reactions.")

    await COLLECTION.delete_many({})
    custom_mentions.clear()
    await message.reply_text("🧹 Cleared all custom reaction mentions.")


# =================== REACT ON MENTION ===================
@app.on_message((filters.text | filters.caption) & ~BANNED_USERS)
async def react_on_mentions(client, message: Message):
    """Automatically react when a trigger is found in text, caption, or usernames."""
    text = ""
    if message.text:
        text += message.text.lower()
    if message.caption:
        text += " " + message.caption.lower()
    if message.entities:
        for ent in message.entities:
            if ent.type == "mention" and message.text:
                text += " " + message.text[ent.offset:ent.offset + ent.length].lower()

    try:
        for name in custom_mentions:
            if name in text:
                emoji = random.choice(START_REACTIONS)
                await message.react(emoji)
                break
    except Exception as e:
        print(f"[mention_react] Error: {e}")
        pass
