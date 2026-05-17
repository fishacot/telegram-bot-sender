from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class AiRecommendationEntity:
    campaign_id: int | None
    recommendation_type: str
    payload: dict[str, Any]
    created_at: datetime
    accepted_by_user: bool = False
