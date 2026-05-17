from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.container import get_container
from app.infrastructure.db.session import SessionLocal
from app.services.audit_service import AuditService
from app.services.joiner_service import JoinerService

router = Router()


@router.message(Command("join_open_chats"))
async def join_open_chats_handler(message: Message) -> None:
    await message.answer(
        "Join and add chat to pool:\n"
        "/join <account_id> <target>\n"
        "/chat_add_link <account_id> <target>\n\n"
        "Target examples:\n"
        "- @channelname\n"
        "- channelname\n"
        "- https://t.me/channelname\n"
        "- https://t.me/+inviteHash\n"
        "- https://t.me/joinchat/inviteHash"
    )


@router.message(Command("join", "chat_add_link"))
async def join_handler(message: Message) -> None:
    parts = (message.text or "").strip().split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer(
            "Usage: /join <account_id> <@username|t.me/link|invite>\n"
            "Alias: /chat_add_link <account_id> <target>"
        )
        return

    account_id = int(parts[1])
    raw_target = parts[2]
    container = get_container()
    actor_id = message.from_user.id if message.from_user else 0

    try:
        parsed = container.guard.parse_join_target(raw_target)
    except Exception as error:  # noqa: BLE001
        await message.answer(f"Invalid target format: {error}")
        return

    try:
        async with SessionLocal() as session:
            service = JoinerService(session, container.guard, container.telethon_adapter)
            task = await service.queue_join(account_id, raw_target)
            await AuditService(session).log(
                actor_id,
                "join.queue",
                {
                    "task_id": task.id,
                    "account_id": account_id,
                    "target": parsed.storage_key,
                    "raw": raw_target,
                },
            )
            task_id = task.id
        await JoinerService.run_join_async_static(task_id, notify_user_id=actor_id)
        await message.answer(
            f"Join started (task #{task_id}).\n"
            f"Normalized target: {parsed.storage_key}\n"
            "You will get a message when join finishes."
        )
    except Exception as error:  # noqa: BLE001
        await message.answer(f"Join rejected: {error}")


@router.message(Command("chat_add_link_sync"))
async def chat_add_link_sync_handler(message: Message) -> None:
    """Join immediately and return chat id (blocking)."""
    parts = (message.text or "").strip().split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer("Usage: /chat_add_link_sync <account_id> <target>")
        return

    account_id = int(parts[1])
    raw_target = parts[2]
    container = get_container()
    actor_id = message.from_user.id if message.from_user else 0

    try:
        async with SessionLocal() as session:
            service = JoinerService(session, container.guard, container.telethon_adapter)
            task, chat, parsed = await service.join_and_add(account_id, raw_target)
            await AuditService(session).log(
                actor_id,
                "chat.add_link",
                {"task_id": task.id, "chat_id": chat.id, "target": parsed.storage_key},
            )
        await message.answer(
            f"Chat added to pool #{chat.id}\n"
            f"- title: {chat.title}\n"
            f"- tg_chat_id: {chat.tg_chat_id}\n"
            f"- type: {chat.type}\n"
            f"- can_send: {int(chat.can_send)}\n"
            f"- normalized: {parsed.storage_key}"
        )
    except Exception as error:  # noqa: BLE001
        await message.answer(f"Failed to add chat: {error}")
