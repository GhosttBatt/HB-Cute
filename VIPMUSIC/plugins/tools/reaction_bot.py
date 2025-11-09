import asyncio
from pyrogram import filters
from VIPMUSIC import app
from VIPMUSIC.utils.database import reactiondb
from VIPMUSIC.utils.database.reactiondb import get_reaction_status, set_reaction_status
from VIPMUSIC.misc import SUDOERS
from VIPMUSIC.utils.decorators import AdminActual
from VIPMUSIC.utils.database import is_reaction_enabled, enable_reactions, disable_reactions
from VIPMUSIC.utils.filters import command
from VIPMUSIC import LOGGER
from config import BANNED_USERS

# ======================
# Reaction Control System
# ======================

@app.on_message(filters.command(["reactionon", "reaction_enable", "reaction_enable"]) & ~BANNED_USERS & filters.chat_type.groups)
@AdminActual
async def reaction_on(_, message):
    chat_id = message.chat.id
    status = await get_reaction_status(chat_id)
    if status:
        await message.reply_text("✅ Reactions are already **enabled** in this chat.")
    else:
        await set_reaction_status(chat_id, True)
        await message.reply_text("🎉 Reactions have been **enabled** successfully for this chat!")


@app.on_message(filters.command(["reactionoff", "reaction_disable", "reaction_disable"]) & ~BANNED_USERS & filters.chat_type.groups)
@AdminActual
async def reaction_off(_, message):
    chat_id = message.chat.id
    status = await get_reaction_status(chat_id)
    if not status:
        await message.reply_text("⚠️ Reactions are already **disabled** in this chat.")
    else:
        await set_reaction_status(chat_id, False)
        await message.reply_text("🚫 Reactions have been **disabled** for this chat.")


@app.on_message(filters.command(["reaction", "reactstatus"]) & ~BANNED_USERS & filters.chat_type.groups)
@AdminActual
async def reaction_status(_, message):
    chat_id = message.chat.id
    status = await get_reaction_status(chat_id)
    if status:
        await message.reply_text("✅ Reactions are currently **enabled** in this chat.")
    else:
        await message.reply_text("❌ Reactions are currently **disabled** in this chat.")


# ======================
# Auto Reaction Handler
# ======================

@app.on_message((filters.text | filters.caption) & ~BANNED_USERS & filters.chat_type.groups)
async def auto_react(client, message):
    try:
        chat_id = message.chat.id
        status = await get_reaction_status(chat_id)
        if not status:
            return

        # Fetch triggers and react
        mention_triggers = await reactiondb.get_mention_triggers()
        for trigger in mention_triggers:
            if trigger.lower() in (message.text or "").lower():
                emoji = await reactiondb.get_random_emoji()
                if emoji:
                    try:
                        await message.react(emoji)
                    except Exception as e:
                        LOGGER(__name__).warning(f"[Reaction Manager] Reaction failed: {e}")
                break
    except Exception as e:
        LOGGER(__name__).error(f"[Reaction Manager] Error in auto_react: {e}")
