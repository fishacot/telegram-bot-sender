from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select

from app.infrastructure.db.models import Campaign, CampaignSettings
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.campaign_repository import CampaignRepository
from app.services.campaign_service import CampaignService

logger = logging.getLogger(__name__)


class CampaignSchedulerService:
    def __init__(self, scheduler: AsyncIOScheduler) -> None:
        self.scheduler = scheduler

    def schedule_campaign_run(self, campaign_id: int, run_at: datetime) -> None:
        self.scheduler.add_job(
            self._run_campaign_job,
            trigger=DateTrigger(run_date=run_at),
            id=f"campaign_run_{campaign_id}",
            replace_existing=True,
            kwargs={"campaign_id": campaign_id},
        )
        logger.info("Scheduled campaign %s at %s", campaign_id, run_at.isoformat())

    async def restore_pending_schedules(self) -> int:
        now = datetime.utcnow()
        restored = 0
        async with SessionLocal() as session:
            result = await session.execute(
                select(Campaign, CampaignSettings)
                .join(CampaignSettings, Campaign.id == CampaignSettings.campaign_id)
                .where(
                    Campaign.mode == "scheduled_once",
                    Campaign.status == "queued",
                    CampaignSettings.scheduled_at.is_not(None),
                    CampaignSettings.scheduled_at > now,
                )
            )
            for campaign, settings in result.all():
                self.schedule_campaign_run(campaign.id, settings.scheduled_at)
                restored += 1
        if restored:
            logger.info("Restored %s scheduled campaign(s)", restored)
        return restored

    async def _run_campaign_job(self, campaign_id: int) -> None:
        from app.container import get_container

        container = get_container()
        async with SessionLocal() as session:
            service = CampaignService(session, container.guard, container.sender_service)
            await service.run_campaign(campaign_id, confirmed=True)
            repo = CampaignRepository(session)
            campaign = await repo.get_campaign(campaign_id)
            if campaign and campaign.status == "queued":
                await repo.update_campaign_status(campaign_id, "running")
