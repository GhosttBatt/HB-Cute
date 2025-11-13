from pyrogram.types import InlineKeyboardButton
import config
from VIPMUSIC import app


def start_panel(_):
    buttons = [
        [
            InlineKeyboardButton(text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true"),
        ],
        [
            InlineKeyboardButton(text=_["S_B_12"], callback_data="settings_back_helper"),
            InlineKeyboardButton(text=_["S_B_13"], callback_data="settings_helper"),
        ],
        [
            InlineKeyboardButton(text=_["CHT"], url=config.SUPPORT_CHAT),
            InlineKeyboardButton(text=_["DEV"], url=f"https://t.me/{config.OWNER_USERNAME}"),
            InlineKeyboardButton(text=_["NET"], url=config.SUPPORT_CHANNEL),
        ],
    ]
    return buttons


def private_panel(_):
    buttons = [
        [
            InlineKeyboardButton(text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true",)
        ],
        [
            InlineKeyboardButton(text=_["CHT"], url=config.SUPPORT_CHAT),
            InlineKeyboardButton(text=_["DEV"], url=f"https://t.me/{config.OWNER_USERNAME}"),
            InlineKeyboardButton(text=_["NET"], url=config.SUPPORT_CHANNEL),
        ],
        [
            InlineKeyboardButton(text=_["S_B_4"], callback_data="settings_back_helper")
        ],
    ]
    return buttons
