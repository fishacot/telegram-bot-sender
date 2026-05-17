from __future__ import annotations

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup

logger = logging.getLogger(__name__)


async def send_screen(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None = None,
    *,
    edit: bool = False,
) -> Message:
    """Отправить или обновить экран; при edit игнорирует «message is not modified»."""
    if edit:
        try:
            if reply_markup is not None:
                await message.edit_text(text, reply_markup=reply_markup)
            else:
                await message.edit_text(text)
            return message
        except TelegramBadRequest as error:
            if "message is not modified" in str(error).lower():
                return message
            logger.debug("edit_text failed: %s", error)
    return await message.answer(text, reply_markup=reply_markup)
