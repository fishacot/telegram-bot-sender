from __future__ import annotations

import asyncio
import logging
from logging import LogRecord


class AgentErrorLogHandler(logging.Handler):
    """Пишет ERROR+ в хранилище агента (изолированно от внешних систем)."""

    def __init__(self, level: int = logging.ERROR) -> None:
        super().__init__(level=level)

    def emit(self, record: LogRecord) -> None:
        try:
            from app.infrastructure.agent.error_store import error_store

            message = self.format(record)
            context = {
                "logger": record.name,
                "pathname": record.pathname,
                "lineno": record.lineno,
            }
            if hasattr(record, "campaign_id"):
                context["campaign_id"] = record.campaign_id
            if hasattr(record, "account_id"):
                context["account_id"] = record.account_id

            exc = record.exc_info[1] if record.exc_info else None
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    error_store.record(
                        source=f"log:{record.name}",
                        level=record.levelname,
                        message=message,
                        exc=exc,
                        context=context,
                    )
                )
            except RuntimeError:
                pass
        except Exception:  # noqa: BLE001
            pass
