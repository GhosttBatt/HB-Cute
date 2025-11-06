import random
import io
import requests
from VIPMUSIC import app
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageStat
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatType

# --- FLAMES RESULT CONFIG ---
RESULTS = {
    "F": {
        "title": "💛 FRIENDS",
        "desc": "A strong bond filled with laughter, trust, and memories. You two are perfect as friends forever! 🤝",
        "images": [
            "https://files.catbox.moe/mus8qn.jpg",
"https://files.catbox.moe/n7t6ma.jpg",
"https://files.catbox.moe/tb66lq.jpg",
"https://files.catbox.moe/imwrq4.jpg",
"https://files.catbox.moe/3u3dcp.jpg",
"https://files.catbox.moe/70fnlf.jpg",
"https://files.catbox.moe/i8r1dm.jpg",
"https://files.catbox.moe/5u11yx.jpg"
        ]
    },
    "L": {
        "title": "❤️ LOVE",
        "desc": "There’s a spark and magic between you both — a true love story is forming! 💞",
        "images": [
            "https://files.catbox.moe/mus8qn.jpg",
            "https://files.catbox.moe/n7t6ma.jpg",
            "https://files.catbox.moe/tb66lq.jpg",
            "https://files.catbox.moe/imwrq4.jpg",
            "https://files.catbox.moe/3u3dcp.jpg",
            "https://files.catbox.moe/70fnlf.jpg",
            "https://files.catbox.moe/i8r1dm.jpg",
            "https://files.catbox.moe/5u11yx.jpg"
        ]
    },
    "A": {
        "title": "💖 AFFECTION",
        "desc": "You both care deeply for each other — gentle hearts and pure emotion bloom! 🌸",
        "images": [
            "https://files.catbox.moe/mus8qn.jpg",
"https://files.catbox.moe/n7t6ma.jpg",
"https://files.catbox.moe/tb66lq.jpg",
"https://files.catbox.moe/imwrq4.jpg",
"https://files.catbox.moe/3u3dcp.jpg",
"https://files.catbox.moe/70fnlf.jpg",
"https://files.catbox.moe/i8r1dm.jpg",
"https://files.catbox.moe/5u11yx.jpg"
        ]
    },
    "M": {
        "title": "💍 MARRIAGE",
        "desc": "Destiny has already written your names together — a wedding bell symphony awaits! 💫",
        "images": [
            "https://files.catbox.moe/mus8qn.jpg",
"https://files.catbox.moe/n7t6ma.jpg",
"https://files.catbox.moe/tb66lq.jpg",
"https://files.catbox.moe/imwrq4.jpg",
"https://files.catbox.moe/3u3dcp.jpg",
"https://files.catbox.moe/70fnlf.jpg",
"https://files.catbox.moe/i8r1dm.jpg",
"https://files.catbox.moe/5u11yx.jpg"
        ]
    },
    "E": {
        "title": "💔 ENEMY",
        "desc": "Clashing energies and fiery tempers — maybe not meant to be this time 😅",
        "images": [
            "https://files.catbox.moe/mus8qn.jpg",
"https://files.catbox.moe/n7t6ma.jpg",
"https://files.catbox.moe/tb66lq.jpg",
"https://files.catbox.moe/imwrq4.jpg",
"https://files.catbox.moe/3u3dcp.jpg",
"https://files.catbox.moe/70fnlf.jpg",
"https://files.catbox.moe/i8r1dm.jpg",
"https://files.catbox.moe/5u11yx.jpg"
        ]
    },
    "S": {
        "title": "💜 SIBLING",
        "desc": "You both share a sibling-like connection — teasing, caring, and protective 💫",
        "images": [
            "https://files.catbox.moe/mus8qn.jpg",
"https://files.catbox.moe/n7t6ma.jpg",
"https://files.catbox.moe/tb66lq.jpg",
"https://files.catbox.moe/imwrq4.jpg",
"https://files.catbox.moe/3u3dcp.jpg",
"https://files.catbox.moe/70fnlf.jpg",
"https://files.catbox.moe/i8r1dm.jpg",
"https://files.catbox.moe/5u11yx.jpg"
        ]
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
def make_poster(image_url, name1, name2, title, percentage):
    try:
        # Try to download background image
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        bg = Image.open(io.BytesIO(response.content)).convert("RGB")
    except Exception as e:
        print(f"[FLAMES] Image download failed: {e}")
        # Use solid color fallback background
        bg = Image.new("RGB", (900, 600), (255, 192, 203))

    bg = bg.resize((900, 600)).filter(ImageFilter.GaussianBlur(4))
    stat = ImageStat.Stat(bg)
    brightness = sum(stat.mean[:3]) / 3
    text_color = "black" if brightness > 130 else "white"

    draw = ImageDraw.Draw(bg)
    try:
        font_title = ImageFont.truetype("VIPMUSIC/assets/DejaVuSans-Bold.ttf", 60)
        font_text = ImageFont.truetype("VIPMUSIC/assets/DejaVuSans.ttf", 45)
        font_small = ImageFont.truetype("VIPMUSIC/assets/DejaVuSans.ttf", 35)
    except:
        font_title = font_text = font_small = ImageFont.load_default()

    def draw_centered_text(y, text, font):
        w, h = draw.textsize(text, font=font)
        draw.text(((900 - w) / 2, y), text, fill=text_color, font=font)

    draw_centered_text(40, "𝑭 𖹭 𝑳 𖹭 𝑨 𖹭 𝑴 𖹭 𝑬 𖹭 𝑺", font_title)
    draw_centered_text(170, f"ᰔᩚ {name1.title()} ❤️ {name2.title()} ᰔᩚ", font_text)
    draw_centered_text(270, f"✰ Result: {title}", font_text)
    draw_centered_text(360, f"⋆.𐙚 ̊ Compatibility: {percentage}%", font_small)
    draw_centered_text(530, "˙⋆✮ мᴀᴅᴇ ᴡɪᴛʜ ❤️ 𝐇в-𝐅ᴀᴍ ✮⋆˙", font_small)

    bio = io.BytesIO()
    bio.name = "ANNIEMUSIC/assets/annie/ANNIECP.png" #"flames_result.jpg"   
    bg.save(bio, "JPEG")
    bio.seek(0)
    return bio


# --- EMOJI BAR FUNCTION ---
def emoji_bar(percent):
    full = int(percent / 20)
    return "✩" * full + "★" * (5 - full)


# --- /FLAMES COMMAND ---
@app.on_message(filters.command("flames"))
async def flames_command(client, message):
    try:
        args = message.text.split(None, 2)
        if len(args) < 3:
            await message.reply_text("❌ Usage: `/flames Name1 Name2`", quote=True)
            return

        name1, name2 = args[1], args[2]
        result_letter = flames_result(name1, name2)
        result = RESULTS[result_letter]

        love = random.randint(60, 100) if result_letter in "LAM" else random.randint(10, 70)
        emotion = random.randint(60, 100)
        fun = random.randint(50, 100)
        communication = random.randint(50, 100)
        trust = random.randint(60, 100)

        image_url = random.choice(result["images"])
        poster = make_poster(image_url, name1, name2, result["title"], love)

        caption = (
            f"{result['title']}\n\n"
            f"👩‍❤️‍👨 **{name1.title()} × {name2.title()}**\n\n"
            f"💞 Compatibility: **{love}%** {emoji_bar(love)}\n"
            f"💓 Emotional Bond: **{emotion}%** {emoji_bar(emotion)}\n"
            f"😄 Fun Level: **{fun}%** {emoji_bar(fun)}\n"
            f"💬 Communication: **{communication}%** {emoji_bar(communication)}\n"
            f"🤝 Trust: **{trust}%** {emoji_bar(trust)}\n\n"
            f"📝 {result['desc']}"
        )

        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔁 Try Again", callback_data="flames_retry"),
                InlineKeyboardButton("💌 Share Result", switch_inline_query="flames love test"),
            ],
            [
                InlineKeyboardButton("🎭 View All Results", callback_data="flames_list")
            ]
        ])

        await message.reply_photo(photo=poster, caption=caption, reply_markup=buttons)

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}")


# --- /MATCH COMMAND ---
@app.on_message(filters.command("match"))
async def match_command(client, message):
    try:
        if message.chat.type not in (ChatType.SUPERGROUP, ChatType.GROUP, "supergroup", "group"):
            await message.reply_text("❌ This command only works in groups!", quote=True)
            return

        user = message.from_user
        members = []
        async for member in client.get_chat_members(message.chat.id):
            if not member.user.is_bot and member.user.id != user.id:
                members.append(member.user)
            if len(members) >= 50:
                break

        if len(members) < 3:
            await message.reply_text("⚠️ Not enough members in this group to match!", quote=True)
            return

        selected = random.sample(members, 3)

        text = f"🎯 **Top 3 Matches for [{user.first_name}](tg://user?id={user.id})** 💘\n\n"
        for idx, member in enumerate(selected, start=1):
            name = member.first_name or "Unknown"
            uid = member.id
            tag = f"[{name}](tg://user?id={uid})"
            result_letter = random.choice(list(RESULTS.keys()))
            result = RESULTS[result_letter]
            percent = random.randint(50, 100)

            alert = "💞 **Perfect Couple Alert!** 💞" if percent >= 85 and result_letter in ["L", "S", "M"] else ""

            text += (
                f"{idx}. {tag} → {result['title']} ({percent}%) {emoji_bar(percent)}\n"
                f"📝 {result['desc']}\n{alert}\n\n"
            )

        all_images = [img for res in RESULTS.values() for img in res["images"]]
        image_url = random.choice(all_images)

        await message.reply_photo(
            photo=image_url,
            caption=text,
            #parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Try Again", callback_data="match_retry")]
            ])
        )

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}")


# --- HANDLE CALLBACK BUTTONS ---
@Client.on_callback_query()
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
        elif cq.data == "match_retry":
            await cq.message.reply_text("🎯 Type `/match` again to get new random matches!")
        await cq.answer()
    except Exception as e:
        await cq.message.reply_text(f"⚠️ Callback Error: {e}")
