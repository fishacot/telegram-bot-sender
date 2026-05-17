import io

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.menu import BTN_CANCEL, cancel_row_keyboard, main_menu_keyboard
from app.bot.states.account_states import AccountProxyState, AccountUploadState
from app.bot.texts import ru as texts
from app.config import get_settings
from app.container import get_container
from app.domain.proxy_url import BulkProxyAssignResult, ProxyParseError, mask_proxy_url
from app.infrastructure.db.models import Account
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.telethon_clients.factory import TelethonClientFactory
from app.services.account_import_service import AccountImportError, AccountImportService
from app.services.account_proxy_service import AccountProxyService
from app.services.audit_service import AuditService

router = Router()


def _make_proxy_service(session: AsyncSession) -> AccountProxyService:
    settings = get_settings()
    factory = TelethonClientFactory(
        sessions_dir=settings.sessions_dir,
        api_id=settings.telegram_api_id,
        api_hash=settings.telegram_api_hash,
        proxy_url=settings.telegram_proxy,
    )
    return AccountProxyService(session, factory)


async def _read_proxy_payload(message: Message) -> str:
    if message.document:
        name = (message.document.file_name or "").lower()
        if not name.endswith(".txt"):
            raise ValueError("Пришлите файл .txt со списком прокси (по одной строке).")
        buffer = io.BytesIO()
        await message.bot.download(message.document, destination=buffer)
        return buffer.getvalue().decode("utf-8", errors="replace")
    text = (message.text or "").strip()
    if not text:
        raise ValueError("Отправьте текст со списком прокси или файл .txt.")
    return text


def _format_bulk_result(result: BulkProxyAssignResult) -> str:
    lines = [f"✅ Обновлено аккаунтов: <b>{len(result.updated)}</b>"]
    for account_id, name, proxy_label in result.updated[:12]:
        lines.append(f"  #{account_id} <b>{name}</b> → {proxy_label}")
    if len(result.updated) > 12:
        lines.append(f"  … и ещё {len(result.updated) - 12}")
    if result.unchanged_account_names:
        names = ", ".join(result.unchanged_account_names[:8])
        suffix = "…" if len(result.unchanged_account_names) > 8 else ""
        lines.append(
            f"\n⚠️ Без изменений (не хватило строк в списке): {names}{suffix}"
        )
    if result.errors:
        lines.append("\n❌ Ошибки:")
        lines.extend(f"  • {err}" for err in result.errors[:8])
    return "\n".join(lines)


async def _invalidate_proxy_clients(account_ids: list[int]) -> None:
    adapter = get_container().telethon_adapter
    for account_id in account_ids:
        await adapter.invalidate_account_client(account_id)


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
                "Не удалось определить имя.\n"
                "Укажите в подписи к файлу: <code>acc1</code> или <code>acc1 support</code>"
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
        await message.answer(f"❌ {error}")
    except Exception as error:  # noqa: BLE001
        await message.answer(f"❌ Ошибка загрузки: {error}")


@router.callback_query(F.data.startswith("accproxy:acc:"))
async def accproxy_pick(callback: CallbackQuery, state: FSMContext) -> None:
    account_id = int(callback.data.split(":")[-1])
    await state.set_state(AccountProxyState.waiting_proxy)
    await state.update_data(proxy_account_id=account_id)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "Отправьте прокси одной строкой:\n"
            "<code>socks5://host:1080</code>\n"
            "<code>socks5://user:pass@host:1080</code>\n"
            "<code>http://host:8080</code>\n"
            "<code>host:443:secret</code> (MTProto)\n\n"
            "Сброс: <code>нет</code>",
            reply_markup=cancel_row_keyboard(),
        )


@router.callback_query(F.data == "accproxy:cancel")
async def accproxy_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())


@router.message(
    StateFilter(
        AccountProxyState.waiting_proxy,
        AccountProxyState.waiting_bulk,
        AccountProxyState.waiting_all,
    ),
    F.text == BTN_CANCEL,
)
async def accproxy_cancel_text(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())


@router.message(StateFilter(AccountProxyState.waiting_proxy))
async def accproxy_set_text(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    account_id = data.get("proxy_account_id")
    if not account_id:
        await state.clear()
        await message.answer("Сессия сброшена. Начните снова из меню Аккаунты.")
        return
    try:
        async with SessionLocal() as session:
            service = _make_proxy_service(session)
            account = await service.set_account_proxy(int(account_id), message.text or "")
            await AuditService(session).log(
                message.from_user.id if message.from_user else 0,
                "account.set_proxy",
                {"account_id": account.id, "proxy": mask_proxy_url(account.proxy)},
            )
    except ProxyParseError as error:
        await message.answer(f"❌ {error}")
        return
    except ValueError as error:
        await message.answer(f"❌ {error}")
        return
    await get_container().telethon_adapter.invalidate_account_client(int(account_id))
    await state.clear()
    await message.answer(
        f"✅ Прокси для #{account.id} <b>{account.name}</b>: {mask_proxy_url(account.proxy)}",
        reply_markup=main_menu_keyboard(),
    )


@router.message(StateFilter(AccountProxyState.waiting_bulk))
async def accproxy_bulk_input(message: Message, state: FSMContext) -> None:
    actor_id = message.from_user.id if message.from_user else 0
    try:
        payload = await _read_proxy_payload(message)
    except ValueError as error:
        await message.answer(str(error))
        return

    try:
        async with SessionLocal() as session:
            service = _make_proxy_service(session)
            result = await service.bulk_assign_by_order(payload)
            await AuditService(session).log(
                actor_id,
                "account.bulk_proxy",
                {"updated": len(result.updated), "errors": len(result.errors)},
            )
    except ProxyParseError as error:
        await message.answer(f"❌ {error}")
        return
    except ValueError as error:
        await message.answer(f"❌ {error}")
        return

    account_ids = [item[0] for item in result.updated]
    await _invalidate_proxy_clients(account_ids)
    await state.clear()
    await message.answer(_format_bulk_result(result), reply_markup=main_menu_keyboard())


@router.message(StateFilter(AccountProxyState.waiting_all))
async def accproxy_all_input(message: Message, state: FSMContext) -> None:
    actor_id = message.from_user.id if message.from_user else 0
    raw = (message.text or "").strip()
    if not raw:
        await message.answer("Отправьте одну строку с прокси.")
        return

    try:
        async with SessionLocal() as session:
            service = _make_proxy_service(session)
            result = await service.apply_proxy_to_all(raw)
            await AuditService(session).log(
                actor_id,
                "account.proxy_all",
                {"updated": len(result.updated)},
            )
    except ProxyParseError as error:
        await message.answer(f"❌ {error}")
        return
    except ValueError as error:
        await message.answer(f"❌ {error}")
        return

    account_ids = [item[0] for item in result.updated]
    await _invalidate_proxy_clients(account_ids)
    await state.clear()
    await message.answer(_format_bulk_result(result), reply_markup=main_menu_keyboard())
