import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.router import build_dispatcher
from app.config import get_settings
from app.container import get_container, shutdown, startup
from app.infrastructure.bot_notifier import BotNotifier
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.agent.error_store import error_store
from app.infrastructure.logging.logger import configure_logging
from app.infrastructure.repositories.campaign_repository import CampaignRepository
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)


async def _on_campaign_complete(campaign_id: int) -> None:
    container = get_container()
    settings = get_settings()
    async with SessionLocal() as session:
        repo = CampaignRepository(session)
        stopped = campaign_id in container.sender_service.stopped_campaigns
        status = "failed" if stopped else "completed"
        await repo.update_campaign_status(campaign_id, status)
        campaign = await repo.get_campaign(campaign_id)
        summary = await ReportService(session).build_campaign_summary(campaign_id)

    if not campaign:
        return

    title = "⏹ Остановлена" if stopped else "✅ Завершена"
    text = (
        f"{title}: рассылка <b>#{campaign_id}</b> «{campaign.name}»\n"
        f"✅ Отправлено: {summary.get('sent_ok', 0)}\n"
        f"❌ Ошибки: {summary.get('failed', 0)}\n"
        f"⏭ Пропущено: {summary.get('skipped', 0)}\n\n"
        "📋 <b>Мои рассылки</b> — подробности"
    )
    for admin_id in settings.admin_id_list:
        await BotNotifier.send(admin_id, text)


async def _start_health_server() -> web.AppRunner | None:
    """Render and similar hosts require HTTP on PORT; Railway does not set PORT."""
    port = os.getenv("PORT")
    if not port:
        return None
    app = web.Application()

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(port)).start()
    logger.info("Health check listening on port %s", port)
    return runner


async def run() -> None:
    settings = get_settings()
    configure_logging()
    health_runner = await _start_health_server()
    container = await startup()
    container.sender_service.set_campaign_complete_handler(_on_campaign_complete)

    bot_kwargs: dict = {
        "token": settings.bot_token,
        "default": DefaultBotProperties(parse_mode=ParseMode.HTML),
    }
    if settings.telegram_proxy:
        try:
            import aiohttp_socks  # noqa: F401
        except ImportError as error:
            raise RuntimeError(
                "TELEGRAM_PROXY is set but aiohttp-socks is not installed. "
                "Run: pip install aiohttp-socks"
            ) from error
        bot_kwargs["proxy"] = settings.telegram_proxy
        logger.info("Using TELEGRAM_PROXY for Bot API connection")
    bot = Bot(**bot_kwargs)
    BotNotifier.register(bot)

    if settings.ai_agent_enabled and settings.agent_notify_on_error:

        async def _agent_error_notify(record) -> None:
            for admin_id in settings.admin_id_list:
                await BotNotifier.send(
                    admin_id,
                    f"⚠️ <b>Ошибка</b> ({record.source})\n"
                    f"<code>{record.message[:350]}</code>\n\n"
                    "🤖 Агент → <b>Разбор ошибок</b>",
                )

        error_store.set_notify_callback(_agent_error_notify)

    dispatcher = build_dispatcher()
    logger.info(
        "Starting bot polling (admins=%s, sessions=%s)",
        len(settings.admin_id_list),
        settings.sessions_dir,
    )
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        await shutdown()
        if health_runner:
            await health_runner.cleanup()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
