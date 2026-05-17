from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import (
    Campaign,
    CampaignAccount,
    CampaignChat,
    CampaignSettings,
    Chat,
    Template,
)
from app.infrastructure.repositories.account_pack_repository import AccountPackRepository
from app.infrastructure.repositories.campaign_repository import CampaignRepository
from app.services.compliance_guard import ComplianceError, ComplianceGuard
from app.services.sender_service import SendTask, SenderService
from app.services.team_dialogue_service import TeamDialogueService
from app.services.template_service import TemplateService


@dataclass(slots=True)
class PreflightResult:
    allowed_chats: list[int]
    excluded_chats: list[dict]
    warnings: list[str]


class CampaignService:
    @staticmethod
    def pick_account_id(mode: str, account_ids: list[int], chat_index: int) -> int:
        if mode == "rotate":
            return account_ids[chat_index % len(account_ids)]
        return account_ids[0]

    def __init__(
        self,
        session: AsyncSession,
        guard: ComplianceGuard,
        sender_service: SenderService,
    ) -> None:
        self.session = session
        self.guard = guard
        self.sender_service = sender_service
        self.repository = CampaignRepository(session)
        self.pack_repository = AccountPackRepository(session)
        self.template_service = TemplateService(guard)

    async def resolve_account_ids(self, account_mode: str, manual_ids: list[int], pack_ids: list[int]) -> list[int]:
        if account_mode == "pack":
            account_ids = await self.pack_repository.resolve_account_ids(pack_ids)
            if not account_ids:
                raise ComplianceError("Selected packs contain no accounts.")
            return account_ids
        return manual_ids

    async def validate_entities(
        self,
        account_ids: list[int],
        chat_ids: list[int],
        template_id: int,
    ) -> None:
        missing_accounts = await self.pack_repository.validate_account_ids(account_ids)
        if missing_accounts:
            raise ComplianceError(f"Unknown or inactive accounts: {missing_accounts}")
        template = await self.session.get(Template, template_id)
        if not template or not template.is_active:
            raise ComplianceError("Template not found or inactive.")
        if template.kind == "team":
            await TeamDialogueService(self.session, self.guard).load_steps(template_id)
        for chat_id in chat_ids:
            chat = await self.session.get(Chat, chat_id)
            if not chat:
                raise ComplianceError(f"Chat {chat_id} not found.")

    async def create_campaign(
        self,
        name: str,
        mode: str,
        template_id: int,
        created_by: int,
        account_ids: list[int],
        chat_ids: list[int],
        settings: dict,
        scheduled_at: datetime | None = None,
    ) -> Campaign:
        if mode not in {"single", "rotate", "team_dialogue", "scheduled_once"}:
            raise ComplianceError(f"Unsupported campaign mode: {mode}")
        self.guard.validate_campaign_limits(settings)
        await self.validate_entities(account_ids, chat_ids, template_id)
        campaign = Campaign(
            name=name,
            mode=mode,
            template_id=template_id,
            created_by=created_by,
            status="queued",
            created_at=datetime.utcnow(),
        )
        self.session.add(campaign)
        await self.session.flush()
        for account_id in account_ids:
            self.session.add(CampaignAccount(campaign_id=campaign.id, account_id=account_id))
        for chat_id in chat_ids:
            self.session.add(CampaignChat(campaign_id=campaign.id, chat_id=chat_id))
        allowed_keys = {
            "min_delay_msg",
            "max_delay_msg",
            "min_delay_chat",
            "max_delay_chat",
            "active_hours",
            "max_per_acc_hour",
            "max_per_chat_day",
            "cooldown_hours",
            "jitter_percent",
            "retry_count",
            "retry_backoff_sec",
        }
        filtered_settings = {k: v for k, v in settings.items() if k in allowed_keys}
        settings_row = CampaignSettings(
            campaign_id=campaign.id,
            scheduled_at=scheduled_at,
            **filtered_settings,
        )
        self.session.add(settings_row)
        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign

    async def preflight(self, campaign_id: int) -> PreflightResult:
        chat_ids = await self.repository.list_campaign_chats(campaign_id)
        excluded: list[dict] = []
        allowed: list[int] = []
        for chat_id in chat_ids:
            chat = await self.session.get(Chat, chat_id)
            if not chat:
                excluded.append({"chat_id": chat_id, "reason": "not_found"})
                continue
            try:
                self.guard.validate_send_permissions(chat.can_send, chat.type)
                if chat.is_blacklisted or chat.is_archived:
                    raise ComplianceError("chat_archived_or_blacklisted")
                allowed.append(chat.id)
            except ComplianceError as error:
                excluded.append({"chat_id": chat.id, "reason": str(error)})
        return PreflightResult(allowed_chats=allowed, excluded_chats=excluded, warnings=[])

    async def run_campaign(self, campaign_id: int, confirmed: bool) -> int:
        if not confirmed:
            raise ComplianceError("Explicit confirmation is required before run.")
        campaign = await self.repository.get_campaign(campaign_id)
        if not campaign:
            raise ValueError("Campaign not found.")

        preflight = await self.preflight(campaign_id)
        template = await self.session.get(Template, campaign.template_id)
        if not template:
            raise ValueError("Template not found.")

        account_ids = await self.repository.list_campaign_accounts(campaign_id)
        settings_obj = await self.repository.get_settings(campaign_id)
        if not settings_obj:
            raise ComplianceError("Campaign settings not found.")
        settings = SenderService.settings_to_dict(settings_obj)
        variables = {str(k): str(v) for k, v in (template.variables_json or {}).items()}

        self.guard.validate_before_run(
            {
                "confirmed": confirmed,
                "account_ids": account_ids,
                "chat_ids": preflight.allowed_chats,
            }
        )

        self.sender_service.register_campaign_settings(campaign_id, settings)
        await self.repository.update_campaign_status(campaign_id, "running")
        await self.sender_service.start_background_worker()

        queued = 0
        team_service = TeamDialogueService(self.session, self.guard)

        if campaign.mode == "team_dialogue" or template.kind == "team":
            for chat_id in preflight.allowed_chats:
                task = await team_service.build_chat_task(
                    campaign_id=campaign_id,
                    template_id=template.id,
                    chat_id=chat_id,
                    account_ids=account_ids,
                    variables=variables,
                )
                await self.sender_service.enqueue(task)
                queued += 1
            return queued

        for idx, chat_id in enumerate(preflight.allowed_chats):
            account_id = self.pick_account_id(campaign.mode, account_ids, idx)
            text = self.template_service.render_preview(template.body, variables)
            await self.sender_service.enqueue(
                SendTask(
                    campaign_id=campaign_id,
                    account_id=account_id,
                    chat_id=chat_id,
                    text=text,
                    step_no=1,
                )
            )
            queued += 1
        return queued

    async def pause(self, campaign_id: int) -> None:
        self.sender_service.pause(campaign_id)
        await self.repository.update_campaign_status(campaign_id, "paused")

    async def resume(self, campaign_id: int) -> None:
        self.sender_service.resume(campaign_id)
        await self.repository.update_campaign_status(campaign_id, "running")

    async def stop(self, campaign_id: int) -> None:
        self.sender_service.stop(campaign_id)
        await self.repository.update_campaign_status(campaign_id, "failed")

    async def list_campaigns(self) -> list[Campaign]:
        result = await self.session.execute(select(Campaign).order_by(Campaign.created_at.desc()))
        return list(result.scalars().all())
