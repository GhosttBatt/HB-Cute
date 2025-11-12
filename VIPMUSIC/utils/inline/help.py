from typing import Union

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from VIPMUSIC import app

def first_page(_):
	controll_button = [
		InlineKeyboardButton(text="💕 𝐌𖾔𖽡𖽪 🦋", callback_data=f"settingsback_helper"),
		InlineKeyboardButton(text="💕 𝐍𖾔𝅃𖾓 🦋", callback_data=f"GhostPage1")
	]
	first_page_menu = InlineKeyboardMarkup(
		[
			[
				InlineKeyboardButton(text=_["H_B_1"], callback_data="help_callback hb1"),
				InlineKeyboardButton(text=_["H_B_2"], callback_data="help_callback hb2"),
				InlineKeyboardButton(text=_["H_B_3"], callback_data="help_callback hb3")
			],
			[
				InlineKeyboardButton(text=_["H_B_4"], callback_data="help_callback hb4"),
				InlineKeyboardButton(text=_["H_B_5"], callback_data="help_callback hb5"),
				InlineKeyboardButton(text=_["H_B_6"], callback_data="help_callback hb6")
			],
			[
				InlineKeyboardButton(text=_["H_B_7"], callback_data="help_callback hb7"),
				InlineKeyboardButton(text=_["H_B_8"], callback_data="help_callback hb8")
			],
            [
				InlineKeyboardButton(text=_["H_B_9"], callback_data="help_callback hb9"),
				InlineKeyboardButton(text=_["H_B_10"], callback_data="help_callback hb10")
			],
            [
				InlineKeyboardButton(text=_["H_B_11"], callback_data="help_callback hb11")
			],
			controll_button,
		]
	)
	return first_page_menu


def second_page(_):
	controll_button = [InlineKeyboardButton(text="💕 𝐁꘍𖽝ᴋ 🦋", callback_data=f"settings_back_helper"),
					   InlineKeyboardButton(text="💕 𝐍𖾔𝅃𖾓 🦋", callback_data=f"GhostPage2")
					  ]
	second_page_menu = InlineKeyboardMarkup(
		[
			[
				InlineKeyboardButton(text=_["H_B_12"], callback_data="help_callback hb12"),
				InlineKeyboardButton(text=_["H_B_13"], callback_data="help_callback hb13"),
				InlineKeyboardButton(text=_["H_B_14"], callback_data="help_callback hb14")
			],
			[
				InlineKeyboardButton(text=_["H_B_15"], callback_data="help_callback hb15"),
				InlineKeyboardButton(text=_["H_B_16"], callback_data="help_callback hb16"),
				InlineKeyboardButton(text=_["H_B_17"], callback_data="help_callback hb17")
			],
			[
				InlineKeyboardButton(text=_["H_B_18"], callback_data="help_callback hb18"),
				InlineKeyboardButton(text=_["H_B_19"], callback_data="help_callback hb19")
			],
            [
				InlineKeyboardButton(text=_["H_B_20"], callback_data="help_callback hb20"),
				InlineKeyboardButton(text=_["H_B_21"], callback_data="help_callback hb21")
			],
            [
				InlineKeyboardButton(text=_["H_B_22"], callback_data="help_callback hb22")
			],
			controll_button,
		]
	)
	return second_page_menu


def third_page(_):
	controll_button = [InlineKeyboardButton(text="💕 𝐁꘍𖽝ᴋ 🦋", callback_data=f"settings_back_helper")]
	third_page_menu = InlineKeyboardMarkup(
		[
			[
				InlineKeyboardButton(text=_["H_B_23"], callback_data="help_callback hb23"),
				InlineKeyboardButton(text=_["H_B_24"], callback_data="help_callback hb24"),
				InlineKeyboardButton(text=_["H_B_25"], callback_data="help_callback hb25")
			],
			[
				InlineKeyboardButton(text=_["H_B_26"], callback_data="help_callback hb26"),
				InlineKeyboardButton(text=_["H_B_27"], callback_data="help_callback hb27"),
				InlineKeyboardButton(text=_["H_B_28"], callback_data="help_callback hb28")
			],
			[
				InlineKeyboardButton(text=_["H_B_29"], callback_data="help_callback hb29"),
				InlineKeyboardButton(text=_["H_B_30"], callback_data="help_callback hb30")
			],
            [
				InlineKeyboardButton(text=_["H_B_31"], callback_data="help_callback hb31"),
				InlineKeyboardButton(text=_["H_B_32"], callback_data="help_callback hb32")
			],
            [
				InlineKeyboardButton(text=_["H_B_33"], callback_data="help_callback hb33")
			],
			controll_button,
		]
	)
	return third_page_menu
    

def help_pannel(_, START: Union[bool, int] = None):
    first = [InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data=f"close")]
    second = [
        InlineKeyboardButton(text=_["BACK_BUTTON"],callback_data=f"settingsback_helper"),
        InlineKeyboardButton(text=_["CLOSEMENU_BUTTON"], callback_data=f"close"),
    ]
    mark = second if START else first
    upl = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text="⌯ 𝐀𖽴𖾕𖽹𖽡 ⌯",callback_data="help_callback hb1"),
                InlineKeyboardButton(text="⌯ 𝐀𖽪𖾓𖽻 ⌯",callback_data="help_callback hb2"),
                InlineKeyboardButton(text="💕 𝐁꘍𖽝ᴋ 🦋",callback_data="help_callback hb3"),
            ],
            [
                InlineKeyboardButton(text="⌯ 𝐆𖽝꘍𖾗𖾓 ⌯",callback_data="help_callback hb4"),
                InlineKeyboardButton(text="⌯ 𝐆 𖽜꘍𖽡⌯ ",callback_data="help_callback hb12"),
                InlineKeyboardButton(text="⌯ 𝐋ʏ𖽷𖽹𖽝𖾗 ⌯",callback_data="help_callback hb5"),
            ],
            [
                InlineKeyboardButton(text="⌯ 𝐏𖾘꘍ʏ𖾘𖽹𖾗𖾓 ⌯",callback_data="help_callback hb6"),
                InlineKeyboardButton(text="⌯ 𝐕𖽙𖽹𖽝𖽞𝐂𖽻꘍𖾓 ⌯",callback_data="help_callback hb10"),
            ],
            [
           
                InlineKeyboardButton(text="⌯ 𝐏𖾘꘍ʏ ⌯",callback_data="help_callback hb8"),
                InlineKeyboardButton(text="⌯ 𝐒𖽪𖽴𖽙 ⌯",callback_data="help_callback hb9"),
            ],
            [
                InlineKeyboardButton(text="💕 𝐒𖾓꘍𖽷𖾓 🦋",callback_data="help_callback hb11"),
            ],
            mark,
        ]
    )
    return upl


def help_back_markup(_):
    upl = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(text=_["BACK_BUTTON"],callback_data=f"settings_back_helper"),
                InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data=f"close"),
            ]
        ]
    )
    return upl


def private_help_panel(_):
    buttons = [
        [
            InlineKeyboardButton(text="💕 𝐇𖾔𖾘𖽳 🦋",callback_data="settings_back_helper"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)

