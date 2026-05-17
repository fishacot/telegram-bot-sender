import pytest

from app.domain.chat_target import ChatTargetKind
from app.services.compliance_guard import ComplianceError, ComplianceGuard


def test_parse_join_target_username() -> None:
    parsed = ComplianceGuard().parse_join_target("@MyGroup")
    assert parsed.kind == ChatTargetKind.USERNAME
    assert parsed.username == "mygroup"


def test_parse_join_target_invite_link() -> None:
    parsed = ComplianceGuard().parse_join_target("https://t.me/+AbCdEfGhIjKlMn")
    assert parsed.kind == ChatTargetKind.INVITE
    assert parsed.invite_hash == "+AbCdEfGhIjKlMn"


def test_validate_join_target_rejects_invalid() -> None:
    with pytest.raises(ComplianceError):
        ComplianceGuard().parse_join_target("not a valid target !!!")
