from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import (
    Campaign,
    CampaignAccount,
    CampaignChat,
    CampaignSettings,
    SendAttempt,
)


class CampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_campaign(self, campaign_id: int) -> Campaign | None:
        return await self.session.get(Campaign, campaign_id)

    async def list_campaign_accounts(self, campaign_id: int) -> list[int]:
        result = await self.session.execute(
            select(CampaignAccount.account_id).where(CampaignAccount.campaign_id == campaign_id)
        )
        return [row[0] for row in result.fetchall()]

    async def list_campaign_chats(self, campaign_id: int) -> list[int]:
        result = await self.session.execute(
            select(CampaignChat.chat_id).where(CampaignChat.campaign_id == campaign_id)
        )
        return [row[0] for row in result.fetchall()]

    async def get_settings(self, campaign_id: int) -> CampaignSettings | None:
        return await self.session.get(CampaignSettings, campaign_id)

    async def add_attempt(self, payload: SendAttempt) -> None:
        self.session.add(payload)
        await self.session.commit()

    async def update_campaign_status(self, campaign_id: int, status: str) -> None:
        campaign = await self.session.get(Campaign, campaign_id)
        if campaign:
            campaign.status = status
            await self.session.commit()

    async def clear_targets(self, campaign_id: int) -> None:
        await self.session.execute(delete(CampaignAccount).where(CampaignAccount.campaign_id == campaign_id))
        await self.session.execute(delete(CampaignChat).where(CampaignChat.campaign_id == campaign_id))
        await self.session.commit()
