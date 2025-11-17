import os
import threading
import time
import requests
from flask import Flask
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

from autorestart import autorestart

from helper.utils import (
    is_admin,
    get_config, update_config,
    increment_warning, reset_warnings,
    is_whitelisted, add_whitelist, remove_whitelist, get_whitelist
)

from config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    URL_PATTERN,
)

# ---------------- PYROGRAM BOT ---------------- #
app = Client(
    "BioLinkRobot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


@app.on_message(filters.group & filters.command("config"))
async def configure(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not await is_admin(client, chat_id, user_id):
        return

    mode, limit, penalty = await get_config(chat_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Warn", callback_data="warn")],
        [
            InlineKeyboardButton("🔻 𝐌ʋтɛ ✅" if penalty == "mute" else "Mute", callback_data="mute"),
            InlineKeyboardButton("🔻 𝐁αи ✅" if penalty == "ban" else "Ban", callback_data="ban")
        ],
        [InlineKeyboardButton("Close", callback_data="close")]
    ])
    await client.send_message(
        chat_id,
        "**Choose penalty for users with links in bio:**",
        reply_markup=keyboard
    )
    await message.delete()

@app.on_message(filters.group & filters.command("free"))
async def command_free(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not await is_admin(client, chat_id, user_id):
        return

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        arg = message.command[1]
        target = await client.get_users(int(arg) if arg.isdigit() else arg)
    else:
        return await client.send_message(chat_id, "**Reply or use /free user or id to whitelist someone.**")

    await add_whitelist(chat_id, target.id)
    await reset_warnings(chat_id, target.id)

    text = f"**✅ {target.mention} 𝐀ᴅᴅɛᴅ 𝐓σ 𝐖нιтɛƖιƨт**"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔻 𝐔и𝐖нιтɛƖιƨт 🚫", callback_data=f"unwhitelist_{target.id}"),
            InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🗑️", callback_data="close")
        ]
    ])
    await client.send_message(chat_id, text, reply_markup=keyboard)

@app.on_message(filters.group & filters.command("unfree"))
async def command_unfree(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if not await is_admin(client, chat_id, user_id):
        return

    if message.reply_to_message:
        target = message.reply_to_message.from_user
    elif len(message.command) > 1:
        arg = message.command[1]
        target = await client.get_users(int(arg) if arg.isdigit() else arg)
    else:
        return await client.send_message(chat_id, "**Reply or use /unfree user or id to unwhitelist someone.**")

    if await is_whitelisted(chat_id, target.id):
        await remove_whitelist(chat_id, target.id)
        text = f"**🚫 {target.mention} 𝐑ɛмσᴠɛ 𝐓σ 𝐖нιтɛƖιƨт**"
    else:
        text = f"**ℹ️ {target.mention} 𝐈ƨ 𝐍σт 𝐖нιтɛƖιƨт.**"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔻 𝐖нιƖιƨт ✅ ", callback_data=f"whitelist_{target.id}"),
            InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🗑️", callback_data="close")
        ]
    ])
    await client.send_message(chat_id, text, reply_markup=keyboard)

@app.on_message(filters.group & filters.command("freelist"))
async def command_freelist(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
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
        except:
            text += f"{i}: [User not found] [`{uid}`]\n"

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Close", callback_data="close")]])
    await client.send_message(chat_id, text, reply_markup=keyboard)

@app.on_callback_query()
async def callback_handler(client: Client, callback_query):
    data = callback_query.data
    chat_id = callback_query.message.chat.id
    user_id = callback_query.from_user.id
    if not await is_admin(client, chat_id, user_id):
        return await callback_query.answer("❌ You are not administrator", show_alert=True)

    if data == "close":
        return await callback_query.message.delete()

    if data == "back":
        mode, limit, penalty = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Warn", callback_data="warn")],
            [
                InlineKeyboardButton("🔻 𝐌ʋтɛ ✅" if penalty=="mute" else "Mute", callback_data="mute"),
                InlineKeyboardButton("🔻 𝐁αи ✅" if penalty=="ban" else "Ban", callback_data="ban")
            ],
            [InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🔻", callback_data="close")]
        ])
        await callback_query.message.edit_text("**𝐂нσƨɛ 𝐏ɛиαƖιтʏ 𝐅σя 𝐔ƨɛяƨ 𝐖ιтн 𝐋ιиκ 𝐈и 𝐁ισ:**", reply_markup=kb)
        return await callback_query.answer()

    if data == "warn":
        _, selected_limit, _ = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🍏" if selected_limit==0 else "0", callback_data="warn_0"),
             InlineKeyboardButton(f"🍏" if selected_limit==1 else "1", callback_data="warn_1"),
             InlineKeyboardButton(f"🍏" if selected_limit==2 else "2", callback_data="warn_2"),
             InlineKeyboardButton(f"🍏" if selected_limit==3 else "3", callback_data="warn_3"),
             InlineKeyboardButton(f"🍏" if selected_limit==4 else "4", callback_data="warn_4"),
             InlineKeyboardButton(f"🍏" if selected_limit==5 else "5", callback_data="warn_5")],
            [InlineKeyboardButton("Back", callback_data="back"), InlineKeyboardButton("Close", callback_data="close")]
        ])
        return await callback_query.message.edit_text("**𝐒ɛт 𝐍ʋмвɛя 𝐎ғ 𝐁αиƨ:**", reply_markup=kb)

    if data in ["mute", "ban"]:
        await update_config(chat_id, penalty=data)
        mode, limit, penalty = await get_config(chat_id)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔻 𝐖αяи 🔻", callback_data="warn")],
            [
                InlineKeyboardButton("🔻 𝐌ʋтɛ ✅" if penalty=="mute" else "Mute", callback_data="mute"),
                InlineKeyboardButton("🔻 𝐁αи ✅" if penalty=="ban" else "Ban", callback_data="ban")
            ],
            [InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🔻", callback_data="close")]
        ])
        await callback_query.message.edit_text("**𝐏ʋиιƨнмɛит 𝐒ɛƖɛcтɛᴅ**", reply_markup=kb)
        return await callback_query.answer()

    if data.startswith("warn_"):
        count = int(data.split("_")[1])
        await update_config(chat_id, limit=count)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🍏" if count==0 else "0", callback_data="warn_0"),
             InlineKeyboardButton(f"🍏" if count==1 else "1", callback_data="warn_1"),
             InlineKeyboardButton(f"🍏" if count==2 else "2", callback_data="warn_2"),
             InlineKeyboardButton(f"🍏" if count==3 else "3", callback_data="warn_3"),
             InlineKeyboardButton(f"🍏" if count==4 else "4", callback_data="warn_4"),
             InlineKeyboardButton(f"🍏" if count==5 else "5", callback_data="warn_5")],
            [InlineKeyboardButton("Back", callback_data="back"), InlineKeyboardButton("Close", callback_data="close")]
        ])
        await callback_query.message.edit_text(f"**𝐖αяиιиɢ 𝐋ιмιт 𝐒ɛт 𝐓σ {count}**", reply_markup=kb)
        return await callback_query.answer()

    if data.startswith(("unmute_", "unban_")):
        action, uid = data.split("_")
        target_id = int(uid)
        user = await client.get_chat(target_id)
        name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
        try:
            if action == "unmute":
                await client.restrict_chat_member(chat_id, target_id, ChatPermissions(can_send_messages=True))
            else:
                await client.unban_chat_member(chat_id, target_id)
            await reset_warnings(chat_id, target_id)
            msg = f"**{name} (`{target_id}`) has been {'unmuted' if action=='unmute' else 'unbanned'}**."

            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔻 𝐖нιƖιƨт ✅", callback_data=f"whitelist_{target_id}"),
                    InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🔻", callback_data="close")
                ]
            ])
            await callback_query.message.edit_text(msg, reply_markup=kb)
        
        except errors.ChatAdminRequired:
            await callback_query.message.edit_text(f"ɪ ᴅᴏɴᴛ ʜᴀᴠᴇ ᴘᴇʀᴍɪ𝗌𝗌ɪᴏɴ ᴛᴏ {action} ᴜ𝗌ᴇʀ𝗌.")
        return await callback_query.answer()

    if data.startswith("cancel_warn_"):
        target_id = int(data.split("_")[-1])
        await reset_warnings(chat_id, target_id)
        user = await client.get_chat(target_id)
        full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
        mention = f"[{full_name}](tg://user?id={target_id})"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔻 𝐖нιƖιƨт ✅", callback_data=f"whitelist_{target_id}"),
             InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🔻", callback_data="close")]
        ])
        await callback_query.message.edit_text(f"**✅ {mention} [`{target_id}`] ʜᴀ𝗌 ɴᴏ ᴍᴏʀᴇ ᴡᴀʀɴɪɴɢ𝗌!**", reply_markup=kb)
        return await callback_query.answer()

    if data.startswith("whitelist_"):
        target_id = int(data.split("_")[1])
        await add_whitelist(chat_id, target_id)
        await reset_warnings(chat_id, target_id)
        user = await client.get_chat(target_id)
        full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
        mention = f"[{full_name}](tg://user?id={target_id})"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔻 𝐔и𝐖нιтɛƖιƨт 🚫", callback_data=f"unwhitelist_{target_id}"),
             InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🔻", callback_data="close")]
        ])
        await callback_query.message.edit_text(f"**✅ {mention} [`{target_id}`] ʜᴀ𝗌 ʙᴇᴇɴ ᴡʜɪᴛᴇʟɪ𝗌ᴛᴇᴅ!**", reply_markup=kb)
        return await callback_query.answer()

    if data.startswith("unwhitelist_"):
        target_id = int(data.split("_")[1])
        await remove_whitelist(chat_id, target_id)
        user = await client.get_chat(target_id)
        full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
        mention = f"[{full_name}](tg://user?id={target_id})"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔻 𝐖нιƖιƨт ✅", callback_data=f"whitelist_{target_id}"),
             InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🔻", callback_data="close")]
        ])
        await callback_query.message.edit_text(f"**❌ {mention} [`{target_id}`] has been removed from whitelist.**", reply_markup=kb)
        return await callback_query.answer()

@app.on_message(filters.group)
async def check_bio(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
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
            return await message.reply_text("Remove Your Bio-Link.")

        mode, limit, penalty = await get_config(chat_id)
        if mode == "warn":
            count = await increment_warning(chat_id, user_id)
            warning_text = (
                "**🚨 𝐖αяиιиɢ** 🚨\n\n"
                f"👤 **𝐔ƨɛя:** {mention} `[{user_id}]`\n"
                "❌ **𝐑ɛαƨσи:** URL found in bio\n"
                f"⚠️ **𝐖αяиιиɢ:** {count}/{limit}\n\n"
                "**𝐍𝐎𝐓𝐈𝐂𝐄: 𝐑𝐞𝐦𝐨𝐯𝐞 𝐋𝐢𝐧𝐤 𝐈𝐧 𝐘𝐨𝐮𝐫 𝐁𝐢𝐨**"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔻𝐂αиᴄɛƖ 𝐖αяиιиɢ ❌", callback_data=f"cancel_warn_{user_id}"),
                 InlineKeyboardButton("🔻 𝐖нιƖιƨт ✅", callback_data=f"whitelist_{user_id}")],
                [InlineKeyboardButton("🔻 𝐂Ɩσƨɛ 🔻", callback_data="close")]
            ])
            sent = await message.reply_text(warning_text, reply_markup=keyboard)
            if count >= limit:
                try:
                    if penalty == "mute":
                        await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unmute🔻 𝐔и𝐌ʋтɛ ✅", callback_data=f"unmute_{user_id}")]])
                        await sent.edit_text(f"**{user_name} ʜᴀ𝗌 ʙᴇᴇɴ 🔇 ᴍᴜᴛᴇᴅ ғᴏʀ [Link In Bio].**", reply_markup=kb)
                    else:
                        await client.ban_chat_member(chat_id, user_id)
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔻 𝐔и𝐁αи ✅", callback_data=f"unban_{user_id}")]])
                        await sent.edit_text(f"**{user_name} ʜᴀ𝗌 ʙᴇᴇɴ 🔨 вαииɛᴅ ғσя [Link In Bio].**", reply_markup=kb)
                
                except errors.ChatAdminRequired:
                    await sent.edit_text(f"**ʀᴇᴍᴏᴠᴇ ʏᴏᴜʀ ʙɪᴏ ʟɪɴᴋ. ɪғ ɴᴏᴛ ᴜ ᴀʀᴇ {penalty} ᴜɴᴛɪʟ ᴜ ʀᴇᴍᴏᴠᴇ ʏᴏᴜʀ ʙɪᴏ.**")
        else:
            try:
                if mode == "mute":
                    await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔻𝐔и𝐌ʋтɛ🔻", callback_data=f"unmute_{user_id}")]])
                    await message.reply_text(f"{user_name} ʜᴀ𝗌 ʙᴇᴇɴ 🔇 ᴍᴜᴛᴇᴅ ғᴏʀ [Link In Bio].", reply_markup=kb)
                else:
                    await client.ban_chat_member(chat_id, user_id)
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unban", callback_data=f"unban_{user_id}")]])
                    await message.reply_text(f"{user_name} ʜᴀ𝗌 ʙᴇᴇɴ 🔨 ʙᴀɴɴᴇᴅ ғᴏʀ [Link In Bio].", reply_markup=kb)
            except errors.ChatAdminRequired:
                return await message.reply_text(f"I don't have permission to {mode} users.")
    else:
        await reset_warnings(chat_id, user_id)
