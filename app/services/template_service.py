from __future__ import annotations

from app.services.compliance_guard import ComplianceGuard


class TemplateService:
    def __init__(self, guard: ComplianceGuard) -> None:
        self.guard = guard

    def render_preview(self, body: str, variables: dict[str, str]) -> str:
        rendered = body
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{key}}}", value)
        self.guard.assert_safe_content(rendered)
        return rendered
