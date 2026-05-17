from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import Account, TeamStep
from app.services.compliance_guard import ComplianceGuard
from app.services.sender_service import SendTask, SubSendStep
from app.services.template_service import TemplateService


class TeamDialogueService:
    def __init__(self, session: AsyncSession, guard: ComplianceGuard) -> None:
        self.session = session
        self.guard = guard
        self.template_service = TemplateService(guard)

    async def load_steps(self, template_id: int) -> list[TeamStep]:
        result = await self.session.execute(
            select(TeamStep).where(TeamStep.template_id == template_id).order_by(TeamStep.step_no)
        )
        steps = list(result.scalars().all())
        if not steps:
            raise ValueError("Team template has no steps configured.")
        return steps

    async def resolve_role_accounts(self, account_ids: list[int]) -> dict[str, int]:
        role_map: dict[str, int] = {}
        for account_id in account_ids:
            account = await self.session.get(Account, account_id)
            if account:
                role_map.setdefault(account.role, account.id)
        return role_map

    async def build_chat_task(
        self,
        campaign_id: int,
        template_id: int,
        chat_id: int,
        account_ids: list[int],
        variables: dict[str, str] | None = None,
    ) -> SendTask:
        steps = await self.load_steps(template_id)
        role_map = await self.resolve_role_accounts(account_ids)
        variables = variables or {}
        subtasks: list[SubSendStep] = []
        for step in steps:
            account_id = role_map.get(step.role) or account_ids[(step.step_no - 1) % len(account_ids)]
            text = self.template_service.render_preview(step.text, variables)
            subtasks.append(
                SubSendStep(
                    account_id=account_id,
                    text=text,
                    step_no=step.step_no,
                    delay_before_sec=step.delay_sec,
                    reply_to_prev=step.reply_to_prev,
                )
            )
        return SendTask(
            campaign_id=campaign_id,
            account_id=subtasks[0].account_id,
            chat_id=chat_id,
            text=subtasks[0].text,
            step_no=1,
            subtasks=subtasks,
        )
