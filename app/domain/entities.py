from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ChatEntity:
    id: int
    tg_chat_id: int
    title: str
    username: str | None
    type: str
    can_send: bool
    is_archived: bool
    is_blacklisted: bool


@dataclass(slots=True)
class CampaignSettingsEntity:
    min_delay_msg: int
    max_delay_msg: int
    min_delay_chat: int
    max_delay_chat: int
    active_hours: str
    max_per_acc_hour: int
    max_per_chat_day: int
    cooldown_hours: int
    jitter_percent: int
    retry_count: int
    retry_backoff_sec: int


@dataclass(slots=True)
class CampaignEntity:
    id: int
    name: str
    mode: str
    status: str
    template_id: int
    created_by: int
    created_at: datetime
    settings: CampaignSettingsEntity | None = None
    account_ids: list[int] = field(default_factory=list)
    chat_ids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class AuditEventEntity:
    actor_id: int
    action: str
    payload_json: dict[str, Any]
    created_at: datetime
