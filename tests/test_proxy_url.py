import pytest

from app.domain.proxy_url import (
    ProxyParseError,
    is_mtproto_proxy,
    mask_proxy_url,
    parse_proxy_bulk_text,
    parse_proxy_for_telethon,
    parse_proxy_line,
)


def test_parse_socks5_host_port():
    assert parse_proxy_for_telethon("socks5://1.2.3.4:1080") == ("socks5", "1.2.3.4", 1080)


def test_parse_socks5_with_auth():
    assert parse_proxy_for_telethon("socks5://user:secret@1.2.3.4:1080") == (
        "socks5",
        "1.2.3.4",
        1080,
        True,
        "user",
        "secret",
    )


def test_parse_shorthand_host_port():
    assert parse_proxy_for_telethon("1.2.3.4:1080") == ("socks5", "1.2.3.4", 1080)


def test_parse_shorthand_host_port_user_pass():
    line = parse_proxy_line("1.2.3.4:1080:u:p")
    assert "u:p@1.2.3.4:1080" in line


def test_parse_mtproto_colon():
    line = parse_proxy_line("proxy.example.com:443:ee0123456789abcdef")
    assert is_mtproto_proxy(line)
    assert "secret=ee" in line


def test_parse_tg_proxy_link():
    line = parse_proxy_line("tg://proxy?server=1.2.3.4&port=443&secret=eeabcd")
    assert line.startswith("mtproto://1.2.3.4:443")


def test_parse_bulk_skips_comments():
    lines = parse_proxy_bulk_text(
        "# comment\nsocks5://1.1.1.1:1080\n\n2.2.2.2:1080\n"
    )
    assert len(lines) == 2


def test_parse_disabled():
    assert parse_proxy_for_telethon(None) is None
    assert parse_proxy_for_telethon("") is None


def test_parse_invalid_raises():
    with pytest.raises(ProxyParseError):
        parse_proxy_line("ftp://bad-scheme:1")


def test_mask_hides_password():
    assert "***" in mask_proxy_url("socks5://u:pass@host:1080")


def test_mask_mtproto():
    assert "secret=***" in mask_proxy_url("mtproto://h:443?secret=eeabc")
