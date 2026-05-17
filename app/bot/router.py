from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import ALL_ROUTERS
from app.bot.middlewares.admin_guard import AdminGuardMiddleware
from app.bot.middlewares.agent_errors import AgentErrorMiddleware
from app.bot.middlewares.slash_redirect import SlashCommandRedirectMiddleware
from app.config import get_settings


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    settings = get_settings()
    dispatcher.message.middleware(AdminGuardMiddleware(settings.admin_id_list))
    dispatcher.callback_query.middleware(AdminGuardMiddleware(settings.admin_id_list))
    dispatcher.message.middleware(SlashCommandRedirectMiddleware())
    if settings.ai_agent_enabled:
        dispatcher.message.middleware(AgentErrorMiddleware())
        dispatcher.callback_query.middleware(AgentErrorMiddleware())
    for item in ALL_ROUTERS:
        dispatcher.include_router(item)
    return dispatcher
