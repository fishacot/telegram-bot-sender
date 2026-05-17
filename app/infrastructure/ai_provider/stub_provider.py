from __future__ import annotations

from typing import Any

from app.infrastructure.ai_provider.base import AiProvider


class StubAiProvider(AiProvider):
    async def recommend(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        _ = prompt
        risk = "low"
        reasons: list[str] = []
        settings = context.get("settings", {})
        min_delay = settings.get("min_delay_msg", 0)
        if min_delay < 8:
            risk = "high"
            reasons.append("Message delay is too low for safe sending.")
        elif min_delay < 15:
            risk = "medium"
            reasons.append("Message delay may still be aggressive.")
        return {
            "risk": risk,
            "reasons": reasons or ["Configuration looks conservative."],
            "suggestions": [
                {"field": "min_delay_msg", "value": max(min_delay, 15)},
                {"field": "max_per_acc_hour", "value": min(settings.get("max_per_acc_hour", 20), 15)},
            ],
        }
