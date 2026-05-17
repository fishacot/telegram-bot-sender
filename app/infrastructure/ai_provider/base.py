from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AiProvider(ABC):
    @abstractmethod
    async def recommend(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
