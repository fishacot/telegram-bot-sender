from __future__ import annotations

from pathlib import Path

from telethon import TelegramClient
from telethon.network.connection.tcpmtproxy import ConnectionTcpMTProxyRandomizedIntermediate

from app.domain.proxy_url import (
    is_mtproto_proxy,
    parse_mtproto_for_telethon,
    parse_proxy_for_telethon,
)


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

    def create(self, session_name: str, proxy_url: str | None = None) -> TelegramClient:
        session_path = self.sessions_dir / session_name
        effective = proxy_url if proxy_url is not None else self.proxy_url
        return self._build_client(str(session_path), effective)

    def _build_client(self, session_path: str, proxy_url: str | None) -> TelegramClient:
        if proxy_url and is_mtproto_proxy(proxy_url):
            mtproxy = parse_mtproto_for_telethon(proxy_url)
            return TelegramClient(
                session_path,
                self.api_id,
                self.api_hash,
                connection=ConnectionTcpMTProxyRandomizedIntermediate,
                proxy=mtproxy,
            )
        proxy = parse_proxy_for_telethon(proxy_url) if proxy_url else None
        return TelegramClient(session_path, self.api_id, self.api_hash, proxy=proxy)

    @staticmethod
    def validate_proxy(proxy_url: str) -> None:
        if is_mtproto_proxy(proxy_url):
            parse_mtproto_for_telethon(proxy_url)
            return
        parsed = parse_proxy_for_telethon(proxy_url)
        if parsed is None:
            raise ValueError("Proxy URL is empty.")

    @staticmethod
    def parse_proxy(proxy_url: str) -> tuple:
        TelethonClientFactory.validate_proxy(proxy_url)
        if is_mtproto_proxy(proxy_url):
            return parse_mtproto_for_telethon(proxy_url)
        parsed = parse_proxy_for_telethon(proxy_url)
        if parsed is None:
            raise ValueError("Proxy URL is empty.")
        return parsed
