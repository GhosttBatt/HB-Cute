import random
import io
import os
import requests
from VIPMUSIC import app
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageStat
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType

# --- FLAMES RESULT CONFIG ---
RESULTS = {
    "F": {
        "title": "💛 𝐅ʀɪᴇɴᴅ𝗌",
        "title_cap": "Friends",
        "desc": "A strong bond filled with laughter, trust, and memories. You two are perfect as friends forever! 🤝",
        "image_url": [""],
        "images": [f"VIPMUSIC/assets/flames/friends/{i}.jpg" for i in range(1, 6)]
    },
    "L": {
        "title": "❤️ 𝐋ᴏᴠᴇ",
        "title_cap": "Love",
        "desc": "There’s a spark and magic between you both — a true love story is forming! 💞",
        "image_url": [
            "https://i.imgur.com/4eAOSDq.jpeg",
            "https://i.imgur.com/4eAOSDq.jpeg",
            "https://i.imgur.com/4eAOSDq.jpeg"
        ],
        "images": [f"VIPMUSIC/assets/flames/love/{i}.jpg" for i in range(1, 6)]
    },
    "A": {
        "title": "💖 𝐀ғғᴇᴄᴛɪᴏɴ",
        "title_cap": "Affection",
        "desc": "You both care deeply for each other — gentle hearts and pure emotion bloom! 🌸",
        "image_url": [
            "https://i.imgur.com/4eAOSDq.jpeg",
            "https://i.imgur.com/4eAOSDq.jpeg",
            "https://i.imgur.com/4eAOSDq.jpeg"
        ],
        "images": [f"VIPMUSIC/assets/flames/affection/{i}.jpg" for i in range(1, 6)]
    },
    "M": {
        "title": "💍 𝐌ᴀʀʀɪᴀɢᴇ",
        "title_cap": "Marriage",
        "desc": "Destiny has already written your names together — a wedding bell symphony awaits! 💫",
        "image_url": [""],
        "images": [f"VIPMUSIC/assets/flames/marriage/{i}.jpg" for i in range(1, 6)]
    },
    "E": {
        "title": "💔 𝐄ɴᴇᴍʏ",
        "title_cap": "Enemy",
        "desc": "Clashing energies and fiery tempers — maybe not meant to be this time 😅",
        "image_url": [""],
        "images": [f"VIPMUSIC/assets/flames/enemy/{i}.jpg" for i in range(1, 6)]
    },
    "S": {
        "title": "💜 𝐒ɪʙʟɪɴɢ𝗦",
        "title_cap": "Siblings",
        "desc": "You both share a sibling-like connection — teasing, caring, and protective 💫",
        "image_url": [""],
        "images": [f"VIPMUSIC/assets/flames/siblings/{i}.jpg" for i in range(1, 6)]
    }
}


# --- FLAMES LOGIC ---
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


# --- CREATE POSTER ---
def make_poster(image_url, name1, name2, title_cap, percentage):
    try:
        bg = None

        # --- Try URL first ---
        if image_url and image_url.startswith(("http://", "https://")):
            try:
                response = requests.get(image_url, timeout=10)
                response.raise_for_status()
                bg = Image.open(io.BytesIO(response.content)).convert("RGB")
            except Exception as e:
                print(f"[FLAMES] URL image failed: {e}")

        # --- If URL invalid or failed, fallback to local folder ---
        if bg is None:
            folder_path = f"VIPMUSIC/assets/flames/{title_cap.lower()}"
            if os.path.exists(folder_path):
                local_images = [
                    os.path.join(folder_path, f)
                    for f in os.listdir(folder_path)
                    if f.lower().endswith((".jpg", ".jpeg", ".png"))
                ]
                if local_images:
                    bg_path = random.choice(local_images)
                    bg = Image.open(bg_path).convert("RGB")
                    print(f"[FLAMES] Using fallback image: {bg_path}")
            if bg is None:
                bg = Image.new("RGB", (900, 600), (255, 192, 203))

        # --- Resize and blur ---
        bg = bg.resize((900, 600)).filter(ImageFilter.GaussianBlur(4))

        # --- Dark vignette effect ---
        shadow = Image.new("L", bg.size, 0)
        draw_shadow = ImageDraw.Draw(shadow)
        max_dim = max(bg.size)
        for i in range(int(max_dim / 2)):
            intensity = int(255 * (i / (max_dim / 2)))
            draw_shadow.ellipse(
                (i - 200, i - 200, bg.size[0] - i + 200, bg.size[1] - i + 200),
                fill=intensity
            )
        shadow = shadow.filter(ImageFilter.GaussianBlur(100))
        shadow_mask = ImageEnhance.Brightness(shadow).enhance(0.8)
        bg.paste((0, 0, 0), mask=shadow_mask)

        # --- Brightness adjust ---
        stat = ImageStat.Stat(bg)
        brightness = sum(stat.mean[:3]) / 3
        if brightness > 160:
            bg = ImageEnhance.Brightness(bg).enhance(0.8)
            text_color = "white"
        elif brightness < 90:
            bg = ImageEnhance.Brightness(bg).enhance(1.3)
            text_color = "white"
        else:
            text_color = "black" if brightness > 130 else "white"

        draw = ImageDraw.Draw(bg)

        # --- Load fonts ---
        try:
            font_title = ImageFont.truetype("VIPMUSIC/assets/DejaVuSans-Bold.ttf", 60)
            font_text = ImageFont.truetype("VIPMUSIC/assets/Rekalgera-Regular.otf", 45)
            font_small = ImageFont.truetype("VIPMUSIC/assets/Sprintura Demo.otf", 35)
            font_fancy = ImageFont.truetype("VIPMUSIC/assets/DejaVuSans.ttf", 35)
        except Exception as e:
            print(f"[FLAMES] Font load failed: {e}")
            font_title = font_text = font_small = font_fancy = ImageFont.load_default()

        def safe_text(text):
            return text.encode("ascii", "ignore").decode("ascii")

        def draw_centered_text(y, text, font=None, max_width=850):
            text = safe_text(str(text))
            fnt = font or ImageFont.load_default()
            w, h = draw.textsize(text, font=fnt)
            while w > max_width and hasattr(fnt, "path") and fnt.size > 15:
                fnt = ImageFont.truetype(fnt.path, fnt.size - 2)
                w, h = draw.textsize(text, font=fnt)
            x = (900 - w) / 2
            shadow_color = (0, 0, 0, 180) if text_color == "white" else (255, 255, 255, 180)
            for ox, oy in [(-3, -3), (-3, 3), (3, -3), (3, 3)]:
                draw.text((x + ox, y + oy), text, font=fnt, fill=shadow_color)
            draw.text((x, y), text, fill=text_color, font=fnt)

        # --- Draw texts on poster ---
        draw_centered_text(40, "F L A M E S", font_title)
        draw_centered_text(170, f"{name1.title()} x {name2.title()}", font_text)
        draw_centered_text(270, f"Result: {title_cap}", font_text)
        draw_centered_text(360, f"Compatibility: {percentage}%", font_small)
        draw_centered_text(530, "Made By x @HeartBeat_Fam", font_fancy)

        # --- Output image ---
        bio = io.BytesIO()
        bio.name = "flames_result.jpg"
        bg.save(bio, "JPEG")
        bio.seek(0)
        return bio

    except Exception as e:
        print(f"[FLAMES ERROR] Poster generation failed: {e}")
        raise


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

        love = random.randint(60, 100) if result_letter in "LAM" else random.randint(10, 70)
        emotion = random.randint(60, 100)
        fun = random.randint(50, 100)
        communication = random.randint(50, 100)
        trust = random.randint(60, 100)

        # --- Random image (URL or local) ---
        image_source = random.choice(result["image_url"] + result["images"])
        poster = make_poster(image_source, name1, name2, result["title_cap"], love)

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
                InlineKeyboardButton("🔻 ᴛʀʏ ᴀɢᴀɪɴ 🔻", callback_data="flames_retry"),
                InlineKeyboardButton("🔻 sʜᴀʀᴇ ʀᴇsᴜʟᴛ 🔻", switch_inline_query="flames love test"),
            ],
            [
                InlineKeyboardButton("🔻 ᴠɪᴇᴡ ᴀʟʟ ʀᴇsᴜʟᴛs 🔻", callback_data="flames_list")
            ]
        ])

        await message.reply_photo(photo=poster, caption=caption, reply_markup=buttons)

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}")


# --- CALLBACKS ---
@app.on_callback_query()
async def callback_handler(client, cq):
    try:
        if cq.data == "flames_retry":
            await cq.message.reply_text("✨ Type `/flames Name1 Name2` again to try another match!")
        elif cq.data == "flames_list":
            await cq.message.reply_text(
                "📜 **FLAMES Meaning:**\n\n"
                "💛 F - Friendship\n"
                "❤️ L - Love\n"
                "💖 A - Affection\n"
                "💍 M - Marriage\n"
                "💔 E - Enemy\n"
                "💜 S - Sibling\n",
                quote=True
            )
        await cq.answer()
    except Exception as e:
        await cq.message.reply_text(f"⚠️ Callback Error: {e}")
