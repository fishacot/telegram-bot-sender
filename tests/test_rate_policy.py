from datetime import datetime

import pytest

from app.domain.policies import RatePolicy


def test_rate_policy_active_hours() -> None:
    policy = RatePolicy()
    now = datetime(2026, 5, 16, 12, 0, 0)
    assert policy.is_within_active_hours("9-21", now)


def test_rate_policy_invalid_delay_window() -> None:
    policy = RatePolicy()
    with pytest.raises(ValueError):
        policy.validate_delay_window(20, 10)
