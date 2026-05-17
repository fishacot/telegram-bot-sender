from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.menu import BTN_CANCEL, main_menu_keyboard
from app.bot.states.account_states import AccountUploadState
from app.bot.texts import ru as texts
from app.config import get_settings
from app.container import get_container
from app.infrastructure.db.models import Account
from app.infrastructure.db.session import SessionLocal
from app.services.account_import_service import AccountImportError, AccountImportService
from app.services.audit_service import AuditService
from sqlalchemy import select

router = Router()


@router.message(Command("accounts"))
async def accounts_handler(message: Message) -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(Account).order_by(Account.id))
        accounts = list(result.scalars().all())
    if not accounts:
        await message.answer(
            "👤 Аккаунтов пока нет.\n"
            "Меню → <b>👤 Аккаунты</b> → <b>➕ Загрузить .session</b>"
        )
        return
    lines = [
        f"#{a.id} {a.name} role={a.role} health={a.health_status} session={a.session_path}"
        for a in accounts
    ]
    await message.answer("Accounts:\n" + "\n".join(lines))


@router.message(Command("account_upload"))
async def account_upload_handler(message: Message, state: FSMContext) -> None:
    parts = (message.text or "").split()
    session_name = parts[1] if len(parts) > 1 else None
    role = parts[2] if len(parts) > 2 else "lead"

    if session_name:
        try:
            session_name = AccountImportService.normalize_session_name(session_name)
        except AccountImportError as error:
            await message.answer(str(error))
            return
        await state.set_state(AccountUploadState.waiting_file)
        await state.update_data(session_name=session_name, role=role)
        await message.answer(
            f"Send the `.session` file for account `{session_name}` (role: {role}).\n"
            "Cancel: /cancel"
        )
        return

    await state.set_state(AccountUploadState.waiting_file)
    await state.update_data(session_name=None, role="lead")
    await message.answer(
        "Send a `.session` file.\n"
        "Caption format: `acc1` or `acc1 support`\n"
        "Or use: /account_upload acc1 lead\n"
        "Cancel: /cancel"
    )


@router.message(Command("cancel"), StateFilter(AccountUploadState.waiting_file))
async def account_upload_cancel_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Session upload cancelled.")


@router.message(StateFilter(AccountUploadState.waiting_file), F.text == BTN_CANCEL)
async def account_upload_cancel_text(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())


@router.message(StateFilter(AccountUploadState.waiting_file), F.document)
async def account_upload_file_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    session_name = data.get("session_name")
    role = data.get("role", "lead")

    if not session_name and message.caption:
        caption_parts = message.caption.strip().split()
        if caption_parts:
            try:
                session_name = AccountImportService.normalize_session_name(caption_parts[0])
                if len(caption_parts) > 1:
                    role = caption_parts[1]
            except AccountImportError as error:
                await message.answer(str(error))
                return

    if not session_name:
        stem = (message.document.file_name or "").removesuffix(".session")
        try:
            session_name = AccountImportService.normalize_session_name(stem)
        except AccountImportError:
            await message.answer(
                "Could not detect account name. Use:\n"
                "/account_upload acc1 lead\n"
                "or caption: acc1 lead"
            )
            return

    settings = get_settings()
    actor_id = message.from_user.id if message.from_user else 0

    try:
        async with SessionLocal() as db_session:
            service = AccountImportService(db_session, settings)
            account, telegram_user = await service.import_from_message(
                message.bot,
                message,
                session_name=session_name,
                role=role,
            )
            await AuditService(db_session).log(
                actor_id,
                "account.upload_session",
                {"account_id": account.id, "name": account.name, "telegram": telegram_user},
            )
        await get_container().telethon_adapter.invalidate_account_client(account.id)
        await state.clear()
        await message.answer(
            f"✅ Аккаунт #{account.id} добавлен\n"
            f"Имя: {account.name} | Роль: {account.role}\n"
            f"Telegram: {telegram_user}",
            reply_markup=main_menu_keyboard(),
        )
    except AccountImportError as error:
        await message.answer(f"Upload failed: {error}")
    except Exception as error:  # noqa: BLE001
        await message.answer(f"Upload failed: {error}")


@router.message(Command("account_add"))
async def account_add_handler(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer(
            "Usage: /account_add <name> <session_path> [role]\n"
            "Easier: /account_upload <name> [role] + send .session file"
        )
        return
    name, session_path = parts[1], parts[2]
    role = parts[3] if len(parts) > 3 else "lead"
    async with SessionLocal() as session:
        existing = await session.execute(select(Account).where(Account.name == name))
        if existing.scalar_one_or_none():
            await message.answer("Account with this name already exists.")
            return
        account = Account(
            name=name,
            session_path=session_path,
            role=role,
            is_active=True,
            health_status="active",
        )
        session.add(account)
        await session.commit()
        await session.refresh(account)
    await message.answer(f"Account #{account.id} added: {name} ({session_path})")
