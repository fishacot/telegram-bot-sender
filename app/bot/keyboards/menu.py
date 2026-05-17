from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

# --- Reply keyboard (главное меню) ---
BTN_CAMPAIGN_NEW = "📤 Новая рассылка"
BTN_CAMPAIGNS = "📋 Мои рассылки"
BTN_ACCOUNTS = "👤 Аккаунты"
BTN_CHATS = "💬 Чаты"
BTN_TEMPLATES = "📝 Шаблоны"
BTN_HELP = "❓ Помощь"
BTN_HOME = "🏠 Меню"
BTN_CANCEL = "✖️ Отмена"

MAIN_MENU_BUTTONS = {
    BTN_CAMPAIGN_NEW,
    BTN_CAMPAIGNS,
    BTN_ACCOUNTS,
    BTN_CHATS,
    BTN_TEMPLATES,
    BTN_HELP,
    BTN_HOME,
    BTN_CANCEL,
}


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CAMPAIGN_NEW), KeyboardButton(text=BTN_CAMPAIGNS)],
            [KeyboardButton(text=BTN_ACCOUNTS), KeyboardButton(text=BTN_CHATS)],
            [KeyboardButton(text=BTN_TEMPLATES), KeyboardButton(text=BTN_HELP)],
            [KeyboardButton(text=BTN_HOME)],
        ],
        resize_keyboard=True,
    )


def cancel_row_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL), KeyboardButton(text=BTN_HOME)]],
        resize_keyboard=True,
    )


def back_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="nav:back")]]
    )


def section_accounts_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Загрузить .session", callback_data="acc:upload")],
            [InlineKeyboardButton(text="🔄 Обновить список", callback_data="acc:list")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:home")],
        ]
    )


def section_chats_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить чат", callback_data="cht:add")],
            [InlineKeyboardButton(text="🔄 Обновить список", callback_data="cht:list")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:home")],
        ]
    )


def section_templates_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Новый шаблон", callback_data="tpl:add")],
            [InlineKeyboardButton(text="🔄 Обновить список", callback_data="tpl:list")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:home")],
        ]
    )
