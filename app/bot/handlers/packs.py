from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.infrastructure.db.models import AccountPack, AccountPackItem
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.account_pack_repository import AccountPackRepository
from sqlalchemy import select

router = Router()


@router.message(Command("packs"))
async def packs_handler(message: Message) -> None:
    async with SessionLocal() as session:
        packs = await AccountPackRepository(session).list_packs()
        lines = []
        for pack in packs:
            account_ids = await AccountPackRepository(session).resolve_account_ids([pack.id])
            lines.append(f"#{pack.id} {pack.name} accounts={account_ids}")
    if not lines:
        await message.answer("No packs. Create: /pack_add <name> | /pack_bind <pack_id> <acc_id>")
        return
    await message.answer("Packs:\n" + "\n".join(lines))


@router.message(Command("pack_add"))
async def pack_add_handler(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /pack_add <name>")
        return
    async with SessionLocal() as session:
        pack = AccountPack(name=parts[1])
        session.add(pack)
        await session.commit()
        await session.refresh(pack)
    await message.answer(f"Pack #{pack.id} created.")


@router.message(Command("pack_bind"))
async def pack_bind_handler(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("Usage: /pack_bind <pack_id> <account_id>")
        return
    pack_id, account_id = int(parts[1]), int(parts[2])
    async with SessionLocal() as session:
        session.add(AccountPackItem(pack_id=pack_id, account_id=account_id))
        await session.commit()
    await message.answer(f"Account {account_id} bound to pack {pack_id}.")
