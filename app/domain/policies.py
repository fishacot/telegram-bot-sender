from __future__ import annotations

from datetime import datetime

from app.domain.value_objects import ActiveHours


class RatePolicy:
    def is_within_active_hours(self, active_hours: str, now: datetime) -> bool:
        start, end = active_hours.split("-")
        hours = ActiveHours(start_hour=int(start), end_hour=int(end))
        return hours.contains(now)

    def validate_delay_window(self, min_delay: int, max_delay: int) -> None:
        if min_delay < 0 or max_delay < 0:
            raise ValueError("Delay values must be non-negative.")
        if min_delay > max_delay:
            raise ValueError("min_delay cannot be greater than max_delay.")
