from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import get_settings

router = Router()


@router.message(Command("settings"))
async def settings_handler(message: Message) -> None:
    settings = get_settings()
    await message.answer(
        "Current settings:\n"
        f"- ADMIN_IDS: {settings.admin_id_list}\n"
        f"- DATABASE_URL: {settings.database_url}\n"
        f"- SESSIONS_DIR: {settings.sessions_dir}\n"
        f"- AI_MODE: {settings.ai_mode}\n"
        f"- AI_PROVIDER: {settings.ai_provider}\n"
        f"- TELEGRAM_PROXY: {settings.telegram_proxy or 'disabled'}\n"
        f"- FLOODWAIT_BUFFER_SEC: {settings.floodwait_buffer_sec}"
    )
