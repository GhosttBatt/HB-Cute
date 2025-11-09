from VIPMUSIC import app
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID, SUDOERS
from VIPMUSIC.utils.databases.reactiondb import is_reaction_on, reaction_on, reaction_off

print("[ReactionBot] Plugin loaded!")

# Helper to check authorized users (Owner / Sudo / Admin)
async def is_auth_user(_, message):
    user_id = message.from_user.id
    member = await message.chat.get_member(user_id)
    if user_id == OWNER_ID or user_id in map(int, SUDOERS) or member.status in ("administrator", "creator"):
        return True
    return False

# ----------------- /reactionon -----------------
@app.on_message(
    filters.command("reactionon") &
    filters.group &
    filters.create(is_auth_user)
)
async def cmd_reactionon(_, message):
    await reaction_on(message.chat.id)
    await message.reply_text("✅ Reactions are now **ON** for this group!")

# ----------------- /reactionoff -----------------
@app.on_message(
    filters.command("reactionoff") &
    filters.group &
    filters.create(is_auth_user)
)
async def cmd_reactionoff(_, message):
    await reaction_off(message.chat.id)
    await message.reply_text("❌ Reactions are now **OFF** for this group!")

# ----------------- /reaction button -----------------
@app.on_message(
    filters.command("reaction") &
    filters.group &
    filters.create(is_auth_user)
)
async def cmd_reaction_buttons(_, message):
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Enable ✅", callback_data="reaction_enable"),
                InlineKeyboardButton("Disable ❌", callback_data="reaction_disable"),
            ]
        ]
    )
    await message.reply_text("Select reaction mode:", reply_markup=keyboard)

# ----------------- Button callback -----------------
@app.on_callback_query(filters.regex(r"reaction_(enable|disable)"))
async def cb_reaction_buttons(_, cq):
    chat_id = cq.message.chat.id
    if cq.data == "reaction_enable":
        await reaction_on(chat_id)
        await cq.answer("✅ Reactions Enabled")
    else:
        await reaction_off(chat_id)
        await cq.answer("❌ Reactions Disabled")

# ----------------- Auto React to messages -----------------
@app.on_message(
    (filters.text | filters.caption) &
    filters.group &
    ~filters.edited
)
async def auto_react(_, message):
    if await is_reaction_on(message.chat.id):
        import random
        from config import START_REACTIONS
        emoji = random.choice(START_REACTIONS)
        try:
            await message.reply_text(emoji)
        except:
            pass
