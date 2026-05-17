from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import unquote, urlparse


class ChatTargetKind(str, Enum):
    USERNAME = "username"
    INVITE = "invite"


@dataclass(slots=True)
class ParsedChatTarget:
    kind: ChatTargetKind
    raw_input: str
    username: str | None = None
    invite_hash: str | None = None

    @property
    def telethon_entity(self) -> str:
        if self.kind == ChatTargetKind.USERNAME and self.username:
            return self.username
        if self.kind == ChatTargetKind.INVITE and self.invite_hash:
            h = self.invite_hash.lstrip("+")
            return f"https://t.me/+{h}"
        return self.raw_input.strip()

    @property
    def storage_key(self) -> str:
        if self.username:
            return f"@{self.username.lower()}"
        if self.invite_hash:
            return f"invite:+{self.invite_hash.lstrip('+')}"
        return self.raw_input.strip()

    @property
    def display(self) -> str:
        return self.storage_key


class ChatTargetParser:
    """Normalize user input: @username, t.me links, invite links -> Telethon-ready target."""

    _USERNAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{3,31}$")
    _INVITE_HASH_RE = re.compile(r"^[a-zA-Z0-9_-]{10,}$")

    @classmethod
    def parse(cls, raw: str) -> ParsedChatTarget:
        text = (raw or "").strip()
        if not text:
            raise ValueError("Chat target is empty.")

        text = unquote(text)

        if text.startswith(("http://", "https://", "tg://")):
            return cls._parse_url(text)

        if text.startswith("@"):
            username = cls._normalize_username(text[1:])
            return ParsedChatTarget(
                kind=ChatTargetKind.USERNAME,
                raw_input=raw,
                username=username,
            )

        if text.startswith("+") and cls._INVITE_HASH_RE.match(text[1:]):
            return ParsedChatTarget(
                kind=ChatTargetKind.INVITE,
                raw_input=raw,
                invite_hash=text,
            )

        if "t.me/" in text or "telegram.me/" in text or "telegram.dog/" in text:
            return cls._parse_url(
                text if text.startswith("http") else f"https://{text.lstrip('/')}"
            )

        if cls._USERNAME_RE.match(text):
            return ParsedChatTarget(
                kind=ChatTargetKind.USERNAME,
                raw_input=raw,
                username=text.lower(),
            )

        raise ValueError(
            "Unrecognized format. Use @username, username, t.me/username, or t.me/+invite / joinchat link."
        )

    @classmethod
    def _parse_url(cls, url: str) -> ParsedChatTarget:
        if url.startswith("tg://"):
            if "invite=" in url:
                invite = url.split("invite=", maxsplit=1)[1].split("&")[0]
                return ParsedChatTarget(
                    kind=ChatTargetKind.INVITE,
                    raw_input=url,
                    invite_hash=f"+{invite.lstrip('+')}",
                )
            raise ValueError("Unsupported tg:// link format.")

        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().replace("www.", "")
        if host not in {"t.me", "telegram.me", "telegram.dog"}:
            raise ValueError("Only t.me / telegram.me links are supported.")

        path = (parsed.path or "").strip("/")
        if not path:
            raise ValueError("Empty t.me path.")

        if path.startswith("+"):
            invite_hash = path[1:].split("/")[0]
            return ParsedChatTarget(
                kind=ChatTargetKind.INVITE,
                raw_input=url,
                invite_hash=f"+{invite_hash}",
            )

        if path.startswith("joinchat/"):
            invite_hash = path.split("/", maxsplit=1)[1]
            return ParsedChatTarget(
                kind=ChatTargetKind.INVITE,
                raw_input=url,
                invite_hash=f"+{invite_hash}",
            )

        username = cls._normalize_username(path.split("/")[0])
        return ParsedChatTarget(
            kind=ChatTargetKind.USERNAME,
            raw_input=url,
            username=username,
        )

    @staticmethod
    def _normalize_username(value: str) -> str:
        username = value.strip().lstrip("@").lower()
        if not ChatTargetParser._USERNAME_RE.match(username):
            raise ValueError(f"Invalid public username: @{username}")
        return username
