from __future__ import annotations

import logging
from pathlib import Path

from telethon import TelegramClient, utils
from telethon.errors import (
    ChatWriteForbiddenError,
    FloodWaitError,
    UserAlreadyParticipantError,
    UserBannedInChannelError,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import Channel, Chat, User

from app.domain.chat_target import ChatTargetKind, ParsedChatTarget
from app.infrastructure.db.models import Account
from app.infrastructure.db.models import Chat as ChatModel
from app.infrastructure.telethon_clients.factory import TelethonClientFactory
from app.services.compliance_guard import ComplianceError

logger = logging.getLogger(__name__)


class TelethonSenderAdapter:
    def __init__(self, factory: TelethonClientFactory) -> None:
        self.factory = factory
        self._clients: dict[int, TelegramClient] = {}

    async def send_group_message(
        self,
        account: Account,
        chat: ChatModel,
        text: str,
        reply_to: int | None = None,
    ) -> int:
        client = await self._get_client(account)
        message = await client.send_message(chat.tg_chat_id, text, reply_to=reply_to)
        return message.id

    async def join_chat(self, account: Account, target: ParsedChatTarget) -> dict:
        client = await self._get_client(account)
        entity = await self._resolve_and_join(client, target)
        if isinstance(entity, User):
            raise ComplianceError("Target is a user dialog. Private/user outreach is forbidden.")

        tg_chat_id = utils.get_peer_id(entity)
        title = getattr(entity, "title", None) or target.display
        username = getattr(entity, "username", None)
        if username:
            username = f"@{username}"

        chat_type = "group"
        if isinstance(entity, Channel):
            chat_type = "channel" if entity.broadcast else "supergroup"
        elif isinstance(entity, Chat):
            chat_type = "group"

        can_send = await self._detect_can_send(client, entity)

        return {
            "tg_chat_id": tg_chat_id,
            "title": title,
            "username": username or target.storage_key,
            "type": chat_type,
            "can_send": can_send,
        }

    async def _resolve_and_join(self, client: TelegramClient, target: ParsedChatTarget):
        if target.kind == ChatTargetKind.INVITE and target.invite_hash:
            invite = target.invite_hash.lstrip("+")
            try:
                updates = await client(ImportChatInviteRequest(invite))
                if updates.chats:
                    return updates.chats[0]
            except Exception:  # noqa: BLE001
                pass
        entity = await client.get_entity(target.telethon_entity)
        if isinstance(entity, (Channel, Chat)):
            try:
                await client(JoinChannelRequest(entity))
            except UserAlreadyParticipantError:
                pass
        return entity

    async def _detect_can_send(self, client: TelegramClient, entity) -> bool:
        try:
            permissions = await client.get_permissions(entity)
            return bool(permissions and permissions.send_messages)
        except Exception:  # noqa: BLE001
            return True

    async def warmup_safe_activity(self, account: Account, max_dialogs: int = 5) -> list[str]:
        """Read-only safe warmup: scan group dialogs only, no PM outreach."""
        client = await self._get_client(account)
        logs: list[str] = []
        count = 0
        async for dialog in client.iter_dialogs(limit=30):
            if count >= max_dialogs:
                break
            entity = dialog.entity
            if isinstance(entity, User):
                continue
            if dialog.is_group or dialog.is_channel:
                await client.get_messages(entity, limit=1)
                logs.append(f"read:{getattr(entity, 'title', dialog.id)}")
                count += 1
        return logs

    async def _get_client(self, account: Account) -> TelegramClient:
        if account.id not in self._clients:
            session_name = Path(account.session_path).stem
            client = self.factory.create(session_name)
            await client.connect()
            if not await client.is_user_authorized():
                raise RuntimeError(
                    f"Session '{account.name}' is not authorized. Run scripts/auth_session.py first."
                )
            self._clients[account.id] = client
        return self._clients[account.id]

    async def disconnect_all(self) -> None:
        for client in self._clients.values():
            if client.is_connected():
                await client.disconnect()
        self._clients.clear()

    async def invalidate_account_client(self, account_id: int) -> None:
        client = self._clients.pop(account_id, None)
        if client and client.is_connected():
            await client.disconnect()

    @staticmethod
    def normalize_error(error: Exception) -> Exception:
        if isinstance(error, FloodWaitError):
            return RuntimeError(f"FloodWait {error.seconds}")
        if isinstance(error, ChatWriteForbiddenError):
            return RuntimeError("ChatWriteForbidden")
        if isinstance(error, UserBannedInChannelError):
            return RuntimeError("UserBannedInChannel")
        return error
