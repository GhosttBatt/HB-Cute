import random
from pyrogram import filters
from pyrogram.types import Message
from VIPMUSIC import app
from config import BANNED_USERS, MENTION_USERNAMES, START_REACTIONS


@app.on_message(filters.text & ~BANNED_USERS)
async def react_on_mentions(client, message: Message):
    """
    React with random emoji when certain names or keywords are mentioned.
    Uses MENTION_USERNAMES and START_REACTIONS from config.py
    """
    try:
        text = message.text.lower()
        if any(name.lower() in text for name in MENTION_USERNAMES):
            emoji = random.choice(START_REACTIONS)
            await message.react(emoji)
    except Exception as e:
        # Just log silently to avoid spammy tracebacks
        print(f"[mention_react] Error: {e}")
        pass
