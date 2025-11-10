# VIPMUSIC/plugins/tools/reaction_bot.py
import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from VIPMUSIC import app
from config import OWNER_ID, SUDOERS, START_REACTIONS
from VIPMUSIC.utils.databases.reactiondb import is_reaction_on, reaction_on, reaction_off

print("[ReactionBot] Plugin loaded!")

# ----------------------------------------
# Helper: Check if user is admin, owner, or sudo
# ----------------------------------------
async def is_user_allowed(_, message):
    if message.from_user:
        user_id = message.from_user.id
        if user_id == OWNER_ID:
            return True
        if str(user_id) in SUDOERS or user_id in SUDOERS:
            return True
        # Check if user is admin
        try:
            member = await app.get_chat_member(message.chat.id, user_id)
            if member.status in ["administrator", "creator"]:
                return True
        except:
            pass
    return False

# ----------------------------------------
# /reactionon command
# ----------------------------------------
@app.on_message(filters.command("reactionon", prefixes="/") & filters.group)
async def reaction_on_cmd(_, message):
    if not await is_user_allowed(_, message):
        return await message.reply_text("❌ You don't have permission to do this.")
    await reaction_on(message.chat.id)
    await message.reply_text("✅ Reactions turned ON for this group.")

# ----------------------------------------
# /reactionoff command
# ----------------------------------------
@app.on_message(filters.command("reactionoff", prefixes="/") & filters.group)
async def reaction_off_cmd(_, message):
    if not await is_user_allowed(_, message):
        return await message.reply_text("❌ You don't have permission to do this.")
    await reaction_off(message.chat.id)
    await message.reply_text("❌ Reactions turned OFF for this group.")

# ----------------------------------------
# /reaction command with Enable/Disable buttons
# ----------------------------------------
@app.on_message(filters.command("reaction", prefixes="/") & filters.group)
async def reaction_button_cmd(_, message):
    if not await is_user_allowed(_, message):
        return await message.reply_text("❌ You don't have permission to do this.")
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Enable", callback_data="reaction_enable"),
            InlineKeyboardButton("❌ Disable", callback_data="reaction_disable")
        ]
    ])
    await message.reply_text("⚡ Choose Reaction Mode:", reply_markup=buttons)

# ----------------------------------------
# Callback Query for reaction buttons
# ----------------------------------------
@app.on_callback_query(filters.regex("reaction_"))
async def reaction_callback(_, query):
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    # Permission check
    allowed = False
    if user_id == OWNER_ID:
        allowed = True
    elif str(user_id) in SUDOERS or user_id in SUDOERS:
        allowed = True
    else:
        try:
            member = await app.get_chat_member(chat_id, user_id)
            if member.status in ["administrator", "creator"]:
                allowed = True
        except:
            pass

    if not allowed:
        return await query.answer("❌ You are not allowed!", show_alert=True)

    # Enable/Disable logic
    if query.data == "reaction_enable":
        await reaction_on(chat_id)
        await query.answer("✅ Reactions enabled!")
        await query.message.edit_text("✅ Reactions enabled for this group.")
    elif query.data == "reaction_disable":
        await reaction_off(chat_id)
        await query.answer("❌ Reactions disabled!")
        await query.message.edit_text("❌ Reactions disabled for this group.")

# ----------------------------------------
# Auto Reaction to messages
# ----------------------------------------
@app.on_message((filters.text | filters.caption) & filters.group)
async def auto_react(_, message):
    # Ignore edited messages in Pyrogram v1
    if message.edit_date:
        return

    if await is_reaction_on(message.chat.id):
        emoji = random.choice(START_REACTIONS)
        try:
            await message.reply_text(emoji)
        except:
            pass
