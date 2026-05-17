from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.policies import RatePolicy
from app.infrastructure.db.models import SendAttempt
from app.services.compliance_guard import ComplianceError


class SendRateLimiter:
    def __init__(self, session: AsyncSession, policy: RatePolicy | None = None) -> None:
        self.session = session
        self.policy = policy or RatePolicy()

    async def assert_allowed(
        self,
        account_id: int,
        chat_id: int,
        settings: dict,
    ) -> None:
        now = datetime.utcnow()
        if not self.policy.is_within_active_hours(settings.get("active_hours", "9-21"), now):
            raise ComplianceError("Outside configured active hours.")

        hour_ago = now - timedelta(hours=1)
        acc_count = await self._count_attempts_since(account_id=account_id, since=hour_ago)
        max_per_acc = int(settings.get("max_per_acc_hour", 20))
        if acc_count >= max_per_acc:
            raise ComplianceError("max_per_acc_hour limit reached.")

        day_ago = now - timedelta(hours=24)
        chat_count = await self._count_attempts_since(chat_id=chat_id, since=day_ago)
        max_per_chat = int(settings.get("max_per_chat_day", 3))
        if chat_count >= max_per_chat:
            raise ComplianceError("max_per_chat_day limit reached.")

    async def _count_attempts_since(
        self,
        since: datetime,
        account_id: int | None = None,
        chat_id: int | None = None,
    ) -> int:
        query = select(func.count(SendAttempt.id)).where(
            SendAttempt.sent_at >= since,
            SendAttempt.status == "sent_ok",
        )
        if account_id is not None:
            query = query.where(SendAttempt.account_id == account_id)
        if chat_id is not None:
            query = query.where(SendAttempt.chat_id == chat_id)
        result = await self.session.execute(query)
        return int(result.scalar_one())
