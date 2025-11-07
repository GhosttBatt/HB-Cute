import asyncio
import random
from pyrogram import filters
from pyrogram.types import Message
from VIPMUSIC import app
from config import BANNED_USERS, MENTION_USERNAMES, START_REACTIONS
from VIPMUSIC.utils.database import mongodb
from VIPMUSIC.misc import SUDOERS

# =================== DATABASE COLLECTION ===================
COLLECTION = mongodb["reaction_mentions"]

# =================== CACHE ===================
custom_mentions = set(MENTION_USERNAMES)


# =================== LOAD CUSTOM MENTIONS ===================
async def load_custom_mentions():
    docs = await COLLECTION.find().to_list(None)
    for doc in docs:
        custom_mentions.add(doc["name"].lower())
    print(f"[Reaction Manager] Loaded {len(custom_mentions)} mention triggers.")


# Auto-load once when bot starts
asyncio.get_event_loop().create_task(load_custom_mentions())


# =================== PERMISSION CHECK ===================
async def is_admin_or_sudo(client, message: Message) -> bool:
    """Check if the user is admin or in sudoers."""
    user_id = message.from_user.id

    if user_id in SUDOERS or user_id == app.id:
        return True

    if message.chat.type in ["group", "supergroup"]:
        try:
            member = await message.chat.get_member(user_id)
            if member.status in ["administrator", "creator"]:
                return True
        except Exception:
            pass
    return False


# =================== COMMAND: /addreact ===================
@app.on_message(filters.command("addreact") & ~BANNED_USERS)
async def add_reaction_name(client, message: Message):
    """Add a username or keyword to the reaction list."""
    if not await is_admin_or_sudo(client, message):
        return await message.reply_text("⚠️ Only admins or sudo users can add reaction names.")

    if len(message.command) < 2:
        return await message.reply_text("Usage: `/addreact <name>`", quote=True)

    name_to_add = message.text.split(None, 1)[1].strip().lower()

    if name_to_add in custom_mentions:
        return await message.reply_text(f"✅ `{name_to_add}` is already in the mention list!")

    await COLLECTION.insert_one({"name": name_to_add})
    custom_mentions.add(name_to_add)
    await message.reply_text(f"✨ Added `{name_to_add}` to mention reaction list.")


# =================== COMMAND: /reactlist (Everyone) ===================
@app.on_message(filters.command("reactlist") & ~BANNED_USERS)
async def list_reactions(client, message: Message):
    """Show all active reaction trigger names."""
    if not custom_mentions:
        return await message.reply_text("ℹ️ No mention triggers found.")

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
        return await message.reply_text("Usage: `/delreact <name>`")

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
@app.on_message(filters.text & ~BANNED_USERS)
async def react_on_mentions(client, message: Message):
    """Automatically react with emoji when a trigger name is mentioned."""
    text = message.text.lower()
    try:
        if any(name in text for name in custom_mentions):
            emoji = random.choice(START_REACTIONS)
            await message.react(emoji)
    except Exception as e:
        print(f"[mention_react] Error: {e}")
        pass
