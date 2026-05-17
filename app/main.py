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
from app.infrastructure.logging.logger import configure_logging
from app.infrastructure.repositories.campaign_repository import CampaignRepository

logger = logging.getLogger(__name__)


async def _on_campaign_complete(campaign_id: int) -> None:
    container = get_container()
    async with SessionLocal() as session:
        repo = CampaignRepository(session)
        if campaign_id in container.sender_service.stopped_campaigns:
            await repo.update_campaign_status(campaign_id, "failed")
        else:
            await repo.update_campaign_status(campaign_id, "completed")


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
    dispatcher = build_dispatcher()
    logger.info("Starting bot polling")
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
