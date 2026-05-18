import logging
import sys

from pythonjsonlogger import jsonlogger

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if settings.log_json:
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(campaign_id)s %(account_id)s %(chat_id)s"
        )
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
        )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Render health-check каждые 5 с — не засорять логи
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.server").setLevel(logging.WARNING)

    if settings.ai_agent_enabled:
        from app.infrastructure.logging.agent_handler import AgentErrorLogHandler

        agent_handler = AgentErrorLogHandler()
        agent_handler.setFormatter(formatter)
        root.addHandler(agent_handler)
