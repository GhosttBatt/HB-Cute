import asyncio
import random
import traceback
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.enums import ChatMemberStatus

from VIPMUSIC import app
from config import OWNER_ID, BANNED_USERS, REACTION_BOT, START_REACTIONS
from VIPMUSIC.utils.database import get_sudoers
from VIPMUSIC.utils.databases import reactiondb


print("[ReactionBot] Plugin loaded — starting extended debug logging...")

# --- global message debug logger ---
@app.on_message(filters.group)
async def debug_all_messages(client, message: Message):
    """This will log every group message to confirm command reception."""
    try:
        if message.text:
            print(f"[DebugMsg] Chat={message.chat.id} | From={getattr(message.from_user, 'id', None)} | Text={message.text}")
        elif message.caption:
            print(f"[DebugMsg] Chat={message.chat.id} | Caption={message.caption}")
    except Exception as e:
        print(f"[DebugMsg] Error: {e}")
        traceback.print_exc()


VALID_REACTIONS = {
    "❤️", "💖", "💘", "💞", "💓", "✨", "🔥", "💫",
    "💥", "🌸", "😍", "🥰", "💎", "🌙", "🌹", "😂",
    "😎", "🤩", "😘", "😉", "🤭", "💐", "😻", "🥳"
}

SAFE_REACTIONS = [e for e in START_REACTIONS if e in VALID_REACTIONS]
if not SAFE_REACTIONS:
    SAFE_REACTIONS = list(VALID_REACTIONS)

chat_used_reactions = {}


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


async def is_admin_or_sudo(client, message: Message):
    try:
        user_id = getattr(message.from_user, "id", None)
        chat_id = message.chat.id
        sudoers = await get_sudoers()
        if user_id == OWNER_ID or user_id in sudoers:
            return True
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR):
            return True
    except Exception as e:
        print(f"[AdminCheck] Error: {e}")
    return False


# --- reaction control commands ---
@app.on_message(filters.command(["reactionon"], prefixes=["/", "!", "."]) & filters.group)
async def cmd_reaction_on(client, message: Message):
    print(f"[Command Trigger] /reactionon triggered in chat {message.chat.id}")
    try:
        if not await is_admin_or_sudo(client, message):
            return await message.reply_text("⚠️ Only admins or sudo users can use this.")
        await reactiondb.reaction_on(message.chat.id)
        await message.reply_text("✅ Reactions enabled for this chat.")
    except Exception as e:
        print(f"[reactionon] Error: {e}")
        traceback.print_exc()


@app.on_message(filters.command(["reactionoff"], prefixes=["/", "!", "."]) & filters.group)
async def cmd_reaction_off(client, message: Message):
    print(f"[Command Trigger] /reactionoff triggered in chat {message.chat.id}")
    try:
        if not await is_admin_or_sudo(client, message):
            return await message.reply_text("⚠️ Only admins or sudo users can use this.")
        await reactiondb.reaction_off(message.chat.id)
        await message.reply_text("🚫 Reactions disabled for this chat.")
    except Exception as e:
        print(f"[reactionoff] Error: {e}")
        traceback.print_exc()


@app.on_message(filters.command(["reaction"], prefixes=["/", "!", "."]) & filters.group)
async def cmd_reaction_menu(client, message: Message):
    print(f"[Command Trigger] /reaction menu triggered in chat {message.chat.id}")
    try:
        if not await is_admin_or_sudo(client, message):
            return await message.reply_text("⚠️ Only admins or sudo users can use this.")
        buttons = [[
            InlineKeyboardButton("✅ Enable", callback_data=f"reaction_enable_{message.chat.id}"),
            InlineKeyboardButton("🚫 Disable", callback_data=f"reaction_disable_{message.chat.id}")
        ]]
        await message.reply_text("🎭 Reaction Menu", reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e:
        print(f"[reaction] Error: {e}")
        traceback.print_exc()


# --- callback handling ---
@app.on_callback_query(filters.regex("^reaction_(enable|disable)_(.*)$"))
async def reaction_callback(client, cq):
    try:
        data = cq.data.split("_")
        action, chat_id = data[1], int(data[2])
        print(f"[Callback] {action.upper()} pressed in chat {chat_id}")
        if action == "enable":
            await reactiondb.reaction_on(chat_id)
            await cq.edit_message_text("✅ Reactions Enabled")
        else:
            await reactiondb.reaction_off(chat_id)
            await cq.edit_message_text("🚫 Reactions Disabled")
    except Exception as e:
        print(f"[reaction_callback] Error: {e}")
        traceback.print_exc()


# --- auto reaction ---
@app.on_message(filters.group & ~BANNED_USERS)
async def auto_react_messages(client, message: Message):
    try:
        if not REACTION_BOT:
            return
        if not message.text and not message.caption:
            return
        if message.text and message.text.startswith("/"):
            return
        chat_id = message.chat.id
        if not await reactiondb.is_reaction_on(chat_id):
            return
        emoji = next_emoji(chat_id)
        await message.react(emoji)
    except Exception as e:
        print(f"[auto_react_messages] Error: {e}")
        traceback.print_exc()


print("[ReactionBot] Extended debug version loaded successfully ✅")
