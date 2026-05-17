from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.container import get_container
from app.infrastructure.db.session import SessionLocal
from app.services.audit_service import AuditService
from app.services.warmup_service import WarmupService

router = Router()


@router.message(Command("warmup"))
async def warmup_handler(message: Message) -> None:
    await message.answer(
        "Warmup commands:\n"
        "/warmup_start <account_id> <soft|normal|custom>\n"
        "/warmup_stop <run_id>"
    )


@router.message(Command("warmup_start"))
async def warmup_start_handler(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) != 3 or not parts[1].isdigit():
        await message.answer("Usage: /warmup_start <account_id> <soft|normal|custom>")
        return
    account_id = int(parts[1])
    mode = parts[2]
    container = get_container()
    actor_id = message.from_user.id if message.from_user else 0
    async with SessionLocal() as session:
        run = await WarmupService(session, container.guard, container.telethon_adapter).start(
            account_id, mode
        )
        await AuditService(session).log(actor_id, "warmup.start", {"run_id": run.id, "account_id": account_id})
    await message.answer(f"Warmup run #{run.id} started for account {account_id}.")


@router.message(Command("warmup_stop"))
async def warmup_stop_handler(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Usage: /warmup_stop <run_id>")
        return
    run_id = int(parts[1])
    container = get_container()
    async with SessionLocal() as session:
        await WarmupService(session, container.guard, container.telethon_adapter).stop(run_id)
    await message.answer(f"Warmup run #{run_id} stopped.")
