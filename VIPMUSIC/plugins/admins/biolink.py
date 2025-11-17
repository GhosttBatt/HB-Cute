# VIPMUSIC/plugins/admins/biolink.py
"""
BioLink plugin (integrated with VIPMUSIC main app).

Features:
- Detects links in user bios and adverts in messages.
- Configurable per-chat: mode (warn/mute/ban), limit, penalty.
- Whitelist support for safe users.
- In-memory simple anti-flood detection.
- Uses the main `app` from VIPMUSIC; no separate client.
"""

import re
import aiosqlite
import asyncio
from typing import List, Tuple, Optional

from pyrogram import filters, errors
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ChatPermissions,
    Message,
    CallbackQuery,
)

# Use main bot client from VIPMUSIC
from VIPMUSIC import app
from config import URL_PATTERN  # optional pattern from config

DB_PATH = "biolink_combined.db"

# ------------------ Database helpers ------------------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS config (
                chat_id INTEGER PRIMARY KEY,
                mode TEXT DEFAULT 'warn',
                limit INTEGER DEFAULT 3,
                penalty TEXT DEFAULT 'mute'
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS warnings (
                chat_id INTEGER,
                user_id INTEGER,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS whitelist (
                chat_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        await db.commit()

"""
# schedule DB init (non-blocking) when module is imported
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # if loop is already running, create_task will schedule it
        loop.create_task(init_db())
    else:
        # loop exists but not running (rare in typical bot startup), schedule safe
        loop.run_until_complete(init_db())
except RuntimeError:
    # Fallback: create a new event loop to init DB (safe during imports)
    loop = asyncio.new_event_loop()
    loop.run_until_complete(init_db())
    loop.close()

"""
# ---------- DB API ----------
async def get_config(chat_id: int) -> Tuple[str, int, str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT mode, limit, penalty FROM config WHERE chat_id = ?", (chat_id,))
        row = await cur.fetchone()
        if row:
            return row[0], row[1], row[2]
        # create default and return it
        await db.execute(
            "INSERT OR REPLACE INTO config(chat_id, mode, limit, penalty) VALUES (?, 'warn', 3, 'mute')",
            (chat_id,),
        )
        await db.commit()
        return "warn", 3, "mute"


async def update_config(chat_id: int, mode: Optional[str] = None, limit: Optional[int] = None, penalty: Optional[str] = None):
    cur_mode, cur_limit, cur_penalty = await get_config(chat_id)
    mode = mode if mode is not None else cur_mode
    limit = cur_limit if limit is None else limit
    penalty = penalty if penalty is not None else cur_penalty
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO config(chat_id, mode, limit, penalty) VALUES (?, ?, ?, ?)",
            (chat_id, mode, limit, penalty),
        )
        await db.commit()


async def increment_warning(chat_id: int, user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        row = await cur.fetchone()
        if row:
            new = row[0] + 1
            await db.execute("UPDATE warnings SET count = ? WHERE chat_id = ? AND user_id = ?", (new, chat_id, user_id))
        else:
            new = 1
            await db.execute("INSERT INTO warnings(chat_id, user_id, count) VALUES (?, ?, 1)", (chat_id, user_id))
        await db.commit()
        return new


async def reset_warnings(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        await db.commit()


async def is_whitelisted(chat_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT 1 FROM whitelist WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        return bool(await cur.fetchone())


async def add_whitelist(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO whitelist(chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
        await db.commit()


async def remove_whitelist(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM whitelist WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        await db.commit()


async def get_whitelist(chat_id: int) -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM whitelist WHERE chat_id = ?", (chat_id,))
        rows = await cur.fetchall()
        return [r[0] for r in rows]


# ------------------ Helper utils ------------------
AD_PATTERNS = [
    r"\b(?:free|cheap|discount|buy now|sale)\b",
    r"\b(?:\.com|\.net|\.org|\.xyz|\.site|\.online|\.shop)\b",
]

try:
    # URL_PATTERN could be a compiled regex or a string in config
    if isinstance(URL_PATTERN, re.Pattern):
        URL_RE = URL_PATTERN
    else:
        URL_RE = re.compile(URL_PATTERN)
except Exception:
    URL_RE = re.compile(r"https?://", re.IGNORECASE)

AD_RE = re.compile("(?:" + ")|(?:".join(p.strip('()') for p in AD_PATTERNS) + ")", re.IGNORECASE)


async def is_admin(client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


# ------------------ Admin GUI keyboard builder ------------------
def build_main_keyboard(penalty: str):
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Warn", callback_data="warn")],
            [
                InlineKeyboardButton("🔻 𝐌ʋтɛ ✅" if penalty == "mute" else "Mute", callback_data="mute"),
                InlineKeyboardButton("🔻 𝐁αи ✅" if penalty == "ban" else "Ban", callback_data="ban"),
            ],
            [InlineKeyboardButton("Close", callback_data="close")],
        ]
    )


# ------------------ Commands ------------------
# Ensure these handlers use the main `app` and are assigned groups to avoid conflicts.

@app.on_message(filters.group & filters.command("config"), group=10)
async def configure(client, message: Message):
    chat_id = message.chat.id
    user = message.from_user
    if not user:
        return
    user_id = user.id
    if not await is_admin(client, chat_id, user_id):
        return await message.reply_text("❌ You must be an admin to use this command.", quote=True)

    mode, limit, penalty = await get_config(chat_id)
    keyboard = build_main_keyboard(penalty)
    await client.send_message(chat_id, "**Choose penalty for users with links in bio:**", reply_markup=keyboard)
    try:
        await message.delete()
    except Exception:
        pass


@app.on_message(filters.group & filters.command("free"), group=11)
async def command_free(client, message: Message):
    chat_id = message.chat.id
    user = message.from_user
    if not user:
        return
    user_id = user.id
    if not await is_admin(client, chat_id, user_id):
        return

    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        arg = message.command[1]
        try:
            target = await client.get_users(int(arg) if arg.isdigit() else arg)
        except Exception:
            return await client.send_message(chat_id, "**Invalid user id/username.**")

    if not target:
        return await client.send_message(chat_id, "**Reply or use /free user or id to whitelist someone.**")

    await add_whitelist(chat_id, target.id)
    await reset_warnings(chat_id, target.id)

    text = f"**✅ {target.mention} 𝐀ᴅᴅɛᴅ 𝐓σ 𝐖нιтɛƖιƨт**"
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔻 𝐔и𝐖нιтɛƖιƨт 🚫", callback_data=f"unwhitelist_{target.id}"),
                InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🗑️", callback_data="close"),
            ]
        ]
    )
    await client.send_message(chat_id, text, reply_markup=keyboard)


@app.on_message(filters.group & filters.command("unfree"), group=12)
async def command_unfree(client, message: Message):
    chat_id = message.chat.id
    user = message.from_user
    if not user:
        return
    user_id = user.id
    if not await is_admin(client, chat_id, user_id):
        return

    target = None
    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        arg = message.command[1]
        try:
            target = await client.get_users(int(arg) if arg.isdigit() else arg)
        except Exception:
            return await client.send_message(chat_id, "**Invalid user id/username.**")

    if not target:
        return await client.send_message(chat_id, "**Reply or use /unfree user or id to unwhitelist someone.**")

    if await is_whitelisted(chat_id, target.id):
        await remove_whitelist(chat_id, target.id)
        text = f"**🚫 {target.mention} 𝐑ɛмσᴠɛ 𝐓σ 𝐖нιтɛƖιƨт**"
    else:
        text = f"**ℹ️ {target.mention} 𝐈ƨ 𝐍σт 𝐖нιтɛƖιƨt.**"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔻 𝐖нιƖιƨт ✅ ", callback_data=f"whitelist_{target.id}"),
                InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🗑️", callback_data="close"),
            ]
        ]
    )
    await client.send_message(chat_id, text, reply_markup=keyboard)


@app.on_message(filters.group & filters.command("freelist"), group=13)
async def command_freelist(client, message: Message):
    chat_id = message.chat.id
    user = message.from_user
    if not user:
        return
    user_id = user.id
    if not await is_admin(client, chat_id, user_id):
        return

    ids = await get_whitelist(chat_id)
    if not ids:
        await client.send_message(chat_id, "**⚠️ No users are whitelisted in this group.**")
        return

    text = "**📋 Whitelisted Users:**\n\n"
    for i, uid in enumerate(ids, start=1):
        try:
            user = await client.get_users(uid)
            name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
            text += f"{i}: {name} [`{uid}`]\n"
        except Exception:
            text += f"{i}: [User not found] [`{uid}`]\n"

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Close", callback_data="close")]])
    await client.send_message(chat_id, text, reply_markup=keyboard)


# ------------------ Callback handler (admin GUI) ------------------
@app.on_callback_query(group=20)
async def callback_handler(client, callback_query: CallbackQuery):
    data = callback_query.data
    if not callback_query.message:
        return await callback_query.answer()
    chat_id = callback_query.message.chat.id
    user = callback_query.from_user
    if not user:
        return await callback_query.answer()
    user_id = user.id

    if not await is_admin(client, chat_id, user_id):
        return await callback_query.answer("❌ You are not administrator", show_alert=True)

    # Close button
    if data == "close":
        try:
            return await callback_query.message.delete()
        except Exception:
            return await callback_query.answer()

    # back -> show main
    if data == "back":
        mode, limit, penalty = await get_config(chat_id)
        kb = build_main_keyboard(penalty)
        await callback_query.message.edit_text("**Choose penalty for users with links in bio:**", reply_markup=kb)
        return await callback_query.answer()

    # set warn mode (choose limit)
    if data == "warn":
        _, selected_limit, _ = await get_config(chat_id)
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(f"🍏" if selected_limit == 0 else "0", callback_data="warn_0"),
                    InlineKeyboardButton(f"🍏" if selected_limit == 1 else "1", callback_data="warn_1"),
                    InlineKeyboardButton(f"🍏" if selected_limit == 2 else "2", callback_data="warn_2"),
                    InlineKeyboardButton(f"🍏" if selected_limit == 3 else "3", callback_data="warn_3"),
                    InlineKeyboardButton(f"🍏" if selected_limit == 4 else "4", callback_data="warn_4"),
                    InlineKeyboardButton(f"🍏" if selected_limit == 5 else "5", callback_data="warn_5"),
                ],
                [InlineKeyboardButton("Back", callback_data="back"), InlineKeyboardButton("Close", callback_data="close")],
            ]
        )
        return await callback_query.message.edit_text("**Set number of bans/warns:**", reply_markup=kb)

    if data in ["mute", "ban"]:
        await update_config(chat_id, penalty=data)
        mode, limit, penalty = await get_config(chat_id)
        kb = build_main_keyboard(penalty)
        await callback_query.message.edit_text("**Penalty selected**", reply_markup=kb)
        return await callback_query.answer()

    if data.startswith("warn_"):
        try:
            count = int(data.split("_")[1])
        except Exception:
            return await callback_query.answer()
        await update_config(chat_id, limit=count)
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(f"🍏" if count == 0 else "0", callback_data="warn_0"),
                    InlineKeyboardButton(f"🍏" if count == 1 else "1", callback_data="warn_1"),
                    InlineKeyboardButton(f"🍏" if count == 2 else "2", callback_data="warn_2"),
                    InlineKeyboardButton(f"🍏" if count == 3 else "3", callback_data="warn_3"),
                    InlineKeyboardButton(f"🍏" if count == 4 else "4", callback_data="warn_4"),
                    InlineKeyboardButton(f"🍏" if count == 5 else "5", callback_data="warn_5"),
                ],
                [InlineKeyboardButton("Back", callback_data="back"), InlineKeyboardButton("Close", callback_data="close")],
            ]
        )
        await callback_query.message.edit_text(f"**Warning limit set to {count}**", reply_markup=kb)
        return await callback_query.answer()

    # unmute / unban
    if data.startswith(("unmute_", "unban_")):
        action, uid = data.split("_")
        target_id = int(uid)
        try:
            # fetch user chat info for nice name
            user_info = await client.get_chat(target_id)
            name = f"{user_info.first_name}{(' ' + user_info.last_name) if user_info.last_name else ''}"
        except Exception:
            name = str(target_id)
        try:
            if action == "unmute":
                # restore basic sending permission
                await client.restrict_chat_member(chat_id, target_id, ChatPermissions(can_send_messages=True))
            else:
                await client.unban_chat_member(chat_id, target_id)
            await reset_warnings(chat_id, target_id)
            msg = f"**{name} (`{target_id}`) has been {'unmuted' if action == 'unmute' else 'unbanned'}**."

            kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🔻 𝐖нιƖιƨт ✅", callback_data=f"whitelist_{target_id}"),
                        InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🔻", callback_data="close"),
                    ]
                ]
            )
            await callback_query.message.edit_text(msg, reply_markup=kb)
        except errors.ChatAdminRequired:
            await callback_query.message.edit_text(f"I don't have permission to {action} users.")
        return await callback_query.answer()

    # cancel warning
    if data.startswith("cancel_warn_"):
        target_id = int(data.split("_")[-1])
        await reset_warnings(chat_id, target_id)
        try:
            user = await client.get_chat(target_id)
            full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
        except Exception:
            full_name = str(target_id)
        mention = f"[{full_name}](tg://user?id={target_id})"
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔻 𝐖нιƖιƨт ✅", callback_data=f"whitelist_{target_id}"),
                    InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🔻", callback_data="close"),
                ]
            ]
        )
        await callback_query.message.edit_text(f"**✅ {mention} [`{target_id}`] has no more warnings!**", reply_markup=kb)
        return await callback_query.answer()

    # whitelist / unwhitelist via callback
    if data.startswith("whitelist_"):
        target_id = int(data.split("_")[1])
        await add_whitelist(chat_id, target_id)
        await reset_warnings(chat_id, target_id)
        try:
            user = await client.get_chat(target_id)
            full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
        except Exception:
            full_name = str(target_id)
        mention = f"[{full_name}](tg://user?id={target_id})"
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔻 𝐔и𝐖нιтɛƖιƨт 🚫", callback_data=f"unwhitelist_{target_id}"),
                    InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🔻", callback_data="close"),
                ]
            ]
        )
        await callback_query.message.edit_text(f"**✅ {mention} [`{target_id}`] has been whitelisted!**", reply_markup=kb)
        return await callback_query.answer()

    if data.startswith("unwhitelist_"):
        target_id = int(data.split("_")[1])
        await remove_whitelist(chat_id, target_id)
        try:
            user = await client.get_chat(target_id)
            full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
        except Exception:
            full_name = str(target_id)
        mention = f"[{full_name}](tg://user?id={target_id})"
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔻 𝐖нιƖιƨт ✅", callback_data=f"whitelist_{target_id}"),
                    InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🔻", callback_data="close"),
                ]
            ]
        )
        await callback_query.message.edit_text(f"**❌ {mention} [`{target_id}`] has been removed from whitelist.**", reply_markup=kb)
        return await callback_query.answer()

    # fallback
    return await callback_query.answer()


# ------------------ Primary bio/link check + anti-ads/anti-bot ------------------
# group numbers chosen to reduce risk of interference with other plugins
@app.on_message(filters.group, group=30)
async def check_bio_and_ads(client, message: Message):
    chat_id = message.chat.id
    if not message.from_user:
        return
    user_id = message.from_user.id

    # Admins or whitelisted are bypassed
    if await is_admin(client, chat_id, user_id) or await is_whitelisted(chat_id, user_id):
        return

    # Fetch the user's profile (bio)
    try:
        user = await client.get_chat(user_id)
    except Exception:
        return

    bio = getattr(user, "bio", None) or ""
    full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
    mention = f"[{full_name}](tg://user?id={user_id})"

    # Anti-bio link - original functionality
    if URL_RE.search(bio):
        # Try to delete the message (if permissions allow)
        try:
            await message.delete()
        except errors.MessageDeleteForbidden:
            # If bot cannot delete messages, politely instruct
            return await message.reply_text("Please remove the link from your bio.", quote=True)

        mode, limit, penalty = await get_config(chat_id)
        if mode == "warn":
            count = await increment_warning(chat_id, user_id)
            warning_text = (
                "**🚨 Warning** 🚨\n\n"
                f"👤 **User:** {mention} `[{user_id}]`\n"
                "❌ **Reason:** URL found in bio\n"
                f"⚠️ **Warning:** {count}/{limit}\n\n"
                "**NOTICE: Remove Link In Your Bio**"
            )
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Cancel Warning ❌", callback_data=f"cancel_warn_{user_id}"),
                        InlineKeyboardButton("Whitelist ✅", callback_data=f"whitelist_{user_id}"),
                    ],
                    [InlineKeyboardButton("Close", callback_data="close")],
                ]
            )
            sent = await message.reply_text(warning_text, reply_markup=keyboard)
            if count >= limit:
                try:
                    if penalty == "mute":
                        # restrict: disallow sending messages
                        await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unmute", callback_data=f"unmute_{user_id}")]])
                        await sent.edit_text(f"**{full_name} has been muted for [Link In Bio].**", reply_markup=kb)
                    else:
                        await client.ban_chat_member(chat_id, user_id)
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unban", callback_data=f"unban_{user_id}")]])
                        await sent.edit_text(f"**{full_name} has been banned for [Link In Bio].**", reply_markup=kb)
                except errors.ChatAdminRequired:
                    await sent.edit_text(f"**Remove your bio link. I don't have permission to {penalty}.**")
        else:
            # direct punish modes
            try:
                if mode == "mute":
                    await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unmute", callback_data=f"unmute_{user_id}")]])
                    await message.reply_text(f"{full_name} has been muted for [Link In Bio].", reply_markup=kb)
                else:
                    await client.ban_chat_member(chat_id, user_id)
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unban", callback_data=f"unban_{user_id}")]])
                    await message.reply_text(f"{full_name} has been banned for [Link In Bio].", reply_markup=kb)
            except errors.ChatAdminRequired:
                return await message.reply_text(f"I don't have permission to {mode} users.")
        return

    # Anti-ads - check message content for ad patterns
    text = (message.text or message.caption or "") or ""
    if AD_RE.search(text):
        # treat as link/advertisement: delete message and warn
        try:
            await message.delete()
        except errors.MessageDeleteForbidden:
            return

        mode, limit, penalty = await get_config(chat_id)
        if mode == "warn":
            count = await increment_warning(chat_id, user_id)
            await message.reply_text(f"⚠️ {mention} Advertising detected. Warning {count}/{limit}.")
            if count >= limit:
                try:
                    if penalty == "mute":
                        await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
                        await message.reply_text(f"{full_name} muted for advertising.")
                    else:
                        await client.ban_chat_member(chat_id, user_id)
                        await message.reply_text(f"{full_name} banned for advertising.")
                except errors.ChatAdminRequired:
                    await message.reply_text(f"I don't have permission to {penalty} users.")
                await reset_warnings(chat_id, user_id)
        else:
            try:
                if mode == "mute":
                    await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
                    await message.reply_text(f"{full_name} muted for advertising.")
                else:
                    await client.ban_chat_member(chat_id, user_id)
                    await message.reply_text(f"{full_name} banned for advertising.")
            except errors.ChatAdminRequired:
                await message.reply_text(f"I don't have permission to {mode} users.")
        return

    # Anti-bot / join-protection placeholder (kept minimal)
    # If you want join-protection on first post, implement a first-message check or track joins in DB.
    # Currently left intentionally minimal.


# ------------------ Extra anti-spam simple handler ------------------
_spam_cache = {}
_SPAM_WINDOW = 7  # seconds
_SPAM_LIMIT = 6


@app.on_message(filters.group, group=40)
async def anti_flood_detect(client, message: Message):
    try:
        uid = (message.chat.id, message.from_user.id)
    except Exception:
        return
    now = asyncio.get_event_loop().time()
    entry = _spam_cache.get(uid)
    if not entry:
        _spam_cache[uid] = [now]
        return
    # prune old timestamps
    entry = [t for t in entry if now - t <= _SPAM_WINDOW]
    entry.append(now)
    _spam_cache[uid] = entry
    if len(entry) > _SPAM_LIMIT:
        chat_id = message.chat.id
        user_id = message.from_user.id
        if await is_admin(client, chat_id, user_id) or await is_whitelisted(chat_id, user_id):
            # clear early and return
            _spam_cache.pop(uid, None)
            return
        mode, limit, penalty = await get_config(chat_id)
        if mode == "warn":
            count = await increment_warning(chat_id, user_id)
            await message.reply_text(f"⚠️ Flood detected. Warning {count}/{limit}.")
            if count >= limit:
                try:
                    if penalty == "mute":
                        await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
                        await message.reply_text("User muted for flooding.")
                    else:
                        await client.ban_chat_member(chat_id, user_id)
                        await message.reply_text("User banned for flooding.")
                except errors.ChatAdminRequired:
                    await message.reply_text(f"I don't have permission to {penalty} users.")
                await reset_warnings(chat_id, user_id)
        else:
            try:
                if mode == "mute":
                    await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
                    await message.reply_text("User muted for flooding.")
                else:
                    await client.ban_chat_member(chat_id, user_id)
                    await message.reply_text("User banned for flooding.")
            except errors.ChatAdminRequired:
                await message.reply_text(f"I don't have permission to {mode} users.")
        # clear cache for that user to avoid repeated actions
        _spam_cache.pop(uid, None)

# ---- Ensure DB tables exist once bot is fully started ----

async def __biolink_db_init():
    try:
        await init_db()
    except Exception as e:
        print("[BioLink] DB Init Error:", e)

@app.on_message(filters.command("start"), group=-99)
async def __biolink_hidden_starter(_, __):
    # run only once, when the bot handles the first message after startup
    if not getattr(app, "_biolink_db_ready", False):
        app._biolink_db_ready = True
        asyncio.create_task(__biolink_db_init())
