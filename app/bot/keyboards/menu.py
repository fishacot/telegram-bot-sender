from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.bot.keyboards.builders import (
    section_accounts_keyboard,
    section_chats_keyboard,
    section_proxy_keyboard,
    section_templates_keyboard,
)

# --- Reply keyboard (главное меню, mobile-first: 2 кнопки в ряд) ---
BTN_CAMPAIGN_NEW = "📤 Новая рассылка"
BTN_CAMPAIGNS = "📋 Мои рассылки"
BTN_ACCOUNTS = "👤 Аккаунты"
BTN_CHATS = "💬 Чаты"
BTN_TEMPLATES = "📝 Шаблоны"
BTN_STATUS = "📊 Статус"
BTN_AGENT = "🤖 Агент"
BTN_HELP = "❓ Помощь"
BTN_HOME = "🏠 Меню"
BTN_CANCEL = "✖️ Отмена"

MAIN_MENU_BUTTONS = {
    BTN_CAMPAIGN_NEW,
    BTN_CAMPAIGNS,
    BTN_ACCOUNTS,
    BTN_CHATS,
    BTN_TEMPLATES,
    BTN_STATUS,
    BTN_AGENT,
    BTN_HELP,
    BTN_HOME,
    BTN_CANCEL,
}


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CAMPAIGN_NEW), KeyboardButton(text=BTN_CAMPAIGNS)],
            [KeyboardButton(text=BTN_ACCOUNTS), KeyboardButton(text=BTN_CHATS)],
            [KeyboardButton(text=BTN_TEMPLATES), KeyboardButton(text=BTN_STATUS)],
            [KeyboardButton(text=BTN_AGENT), KeyboardButton(text=BTN_HELP)],
            [KeyboardButton(text=BTN_HOME)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def cancel_row_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL), KeyboardButton(text=BTN_HOME)]],
        resize_keyboard=True,
    )


__all__ = [
    "BTN_ACCOUNTS",
    "BTN_CAMPAIGN_NEW",
    "BTN_CAMPAIGNS",
    "BTN_CANCEL",
    "BTN_CHATS",
    "BTN_HELP",
    "BTN_HOME",
    "BTN_AGENT",
    "BTN_STATUS",
    "BTN_TEMPLATES",
    "MAIN_MENU_BUTTONS",
    "cancel_row_keyboard",
    "main_menu_keyboard",
    "section_accounts_keyboard",
    "section_chats_keyboard",
    "section_proxy_keyboard",
    "section_templates_keyboard",
]
