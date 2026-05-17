from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.bot.keyboards.menu import main_menu_keyboard

# Только служебные команды Telegram; всё остальное — кнопки.
ALLOWED_SLASH_COMMANDS = frozenset({"/start", "/menu", "/help"})


class SlashCommandRedirectMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            text = event.text.strip()
            if text.startswith("/"):
                command = text.split()[0].split("@")[0].lower()
                if command not in ALLOWED_SLASH_COMMANDS:
                    await event.answer(
                        "⌨️ Команды не нужны — всё через <b>кнопки</b> внизу.\n"
                        "Нажмите <b>🏠 Меню</b>.",
                        reply_markup=main_menu_keyboard(),
                    )
                    return None
        return await handler(event, data)
