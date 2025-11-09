# VIPMUSIC/plugins/tools/reaction_bot.py

import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from VIPMUSIC import app
from config import BANNED_USERS, OWNER_ID, START_REACTIONS, REACTION_BOT
from VIPMUSIC.utils.databases import get_reaction_status, set_reaction_status
from VIPMUSIC.utils.databases import load_reaction_data

# Optional: import sudo list if available
try:
    from VIPMUSIC.utils.database import get_sudoers
except ImportError:
    async def get_sudoers():
        return []


# Maintain separate emoji rotation per chat
chat_emoji_cycle = {}


def get_next_emoji(chat_id: int) -> str:
    """Get next emoji for this chat (non-repeating)."""
    global chat_emoji_cycle
    if chat_id not in chat_emoji_cycle or not chat_emoji_cycle[chat_id]:
        emojis = START_REACTIONS.copy()
        random.shuffle(emojis)
        chat_emoji_cycle[chat_id] = emojis
    return chat_emoji_cycle[chat_id].pop()


# ✅ COMMAND: /reaction (menu)
@app.on_message(filters.command("reaction") & filters.group & ~BANNED_USERS)
async def reaction_toggle(client, message: Message):
    chat_id = message.chat.id
    user = message.from_user

    if not user:
        return await message.reply_text("Unknown user.")

    # Check admin or sudo
    member = await app.get_chat_member(chat_id, user.id)
    if not (
        member.status in ("administrator", "creator")
        or user.id == OWNER_ID
        or user.id in await get_sudoers()
    ):
        return await message.reply_text("You must be an admin or sudo user to toggle reactions.")

    # Inline buttons
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Enable", callback_data=f"reaction_enable:{chat_id}"),
                InlineKeyboardButton("❌ Disable", callback_data=f"reaction_disable:{chat_id}"),
            ]
        ]
    )

    status = get_reaction_status(chat_id)
    text = f"🎭 **Reaction Bot Control**\n\nCurrent status: **{'ON ✅' if status else 'OFF ❌'}**"
    await message.reply_text(text, reply_markup=keyboard)


# ✅ COMMAND: /reactionon
@app.on_message(filters.command("reactionon") & filters.group & ~BANNED_USERS)
async def enable_reactions(client, message: Message):
    chat_id = message.chat.id
    user = message.from_user
    if not user:
        return

    member = await app.get_chat_member(chat_id, user.id)
    if not (
        member.status in ("administrator", "creator")
        or user.id == OWNER_ID
        or user.id in await get_sudoers()
    ):
        return await message.reply_text("Admins or sudo users only!")

    set_reaction_status(chat_id, True)
    await message.reply_text("✅ **Reactions enabled** in this chat.")


# ✅ COMMAND: /reactionoff
@app.on_message(filters.command("reactionoff") & filters.group & ~BANNED_USERS)
async def disable_reactions(client, message: Message):
    chat_id = message.chat.id
    user = message.from_user
    if not user:
        return

    member = await app.get_chat_member(chat_id, user.id)
    if not (
        member.status in ("administrator", "creator")
        or user.id == OWNER_ID
        or user.id in await get_sudoers()
    ):
        return await message.reply_text("Admins or sudo users only!")

    set_reaction_status(chat_id, False)
    await message.reply_text("❌ **Reactions disabled** in this chat.")


# ✅ Handle inline button presses
@app.on_callback_query(filters.regex("^reaction_(enable|disable):"))
async def reaction_button(client, query):
    user = query.from_user
    chat_id = int(query.data.split(":")[1])
    action = query.data.split(":")[0].replace("reaction_", "")

    member = await app.get_chat_member(chat_id, user.id)
    if not (
        member.status in ("administrator", "creator")
        or user.id == OWNER_ID
        or user.id in await get_sudoers()
    ):
        return await query.answer("Admins only!", show_alert=True)

    if action == "enable":
        set_reaction_status(chat_id, True)
        await query.message.edit_text("✅ Reactions have been **enabled** in this chat.")
    else:
        set_reaction_status(chat_id, False)
        await query.message.edit_text("❌ Reactions have been **disabled** in this chat.")


# ✅ Auto React on each message
@app.on_message(filters.text & filters.group & ~BANNED_USERS)
async def auto_react(client, message: Message):
    if not REACTION_BOT:
        return  # globally disabled

    chat_id = message.chat.id
    if not get_reaction_status(chat_id):
        return

    emoji = get_next_emoji(chat_id)
    try:
        await message.react(emoji)
    except Exception:
        pass


print("[ReactionBot] Loaded successfully ✅")
