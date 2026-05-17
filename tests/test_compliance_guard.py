import pytest

from app.services.compliance_guard import ComplianceError, ComplianceGuard


def test_private_dialog_denied() -> None:
    guard = ComplianceGuard()
    with pytest.raises(ComplianceError):
        guard.validate_chat_type("private")


def test_campaign_limits_rejected_for_aggressive_settings() -> None:
    guard = ComplianceGuard()
    with pytest.raises(ComplianceError):
        guard.validate_campaign_limits(
            {
                "min_delay_msg": 1,
                "max_delay_msg": 10,
                "max_per_acc_hour": 10,
            }
        )
