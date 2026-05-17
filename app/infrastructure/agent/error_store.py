from __future__ import annotations

import asyncio
import traceback
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import AgentErrorEvent
from app.infrastructure.db.session import SessionLocal


@dataclass(slots=True)
class ErrorRecord:
    source: str
    level: str
    message: str
    traceback: str | None
    context: dict[str, Any]
    created_at: datetime


class AgentErrorStore:
    """Кольцевой буфер + сохранение в БД для AI-агента."""

    def __init__(self, *, memory_limit: int = 100) -> None:
        self._memory: deque[ErrorRecord] = deque(maxlen=memory_limit)
        self._lock = asyncio.Lock()
        self._notify_callback = None

    def set_notify_callback(self, callback) -> None:
        self._notify_callback = callback

    async def record(
        self,
        *,
        source: str,
        level: str,
        message: str,
        exc: BaseException | None = None,
        context: dict[str, Any] | None = None,
        persist: bool = True,
    ) -> None:
        tb = None
        if exc is not None:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        record = ErrorRecord(
            source=source,
            level=level,
            message=message[:4000],
            traceback=tb,
            context=context or {},
            created_at=datetime.utcnow(),
        )
        async with self._lock:
            self._memory.appendleft(record)
        if persist:
            await self._persist(record)
        if self._notify_callback and level.upper() in {"ERROR", "CRITICAL"}:
            await self._notify_callback(record)

    async def _persist(self, record: ErrorRecord) -> None:
        try:
            async with SessionLocal() as session:
                row = AgentErrorEvent(
                    source=record.source,
                    level=record.level,
                    message=record.message,
                    traceback=record.traceback,
                    context_json=record.context,
                    analyzed=False,
                    created_at=record.created_at,
                )
                session.add(row)
                await session.commit()
        except Exception:  # noqa: BLE001
            pass

    def memory_snapshot(self, limit: int = 20) -> list[dict]:
        items = list(self._memory)[:limit]
        return [
            {
                "source": item.source,
                "level": item.level,
                "message": item.message,
                "traceback": (item.traceback or "")[:800],
                "context": item.context,
                "at": item.created_at.isoformat(),
            }
            for item in items
        ]


error_store = AgentErrorStore()
