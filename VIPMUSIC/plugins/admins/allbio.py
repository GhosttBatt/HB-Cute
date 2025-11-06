#from VIPMUSIC.utils.Ghostt_ban import admin_filter
from VIPMUSIC.misc import SUDOERS
from config import SUDOERS
import os
import csv
from VIPMUSIC import app
from pyrogram import Client, filters
from pyrogram.types import Message

# assuming `app` and `SUDOERS` are already defined in your main bot file

@app.on_message(filters.command("allbio") & filters.user(SUDOERS))
def get_all_bios(client: Client, message: Message):
    chat_id = message.chat.id
    members_data = []

    try:
        # Iterate through all chat members
        for member in client.get_chat_members(chat_id):
            user = member.user
            try:
                # Fetch full user info for bio
                user_full = client.get_users(user.id)
                bio = user_full.bio if getattr(user_full, "bio", None) else "No bio"
            except Exception:
                bio = "Unable to fetch bio"

            # Full name (first + last)
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "No name"
            username = f"@{user.username}" if user.username else "No username"

            # Add member data to list
            members_data.append(
                f"👤 Name: {full_name}\n"
                f"🔗 Username: {username}\n"
                f"🆔 User ID: {user.id}\n"
                f"📝 Bio: {bio}\n"
                + "-" * 50 + "\n"
            )

        # Write all data into a text file
        with open("members_bio.txt", "w", encoding="utf-8") as f:
            f.writelines(members_data)

        # Send the text file back as a downloadable document
        client.send_document(chat_id, "members_bio.txt", caption="📄 All members’ bio list")

    except Exception as e:
        message.reply_text(f"❌ Error occurred: {e}")
