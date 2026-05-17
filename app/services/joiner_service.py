from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat_target import ParsedChatTarget
from app.infrastructure.db.models import Account, Chat, JoinTask
from app.infrastructure.telethon_clients.sender_adapter import TelethonSenderAdapter
from app.services.compliance_guard import ComplianceGuard

logger = logging.getLogger(__name__)


class JoinerService:
    def __init__(
        self,
        session: AsyncSession,
        guard: ComplianceGuard,
        telethon_adapter: TelethonSenderAdapter,
    ) -> None:
        self.session = session
        self.guard = guard
        self.telethon_adapter = telethon_adapter

    async def queue_join(self, account_id: int, raw_target: str) -> JoinTask:
        parsed = self.guard.parse_join_target(raw_target)
        task = JoinTask(
            account_id=account_id,
            chat_username=parsed.storage_key,
            status="queued",
            created_at=datetime.utcnow(),
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def execute_join(self, task_id: int) -> tuple[JoinTask, Chat, ParsedChatTarget]:
        task = await self.session.get(JoinTask, task_id)
        if not task:
            raise ValueError("Join task not found.")
        account = await self.session.get(Account, task.account_id)
        if not account:
            raise ValueError("Account not found.")

        parsed = self.guard.parse_join_target(task.chat_username)

        task.status = "running"
        await self.session.commit()
        try:
            info = await self.telethon_adapter.join_chat(account, parsed)
            chat = await self._upsert_chat(info)
            task.status = "completed"
            task.error_text = None
            await self.session.commit()
            await self.session.refresh(task)
            return task, chat, parsed
        except Exception as error:  # noqa: BLE001
            task.status = "failed"
            task.error_text = str(error)
            await self.session.commit()
            raise

    async def join_and_add(self, account_id: int, raw_target: str) -> tuple[JoinTask, Chat, ParsedChatTarget]:
        task = await self.queue_join(account_id, raw_target)
        return await self.execute_join(task.id)

    async def _upsert_chat(self, info: dict) -> Chat:
        result = await self.session.execute(select(Chat).where(Chat.tg_chat_id == info["tg_chat_id"]))
        existing = result.scalar_one_or_none()
        if existing:
            existing.title = info["title"]
            existing.username = info.get("username")
            existing.type = info["type"]
            existing.can_send = info["can_send"]
            existing.is_archived = False
            existing.is_blacklisted = False
            chat = existing
        else:
            chat = Chat(
                tg_chat_id=info["tg_chat_id"],
                title=info["title"],
                username=info.get("username"),
                type=info["type"],
                can_send=info["can_send"],
                is_archived=False,
                is_blacklisted=False,
            )
            self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)
        return chat

    @staticmethod
    async def run_join_async_static(task_id: int, notify_user_id: int | None = None) -> None:
        asyncio.create_task(JoinerService._execute_join_background(task_id, notify_user_id))

    @staticmethod
    async def _execute_join_background(task_id: int, notify_user_id: int | None = None) -> None:
        from app.infrastructure.bot_notifier import BotNotifier
        from app.infrastructure.db.session import SessionLocal

        async with SessionLocal() as session:
            from app.container import get_container

            container = get_container()
            service = JoinerService(session, container.guard, container.telethon_adapter)
            try:
                task, chat, parsed = await service.execute_join(task_id)
                if notify_user_id:
                    await BotNotifier.send(
                        notify_user_id,
                        (
                            f"Join completed (task #{task_id})\n"
                            f"Chat pool id: #{chat.id}\n"
                            f"Title: {chat.title}\n"
                            f"tg_chat_id: {chat.tg_chat_id}\n"
                            f"can_send: {int(chat.can_send)}\n"
                            f"Target: {parsed.storage_key}"
                        ),
                    )
            except Exception as error:  # noqa: BLE001
                logger.warning("Join task %s failed: %s", task_id, error)
                if notify_user_id:
                    await BotNotifier.send(
                        notify_user_id,
                        f"Join failed (task #{task_id})\n{error}",
                    )
