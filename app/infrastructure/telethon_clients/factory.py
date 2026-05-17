from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from telethon import TelegramClient


class TelethonClientFactory:
    def __init__(
        self,
        sessions_dir: str,
        api_id: int,
        api_hash: str,
        proxy_url: str | None = None,
    ) -> None:
        self.sessions_dir = Path(sessions_dir)
        self.api_id = api_id
        self.api_hash = api_hash
        self.proxy_url = proxy_url
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def create(self, session_name: str) -> TelegramClient:
        session_path = self.sessions_dir / session_name
        proxy = self._parse_proxy(self.proxy_url) if self.proxy_url else None
        return TelegramClient(str(session_path), self.api_id, self.api_hash, proxy=proxy)

    @staticmethod
    def _parse_proxy(proxy_url: str) -> tuple:
        parsed = urlparse(proxy_url)
        scheme = (parsed.scheme or "socks5").lower()
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 1080
        if scheme in {"socks5", "socks"}:
            return ("socks5", host, port)
        if scheme == "socks4":
            return ("socks4", host, port)
        if scheme in {"http", "https"}:
            return ("http", host, port)
        match = re.match(r"^(socks5|socks4|http)://([^:]+):(\d+)$", proxy_url.strip(), re.I)
        if match:
            return (match.group(1).lower(), match.group(2), int(match.group(3)))
        raise ValueError(f"Unsupported proxy URL: {proxy_url}")
