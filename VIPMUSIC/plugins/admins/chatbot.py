import os
import random
import asyncio
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
# Try common import patterns for HB-Cute / VIPMUSIC
try:
    from VIPMUSIC import app
except Exception:
    try:
        from main import app
    except Exception:
        raise RuntimeError("Could not import Pyrogram Client as 'app'. Ensure your project exposes it.")

# -------------------- MongoDB setup -------------------- #
try:
    from config import MONGO_URL
except Exception:
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")

mongo = MongoClient(MONGO_URL)
db = mongo.get_database("vipmusic_db")

chatai_coll = db.get_collection("chatai")            # learned replies
status_coll = db.get_collection("chatbot_status")    # per-chat enabled/disabled
lang_coll = db.get_collection("chat_langs")         # per-chat language

# -------------------- Translator -------------------- #
translator = GoogleTranslator()  # used when /setlang is set for a chat

# -------------------- Runtime caches -------------------- #
replies_cache = []     # list of reply dicts from DB
blocklist = {}         # user_id -> unblock_datetime (UTC)
message_counts = {}    # user_id -> {"count": int, "last_time": datetime}


# -------------------- Utility helpers -------------------- #
async def load_replies_cache():
    """Load entire replies DB into memory (non-blocking)."""
    global replies_cache
    try:
        docs = list(chatai_coll.find({}))
        replies_cache = docs
    except Exception as e:
        print("[chatbot] load_replies_cache:", e)
        replies_cache = []


def _photo_file_id(msg: Message) -> Optional[str]:
    """
    Safely return a photo file_id. In Pyrogram message.photo can be PhotoSize or list.
    """
    try:
        photo = getattr(msg, "photo", None)
        if not photo:
            return None
        # PhotoSize object has file_id; if it's a list, get the largest (last)
        if hasattr(photo, "file_id"):
            return photo.file_id
        # if list-like
        if isinstance(photo, (list, tuple)) and len(photo) > 0:
            return photo[-1].file_id
    except Exception:
        pass
    return None


def get_reply_sync(word: str):
    """Return one reply dict from cache or DB. Prefers exact word matches."""
    global replies_cache
    if not replies_cache:
        try:
            docs = list(chatai_coll.find({}))
            replies_cache.extend(docs)
        except Exception:
            pass

    if not replies_cache:
        return None

    exact = [r for r in replies_cache if r.get("word") == (word or "")]
    candidates = exact if exact else replies_cache
    return random.choice(candidates) if candidates else None


async def is_user_admin(client, chat_id: int, user_id: int) -> bool:
    """Return True if user is admin or owner of chat. Awaited (Pyrogram v2)."""
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)
    except Exception:
        return False


async def save_reply(original_message: Message, reply_message: Message):
    """
    Save mapping original_message.text -> reply_message content (file_id or text).
    Only if original_message has text (word).
    """
    try:
        if not original_message or not getattr(original_message, "text", None):
            return

        reply_data = {"word": original_message.text, "text": None, "kind": "text", "created_at": datetime.utcnow()}

        # choose type and file_id/text
        if getattr(reply_message, "sticker", None):
            reply_data["text"] = reply_message.sticker.file_id
            reply_data["kind"] = "sticker"
        elif _photo_file_id(reply_message):
            reply_data["text"] = _photo_file_id(reply_message)
            reply_data["kind"] = "photo"
        elif getattr(reply_message, "video", None):
            reply_data["text"] = reply_message.video.file_id
            reply_data["kind"] = "video"
        elif getattr(reply_message, "audio", None):
            reply_data["text"] = reply_message.audio.file_id
            reply_data["kind"] = "audio"
        elif getattr(reply_message, "animation", None):
            reply_data["text"] = reply_message.animation.file_id
            reply_data["kind"] = "gif"
        elif getattr(reply_message, "voice", None):
            reply_data["text"] = reply_message.voice.file_id
            reply_data["kind"] = "voice"
        elif getattr(reply_message, "text", None):
            reply_data["text"] = reply_message.text
            reply_data["kind"] = "text"
        else:
            return

        # dedupe
        exists = chatai_coll.find_one({"word": reply_data["word"], "text": reply_data["text"], "kind": reply_data["kind"]})
        if not exists:
            chatai_coll.insert_one(reply_data)
            replies_cache.append(reply_data)
    except Exception as e:
        print("[chatbot] save_reply error:", e)


async def get_chat_language(chat_id: int) -> Optional[str]:
    doc = lang_coll.find_one({"chat_id": chat_id})
    if doc and "language" in doc:
        return doc["language"]
    return None


# -------------------- Inline keyboard helpers -------------------- #
def chatbot_keyboard(is_enabled: bool):
    if is_enabled:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔴 Disable", callback_data="cb_disable")]])
    return InlineKeyboardMarkup([[InlineKeyboardButton("🟢 Enable", callback_data="cb_enable")]])


# -------------------- Commands: /chatbot -------------------- #
@app.on_message(filters.command("chatbot") & filters.group)
async def chatbot_settings_group(client, message: Message):
    """Show chatbot status and inline toggle — admin only."""
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_user_admin(client, chat_id, user_id):
        return await message.reply_text("❌ Only admins can manage chatbot settings.")

    status_doc = status_coll.find_one({"chat_id": chat_id})
    is_enabled = not status_doc or status_doc.get("status") == "enabled"

    txt = (
        "**🤖 Chatbot Settings**\n\n"
        f"Current Status: **{'🟢 Enabled' if is_enabled else '🔴 Disabled'}**\n\n"
        "Use the buttons below to toggle the chatbot for this chat.\n(Only admins can change this.)"
    )

    await message.reply_text(txt, reply_markup=chatbot_keyboard(is_enabled))


@app.on_message(filters.command("chatbot") & filters.private)
async def chatbot_settings_private(client, message: Message):
    """Show chatbot status in private."""
    chat_id = message.chat.id
    status_doc = status_coll.find_one({"chat_id": chat_id})
    is_enabled = not status_doc or status_doc.get("status") == "enabled"
    txt = f"**🤖 Chatbot (private)**\nStatus: **{'🟢 Enabled' if is_enabled else '🔴 Disabled'}**"
    await message.reply_text(txt, reply_markup=chatbot_keyboard(is_enabled))


# -------------------- Callback handlers -------------------- #
@app.on_callback_query(filters.regex("^cb_(enable|disable)$"))
async def chatbot_toggle_cb(client, cq: CallbackQuery):
    chat_id = cq.message.chat.id
    caller_id = cq.from_user.id

    # only admins in groups
    if cq.message.chat.type in ("group", "supergroup"):  # group covers both; keep supergroup check harmless
        if not await is_user_admin(client, chat_id, caller_id):
            return await cq.answer("Only group admins can perform this action.", show_alert=True)

    if cq.data == "cb_enable":
        status_coll.update_one({"chat_id": chat_id}, {"$set": {"status": "enabled"}}, upsert=True)
        await cq.message.edit_text("**🤖 Chatbot Enabled Successfully!**\n\nStatus: **🟢 Enabled**", reply_markup=chatbot_keyboard(True))
        await cq.answer("Chatbot enabled.")
    else:
        status_coll.update_one({"chat_id": chat_id}, {"$set": {"status": "disabled"}}, upsert=True)
        await cq.message.edit_text("**🤖 Chatbot Disabled Successfully!**\n\nStatus: **🔴 Disabled**", reply_markup=chatbot_keyboard(False))
        await cq.answer("Chatbot disabled.")


# -------------------- /chatbot reset (admin) -------------------- #
@app.on_message(filters.command("chatbot") & filters.regex(r"^/chatbot\s+reset$", flags=0) & filters.group)
async def chatbot_reset_group(client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not await is_user_admin(client, chat_id, user_id):
        return await message.reply_text("❌ Only group admins can reset chatbot data.")
    chatai_coll.delete_many({})
    replies_cache.clear()
    await message.reply_text("✅ All learned replies cleared (global).")


@app.on_message(filters.command("chatbot") & filters.regex(r"^/chatbot\s+reset$", flags=0) & filters.private)
async def chatbot_reset_private(client, message: Message):
    chatai_coll.delete_many({})
    replies_cache.clear()
    await message.reply_text("✅ All learned replies cleared (global).")


# -------------------- /setlang -------------------- #
@app.on_message(filters.command("setlang") & filters.group)
async def setlang_group(client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not await is_user_admin(client, chat_id, user_id):
        return await message.reply_text("❌ Only group admins can set chatbot language for the chat.")
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply_text("Usage: /setlang <language_code>\nExample: /setlang en")
    lang = parts[1].strip()
    lang_coll.update_one({"chat_id": chat_id}, {"$set": {"language": lang}}, upsert=True)
    await message.reply_text(f"✅ Chatbot language set to: `{lang}`")


@app.on_message(filters.command("setlang") & filters.private)
async def setlang_private(client, message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.reply_text("Usage: /setlang <language_code>")
    lang = parts[1].strip()
    lang_coll.update_one({"chat_id": message.chat.id}, {"$set": {"language": lang}}, upsert=True)
    await message.reply_text(f"✅ Chatbot language set to: `{lang}`")


# -------------------- Learning: Save replies to DB -------------------- #
@app.on_message(filters.reply & filters.group)
async def learn_reply_group(client, message: Message):
    # Save user reply when replying to bot's message
    try:
        if not message.reply_to_message:
            return
        bot = await client.get_me()
        if getattr(message.reply_to_message, "from_user", None) and message.reply_to_message.from_user.id == bot.id:
            await save_reply(message.reply_to_message, message)
    except Exception:
        pass


@app.on_message(filters.reply & filters.private)
async def learn_reply_private(client, message: Message):
    try:
        if not message.reply_to_message:
            return
        bot = await client.get_me()
        if getattr(message.reply_to_message, "from_user", None) and message.reply_to_message.from_user.id == bot.id:
            await save_reply(message.reply_to_message, message)
    except Exception:
        pass


# -------------------- Main Chatbot Handler -------------------- #
@app.on_message(filters.incoming)
async def chatbot_handler(client, message: Message):
    # ignore edited messages
    if message.edit_date:
        return

    # basic sanity
    if not message.from_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    now = datetime.utcnow()

    # cleanup expired blocks
    global blocklist, message_counts
    blocklist = {uid: t for uid, t in blocklist.items() if t > now}

    # rate limiting: quick spam blocker
    mc = message_counts.get(user_id)
    if not mc:
        message_counts[user_id] = {"count": 1, "last_time": now}
    else:
        diff = (now - mc["last_time"]).total_seconds()
        if diff <= 3:
            mc["count"] += 1
        else:
            mc["count"] = 1
        mc["last_time"] = now

        if mc["count"] >= 6:
            blocklist[user_id] = now + timedelta(minutes=1)
            message_counts.pop(user_id, None)
            try:
                await message.reply_text("⛔ You are blocked for 1 minute due to spam.")
            except Exception:
                pass
            return

    if user_id in blocklist:
        return

    # respect enabled/disabled
    s = status_coll.find_one({"chat_id": chat_id})
    if s and s.get("status") == "disabled":
        return

    # ignore commands
    if getattr(message, "text", None) and message.text.startswith(("/", "!", ".", "@", "#", "?")):
        return

    # decide whether to answer: explicit replies to bot OR general chat (configurable)
    should_respond = False
    if message.reply_to_message:
        if getattr(message.reply_to_message, "from_user", None):
            bot = await client.get_me()
            if message.reply_to_message.from_user.id == bot.id:
                should_respond = True
    else:
        # set to False if you want bot to only respond to replies directed to it
        should_respond = True

    if not should_respond:
        return

    # pick reply
    r = get_reply_sync(message.text or "")
    if r:
        response = r.get("text") or ""
        kind = r.get("kind", "text")
        chat_lang = await get_chat_language(chat_id)

        # translate textual replies if language set
        if kind == "text" and response and chat_lang and chat_lang != "nolang":
            try:
                response = translator.translate(response, target=chat_lang)
            except Exception:
                pass

        # send by type
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
            else:  # text
                await message.reply_text(response or "I don't understand.")
        except MessageEmpty:
            pass
        except Exception as e:
            # fallback to text if media fails
            try:
                await message.reply_text(response or "I don't understand.")
            except Exception:
                print("[chatbot] send error:", e)
    else:
        try:
            await message.reply_text("I don't understand. 🤔")
        except Exception:
            pass
