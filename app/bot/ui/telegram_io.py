from __future__ import annotations

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message, ReplyKeyboardMarkup

_ReplyMarkup = InlineKeyboardMarkup | ReplyKeyboardMarkup | None

logger = logging.getLogger(__name__)


async def send_screen(
    message: Message,
    text: str,
    reply_markup: _ReplyMarkup = None,
    *,
    edit: bool = False,
) -> Message:
    """Отправить или обновить экран; reply-клавиатуру нельзя передать в edit_text."""
    if edit and isinstance(reply_markup, ReplyKeyboardMarkup):
        edit = False
    if edit:
        try:
            if isinstance(reply_markup, InlineKeyboardMarkup):
                await message.edit_text(text, reply_markup=reply_markup)
            else:
                await message.edit_text(text)
            return message
        except TelegramBadRequest as error:
            if "message is not modified" in str(error).lower():
                return message
            logger.debug("edit_text failed: %s", error)
    return await message.answer(text, reply_markup=reply_markup)
