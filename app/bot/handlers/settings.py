from aiogram import Router
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.keyboards.builders import nav_row
from app.config import get_settings

router = Router()


def build_settings_text() -> str:
    settings = get_settings()
    proxy = "включён" if settings.telegram_proxy else "выкл."
    return (
        "⚙️ <b>Настройки сервера</b>\n\n"
        f"База: <code>{_short_db(settings.database_url)}</code>\n"
        f"Сессии: <code>{settings.sessions_dir}</code>\n"
        f"AI: <code>{settings.ai_provider}</code> · режим <code>{settings.ai_mode}</code>\n"
        f"Агент: {'вкл' if settings.ai_agent_enabled else 'выкл'}\n"
        f"Прокси бота: {proxy}\n"
        f"Админов: <b>{len(settings.admin_id_list)}</b>"
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆔 Мой Telegram ID", callback_data="tool:myid")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="nav:home")],
        ]
    )


def _short_db(url: str) -> str:
    if len(url) > 48:
        return url[:20] + "…" + url[-15:]
    return url


async def send_settings_screen(message: Message, *, edit: bool = False) -> None:
    text = build_settings_text()
    markup = settings_keyboard()
    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)
