from __future__ import annotations

import asyncio
import logging
import random
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.config import get_settings
from app.domain.policies import RatePolicy
from app.infrastructure.db.models import Account, CampaignSettings, Chat, SendAttempt
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.telethon_clients.sender_adapter import TelethonSenderAdapter
from app.services.compliance_guard import ComplianceError, ComplianceGuard
from app.services.rate_limiter import SendRateLimiter

logger = logging.getLogger(__name__)

OnCampaignComplete = Callable[[int], Awaitable[None]]


@dataclass(slots=True)
class SubSendStep:
    account_id: int
    text: str
    step_no: int
    delay_before_sec: int = 0
    reply_to_prev: bool = False


@dataclass(slots=True)
class SendTask:
    campaign_id: int
    account_id: int
    chat_id: int
    text: str
    step_no: int = 1
    subtasks: list[SubSendStep] | None = None
    delay_before_sec: int = 0
    reply_to_prev: bool = False


class SenderService:
    def __init__(self, guard: ComplianceGuard, telethon_adapter: TelethonSenderAdapter) -> None:
        self.guard = guard
        self.telethon_adapter = telethon_adapter
        self.queue: asyncio.Queue[SendTask | None] = asyncio.Queue()
        self.paused_campaigns: set[int] = set()
        self.stopped_campaigns: set[int] = set()
        self._pending_by_campaign: dict[int, int] = defaultdict(int)
        self._campaign_settings: dict[int, dict] = {}
        self._worker_task: asyncio.Task[None] | None = None
        self._on_campaign_complete: OnCampaignComplete | None = None
        self._policy = RatePolicy()

    def set_campaign_complete_handler(self, handler: OnCampaignComplete) -> None:
        self._on_campaign_complete = handler

    def register_campaign_settings(self, campaign_id: int, settings: dict) -> None:
        self._campaign_settings[campaign_id] = settings

    async def enqueue(self, task: SendTask) -> None:
        self._pending_by_campaign[task.campaign_id] += 1
        await self.queue.put(task)

    def pause(self, campaign_id: int) -> None:
        self.paused_campaigns.add(campaign_id)

    def resume(self, campaign_id: int) -> None:
        self.paused_campaigns.discard(campaign_id)

    def stop(self, campaign_id: int) -> None:
        self.stopped_campaigns.add(campaign_id)
        self.paused_campaigns.discard(campaign_id)

    async def start_background_worker(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("Sender background worker started")

    async def stop_background_worker(self) -> None:
        if self._worker_task is None:
            return
        await self.queue.put(None)
        await self._worker_task
        self._worker_task = None
        logger.info("Sender background worker stopped")

    async def _worker_loop(self) -> None:
        while True:
            task = await self.queue.get()
            if task is None:
                self.queue.task_done()
                break
            try:
                await self._process_task(task)
            except Exception as error:  # noqa: BLE001
                logger.exception("Unexpected sender worker error: %s", error)
            finally:
                self._pending_by_campaign[task.campaign_id] -= 1
                if self._pending_by_campaign[task.campaign_id] <= 0:
                    self._pending_by_campaign.pop(task.campaign_id, None)
                    self._campaign_settings.pop(task.campaign_id, None)
                    if self._on_campaign_complete:
                        await self._on_campaign_complete(task.campaign_id)
                self.queue.task_done()

    async def _process_task(self, task: SendTask) -> None:
        if task.campaign_id in self.stopped_campaigns:
            await self._save_attempt(task, "skipped", "campaign_stopped", "Campaign was stopped")
            return

        while task.campaign_id in self.paused_campaigns:
            await asyncio.sleep(1)

        settings = self._campaign_settings.get(task.campaign_id, {})
        if task.subtasks:
            await self._process_subtasks(task, settings)
            return

        if task.delay_before_sec > 0:
            await asyncio.sleep(task.delay_before_sec)

        await self._send_single(task, settings, reply_to=None)
        await self._sleep_with_jitter(settings)

    async def _process_subtasks(self, task: SendTask, settings: dict) -> None:
        reply_to: int | None = None
        for sub in task.subtasks or []:
            if task.campaign_id in self.stopped_campaigns:
                break
            while task.campaign_id in self.paused_campaigns:
                await asyncio.sleep(1)
            if sub.delay_before_sec > 0:
                await asyncio.sleep(sub.delay_before_sec)
            sub_task = SendTask(
                campaign_id=task.campaign_id,
                account_id=sub.account_id,
                chat_id=task.chat_id,
                text=sub.text,
                step_no=sub.step_no,
            )
            reply_to = await self._send_single(
                sub_task,
                settings,
                reply_to=reply_to if sub.reply_to_prev else None,
            )
            await self._sleep_with_jitter(settings)

    async def _send_single(
        self,
        task: SendTask,
        settings: dict,
        reply_to: int | None,
    ) -> int | None:
        try:
            self.guard.assert_safe_content(task.text)
            async with SessionLocal() as session:
                limiter = SendRateLimiter(session, self._policy)
                await limiter.assert_allowed(task.account_id, task.chat_id, settings)
                account = await session.get(Account, task.account_id)
                chat = await session.get(Chat, task.chat_id)
                if not account or not chat:
                    raise ComplianceError("Account or chat not found.")
                self.guard.validate_send_permissions(chat.can_send, chat.type)
                try:
                    message_id = await self.telethon_adapter.send_group_message(
                        account, chat, task.text, reply_to=reply_to
                    )
                except Exception as error:  # noqa: BLE001
                    raise self.telethon_adapter.normalize_error(error) from error
            await self._save_attempt(task, "sent_ok", None, None)
            return message_id
        except ComplianceError as error:
            await self._save_attempt(
                task,
                "skipped" if "limit" in str(error).lower() else "failed",
                "compliance",
                str(error),
            )
            return None
        except Exception as error:  # noqa: BLE001
            await self._handle_send_exception(task, error, settings)
            return None

    async def _handle_send_exception(self, task: SendTask, error: Exception, settings: dict) -> None:
        message = str(error).lower()
        if "floodwait" in message:
            wait_seconds = self._extract_floodwait_seconds(message)
            wait_seconds += get_settings().floodwait_buffer_sec
            logger.warning("FloodWait detected", extra={"campaign_id": task.campaign_id})
            await self._save_attempt(task, "failed", "floodwait", str(error))
            await asyncio.sleep(wait_seconds)
            await self._retry(task, settings)
            return
        if "chatwriteforbidden" in message or "userbannedinchannel" in message:
            await self._save_attempt(task, "skipped", "chat_permission_denied", str(error))
            await self._record_agent_error(task, error)
            return
        await self._save_attempt(task, "failed", "unknown", str(error))
        await self._record_agent_error(task, error)

    @staticmethod
    async def _record_agent_error(task: SendTask, error: Exception) -> None:
        settings = get_settings()
        if not settings.ai_agent_enabled:
            return
        try:
            from app.infrastructure.agent.error_store import error_store

            await error_store.record(
                source="sender",
                level="ERROR",
                message=str(error),
                exc=error,
                context={
                    "campaign_id": task.campaign_id,
                    "account_id": task.account_id,
                    "chat_id": task.chat_id,
                },
            )
        except Exception:  # noqa: BLE001
            pass

    async def _retry(self, task: SendTask, settings: dict) -> None:
        retries = int(settings.get("retry_count", 0))
        backoff = int(settings.get("retry_backoff_sec", 30))
        for _ in range(retries):
            try:
                await asyncio.sleep(backoff)
                await self._send_single(task, settings, reply_to=None)
                return
            except Exception as error:  # noqa: BLE001
                await self._save_attempt(task, "failed", "retry_error", str(error))

    async def _save_attempt(
        self,
        task: SendTask,
        status: str,
        error_code: str | None,
        error_text: str | None,
    ) -> None:
        async with SessionLocal() as session:
            attempt = SendAttempt(
                campaign_id=task.campaign_id,
                account_id=task.account_id,
                chat_id=task.chat_id,
                step_no=task.step_no,
                status=status,
                error_code=error_code,
                error_text=error_text,
            )
            session.add(attempt)
            await session.commit()

    def _extract_floodwait_seconds(self, message: str) -> int:
        digits = "".join(ch for ch in message if ch.isdigit())
        return int(digits) if digits else 10

    async def _sleep_with_jitter(self, settings: dict) -> None:
        min_delay = int(settings.get("min_delay_msg", 15))
        max_delay = int(settings.get("max_delay_msg", 30))
        if min_delay > max_delay:
            min_delay, max_delay = max_delay, min_delay
        jitter_percent = int(settings.get("jitter_percent", 20))
        base = random.randint(min_delay, max(max_delay, min_delay))
        jitter = int(base * (jitter_percent / 100))
        await asyncio.sleep(max(1, base + random.randint(-jitter, jitter)))

    @staticmethod
    def settings_to_dict(settings: CampaignSettings) -> dict[str, Any]:
        return {
            "min_delay_msg": settings.min_delay_msg,
            "max_delay_msg": settings.max_delay_msg,
            "min_delay_chat": settings.min_delay_chat,
            "max_delay_chat": settings.max_delay_chat,
            "active_hours": settings.active_hours,
            "max_per_acc_hour": settings.max_per_acc_hour,
            "max_per_chat_day": settings.max_per_chat_day,
            "cooldown_hours": settings.cooldown_hours,
            "jitter_percent": settings.jitter_percent,
            "retry_count": settings.retry_count,
            "retry_backoff_sec": settings.retry_backoff_sec,
            "scheduled_at": getattr(settings, "scheduled_at", None),
        }
