from __future__ import annotations

from app.config import Settings
from app.infrastructure.ai_provider.base import AiProvider
from app.infrastructure.ai_provider.openai_provider import OpenAiProvider
from app.infrastructure.ai_provider.stub_provider import StubAiProvider


def build_ai_provider(settings: Settings) -> AiProvider:
    name = (settings.ai_provider or "stub").lower()
    if name == "openai":
        if not settings.openai_api_key:
            return StubAiProvider()
        return OpenAiProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
        )
    return StubAiProvider()
