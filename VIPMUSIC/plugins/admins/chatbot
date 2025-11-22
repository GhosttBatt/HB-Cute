import os
import random
import re
from datetime import datetime, timedelta
from typing import Optional

from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from pyrogram.errors import MessageEmpty
from pyrogram.enums import ChatMemberStatus

from pymongo import MongoClient
from deep_translator import GoogleTranslator

# -------------------- Application client -------------------- #
try:
    from VIPMUSIC import app
except Exception:
    try:
        from main import app
    except Exception:
        raise RuntimeError("Could not import Pyrogram Client as 'app'.")

# -------------------- SUDOERS -------------------- #
try:
    from VIPMUSIC.misc import SUDOERS
except Exception:
    SUDOERS = []

# -------------------- MongoDB setup -------------------- #
try:
    from config import MONGO_URL
except Exception:
    MONGO_URL = os.environ.get(
        "MONGO_URL",
        "mongodb+srv://iamnobita1:nobitamusic1@cluster0.k08op.mongodb.net/?retryWrites=true&w=majority"
    )

mongo = MongoClient(MONGO_URL)
db = mongo.get_database("vipmusic_db")

chatai_coll = db.get_collection("chatai")
status_coll = db.get_collection("chatbot_status")
lang_coll = db.get_collection("chat_langs")
block_coll = db.get_collection("blocklist")  # NEW COLLECTION for blocklist

translator = GoogleTranslator()

# Runtime
replies_cache = []
blocklist = {}
message_counts = {}

# -------------------- Helpers -------------------- #
async def load_replies_cache():
    global replies_cache
    try:
        replies_cache = list(chatai_coll.find({}))
    except Exception:
        replies_cache = []


def _photo_file_id(msg: Message) -> Optional[str]:
    try:
        photo = getattr(msg, "photo", None)
        if not photo:
            return None
        if hasattr(photo, "file_id"):
            return photo.file_id
        if isinstance(photo, (list, tuple)) and len(photo) > 0:
            return photo[-1].file_id
    except Exception:
        pass
    return None


def hash_media(msg: Message):
    """Return a hashable key for media messages to block them."""
    if msg.photo:
        return _photo_file_id(msg)
    elif msg.sticker:
        return msg.sticker.file_id
    elif msg.video:
        return msg.video.file_id
    elif msg.audio:
        return msg.audio.file_id
    elif msg.voice:
        return msg.voice.file_id
    elif msg.animation:
        return msg.animation.file_id
    return None


def get_reply_sync(word: str):
    global replies_cache
    if not replies_cache:
        try:
            replies_cache.extend(list(chatai_coll.find({})))
        except Exception:
            pass
    if not replies_cache:
        return None
    exact = [r for r in replies_cache if r.get("word") == (word or "")]
    candidates = exact if exact else replies_cache
    return random.choice(candidates) if candidates else None


async def is_user_admin(client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


async def save_reply(original: Message, reply: Message):
    try:
        if not original or not original.text:
            return

        data = {
            "word": original.text,
            "text": None,
            "kind": "text",
            "created_at": datetime.utcnow(),
        }

        if reply.sticker:
            data["text"] = reply.sticker.file_id
            data["kind"] = "sticker"
        elif _photo_file_id(reply):
            data["text"] = _photo_file_id(reply)
            data["kind"] = "photo"
        elif reply.video:
            data["text"] = reply.video.file_id
            data["kind"] = "video"
        elif reply.audio:
            data["text"] = reply.audio.file_id
            data["kind"] = "audio"
        elif reply.animation:
            data["text"] = reply.animation.file_id
            data["kind"] = "gif"
        elif reply.voice:
            data["text"] = reply.voice.file_id
            data["kind"] = "voice"
        elif reply.text:
            data["text"] = reply.text
            data["kind"] = "text"
        else:
            return

        exists = chatai_coll.find_one(
            {"word": data["word"], "text": data["text"], "kind": data["kind"]}
        )
        if not exists:
            chatai_coll.insert_one(data)
            replies_cache.append(data)

    except Exception as e:
        print("[chatbot] save_reply:", e)


async def get_chat_language(chat_id: int) -> Optional[str]:
    doc = lang_coll.find_one({"chat_id": chat_id})
    return doc["language"] if doc and "language" in doc else None


# -------------------- Blocklist Helpers -------------------- #
def is_blocked_message(message: Message) -> bool:
    """Check if message matches global or chat blocklist."""
    doc_list = list(block_coll.find({}))

    text_to_check = message.text or message.caption or ""
    text_to_check_lower = text_to_check.lower()

    for d in doc_list:
        word = d.get("word")
        pattern = d.get("pattern")
        # regex
        if pattern:
            try:
                if re.search(pattern, text_to_check, re.IGNORECASE):
                    return True
            except Exception:
                continue
        else:
            if word and word.lower() in text_to_check_lower:
                return True

    # MEDIA
    media_hash = hash_media(message)
    if media_hash:
        exists = block_coll.find_one({"word": media_hash})
        if exists:
            return True
    return False


# -------------------- Keyboards -------------------- #
def chatbot_keyboard(is_enabled: bool):
    if is_enabled:
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔴 Disable", callback_data="cb_disable")]]
        )
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🟢 Enable", callback_data="cb_enable")]]
    )


# -------------------- /chatbot -------------------- #
@app.on_message(filters.command("chatbot") & filters.group)
async def chatbot_settings_group(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_user_admin(client, chat_id, user_id):
        return await message.reply_text("❌ Only admins can manage chatbot settings.")

    doc = status_coll.find_one({"chat_id": chat_id})
    enabled = not doc or doc.get("status") == "enabled"

    txt = (
        "**🤖 Chatbot Settings**\n\n"
        f"Current Status: **{'🟢 Enabled' if enabled else '🔴 Disabled'}**\n"
    )
    await message.reply_text(txt, reply_markup=chatbot_keyboard(enabled))


@app.on_message(filters.command("chatbot") & filters.private)
async def chatbot_settings_private(client, message):
    chat_id = message.chat.id
    doc = status_coll.find_one({"chat_id": chat_id})
    enabled = not doc or doc.get("status") == "enabled"
    txt = f"**🤖 Chatbot (private)**\nStatus: **{'🟢 Enabled' if enabled else '🔴 Disabled'}**"
    await message.reply_text(txt, reply_markup=chatbot_keyboard(enabled))


# -------------------- Callback -------------------- #
@app.on_callback_query(filters.regex("^cb_(enable|disable)$"))
async def chatbot_toggle_cb(client, cq: CallbackQuery):
    chat_id = cq.message.chat.id
    uid = cq.from_user.id

    if cq.message.chat.type in ("group", "supergroup"):
        if not await is_user_admin(client, chat_id, uid):
            return await cq.answer("Only admins can do this.", show_alert=True)

    if cq.data == "cb_enable":
        status_coll.update_one(
            {"chat_id": chat_id}, {"$set": {"status": "enabled"}}, upsert=True
        )
        await cq.message.edit_text(
            "**🤖 Chatbot Enabled!**", reply_markup=chatbot_keyboard(True)
        )
        await cq.answer("Enabled")
    else:
        status_coll.update_one(
            {"chat_id": chat_id}, {"$set": {"status": "disabled"}}, upsert=True
        )
        await cq.message.edit_text(
            "**🤖 Chatbot Disabled!**", reply_markup=chatbot_keyboard(False)
        )
        await cq.answer("Disabled")


# -------------------- /chatbot reset -------------------- #
@app.on_message(filters.command("chatbot") & filters.regex("reset") & filters.group)
async def chatbot_reset_group(client, message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Only admins can do this.")
    chatai_coll.delete_many({})
    replies_cache.clear()
    await message.reply_text("✅ All replies cleared.")


@app.on_message(filters.command("chatbot") & filters.regex("reset") & filters.private)
async def chatbot_reset_private(client, message):
    chatai_coll.delete_many({})
    replies_cache.clear()
    await message.reply_text("✅ All replies cleared.")


# -------------------- /setlang -------------------- #
@app.on_message(filters.command("setlang") & filters.group)
async def setlang_group(client, message):
    if not await is_user_admin(client, message.chat.id, message.from_user.id):
        return await message.reply_text("❌ Only admins can do this.")

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply_text("Usage: /setlang <code>")

    lang = parts[1].strip()
    lang_coll.update_one(
        {"chat_id": message.chat.id}, {"$set": {"language": lang}}, upsert=True
    )
    await message.reply_text(f"✅ Language set to `{lang}`")


@app.on_message(filters.command("setlang") & filters.private)
async def setlang_private(client, message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply_text("Usage: /setlang <code>")
    lang = parts[1].strip()
    lang_coll.update_one(
        {"chat_id": message.chat.id}, {"$set": {"language": lang}}, upsert=True
    )
    await message.reply_text(f"✅ Language set to `{lang}`")


# -------------------- Learn Replies -------------------- #
@app.on_message(filters.reply & filters.group)
async def learn_reply_group(client, message):
    if not message.reply_to_message:
        return
    bot = await client.get_me()
    if (
        message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot.id
    ):
        await save_reply(message.reply_to_message, message)


@app.on_message(filters.reply & filters.private)
async def learn_reply_private(client, message):
    if not message.reply_to_message:
        return
    bot = await client.get_me()
    if (
        message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot.id
    ):
        await save_reply(message.reply_to_message, message)


# -------------------- Blocklist Commands (SUDOERS ONLY) -------------------- #
def is_sudo(user_id: int) -> bool:
    return user_id in SUDOERS


@app.on_message(filters.command("addblock") & filters.group)
async def add_block_command(client, message):
    if not is_sudo(message.from_user.id):
        return await message.reply("❌ Only SUDOERS can use this command.")
    reply = message.reply_to_message
    scope = "chat"
    parts = message.text.split(maxsplit=2)
    if len(parts) == 3 and parts[2].lower() == "global":
        scope = "global"

    if reply:
        media_hash = hash_media(reply)
        txt = reply.text or reply.caption
        if media_hash:
            block_coll.update_one({"word": media_hash}, {"$set": {"kind": "media", "scope": scope}}, upsert=True)
            return await message.reply("✅ Media blocked.")
        if txt:
            block_coll.update_one({"word": txt.lower()}, {"$set": {"kind": "text", "scope": scope}}, upsert=True)
            return await message.reply("✅ Text blocked.")
        return await message.reply("⚠️ Cannot block this message.")

    if len(parts) < 2:
        return await message.reply("Usage:\n`/addblock <word_or_regex> [global]` or reply to a message.")

    word_or_regex = parts[1].strip()
    if word_or_regex.startswith("re:"):
        pattern = word_or_regex[3:].strip()
        block_coll.update_one({"pattern": pattern}, {"$set": {"kind": "text", "scope": scope, "pattern": pattern}}, upsert=True)
        return await message.reply(f"✅ Regex blocked: `{pattern}` ({scope})")
    else:
        block_coll.update_one({"word": word_or_regex.lower()}, {"$set": {"kind": "text", "scope": scope}}, upsert=True)
        return await message.reply(f"✅ Blocked `{word_or_regex}` ({scope})")


@app.on_message(filters.command("rmblock") & filters.group)
async def rm_block_command(client, message):
    if not is_sudo(message.from_user.id):
        return await message.reply("❌ Only SUDOERS can use this command.")

    reply = message.reply_to_message
    if reply:
        media_hash = hash_media(reply)
        txt = reply.text or reply.caption
        if media_hash:
            block_coll.delete_one({"word": media_hash})
            return await message.reply("🗑️ Media unblocked.")
        if txt:
            block_coll.delete_one({"word": txt.lower()})
            return await message.reply("🗑️ Text unblocked.")
        return await message.reply("⚠️ Cannot identify this message.")

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        return await message.reply("Usage:\n`/rmblock <word_or_regex>` or reply to a message.")

    word_or_regex = parts[1].strip()
    if word_or_regex.startswith("re:"):
        pattern = word_or_regex[3:].strip()
        block_coll.delete_one({"pattern": pattern})
        return await message.reply(f"🗑️ Regex unblocked: `{pattern}`")
    else:
        block_coll.delete_one({"word": word_or_regex.lower()})
        return await message.reply(f"🗑️ Unblocked `{word_or_regex}`")


@app.on_message(filters.command("listblock"))
async def list_block_command(client, message):
    if not is_sudo(message.from_user.id):
        return await message.reply("❌ Only SUDOERS can use this command.")

    data = list(block_coll.find({}))
    if not data:
        return await message.reply("📭 Blocklist empty.")

    txt = "**🚫 Blocked Words & Media:**\n\n"
    for d in data:
        if d.get("pattern"):
            txt += f"• `re:{d.get('pattern')}` ({d.get('scope')})\n"
        else:
            txt += f"• `{d.get('word')}` ({d.get('scope')})\n"

    await message.reply(txt)


# -------------------- MAIN CHATBOT HANDLER -------------------- #
@app.on_message(filters.incoming & ~filters.me, group=99)
async def chatbot_handler(client, message: Message):
    if message.edit_date:
        return
    if not message.from_user:
        return

    # BLOCKLIST CHECK
    if is_blocked_message(message):
        try:
            await message.delete()
        except Exception:
            pass
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    now = datetime.utcnow()

    global blocklist, message_counts
    blocklist = {u: t for u, t in blocklist.items() if t > now}

    mc = message_counts.get(user_id)
    if not mc:
        message_counts[user_id] = {"count": 1, "last_time": now}
    else:
        diff = (now - mc["last_time"]).total_seconds()
        mc["count"] = mc["count"] + 1 if diff <= 3 else 1
        mc["last_time"] = now
        if mc["count"] >= 6:
            blocklist[user_id] = now + timedelta(minutes=1)
            message_counts.pop(user_id, None)
            try:
                await message.reply_text("⛔ Blocked 1 minute for spam.")
            except Exception:
                pass
            return

    if user_id in blocklist:
        return

    s = status_coll.find_one({"chat_id": chat_id})
    if s and s.get("status") == "disabled":
        return

    # FIX: allow /play, /start, /help etc.
    if message.text and message.text.startswith("/"):
        return

    should = False
    if message.reply_to_message:
        bot = await client.get_me()
        if message.reply_to_message.from_user and message.reply_to_message.from_user.id == bot.id:
            should = True
    else:
        should = True

    if not should:
        return

    r = get_reply_sync(message.text or "")
    if r:
        response = r.get("text", "")
        kind = r.get("kind", "text")
        lang = await get_chat_language(chat_id)

        if kind == "text" and response and lang and lang != "nolang":
            try:
                response = translator.translate(response, target=lang)
            except Exception:
                pass

        try:
            if kind == "sticker":
                await message.reply_sticker(response)
            elif kind == "photo":
                await message.reply_photo(response)
            elif kind == "video":
                await message.reply_video(response)
            elif kind == "audio":
                await message.reply_audio(response)
            elif kind == "gif":
                await message.reply_animation(response)
            elif kind == "voice":
                await message.reply_voice(response)
            else:
                await message.reply_text(response or "I don't understand.")
        except Exception:
            try:
                await message.reply_text(response or "I don't understand.")
            except Exception:
                pass
    else:
        try:
            await message.reply_text("I don't understand. 🤔")
        except Exception:
            pass
