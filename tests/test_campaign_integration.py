import pytest

from app.services.compliance_guard import ComplianceError, ComplianceGuard
from app.services.sender_service import SenderService


def test_floodwait_handling(mock_telethon_adapter) -> None:
    sender = SenderService(guard=ComplianceGuard(), telethon_adapter=mock_telethon_adapter)
    wait = sender._extract_floodwait_seconds("floodwait 17")
    assert wait == 17


def test_private_dialog_regression_denied() -> None:
    guard = ComplianceGuard()
    with pytest.raises(ComplianceError):
        guard.validate_send_permissions(can_send=True, chat_type="user")
