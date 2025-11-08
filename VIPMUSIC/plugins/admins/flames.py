import random
import io
import os
import aiohttp
from VIPMUSIC import app
from PIL import Image, ImageDraw, ImageFont
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType


# --- CONFIG: FLAMES RESULT TYPES ---
RESULTS = {
    "F": {"title": "💛 𝐅ʀɪᴇɴᴅ𝘀", "title_cap": "Friends", "desc": "A strong bond filled with laughter, trust, and memories. You two are perfect as friends forever! 🤝", "folder": "VIPMUSIC/assets/flames/friends", "urls": [""]},
    "L": {"title": "❤️ 𝐋ᴏᴠᴇ", "title_cap": "Love", "desc": "There’s a spark and magic between you both — a true love story is forming! 💞", "folder": "VIPMUSIC/assets/flames/love", "urls": [""]},
    "A": {"title": "💖 𝐀ғғᴇᴄᴛɪᴏɴ", "title_cap": "Affection", "desc": "You both care deeply for each other — gentle hearts and pure emotion bloom! 🌸", "folder": "VIPMUSIC/assets/flames/affection", "urls": [""]},
    "M": {"title": "💍 𝐌ᴀʀʀɪᴀɢᴇ", "title_cap": "Marriage", "desc": "Destiny has already written your names together — a wedding bell symphony awaits! 💫", "folder": "VIPMUSIC/assets/flames/marriage", "urls": [""]},
    "E": {"title": "💔 𝐄ɴᴇᴍʏ", "title_cap": "Enemy", "desc": "Clashing energies and fiery tempers — maybe not meant to be this time 😅", "folder": "VIPMUSIC/assets/flames/enemy", "urls": [""]},
    "S": {"title": "💜 𝐒ɪʙʟɪɴɢ𝘀", "title_cap": "Siblings", "desc": "You both share a sibling-like connection — teasing, caring, and protective 💫", "folder": "VIPMUSIC/assets/flames/siblings", "urls": [""]},
}


# --- IMAGE PICKER ---
async def get_random_image(result_letter):
    result = RESULTS[result_letter]
    folder = result["folder"]
    urls = [u for u in result.get("urls", []) if u]

    local_files = []
    if os.path.isdir(folder):
        local_files = [os.path.join(folder, f) for f in os.listdir(folder)
                       if f.lower().endswith((".jpg", ".jpeg", ".png"))]

    if not local_files and not urls:
        raise ValueError(f"No images available for {result_letter}")

    # choose between local or URL
    if local_files and (not urls or random.choice([True, False])):
        return Image.open(random.choice(local_files)).convert("RGB")

    url = random.choice(urls)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception
                data = await resp.read()
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        if local_files:
            return Image.open(random.choice(local_files)).convert("RGB")
        raise


# --- FLAMES RESULT LOGIC ---
def flames_result(name1, name2):
    n1, n2 = name1.replace(" ", "").lower(), name2.replace(" ", "").lower()
    for letter in n1:
        if letter in n2:
            n1 = n1.replace(letter, "", 1)
            n2 = n2.replace(letter, "", 1)
    combined = n1 + n2
    count = len(combined)
    flames = list("FLAMES")
    while len(flames) > 1:
        index = (count % len(flames)) - 1
        if index >= 0:
            flames = flames[index + 1:] + flames[:index]
        else:
            flames = flames[:-1]
    return flames[0]


# --- DARKEN IMAGE ---
def darken_image(image, opacity=0.6):
    overlay = Image.new("RGBA", image.size, (0, 0, 0, int(255 * opacity)))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


# --- FONT LOADERS (Different Fonts for Each Section) ---
def get_font_flames(size):
    # Fonts used for the "F L A M E S" header
    paths = [
        "VIPMUSIC/assets/fonts/DejaVuSans-Bold.ttf",    # example fancy font for F L A M E S
        "VIPMUSIC/assets/Sprintura Demo.otf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def get_font_title(size):
    # Fonts used for the result title (Love, Friends, etc.)
    paths = [
        "VIPMUSIC/assets/fonts/DejaVuSans-Bold.ttf",          # bold elegant font for Title
        "VIPMUSIC/assets/Sprintura Demo.otf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def get_font_compat(size):
    # Fonts used for the Compatibility line
    paths = [
        "VIPMUSIC/assets/fonts/DejaVuSans-Bold.ttf",    # clean readable font for Compatibility
        "VIPMUSIC/assets/fonts/Rekalgera-Regular.otf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def get_font(size):
    # fallback / general font
    for f in [
        "VIPMUSIC/assets/fonts/Rekalgera-Regular.otf",
        "VIPMUSIC/assets/fonts/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


# --- DRAW RESULT ---
def draw_result(image, title_cap, desc, percent, name1=None, name2=None):
    image = darken_image(image, 0.55)
    draw = ImageDraw.Draw(image)
    W, H = image.size

    font_flames = get_font_flames(int(W * 0.09))
    font_title = get_font_title(int(W * 0.07))
    font_compat = get_font_compat(int(W * 0.045))
    font_name = get_font(int(W * 0.06))
    font_small = get_font(int(W * 0.035))
    font_bottom = get_font(int(W * 0.03))

    def shadowed_text(x, y, text, font, fill="white"):
        for ox, oy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            draw.text((x + ox, y + oy), text, font=font, fill="black")
        draw.text((x, y), text, font=font, fill=fill)

    # --- FLAMES HEADER ---
    flames_title = "-- F L A M E S --"
    shadowed_text((W - draw.textlength(flames_title, font=font_flames)) / 2, H * 0.08, flames_title, font_flames)

    # --- NAMES ---
    if name1 and name2:
        names_text = f"{name1.title()} x {name2.title()}"
        shadowed_text((W - draw.textlength(names_text, font=font_name)) / 2, H * 0.25, names_text, font_name)

    # --- TITLE (Result Type) ---
    shadowed_text((W - draw.textlength(title_cap, font=font_title)) / 2, H * 0.38, title_cap, font_title)

    # --- COMPATIBILITY ---
    comp_heading = f"Compatibility: {percent}%"
    shadowed_text((W - draw.textlength(comp_heading, font=font_compat)) / 2, H * 0.50, comp_heading, font_compat)

    # --- DESCRIPTION ---
    shadowed_text((W - draw.textlength(desc, font=font_small)) / 2, H * 0.64, desc, font_small)

    # --- FOOTER ---
    footer = "Made With x @HeartBeat_Fam"
    shadowed_text((W - draw.textlength(footer, font=font_bottom)) / 2, H * 0.86, footer, font_bottom)

    return image


# --- EMOJI BAR ---
def emoji_bar(percent):
    filled = int(percent / 20)
    return "★" * filled + "✩" * (5 - filled)


# --- /FLAMES COMMAND ---
@app.on_message(filters.command("flames"))
async def flames_command(client, message):
    try:
        args = message.text.split(None, 2)
        if len(args) < 3:
            return await message.reply_text("✨ Usage: `/flames Name1 Name2`", quote=True)

        name1, name2 = args[1], args[2]
        result_letter = flames_result(name1, name2)
        result = RESULTS[result_letter]

        # Restore all stat variables used in caption
        love = random.randint(60, 100)
        emotion = random.randint(40, 100)
        fun = random.randint(30, 100)
        communication = random.randint(50, 100)
        trust = random.randint(40, 100)

        # percent used for the image compatibility display
        percent = random.randint(10, 100)

        bg = await get_random_image(result_letter)
        bg = draw_result(bg, result["title_cap"], result["desc"], percent, name1, name2)
        buffer = io.BytesIO()
        bg.save(buffer, "JPEG")
        buffer.seek(0)

        caption = (
            f"<blockquote>{result['title']}</blockquote>\n"
            f"<blockquote>💥 **{name1.title()} ❣️ {name2.title()}**\n"
            f"💞 𝐂ᴏᴍᴘᴀᴛɪʙɪʟɪᴛʏ: **{love}%**\n{emoji_bar(love)}\n"
            f"💓 𝐄ᴍᴏᴛɪᴏɴᴀʟ𝐁ᴏɴᴅ: **{emotion}%**\n{emoji_bar(emotion)}\n"
            f"🤞🏻 𝐅ᴜɴ𝐋ᴇᴠᴇʟ: **{fun}%**\n{emoji_bar(fun)}\n"
            f"✨ 𝐂ᴏᴍᴍᴜɴɪᴄᴀᴛɪᴏɴ: **{communication}%**\n{emoji_bar(communication)}\n"
            f"💯 𝐓ʀᴜsᴛ: **{trust}%**\n{emoji_bar(trust)}</blockquote>\n"
            f"<blockquote>🔥 {result['desc']}</blockquote>"
        )

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔻 sʜᴀʀᴇ 🔻", switch_inline_query="flames love test"),
                InlineKeyboardButton("🔻 ᴠɪᴇᴡ ᴀʟʟ 🔻", callback_data="flames_list")
            ]
        ])

        await message.reply_photo(photo=buffer, caption=caption, reply_markup=buttons)

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}")


# --- /MATCH COMMAND ---
@app.on_message(filters.command("match"))
async def match_command(client, message):
    try:
        if message.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP):
            return await message.reply_text("❌ This command only works in groups!", quote=True)

        user = message.from_user
        members = [m.user async for m in client.get_chat_members(message.chat.id)
                   if not m.user.is_bot and m.user.id != user.id]

        if len(members) < 3:
            return await message.reply_text("⚠️ Not enough members in this group!", quote=True)

        selected = random.sample(members, 3)
        text = f"<blockquote>🎯 **𝐓ᴏᴘ 3 𝐌ᴀᴛᴄʜᴇs 𝐅ᴏʀ [{user.first_name}](tg://user?id={user.id}) 💘**</blockquote>\n"

        for idx, member in enumerate(selected, start=1):
            tag = f"[{member.first_name}](tg://user?id={member.id})"
            result_letter = random.choice(list(RESULTS.keys()))
            result = RESULTS[result_letter]
            percent = random.randint(50, 100)
            alert = "💞 **Perfect Couple Alert!** 💞" if percent >= 85 and result_letter in ["L", "M"] else ""
            text += f"<blockquote>{idx}. {tag} → {result['title']} ({percent}%)\n{emoji_bar(percent)}\n📝 {result['desc']}\n{alert}</blockquote>\n"

        random_result = random.choice(list(RESULTS.keys()))
        bg = await get_random_image(random_result)
        bg = draw_result(bg, RESULTS[random_result]["title_cap"], RESULTS[random_result]["desc"], random.randint(60, 100))
        output = io.BytesIO()
        output.name = "match_result.jpg"
        bg.save(output, "JPEG")
        output.seek(0)

        await message.reply_photo(photo=output, caption=text,
                                  reply_markup=InlineKeyboardMarkup(
                                      [[InlineKeyboardButton("🔻 ᴛʀʏ ᴀɢᴀɪɴ 🔻", callback_data="match_retry")]]))

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}")


# --- CALLBACK HANDLER ---
@app.on_callback_query()
async def callback_handler(client, cq):
    try:
        if cq.data == "flames_retry":
            await cq.message.reply_text("✨ Type `/flames Name1 Name2` again to try another match!")
        elif cq.data == "flames_list":
            await cq.message.reply_text(
                "📜 **FLAMES Meaning:**\n\n💛 F - Friendship\n❤️ L - Love\n💖 A - Affection\n💍 M - Marriage\n💔 E - Enemy\n💜 S - Sibling\n",
                quote=True
            )
        elif cq.data == "match_retry":
            await cq.message.reply_text("🎯 Type `/match` again to get new random matches!")
        await cq.answer()
    except Exception as e:
        await cq.message.reply_text(f"⚠️ Callback Error: {e}")
