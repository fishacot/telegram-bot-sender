from __future__ import annotations

from dataclasses import dataclass

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.infrastructure.telethon_clients.factory import TelethonClientFactory
from app.infrastructure.telethon_clients.sender_adapter import TelethonSenderAdapter
from app.services.compliance_guard import ComplianceGuard
from app.services.scheduler_service import CampaignSchedulerService
from app.services.sender_service import SenderService


@dataclass
class AppContainer:
    guard: ComplianceGuard
    sender_service: SenderService
    telethon_adapter: TelethonSenderAdapter
    scheduler: AsyncIOScheduler
    campaign_scheduler: CampaignSchedulerService


_container: AppContainer | None = None


def get_container() -> AppContainer:
    global _container
    if _container is None:
        settings = get_settings()
        guard = ComplianceGuard()
        factory = TelethonClientFactory(
            sessions_dir=settings.sessions_dir,
            api_id=settings.telegram_api_id,
            api_hash=settings.telegram_api_hash,
            proxy_url=settings.telegram_proxy,
        )
        telethon_adapter = TelethonSenderAdapter(factory)
        sender_service = SenderService(guard=guard, telethon_adapter=telethon_adapter)
        scheduler = AsyncIOScheduler()
        campaign_scheduler = CampaignSchedulerService(scheduler)
        _container = AppContainer(
            guard=guard,
            sender_service=sender_service,
            telethon_adapter=telethon_adapter,
            scheduler=scheduler,
            campaign_scheduler=campaign_scheduler,
        )
    return _container


async def startup() -> AppContainer:
    container = get_container()
    if not container.scheduler.running:
        container.scheduler.start()
    await container.campaign_scheduler.restore_pending_schedules()
    await container.sender_service.start_background_worker()
    return container


async def shutdown() -> None:
    container = get_container()
    if container.scheduler.running:
        container.scheduler.shutdown(wait=False)
    await container.sender_service.stop_background_worker()
    await container.telethon_adapter.disconnect_all()
