from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from BioLink.helper.utils import (
    is_admin,
    get_config, update_config,
    increment_warning, reset_warnings,
    is_whitelisted, add_whitelist, remove_whitelist, get_whitelist
)
from config import API_ID, API_HASH, BOT_TOKEN, URL_PATTERN

# =================== MEMORY CONFIG ===================
BIO_TOGGLE = {}  # {chat_id: True/False} — stores BioLink protection status per group

# =================== BOT INIT ===================
app = Client(
    "BioLinkRobot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# =================== /BIOLINK TOGGLE ===================
@app.on_message(filters.group & filters.command("biolink"))
async def toggle_biolink(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        return await message.reply_text("❌ ᴏɴʟʏ ᴀᴅᴍɪɴs ᴄᴀɴ ᴛᴏɢɢʟᴇ ʙɪᴏʟɪɴᴋ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ.")

    current = BIO_TOGGLE.get(chat_id, False)
    new_status = not current
    BIO_TOGGLE[chat_id] = new_status

    status_text = "✅ **ᴇɴᴀʙʟᴇᴅ**" if new_status else "🚫 **ᴅɪꜱᴀʙʟᴇᴅ**"
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ ᴇɴᴀʙʟᴇ", callback_data=f"bio_on_{chat_id}"),
            InlineKeyboardButton("🚫 ᴅɪꜱᴀʙʟᴇ", callback_data=f"bio_off_{chat_id}")
        ]
    ])
    await message.reply_text(f"**ʙɪᴏʟɪɴᴋ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ ɪꜱ ɴᴏᴡ {status_text}**", reply_markup=kb)

# =================== CALLBACKS ===================
@app.on_callback_query()
async def callback_handler(client: Client, callback_query):
    data = callback_query.data
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id

    # ========== Handle /biolink toggle ==========
    if data.startswith("bio_on_") or data.startswith("bio_off_"):
        if not await is_admin(client, chat_id, user_id):
            return await callback_query.answer("❌ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ.", show_alert=True)

        chat_id = int(data.split("_")[2])
        BIO_TOGGLE[chat_id] = data.startswith("bio_on_")
        status_text = "✅ **ᴇɴᴀʙʟᴇᴅ**" if BIO_TOGGLE[chat_id] else "🚫 **ᴅɪꜱᴀʙʟᴇᴅ**"
        await callback_query.message.edit_text(f"**ʙɪᴏʟɪɴᴋ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ ɪꜱ ɴᴏᴡ {status_text}**")
        return await callback_query.answer()

    # ========== Other callback handling ==========
    if not await is_admin(client, chat_id, user_id):
        return await callback_query.answer("❌ ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴀᴅᴍɪɴ.", show_alert=True)

    if data == "close":
        return await callback_query.message.delete()

    # --- Warn limit selector ---
    if data == "warn":
        _, selected_limit, _ = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"🍏" if selected_limit == i else f"{i}", callback_data=f"warn_{i}")
                for i in range(6)
            ],
            [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back"),
             InlineKeyboardButton("🗑️ ᴄʟᴏꜱᴇ", callback_data="close")]
        ])
        return await callback_query.message.edit_text("**ꜱᴇᴛ ɴᴜᴍʙᴇʀ ᴏꜰ ᴡᴀʀɴɪɴɢꜱ:**", reply_markup=kb)

    # --- Handle warn_x updates ---
    if data.startswith("warn_"):
        count = int(data.split("_")[1])
        await update_config(chat_id, limit=count)
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"🍏" if count == i else f"{i}", callback_data=f"warn_{i}")
                for i in range(6)
            ],
            [InlineKeyboardButton("🔙 ʙᴀᴄᴋ", callback_data="back"),
             InlineKeyboardButton("🗑️ ᴄʟᴏꜱᴇ", callback_data="close")]
        ])
        await callback_query.message.edit_text(f"**ᴡᴀʀɴɪɴɢ ʟɪᴍɪᴛ ꜱᴇᴛ ᴛᴏ {count}**", reply_markup=kb)
        return await callback_query.answer()

# =================== MAIN BIO CHECK ===================
@app.on_message(filters.group)
async def check_bio(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Skip if biolink detection is disabled
    if not BIO_TOGGLE.get(chat_id, False):
        return

    if await is_admin(client, chat_id, user_id) or await is_whitelisted(chat_id, user_id):
        return

    user = await client.get_chat(user_id)
    bio = user.bio or ""
    full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
    mention = f"[{full_name}](tg://user?id={user_id})"

    if URL_PATTERN.search(bio):
        try:
            await message.delete()
        except errors.MessageDeleteForbidden:
            return await message.reply_text("ʀᴇᴍᴏᴠᴇ ʏᴏᴜʀ ʙɪᴏ ʟɪɴᴋ.")

        mode, limit, penalty = await get_config(chat_id)
        count = await increment_warning(chat_id, user_id)
        warning_text = (
            f"🚨 **ᴡᴀʀɴɪɴɢ** 🚨\n\n"
            f"👤 **ᴜꜱᴇʀ:** {mention} `[{user_id}]`\n"
            f"❌ **ʀᴇᴀꜱᴏɴ:** ʙɪᴏ ᴄᴏɴᴛᴀɪɴꜱ ʟɪɴᴋ\n"
            f"⚠️ **ᴡᴀʀɴɪɴɢ:** {count}/{limit}\n\n"
            "**ɴᴏᴛɪᴄᴇ: ʀᴇᴍᴏᴠᴇ ʟɪɴᴋ ꜰʀᴏᴍ ʏᴏᴜʀ ʙɪᴏ**"
        )

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ ᴡᴀʀɴ", callback_data=f"cancel_warn_{user_id}"),
                InlineKeyboardButton("✅ ᴡʜɪᴛᴇʟɪꜱᴛ", callback_data=f"whitelist_{user_id}")
            ],
            [InlineKeyboardButton("🗑️ ᴄʟᴏꜱᴇ", callback_data="close")]
        ])
        sent = await message.reply_text(warning_text, reply_markup=kb)

        if count >= limit:
            try:
                if penalty == "mute":
                    await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ ᴜɴᴍᴜᴛᴇ", callback_data=f"unmute_{user_id}")]])
                    await sent.edit_text(f"{mention} ʜᴀꜱ ʙᴇᴇɴ 🔇 ᴍᴜᴛᴇᴅ ꜰᴏʀ [ʟɪɴᴋ ɪɴ ʙɪᴏ].", reply_markup=kb)
                else:
                    await client.ban_chat_member(chat_id, user_id)
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ ᴜɴʙᴀɴ", callback_data=f"unban_{user_id}")]])
                    await sent.edit_text(f"{mention} ʜᴀꜱ ʙᴇᴇɴ 🔨 ʙᴀɴɴᴇᴅ ꜰᴏʀ [ʟɪɴᴋ ɪɴ ʙɪᴏ].", reply_markup=kb)
            except errors.ChatAdminRequired:
                await sent.edit_text("ɪ ᴅᴏɴᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪꜱꜱɪᴏɴ ᴛᴏ ᴘᴜɴɪꜱʜ ᴜꜱᴇʀꜱ.")
    else:
        await reset_warnings(chat_id, user_id)

# =================== RUN BOT ===================
async def biolink():
    await app.start()
    print("✅ BioLink Bot started successfully.")
