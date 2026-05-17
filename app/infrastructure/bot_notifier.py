from __future__ import annotations

import logging

from aiogram import Bot

logger = logging.getLogger(__name__)


class BotNotifier:
    _bot: Bot | None = None

    @classmethod
    def register(cls, bot: Bot) -> None:
        cls._bot = bot

    @classmethod
    async def send(cls, user_id: int, text: str) -> None:
        if not cls._bot or not user_id:
            return
        try:
            await cls._bot.send_message(user_id, text[:4096])
        except Exception as error:  # noqa: BLE001
            logger.warning("Bot notify failed for user %s: %s", user_id, error)
