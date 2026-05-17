import pytest

from app.domain.chat_target import ChatTargetKind, ChatTargetParser


def test_parse_at_username() -> None:
    parsed = ChatTargetParser.parse("@MyChannel")
    assert parsed.kind == ChatTargetKind.USERNAME
    assert parsed.username == "mychannel"
    assert parsed.telethon_entity == "mychannel"


def test_parse_tme_username_url() -> None:
    parsed = ChatTargetParser.parse("https://t.me/some_channel")
    assert parsed.username == "some_channel"
    assert parsed.storage_key == "@some_channel"


def test_parse_invite_plus_link() -> None:
    parsed = ChatTargetParser.parse("https://t.me/+AbCdEfGhIjKlMn")
    assert parsed.kind == ChatTargetKind.INVITE
    assert parsed.invite_hash == "+AbCdEfGhIjKlMn"
    assert "t.me/+AbCdEfGhIjKlMn" in parsed.telethon_entity


def test_parse_joinchat_link() -> None:
    parsed = ChatTargetParser.parse("https://t.me/joinchat/AAAA-BBBB-CCCC")
    assert parsed.kind == ChatTargetKind.INVITE
    assert parsed.invite_hash == "+AAAA-BBBB-CCCC"


def test_parse_plain_username() -> None:
    parsed = ChatTargetParser.parse("publicgroup")
    assert parsed.username == "publicgroup"


def test_reject_empty() -> None:
    with pytest.raises(ValueError):
        ChatTargetParser.parse("   ")
