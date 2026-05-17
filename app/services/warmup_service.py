from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Account, WarmupRun
from app.infrastructure.telethon_clients.sender_adapter import TelethonSenderAdapter
from app.services.compliance_guard import ComplianceGuard

logger = logging.getLogger(__name__)

WARMUP_LIMITS = {
    "soft": 3,
    "normal": 5,
    "custom": 8,
}


class WarmupService:
    def __init__(
        self,
        session: AsyncSession,
        guard: ComplianceGuard,
        telethon_adapter: TelethonSenderAdapter,
    ) -> None:
        self.session = session
        self.guard = guard
        self.telethon_adapter = telethon_adapter

    async def start(self, account_id: int, mode: str) -> WarmupRun:
        if mode not in WARMUP_LIMITS:
            raise ValueError("Warmup mode must be one of: soft, normal, custom.")
        run = WarmupRun(
            account_id=account_id,
            mode=mode,
            status="running",
            started_at=datetime.utcnow(),
        )
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        asyncio.create_task(self._run_background(run.id))
        return run

    async def _run_background(self, run_id: int) -> None:
        from app.container import get_container
        from app.infrastructure.db.session import SessionLocal

        async with SessionLocal() as session:
            container = get_container()
            service = WarmupService(session, container.guard, container.telethon_adapter)
            run = await session.get(WarmupRun, run_id)
            if not run:
                return
            account = await session.get(Account, run.account_id)
            if not account:
                run.status = "failed"
                run.ended_at = datetime.utcnow()
                await session.commit()
                return
            try:
                limit = WARMUP_LIMITS[run.mode]
                logs = await service.telethon_adapter.warmup_safe_activity(account, max_dialogs=limit)
                run.status = "completed"
                logger.info("Warmup run %s completed: %s", run_id, logs)
            except Exception as error:  # noqa: BLE001
                run.status = "failed"
                logger.warning("Warmup run %s failed: %s", run_id, error)
            run.ended_at = datetime.utcnow()
            await session.commit()

    async def stop(self, run_id: int) -> None:
        run = await self.session.get(WarmupRun, run_id)
        if not run:
            return
        run.status = "stopped"
        run.ended_at = datetime.utcnow()
        await self.session.commit()
