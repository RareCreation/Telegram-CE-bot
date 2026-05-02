from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.constants import PHOTO

def get_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🫂 Add Friend", callback_data="add_friend")],
            [InlineKeyboardButton(text="⚠️ Ban DOTA2", callback_data="ban_dota")],
            [InlineKeyboardButton(text="🟢 Check-online", callback_data="online_status")],
            [InlineKeyboardButton(text="📱 QR Friend Page", callback_data="qr_friend_page")],
            [InlineKeyboardButton(text="📨 Friend Page", callback_data="friend_page")],
        ]
    )

def get_back_button(callback_data: str = "back_to_main"):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)]]
    )

def get_add_friend_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗒 AF Classic", callback_data="af_classic")],
            [InlineKeyboardButton(text="⚡️ AF Quick", callback_data="af_quick")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )

def get_ban_dota_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗒 Default ban", callback_data="default_ban")],
            [InlineKeyboardButton(text="💅 Ban with nails", callback_data="ban_with_nails")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )

def get_friend_page_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📨 Friend Page", callback_data="friend_page_image")],
            [InlineKeyboardButton(text="🚫 Friend Page not found", callback_data="friend_not_found")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )