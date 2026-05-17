from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


class ProxyParseError(ValueError):
    pass


@dataclass(frozen=True)
class BulkProxyAssignResult:
    updated: list[tuple[int, str, str]]  # account_id, account_name, proxy_masked
    unchanged_account_names: list[str]
    errors: list[str]


def parse_proxy_bulk_text(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(parse_proxy_line(line))
    if not lines:
        raise ProxyParseError("Нет строк с прокси. Одна строка = один прокси.")
    return lines


def parse_proxy_line(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise ProxyParseError("Пустая строка прокси.")
    if text.lower() in {"off", "none", "нет", "-", "remove", "удалить"}:
        return ""

    if text.startswith("tg://") or "t.me/proxy" in text:
        return _normalize_tg_proxy_link(text)

    if "://" in text:
        parsed = urlparse(text)
        scheme = (parsed.scheme or "").lower()
        if scheme in {"mtproto", "mtp"}:
            return _normalize_mtproto_url(parsed.hostname, parsed.port, _secret_from_query(parsed))
        return normalize_proxy_url(text)

    return _parse_colon_shorthand(text)


def normalize_proxy_url(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise ProxyParseError("Прокси пустой.")
    if text.lower() in {"off", "none", "нет", "-", "remove"}:
        return ""
    if text.startswith("tg://") or "t.me/proxy" in text:
        return _normalize_tg_proxy_link(text)
    if "://" not in text:
        text = f"socks5://{text}"
    parsed = urlparse(text)
    scheme = (parsed.scheme or "socks5").lower()
    if scheme in {"mtproto", "mtp"}:
        return _normalize_mtproto_url(parsed.hostname, parsed.port, _secret_from_query(parsed))
    if scheme not in {"socks5", "socks", "socks4", "http", "https"}:
        raise ProxyParseError(f"Неподдерживаемый тип прокси: {scheme}")
    return text


def is_mtproto_proxy(stored: str | None) -> bool:
    if not stored:
        return False
    lowered = str(stored).strip().lower()
    return lowered.startswith("mtproto://") or lowered.startswith("mtproto:")


def parse_proxy_for_telethon(raw: str | None) -> tuple | None:
    """Return Telethon/python-socks proxy tuple or None if disabled."""
    if not raw or not str(raw).strip():
        return None
    if is_mtproto_proxy(raw):
        return None
    url = normalize_proxy_url(str(raw))
    parsed = urlparse(url)
    scheme = (parsed.scheme or "socks5").lower()
    host = parsed.hostname
    if not host:
        raise ProxyParseError("В URL прокси нет хоста.")
    port = parsed.port or (1080 if scheme.startswith("socks") else 8080)
    user, password = parsed.username, parsed.password

    if scheme in {"socks5", "socks"}:
        if user:
            return ("socks5", host, port, True, user, password or "")
        return ("socks5", host, port)
    if scheme == "socks4":
        return ("socks4", host, port)
    if scheme in {"http", "https"}:
        if user:
            return ("http", host, port, True, user, password or "")
        return ("http", host, port)

    match = re.match(
        r"^(socks5|socks4|http)://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$",
        url.strip(),
        re.I,
    )
    if match:
        scheme, user, password, host, port_s = match.groups()
        port = int(port_s)
        if user:
            return (scheme.lower(), host, port, True, user, password or "")
        return (scheme.lower(), host, port)

    raise ProxyParseError(
        "Формат: socks5://host:port, socks5://user:pass@host:port, http://host:port, "
        "mtproto://host:443?secret=..., tg://proxy?server=...&port=...&secret=..."
    )


def parse_mtproto_for_telethon(stored: str) -> tuple[str, str, int, str]:
    parsed = urlparse(stored.strip())
    if parsed.scheme.lower() not in {"mtproto", "mtp"}:
        raise ProxyParseError("Ожидался mtproto:// URL.")
    host = parsed.hostname
    port = parsed.port
    secret = _secret_from_query(parsed)
    if not host or not port or not secret:
        raise ProxyParseError("MTProto: нужны host, port и secret.")
    return ("mtproxy", host, port, secret)


def mask_proxy_url(raw: str | None) -> str:
    if not raw or not str(raw).strip():
        return "нет"
    url = str(raw).strip()
    if is_mtproto_proxy(url):
        parsed = urlparse(url)
        host = parsed.hostname or "?"
        port = parsed.port or "?"
        return f"mtproto://{host}:{port}?secret=***"
    if "://" not in url:
        url = f"socks5://{url}"
    parsed = urlparse(url)
    host = parsed.hostname or "?"
    port = parsed.port or "?"
    if parsed.username:
        return f"{parsed.scheme}://{parsed.username}:***@{host}:{port}"
    return f"{parsed.scheme}://{host}:{port}"


def _parse_colon_shorthand(text: str) -> str:
    ipv4_port = re.match(r"^(\d+\.\d+\.\d+\.\d+):(\d+)$", text)
    if ipv4_port:
        return normalize_proxy_url(f"socks5://{ipv4_port.group(1)}:{ipv4_port.group(2)}")

    ipv4_auth = re.match(r"^(\d+\.\d+\.\d+\.\d+):(\d+):([^:]+):(.+)$", text)
    if ipv4_auth:
        host, port, user, password = ipv4_auth.groups()
        return normalize_proxy_url(f"socks5://{user}:{password}@{host}:{port}")

    host_port = re.match(r"^([a-zA-Z0-9.-]+):(\d+)$", text)
    if host_port:
        return normalize_proxy_url(f"socks5://{host_port.group(1)}:{host_port.group(2)}")

    host_auth = re.match(r"^([a-zA-Z0-9.-]+):(\d+):([^:]+):(.+)$", text)
    if host_auth:
        host, port, user, password = host_auth.groups()
        return normalize_proxy_url(f"socks5://{user}:{password}@{host}:{port}")

    mtproto = re.match(r"^([a-zA-Z0-9.-]+):(\d+):(.+)$", text)
    if mtproto:
        host, port, secret = mtproto.groups()
        return _normalize_mtproto_url(host, int(port), secret)

    raise ProxyParseError(
        "Короткий формат: 1.2.3.4:1080, host:1080, host:1080:login:pass (SOCKS5) "
        "или host:443:secret (MTProto)"
    )


def _normalize_tg_proxy_link(text: str) -> str:
    if "t.me/proxy" in text:
        parsed = urlparse(text if "://" in text else f"https://{text}")
    else:
        parsed = urlparse(text)
    query = parse_qs(parsed.query)
    server = (query.get("server") or [None])[0]
    port_raw = (query.get("port") or [None])[0]
    secret = (query.get("secret") or [None])[0]
    if not server or not port_raw or not secret:
        raise ProxyParseError("В ссылке tg://proxy нет server, port или secret.")
    return _normalize_mtproto_url(server, int(port_raw), secret)


def _normalize_mtproto_url(host: str | None, port: int | None, secret: str) -> str:
    if not host or not port:
        raise ProxyParseError("MTProto: укажите host и port.")
    secret = (secret or "").strip()
    if not secret:
        raise ProxyParseError("MTProto: не указан secret.")
    return f"mtproto://{host}:{port}?secret={secret}"


def _secret_from_query(parsed) -> str:
    secret = (parse_qs(parsed.query).get("secret") or [None])[0]
    if secret:
        return secret.strip()
    return ""
