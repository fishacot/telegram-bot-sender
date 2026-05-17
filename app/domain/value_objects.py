from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class CampaignStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ChatType(str, Enum):
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"
    PRIVATE = "private"
    USER = "user"


class TemplateKind(str, Enum):
    TEXT = "text"
    TEAM = "team"


class AiMode(str, Enum):
    SUGGESTION_ONLY = "suggestion-only"
    AUTO_APPLY_SAFE = "auto-apply-safe"


@dataclass(slots=True)
class ActiveHours:
    start_hour: int
    end_hour: int

    def contains(self, value: datetime) -> bool:
        return self.start_hour <= value.hour <= self.end_hour
