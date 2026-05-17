from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.chat_repository import ChatRepository

router = Router()


@router.message(Command("chats"))
async def chats_handler(message: Message) -> None:
    async with SessionLocal() as session:
        chats = await ChatRepository(session).list_compliant_chats()
    if not chats:
        await message.answer(
            "No compliant chats.\n"
            "Add manually: /chat_add <tg_chat_id> <title> <type> [can_send:1]\n"
            "Add via link: /join <account_id> <@user|t.me/link>"
        )
        return
    lines = [
        f"#{c.id} tg={c.tg_chat_id} {c.title} type={c.type} can_send={int(c.can_send)}"
        for c in chats[:30]
    ]
    await message.answer("Compliant chats:\n" + "\n".join(lines))


@router.message(Command("chat_add"))
async def chat_add_handler(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=4)
    if len(parts) < 4:
        await message.answer("Usage: /chat_add <tg_chat_id> <title> <type> [can_send:0|1]")
        return
    tg_chat_id = int(parts[1])
    title = parts[2]
    chat_type = parts[3].lower()
    can_send = True
    if len(parts) > 4:
        can_send = parts[4] in {"1", "true", "yes"}
    from app.container import get_container
    from app.infrastructure.db.models import Chat
    from app.services.compliance_guard import ComplianceError

    try:
        get_container().guard.validate_chat_type(chat_type)
    except ComplianceError as error:
        await message.answer(str(error))
        return

    async with SessionLocal() as session:
        chat = Chat(
            tg_chat_id=tg_chat_id,
            title=title,
            type=chat_type,
            can_send=can_send,
            is_archived=False,
            is_blacklisted=False,
        )
        session.add(chat)
        await session.commit()
        await session.refresh(chat)
    await message.answer(f"Chat #{chat.id} added.")
