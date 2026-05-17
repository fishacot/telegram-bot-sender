from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.config import get_settings
from app.infrastructure.agent.error_store import error_store

logger = logging.getLogger(__name__)


class AgentErrorMiddleware(BaseMiddleware):
    """Ловит падения хендлеров и передаёт в AI-агент."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as error:
            user = data.get("event_from_user")
            await error_store.record(
                source="bot:handler",
                level="ERROR",
                message=str(error),
                exc=error,
                context={
                    "user_id": user.id if user else None,
                    "handler": getattr(handler, "__name__", "unknown"),
                },
            )
            settings = get_settings()
            if settings.agent_notify_on_error and user:
                bot = data.get("bot")
                if bot and user.id in settings.admin_id_list:
                    try:
                        await bot.send_message(
                            user.id,
                            f"⚠️ <b>Ошибка бота</b>\n<code>{error}</code>\n\n"
                            "🤖 <b>Агент</b> → «Разбор ошибок»",
                        )
                    except Exception:  # noqa: BLE001
                        pass
            raise
