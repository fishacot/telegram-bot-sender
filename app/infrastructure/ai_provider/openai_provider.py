from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.infrastructure.ai_provider.base import AiProvider

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ты изолированный AI-агент проекта «Telegram Broadcast MVP».
Работаешь ТОЛЬКО с переданным контекстом (логи, код, ошибки). Не выдумывай файлы.
Отвечай СТРОГО JSON без markdown:
{
  "summary": "краткий вывод",
  "severity": "low|medium|high",
  "likely_causes": ["..."],
  "suggested_fixes": ["шаги для разработчика"],
  "rule_suggestions": ["предложения для CursoRules, без автоприменения"],
  "ops_actions": ["что сделать в боте/на сервере"]
}
Язык: русский. Безопасность: не проси секреты, не предлагай спам/обход банов."""


class OpenAiProvider(AiProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        *,
        timeout_sec: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.timeout_sec = timeout_sec

    async def recommend(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        user_content = json.dumps(
            {"task": prompt, "context": context},
            ensure_ascii=False,
            default=str,
        )[:120_000]
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return _normalize_agent_response(parsed)
        except Exception as error:  # noqa: BLE001
            logger.warning("OpenAI agent call failed: %s", error)
            return {
                "summary": f"AI недоступен: {error}",
                "severity": "medium",
                "likely_causes": ["Нет связи с API или неверный OPENAI_API_KEY"],
                "suggested_fixes": [
                    "Проверьте OPENAI_API_KEY и OPENAI_BASE_URL на Render",
                    "Временно используйте AI_PROVIDER=stub",
                ],
                "rule_suggestions": [],
                "ops_actions": ["Повторите /agent_errors позже"],
            }


def _normalize_agent_response(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": str(raw.get("summary", "")),
        "severity": str(raw.get("severity", "medium")),
        "likely_causes": list(raw.get("likely_causes") or []),
        "suggested_fixes": list(raw.get("suggested_fixes") or raw.get("suggestions") or []),
        "rule_suggestions": list(raw.get("rule_suggestions") or []),
        "ops_actions": list(raw.get("ops_actions") or []),
        "risk": raw.get("severity", "medium"),
        "reasons": list(raw.get("likely_causes") or []),
        "suggestions": [
            {"field": "note", "value": item} for item in (raw.get("suggested_fixes") or [])
        ],
    }
