from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class AdminGuardMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: list[int]) -> None:
        self.admin_ids = set(admin_ids)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id is not None and user_id not in self.admin_ids:
            deny_text = (
                "⛔ <b>Доступ только для администратора</b>\n\n"
                f"Ваш Telegram ID: <code>{user_id}</code>\n"
                "Добавьте его в <code>ADMIN_IDS</code> на Render и перезапустите сервис."
            )
            if isinstance(event, Message):
                await event.answer(deny_text)
            elif isinstance(event, CallbackQuery):
                await event.answer("Нет доступа", show_alert=True)
                if event.message:
                    await event.message.answer(deny_text)
            return None
        return await handler(event, data)
