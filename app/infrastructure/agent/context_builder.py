from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.infrastructure.agent.sandbox import AgentSandbox
from app.infrastructure.db.models import (
    Account,
    AgentErrorEvent,
    AuditEvent,
    Campaign,
    SendAttempt,
)
from app.infrastructure.repositories.chat_repository import ChatRepository


class AgentContextBuilder:
    def __init__(self, session: AsyncSession, settings: Settings, sandbox: AgentSandbox) -> None:
        self.session = session
        self.settings = settings
        self.sandbox = sandbox

    async def build_snapshot(
        self,
        *,
        error_limit: int = 15,
        include_files: list[str] | None = None,
    ) -> dict:
        accounts = await self._count(Account)
        chats = len(await ChatRepository(self.session).list_compliant_chats())
        templates = await self._count_by_filter("templates", "is_active", True)
        campaigns_running = await self._count_campaigns_running()
        recent_errors = await self._recent_errors(error_limit)
        failed_sends = await self._recent_failed_sends(10)
        audit = await self._recent_audit(8)

        file_snippets: dict[str, str] = {}
        paths = include_files or self._default_context_files()
        for rel in paths[: self.settings.agent_max_context_files]:
            try:
                file_snippets[rel] = self.sandbox.read_text(rel, max_chars=4000)
            except Exception as exc:  # noqa: BLE001
                file_snippets[rel] = f"[недоступно: {exc}]"

        return {
            "project": {
                "root": str(self.sandbox.root),
                "files_index": self.sandbox.list_project_files(limit=60),
            },
            "runtime": {
                "accounts": accounts,
                "chats": chats,
                "templates": templates,
                "campaigns_running": campaigns_running,
                "ai_provider": self.settings.ai_provider,
                "ai_mode": self.settings.ai_mode,
                "agent_enabled": self.settings.ai_agent_enabled,
            },
            "recent_errors": recent_errors,
            "failed_sends": failed_sends,
            "recent_audit": audit,
            "code_snippets": file_snippets,
            "rules_paths": [
                "CursoRules/AGENTS.md",
                "CursoRules/.cursor/rules/agent-workflow-core.mdc",
            ],
        }

    async def _count(self, model) -> int:
        result = await self.session.execute(select(func.count()).select_from(model))
        return int(result.scalar_one())

    async def _count_by_filter(self, table: str, field: str, value: bool) -> int:
        if table == "templates":
            from app.infrastructure.db.models import Template

            result = await self.session.execute(
                select(func.count()).select_from(Template).where(Template.is_active.is_(value))
            )
            return int(result.scalar_one())
        return 0

    async def _count_campaigns_running(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Campaign)
            .where(Campaign.status.in_(("running", "queued", "paused")))
        )
        return int(result.scalar_one())

    async def _recent_errors(self, limit: int) -> list[dict]:
        result = await self.session.execute(
            select(AgentErrorEvent).order_by(AgentErrorEvent.id.desc()).limit(limit)
        )
        return [
            {
                "id": row.id,
                "source": row.source,
                "level": row.level,
                "message": row.message[:500],
                "traceback": (row.traceback or "")[:1500],
                "context": row.context_json,
                "at": row.created_at.isoformat(),
            }
            for row in result.scalars().all()
        ]

    async def _recent_failed_sends(self, limit: int) -> list[dict]:
        result = await self.session.execute(
            select(SendAttempt)
            .where(SendAttempt.status == "failed")
            .order_by(SendAttempt.id.desc())
            .limit(limit)
        )
        return [
            {
                "campaign_id": row.campaign_id,
                "account_id": row.account_id,
                "chat_id": row.chat_id,
                "error_code": row.error_code,
                "error_text": (row.error_text or "")[:300],
            }
            for row in result.scalars().all()
        ]

    async def _recent_audit(self, limit: int) -> list[dict]:
        result = await self.session.execute(
            select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)
        )
        return [
            {
                "action": row.action,
                "actor_id": row.actor_id,
                "payload": row.payload_json,
                "at": row.created_at.isoformat(),
            }
            for row in result.scalars().all()
        ]

    @staticmethod
    def _default_context_files() -> list[str]:
        return [
            "app/main.py",
            "app/config.py",
            "app/container.py",
            "app/services/sender_service.py",
            "app/bot/router.py",
            "app/bot/handlers/ui_wizard.py",
            "CursoRules/AGENTS.md",
        ]
