from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/accounts"), KeyboardButton(text="/packs")],
            [KeyboardButton(text="/chats"), KeyboardButton(text="/templates")],
            [KeyboardButton(text="/campaign_new"), KeyboardButton(text="/campaigns")],
            [KeyboardButton(text="/warmup"), KeyboardButton(text="/join_open_chats")],
            [KeyboardButton(text="/settings"), KeyboardButton(text="/logs"), KeyboardButton(text="/report")],
        ],
        resize_keyboard=True,
    )
