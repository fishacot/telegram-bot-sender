from __future__ import annotations

import re
from pathlib import Path

from aiogram import Bot
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.infrastructure.db.models import Account
from app.infrastructure.telethon_clients.factory import TelethonClientFactory

SESSION_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{1,31}$")


class AccountImportError(Exception):
    pass


class AccountImportService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    @staticmethod
    def normalize_session_name(value: str) -> str:
        name = value.strip().removesuffix(".session")
        if not SESSION_NAME_RE.match(name):
            raise AccountImportError(
                "Invalid session name. Use 2-32 chars: letters, digits, _ or - (must start with letter)."
            )
        return name

    async def import_from_message(
        self,
        bot: Bot,
        message: Message,
        session_name: str,
        role: str = "lead",
    ) -> tuple[Account, str]:
        if not message.document:
            raise AccountImportError("Send a file (Telethon .session), not text.")

        file_name = (message.document.file_name or "").lower()
        if not file_name.endswith(".session"):
            raise AccountImportError("Only .session files are accepted.")

        session_name = self.normalize_session_name(session_name)
        role = role.strip() or "lead"

        sessions_dir = Path(self.settings.sessions_dir)
        sessions_dir.mkdir(parents=True, exist_ok=True)
        target_path = sessions_dir / f"{session_name}.session"

        await bot.download(message.document, destination=target_path)

        display = await self._verify_session(session_name)

        account = await self._upsert_account(session_name, role)
        return account, display

    async def _verify_session(self, session_name: str) -> str:
        factory = TelethonClientFactory(
            sessions_dir=self.settings.sessions_dir,
            api_id=self.settings.telegram_api_id,
            api_hash=self.settings.telegram_api_hash,
            proxy_url=self.settings.telegram_proxy,
        )
        client = factory.create(session_name)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise AccountImportError(
                    "Session file saved but not authorized. "
                    "Create a valid session (e.g. scripts/auth_session.py) and upload again."
                )
            me = await client.get_me()
            label = f"@{me.username}" if me.username else str(me.id)
            return label
        finally:
            if client.is_connected():
                await client.disconnect()

    async def _upsert_account(self, session_name: str, role: str) -> Account:
        result = await self.session.execute(select(Account).where(Account.name == session_name))
        existing = result.scalar_one_or_none()
        if existing:
            existing.session_path = session_name
            existing.role = role
            existing.is_active = True
            existing.health_status = "active"
            account = existing
        else:
            account = Account(
                name=session_name,
                session_path=session_name,
                role=role,
                is_active=True,
                health_status="active",
            )
            self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        return account
