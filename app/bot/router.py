from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import ALL_ROUTERS
from app.bot.middlewares.admin_guard import AdminGuardMiddleware
from app.config import get_settings


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    settings = get_settings()
    dispatcher.message.middleware(AdminGuardMiddleware(settings.admin_id_list))
    for item in ALL_ROUTERS:
        dispatcher.include_router(item)
    return dispatcher
