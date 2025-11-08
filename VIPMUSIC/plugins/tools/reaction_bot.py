import random
from pyrogram import filters
from pyrogram.types import Message
from VIPMUSIC import app, SUDOERS

# ---------------- EMOJI CONFIG ----------------
VALID_REACTIONS = [
    "❤️", "💖", "💘", "💞", "💓", "💫", "💥", "✨",
    "🌸", "🌹", "💎", "🌙", "🔥", "🥰", "😍",
    "😘", "😉", "🤩", "😂", "😎", "💐", "😻", "🥳"
]

# Track reaction status per chat (True=ON, False=OFF)
reaction_status = {}

# Track recently used emojis per chat
used_emojis = {}
MAX_HISTORY = 6  # don’t reuse last 6 emojis per chat


# ---------------- UTILS ----------------
def next_emoji(chat_id: int) -> str:
    """Return a random emoji not recently used in this chat."""
    global used_emojis
    if chat_id not in used_emojis:
        used_emojis[chat_id] = []

    available = [e for e in VALID_REACTIONS if e not in used_emojis[chat_id]]
    if not available:  # reset when all used
        used_emojis[chat_id].clear()
        available = VALID_REACTIONS.copy()

    emoji = random.choice(available)
    used_emojis[chat_id].append(emoji)
    if len(used_emojis[chat_id]) > MAX_HISTORY:
        used_emojis[chat_id].pop(0)
    return emoji


async def is_admin_or_sudo(chat_id: int, user_id: int) -> bool:
    """Check if user is admin, owner, or sudo."""
    if user_id in SUDOERS:
        return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False


# ---------------- COMMAND HANDLER ----------------
@app.on_message(filters.command(["reaction"]) & (filters.group | filters.supergroup))
async def toggle_reaction(_, message: Message):
    if len(message.command) < 2:
        state = "ON ✅" if reaction_status.get(message.chat.id) else "OFF ❌"
        return await message.reply_text(f"🎭 Reaction Bot is currently **{state}**")

    cmd = message.command[1].lower()
    if cmd not in ["on", "off"]:
        return await message.reply_text("Usage:\n/reaction on — enable\n/reaction off — disable")

    user_id = message.from_user.id if message.from_user else None
    if not await is_admin_or_sudo(message.chat.id, user_id):
        return await message.reply_text("Only Admins, Owners or Sudoers can use this command!")

    if cmd == "on":
        reaction_status[message.chat.id] = True
        await message.reply_text("✅ Reaction Bot is now **ON** — reacting to every message!")
    else:
        reaction_status[message.chat.id] = False
        await message.reply_text("❌ Reaction Bot is now **OFF** — stopped reacting.")


# ---------------- REACTION HANDLER ----------------
@app.on_message(filters.text & (filters.group | filters.supergroup))
async def auto_react(_, message: Message):
    chat_id = message.chat.id

    # Skip bot commands
    if message.text and message.text.startswith("/"):
        return

    # Check if reactions are enabled in this chat
    if not reaction_status.get(chat_id):
        return

    try:
        emoji = next_emoji(chat_id)
        await message.react(emoji)
        print(f"[ReactionBot] Reacted in {chat_id} with {emoji}")
    except Exception as e:
        print(f"[ReactionBot Error] {e}")
