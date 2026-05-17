from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.infrastructure.agent.context_builder import AgentContextBuilder
from app.infrastructure.agent.error_store import error_store
from app.infrastructure.agent.sandbox import AgentSandbox
from app.infrastructure.ai_provider.base import AiProvider
from app.infrastructure.db.models import AgentErrorEvent, AiRecommendation


class ProjectAgentService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        provider: AiProvider,
        sandbox: AgentSandbox,
    ) -> None:
        self.session = session
        self.settings = settings
        self.provider = provider
        self.sandbox = sandbox
        self.context_builder = AgentContextBuilder(session, settings, sandbox)

    async def status(self) -> dict[str, Any]:
        snapshot = await self.context_builder.build_snapshot(error_limit=5, include_files=[])
        provider_label = self.settings.ai_provider
        if self.settings.openai_api_key and provider_label == "openai":
            provider_label = f"openai ({self.settings.openai_model})"
        return {
            "enabled": self.settings.ai_agent_enabled,
            "provider": provider_label,
            "runtime": snapshot["runtime"],
            "errors_in_db": len(snapshot["recent_errors"]),
            "memory_errors": len(error_store.memory_snapshot(50)),
            "reports_dir": str(self.sandbox.reports_dir),
        }

    async def diagnose_errors(self, *, limit: int = 15) -> dict[str, Any]:
        snapshot = await self.context_builder.build_snapshot(error_limit=limit)
        snapshot["memory_errors"] = error_store.memory_snapshot(limit)
        response = await self.provider.recommend(
            "Проанализируй ошибки проекта и предложи исправления. Сформируй отчёт для админа.",
            snapshot,
        )
        report_path = self._write_report_md("diagnosis", response, snapshot)
        await self._save_recommendation("agent_diagnosis", response, report_path)
        await self._mark_errors_analyzed(snapshot["recent_errors"])
        response["report_file"] = str(report_path)
        return response

    async def full_report(self) -> dict[str, Any]:
        snapshot = await self.context_builder.build_snapshot(error_limit=20)
        response = await self.provider.recommend(
            "Полный отчёт о состоянии проекта: риски, ошибки, рекомендации по настройке.",
            snapshot,
        )
        report_path = self._write_report_md("full_report", response, snapshot)
        await self._save_recommendation("agent_report", response, report_path)
        response["report_file"] = str(report_path)
        return response

    async def ask(self, question: str, *, actor_id: int) -> dict[str, Any]:
        snapshot = await self.context_builder.build_snapshot(error_limit=10)
        snapshot["user_question"] = question
        snapshot["actor_id"] = actor_id
        response = await self.provider.recommend(question, snapshot)
        await self._save_recommendation("agent_ask", response, None)
        return response

    def _write_report_md(self, kind: str, analysis: dict, snapshot: dict) -> Path:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        lines = [
            f"# Agent report: {kind}",
            f"Generated: {datetime.utcnow().isoformat()}Z",
            "",
            "## Summary",
            analysis.get("summary", ""),
            "",
            f"**Severity:** {analysis.get('severity', 'medium')}",
            "",
            "## Likely causes",
        ]
        lines.extend(f"- {item}" for item in analysis.get("likely_causes", []))
        lines.extend(["", "## Suggested fixes"])
        lines.extend(f"- {item}" for item in analysis.get("suggested_fixes", []))
        lines.extend(["", "## CursoRules suggestions"])
        lines.extend(f"- {item}" for item in analysis.get("rule_suggestions", []))
        lines.extend(["", "## Ops actions"])
        lines.extend(f"- {item}" for item in analysis.get("ops_actions", []))
        lines.extend(["", "## Runtime snapshot", "```json"])
        lines.append(str(snapshot.get("runtime", {})))
        lines.append("```")
        filename = f"{kind}_{ts}.md"
        return self.sandbox.write_report(filename, "\n".join(lines))

    async def _save_recommendation(
        self,
        rec_type: str,
        payload: dict,
        report_path: Path | None,
    ) -> None:
        if report_path:
            payload = {**payload, "report_file": str(report_path)}
        row = AiRecommendation(
            campaign_id=None,
            type=rec_type,
            payload=payload,
            created_at=datetime.utcnow(),
            accepted_by_user=False,
        )
        self.session.add(row)
        await self.session.commit()

    async def _mark_errors_analyzed(self, errors: list[dict]) -> None:
        ids = [item["id"] for item in errors if "id" in item]
        if not ids:
            return
        await self.session.execute(
            update(AgentErrorEvent).where(AgentErrorEvent.id.in_(ids)).values(analyzed=True)
        )
        await self.session.commit()

    @staticmethod
    def format_telegram_report(analysis: dict) -> str:
        severity = analysis.get("severity", "medium")
        icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(severity, "🟡")
        parts = [
            f"{icon} <b>{analysis.get('summary', '—')}</b>",
            "",
            "<b>Вероятные причины:</b>",
        ]
        causes = analysis.get("likely_causes") or analysis.get("reasons") or []
        parts.extend(f"• {c}" for c in causes[:5]) or parts.append("• —")
        parts.append("")
        parts.append("<b>Что сделать:</b>")
        fixes = analysis.get("suggested_fixes") or []
        if not fixes:
            fixes = [s.get("value") for s in analysis.get("suggestions", []) if s.get("value")]
        parts.extend(f"• {f}" for f in fixes[:6]) or parts.append("• —")
        rules = analysis.get("rule_suggestions") or []
        if rules:
            parts.append("")
            parts.append("<b>CursoRules (вручную):</b>")
            parts.extend(f"• {r}" for r in rules[:4])
        report_file = analysis.get("report_file")
        if report_file:
            parts.append("")
            parts.append(f"📄 Отчёт: <code>{report_file}</code>")
        return "\n".join(parts)
