from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import AuditEvent


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(self, actor_id: int, action: str, payload: dict[str, Any] | None = None) -> None:
        event = AuditEvent(
            actor_id=actor_id,
            action=action,
            payload_json=payload or {},
            created_at=datetime.utcnow(),
        )
        self.session.add(event)
        await self.session.commit()
