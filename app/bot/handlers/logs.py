from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from sqlalchemy import select

from app.infrastructure.db.models import AuditEvent, JoinTask, WarmupRun
from app.infrastructure.db.session import SessionLocal

router = Router()


@router.message(Command("logs"))
async def logs_handler(message: Message) -> None:
    async with SessionLocal() as session:
        audit = await session.execute(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(10))
        joins = await session.execute(select(JoinTask).order_by(JoinTask.id.desc()).limit(5))
        warmups = await session.execute(select(WarmupRun).order_by(WarmupRun.id.desc()).limit(5))

    audit_lines = [f"{e.action} by {e.actor_id} at {e.created_at}" for e in audit.scalars().all()]
    join_lines = [f"#{j.id} acc={j.account_id} {j.chat_username} -> {j.status}" for j in joins.scalars().all()]
    warmup_lines = [f"#{w.id} acc={w.account_id} mode={w.mode} -> {w.status}" for w in warmups.scalars().all()]

    await message.answer(
        "Recent audit:\n" + ("\n".join(audit_lines) or "none") + "\n\n"
        "Join tasks:\n" + ("\n".join(join_lines) or "none") + "\n\n"
        "Warmup runs:\n" + ("\n".join(warmup_lines) or "none")
    )
