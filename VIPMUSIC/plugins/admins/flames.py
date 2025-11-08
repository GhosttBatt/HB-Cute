import random
import io
import os
import aiohttp
from VIPMUSIC import app
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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
    "S": {"title": "💜 𝐒ɪʙʟɪɴɢ𝘴", "title_cap": "Siblings", "desc": "You both share a sibling-like connection — teasing, caring, and protective 💫", "folder": "VIPMUSIC/assets/flames/siblings", "urls": [""]},
}


# --- IMAGE PICKER (Local + URL Fallback) ---
async def get_random_image(result_letter):
    result = RESULTS[result_letter]
    folder = result["folder"]
    urls = [u for u in result.get("urls", []) if u]

    local_files = []
    if os.path.isdir(folder):
        local_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

    if not local_files and not urls:
        raise ValueError(f"No images available for {result_letter}")

    use_local = False
    if local_files and urls:
        use_local = random.choice([True, False])
    elif local_files:
        use_local = True

    if use_local:
        choice = random.choice(local_files)
        print(f"[FLAMES] Selected local: {choice}")
        return Image.open(choice).convert("RGB")

    url = random.choice(urls)
    print(f"[FLAMES] Selected URL: {url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    if local_files:
                        return Image.open(random.choice(local_files)).convert("RGB")
                    raise Exception(f"Failed to fetch URL ({resp.status})")
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


# --- DARK EFFECT ---
def darken_image(image, opacity=0.6):
    overlay = Image.new("RGBA", image.size, (0, 0, 0, int(255 * opacity)))
    darkened = Image.alpha_composite(image.convert("RGBA"), overlay)
    return darkened.convert("RGB")


# --- FANCY FONT ---
def get_font(size):
    font_path = "VIPMUSIC/assets/Sprintura Demo.otf"
    if not os.path.exists(font_path):
        font_path = "VIPMUSIC/assets/Rekalgera-Regular.otf"
    return ImageFont.truetype(font_path, size)


# --- DRAW RESULT ON IMAGE ---
def draw_result(image, title, desc, percent, name1=None, name2=None):
    image = darken_image(image, 0.55)
    draw = ImageDraw.Draw(image)
    W, H = image.size

    # --- Fonts ---
    font_title = get_font(int(W * 0.07))
    font_sub = get_font(int(W * 0.045))
    font_name = get_font(int(W * 0.06))
    font_small = get_font(int(W * 0.035))
    font_bottom = get_font(int(W * 0.03))

    def shadowed_text(x, y, text, font, fill="white"):
        shadow_color = "black"
        offsets = [(-2, -2), (2, -2), (-2, 2), (2, 2)]
        for ox, oy in offsets:
            draw.text((x + ox, y + oy), text, font=font, fill=shadow_color)
        draw.text((x, y), text, font=font, fill=fill)

    # --- Headings ---
    flames_title = "-- F L A M E S --"
    tw = draw.textlength(flames_title, font=font_title)
    shadowed_text((W - tw) / 2, H * 0.10, flames_title, font_title)

    # --- Names ---
    if name1 and name2:
        names_text = f"{name1.title()} ❤ {name2.title()}"
        nw = draw.textlength(names_text, font=font_name)
        shadowed_text((W - nw) / 2, H * 0.28, names_text, font_name)

    # --- Result heading ---
    result_heading = f"Result: {title}"
    rw = draw.textlength(result_heading, font=font_sub)
    shadowed_text((W - rw) / 2, H * 0.43, result_heading, font_sub)

    # --- Compatibility heading ---
    comp_heading = f"Compatibility: {percent}%"
    cw = draw.textlength(comp_heading, font=font_sub)
    shadowed_text((W - cw) / 2, H * 0.56, comp_heading, font_sub)

    # --- Description ---
    dw = draw.textlength(desc, font=font_small)
    shadowed_text((W - dw) / 2, H * 0.68, desc, font_small)

    # --- Footer Signature ---
    footer = "Made by ❤ @HeartBeat_Fam"
    fw = draw.textlength(footer, font=font_bottom)
    shadowed_text((W - fw) / 2, H * 0.88, footer, font_bottom)

    return image


# --- EMOJI BAR ---
def emoji_bar(percent):
    full = int(percent / 20)
    return "✩" * full + "★" * (5 - full)


# --- /FLAMES COMMAND ---
@app.on_message(filters.command("flames"))
async def flames_command(client, message):
    try:
        args = message.text.split(None, 2)
        if len(args) < 3:
            await message.reply_text("✨ Usage: `/flames Name1 Name2`", quote=True)
            return

        name1, name2 = args[1], args[2]
        result_letter = flames_result(name1, name2)
        result = RESULTS[result_letter]

        bg = await get_random_image(result_letter)
        percent = random.randint(10, 100)
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
               # InlineKeyboardButton("🔻 ᴛʀʏ ᴀɢᴀɪɴ 🔻", callback_data="flames_retry"),
                InlineKeyboardButton("🔻 sʜᴀʀᴇ 🔻", switch_inline_query="flames love test"),
            #],
            #[
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
            await message.reply_text("❌ This command only works in groups!", quote=True)
            return

        user = message.from_user
        members = [m.user async for m in client.get_chat_members(message.chat.id) if not m.user.is_bot and m.user.id != user.id]

        if len(members) < 3:
            await message.reply_text("⚠️ Not enough members in this group to match!", quote=True)
            return

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
        bg = draw_result(bg, RESULTS[random_result]["title"], RESULTS[random_result]["desc"], random.randint(60, 100))
        output = io.BytesIO()
        output.name = "match_result.jpg"
        bg.save(output, "JPEG")
        output.seek(0)

        await message.reply_photo(photo=output, caption=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔻 ᴛʀʏ ᴀɢᴀɪɴ 🔻", callback_data="match_retry")]]))
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
