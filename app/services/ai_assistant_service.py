from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.value_objects import AiMode
from app.infrastructure.ai_provider.base import AiProvider
from app.infrastructure.db.models import AiRecommendation


class AiAssistantService:
    def __init__(self, session: AsyncSession, provider: AiProvider, mode: AiMode) -> None:
        self.session = session
        self.provider = provider
        self.mode = mode

    async def preflight_assistant(self, campaign_id: int, context: dict) -> dict:
        response = await self.provider.recommend("analyze campaign preflight", context)
        await self._save(campaign_id, "preflight", response)
        return response

    async def template_assistant(self, campaign_id: int | None, context: dict) -> dict:
        response = await self.provider.recommend("improve safe readability", context)
        await self._save(campaign_id, "template", response)
        return response

    async def runtime_watcher(self, campaign_id: int, context: dict) -> dict:
        response = await self.provider.recommend("runtime anomaly check", context)
        await self._save(campaign_id, "runtime", response)
        return response

    async def report_analyst(self, campaign_id: int, context: dict) -> dict:
        response = await self.provider.recommend("analyze report and suggest safety improvements", context)
        await self._save(campaign_id, "report", response)
        return response

    async def apply_safe_suggestions(self, recommendations: dict, user_opt_in: bool) -> dict:
        if self.mode != AiMode.AUTO_APPLY_SAFE or not user_opt_in:
            return {}
        safe_patch = {}
        for item in recommendations.get("suggestions", []):
            field = item.get("field")
            value = item.get("value")
            if field in {"min_delay_msg", "max_delay_msg", "max_per_acc_hour"}:
                safe_patch[field] = value
        return safe_patch

    async def _save(self, campaign_id: int | None, rec_type: str, payload: dict) -> None:
        row = AiRecommendation(
            campaign_id=campaign_id,
            type=rec_type,
            payload=payload,
            created_at=datetime.utcnow(),
            accepted_by_user=False,
        )
        self.session.add(row)
        await self.session.commit()
