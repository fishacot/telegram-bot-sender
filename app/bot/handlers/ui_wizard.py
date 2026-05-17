from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards.inline import (
    accounts_pick_keyboard,
    campaign_confirm_keyboard,
    campaign_preset_keyboard,
    campaigns_control_keyboard,
    chats_multiselect_keyboard,
    templates_pick_keyboard,
)
from app.bot.keyboards.menu import (
    BTN_CANCEL,
    cancel_row_keyboard,
    main_menu_keyboard,
    section_accounts_keyboard,
    section_chats_keyboard,
    section_templates_keyboard,
)
from app.bot.states.account_states import AccountUploadState
from app.bot.states.ui_states import CampaignUIState, ChatUIState, TemplateUIState
from app.bot.texts import ru as texts
from app.config import get_settings
from app.container import get_container
from app.infrastructure.ai_provider.stub_provider import StubAiProvider
from app.infrastructure.db.models import Account, Campaign, Chat, Template
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.chat_repository import ChatRepository
from app.services.ai_assistant_service import AiAssistantService
from app.services.audit_service import AuditService
from app.services.campaign_service import CampaignService
from app.services.compliance_guard import ComplianceError
from app.services.joiner_service import JoinerService

router = Router()

PRESETS = {
    "safe": {"min_delay_msg": 15, "max_delay_msg": 30, "max_per_acc_hour": 5, "mode": "single"},
    "fast": {"min_delay_msg": 10, "max_delay_msg": 20, "max_per_acc_hour": 10, "mode": "single"},
}


async def _load_accounts() -> list[Account]:
    async with SessionLocal() as session:
        result = await session.execute(select(Account).where(Account.is_active.is_(True)).order_by(Account.id))
        return list(result.scalars().all())


async def _load_chats() -> list[Chat]:
    async with SessionLocal() as session:
        return await ChatRepository(session).list_compliant_chats()


async def _load_templates() -> list[Template]:
    async with SessionLocal() as session:
        result = await session.execute(select(Template).where(Template.is_active.is_(True)).order_by(Template.id))
        return list(result.scalars().all())


async def show_accounts_section(message: Message) -> None:
    accounts = await _load_accounts()
    if not accounts:
        body = "👤 <b>Аккаунты</b>\n\nПока пусто. Загрузите файл сессии Telethon (.session)."
    else:
        lines = [f"#{a.id} <b>{a.name}</b> — {a.role}" for a in accounts]
        body = "👤 <b>Аккаунты</b>\n\n" + "\n".join(lines)
    await message.answer(body, reply_markup=section_accounts_keyboard())


async def show_chats_section(message: Message) -> None:
    chats = await _load_chats()
    if not chats:
        body = "💬 <b>Чаты</b>\n\nПока пусто. Добавьте группу по ссылке или @username."
    else:
        lines = [
            f"#{c.id} {c.title} (отправка: {'да' if c.can_send else 'нет'})" for c in chats[:20]
        ]
        body = "💬 <b>Чаты</b>\n\n" + "\n".join(lines)
    await message.answer(body, reply_markup=section_chats_keyboard())


async def show_templates_section(message: Message) -> None:
    templates = await _load_templates()
    if not templates:
        body = "📝 <b>Шаблоны</b>\n\nПока пусто. Создайте текст сообщения."
    else:
        lines = [f"#{t.id} <b>{t.name}</b>" for t in templates]
        body = "📝 <b>Шаблоны</b>\n\n" + "\n".join(lines)
    await message.answer(body, reply_markup=section_templates_keyboard())


async def start_account_upload(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AccountUploadState.waiting_file)
    await state.update_data(session_name=None, role="lead")
    if callback.message:
        await callback.message.answer(
            "📎 Отправьте файл <code>.session</code>\n\n"
            "Подпись к файлу: <code>acc1</code> или <code>acc1 support</code>\n"
            "Или сначала: /account_upload acc1 lead",
            reply_markup=cancel_row_keyboard(),
        )


async def start_chat_add(callback: CallbackQuery, state: FSMContext) -> None:
    accounts = await _load_accounts()
    if not accounts:
        if callback.message:
            await callback.message.answer(texts.NO_ACCOUNTS, reply_markup=main_menu_keyboard())
        return
    await state.set_state(ChatUIState.pick_account)
    if callback.message:
        await callback.message.answer(
            "Выберите аккаунт, который вступит в группу:",
            reply_markup=accounts_pick_keyboard(accounts, prefix="chat"),
        )


async def start_template_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TemplateUIState.wait_name)
    if callback.message:
        await callback.message.answer(
            "Введите <b>название</b> шаблона (например: promo):",
            reply_markup=cancel_row_keyboard(),
        )


async def start_campaign_wizard(message: Message, state: FSMContext) -> None:
    accounts = await _load_accounts()
    chats = await _load_chats()
    templates = await _load_templates()
    if not accounts:
        await message.answer(texts.NO_ACCOUNTS, reply_markup=main_menu_keyboard())
        return
    if not chats:
        await message.answer(texts.NO_CHATS, reply_markup=main_menu_keyboard())
        return
    if not templates:
        await message.answer(texts.NO_TEMPLATES, reply_markup=main_menu_keyboard())
        return

    await state.clear()
    await state.set_state(CampaignUIState.pick_account)
    await state.update_data(selected_chat_ids=[], account_id=None, template_id=None)
    await message.answer(
        "📤 <b>Новая рассылка</b> — шаг 1 из 4\n\nВыберите аккаунт-отправитель:",
        reply_markup=accounts_pick_keyboard(accounts, prefix="cu"),
    )


async def show_campaigns_list(message: Message) -> None:
    container = get_container()
    async with SessionLocal() as session:
        service = CampaignService(session, container.guard, container.sender_service)
        campaigns = await service.list_campaigns()
    if not campaigns:
        await message.answer("📋 Рассылок пока нет.\nНажмите 📤 Новая рассылка.", reply_markup=main_menu_keyboard())
        return
    for item in campaigns[:5]:
        await message.answer(
            f"#{item.id} <b>{item.name}</b>\nРежим: {item.mode}\nСтатус: <b>{item.status}</b>",
            reply_markup=campaigns_control_keyboard(item.id),
        )


# --- Campaign UI callbacks ---


@router.callback_query(F.data.startswith("cu:acc:"))
async def cu_pick_account(callback: CallbackQuery, state: FSMContext) -> None:
    account_id = int(callback.data.split(":")[-1])
    await state.update_data(account_id=account_id, selected_chat_ids=[])
    await state.set_state(CampaignUIState.pick_chats)
    chats = await _load_chats()
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            "📤 Шаг 2 из 4\n\nВыберите чаты (можно несколько), затем «Готово»:",
            reply_markup=chats_multiselect_keyboard(chats, set()),
        )


@router.callback_query(F.data.startswith("cu:cht:"))
async def cu_toggle_chat(callback: CallbackQuery, state: FSMContext) -> None:
    part = callback.data.split(":")[-1]
    data = await state.get_data()
    selected = set(data.get("selected_chat_ids", []))
    if part == "done":
        if not selected:
            await callback.answer("Выберите хотя бы один чат", show_alert=True)
            return
        await state.set_state(CampaignUIState.pick_template)
        templates = await _load_templates()
        await callback.answer()
        if callback.message:
            await callback.message.edit_text(
                "📤 Шаг 3 из 4\n\nВыберите шаблон сообщения:",
                reply_markup=templates_pick_keyboard(templates),
            )
        return

    chat_id = int(part)
    if chat_id in selected:
        selected.remove(chat_id)
    else:
        selected.add(chat_id)
    await state.update_data(selected_chat_ids=list(selected))
    chats = await _load_chats()
    await callback.answer()
    if callback.message:
        await callback.message.edit_reply_markup(
            reply_markup=chats_multiselect_keyboard(chats, selected),
        )


@router.callback_query(F.data.startswith("cu:tpl:"))
async def cu_pick_template(callback: CallbackQuery, state: FSMContext) -> None:
    template_id = int(callback.data.split(":")[-1])
    await state.update_data(template_id=template_id)
    await state.set_state(CampaignUIState.pick_preset)
    await callback.answer()
    if callback.message:
        await callback.message.edit_text(
            "📤 Шаг 4 из 4\n\nВыберите скорость отправки:",
            reply_markup=campaign_preset_keyboard(),
        )


@router.callback_query(F.data.startswith("cu:preset:"))
async def cu_pick_preset(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":")[-1]
    preset = PRESETS.get(key)
    if not preset:
        await callback.answer("Неизвестный режим")
        return

    settings = {
        "min_delay_msg": preset["min_delay_msg"],
        "max_delay_msg": preset["max_delay_msg"],
        "min_delay_chat": 30,
        "max_delay_chat": 90,
        "active_hours": "9-21",
        "max_per_acc_hour": preset["max_per_acc_hour"],
        "max_per_chat_day": 3,
        "cooldown_hours": 24,
        "jitter_percent": 20,
        "retry_count": 2,
        "retry_backoff_sec": 30,
    }
    container = get_container()
    try:
        container.guard.validate_campaign_limits(settings)
    except ComplianceError as error:
        await callback.answer(str(error), show_alert=True)
        return

    data = await state.get_data()
    allowed: list[int] = []
    excluded: list[str] = []
    async with SessionLocal() as session:
        for chat_id in data.get("selected_chat_ids", []):
            chat = await session.get(Chat, chat_id)
            if not chat:
                excluded.append(f"{chat_id}:нет")
                continue
            try:
                container.guard.validate_send_permissions(chat.can_send, chat.type)
                if chat.is_blacklisted or chat.is_archived:
                    raise ComplianceError("archived")
                allowed.append(chat_id)
            except ComplianceError as error:
                excluded.append(f"{chat_id}:{error}")

    await state.update_data(
        settings=settings,
        campaign_mode=preset["mode"],
        allowed_chat_ids=allowed,
        excluded_chats=excluded,
    )
    await state.set_state(CampaignUIState.confirm)
    await callback.answer()
    if callback.message:
        account_id = data.get("account_id")
        template_id = data.get("template_id")
        await callback.message.edit_text(
            "📋 <b>Проверка перед запуском</b>\n\n"
            f"Аккаунт: #{account_id}\n"
            f"Шаблон: #{template_id}\n"
            f"Чатов выбрано: {len(data.get('selected_chat_ids', []))}\n"
            f"Можно отправить: {len(allowed)}\n"
            f"Исключено: {len(excluded)}\n"
            f"Задержка: {settings['min_delay_msg']}–{settings['max_delay_msg']} сек\n\n"
            "Запустить рассылку?",
            reply_markup=campaign_confirm_keyboard(),
        )


@router.callback_query(F.data == "cu:confirm")
async def cu_confirm_launch(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("allowed_chat_ids"):
        await callback.answer("Нет подходящих чатов", show_alert=True)
        return

    actor_id = callback.from_user.id if callback.from_user else 0
    container = get_container()
    try:
        async with SessionLocal() as session:
            service = CampaignService(session, container.guard, container.sender_service)
            account_ids = [int(data["account_id"])]
            campaign = await service.create_campaign(
                name=f"Рассылка {datetime.utcnow():%d.%m %H:%M}",
                mode=data.get("campaign_mode", "single"),
                template_id=int(data["template_id"]),
                created_by=actor_id,
                account_ids=account_ids,
                chat_ids=data["allowed_chat_ids"],
                settings=data["settings"],
            )
            queued = await service.run_campaign(campaign.id, confirmed=True)
            await AuditService(session).log(
                actor_id,
                "campaign.run.ui",
                {"campaign_id": campaign.id, "queued": queued},
            )
    except (ComplianceError, ValueError) as error:
        await callback.answer()
        if callback.message:
            await callback.message.answer(f"❌ Ошибка: {error}", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    await state.clear()
    await callback.answer("Рассылка запущена!")
    if callback.message:
        await callback.message.answer(
            f"✅ Рассылка #{campaign.id} запущена.\n"
            f"В очереди: {queued} сообщ.\n\n"
            "Смотрите 📋 Мои рассылки",
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(F.data == "cu:cancel")
async def cu_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    if callback.message:
        await callback.message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())


# --- Chat add flow ---


@router.callback_query(F.data == "chat:cancel")
async def chat_flow_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    if callback.message:
        await callback.message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())


@router.callback_query(F.data.startswith("chat:acc:"))
async def chat_pick_account(callback: CallbackQuery, state: FSMContext) -> None:
    account_id = int(callback.data.split(":")[-1])
    await state.update_data(account_id=account_id)
    await state.set_state(ChatUIState.wait_link)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "Вставьте ссылку или @username группы:\n"
            "• @mygroup\n"
            "• https://t.me/mygroup\n"
            "• https://t.me/+invite",
            reply_markup=cancel_row_keyboard(),
        )


@router.message(StateFilter(ChatUIState.wait_link))
async def chat_wait_link(message: Message, state: FSMContext) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())
        return

    raw = (message.text or "").strip()
    if not raw:
        await message.answer("Отправьте ссылку или @username.")
        return

    data = await state.get_data()
    account_id = int(data["account_id"])
    container = get_container()
    actor_id = message.from_user.id if message.from_user else 0

    try:
        async with SessionLocal() as session:
            service = JoinerService(session, container.guard, container.telethon_adapter)
            task, chat, parsed = await service.join_and_add(account_id, raw)
            await AuditService(session).log(
                actor_id,
                "chat.add.ui",
                {"chat_id": chat.id, "target": parsed.storage_key},
            )
        await state.clear()
        await message.answer(
            f"✅ Чат добавлен #{chat.id}\n"
            f"{chat.title}\n"
            f"Можно писать: {'да' if chat.can_send else 'нет'}",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as error:  # noqa: BLE001
        await message.answer(f"❌ Не удалось добавить чат:\n{error}", reply_markup=main_menu_keyboard())
        await state.clear()


# --- Template add flow ---


@router.message(StateFilter(TemplateUIState.wait_name))
async def template_wait_name(message: Message, state: FSMContext) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())
        return
    name = (message.text or "").strip()
    if not name or len(name) > 64:
        await message.answer("Введите короткое название (до 64 символов).")
        return
    await state.update_data(template_name=name)
    await state.set_state(TemplateUIState.wait_body)
    await message.answer("Теперь отправьте <b>текст сообщения</b> для рассылки:")


@router.message(StateFilter(TemplateUIState.wait_body))
async def template_wait_body(message: Message, state: FSMContext) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())
        return
    body = (message.text or "").strip()
    if not body:
        await message.answer("Текст не может быть пустым.")
        return
    data = await state.get_data()
    name = data["template_name"]
    async with SessionLocal() as session:
        template = Template(name=name, kind="text", body=body, variables_json={}, is_active=True)
        session.add(template)
        await session.commit()
        await session.refresh(template)
    await state.clear()
    await message.answer(
        f"✅ Шаблон #{template.id} «{template.name}» сохранён.",
        reply_markup=main_menu_keyboard(),
    )


# --- Campaign controls from list ---


@router.callback_query(F.data.startswith("cmp:pause:"))
async def cmp_pause(callback: CallbackQuery) -> None:
    cid = int(callback.data.split(":")[-1])
    container = get_container()
    async with SessionLocal() as session:
        await CampaignService(session, container.guard, container.sender_service).pause(cid)
    await callback.answer("Пауза")


@router.callback_query(F.data.startswith("cmp:resume:"))
async def cmp_resume(callback: CallbackQuery) -> None:
    cid = int(callback.data.split(":")[-1])
    container = get_container()
    async with SessionLocal() as session:
        await CampaignService(session, container.guard, container.sender_service).resume(cid)
    await callback.answer("Продолжено")


@router.callback_query(F.data.startswith("cmp:stop:"))
async def cmp_stop(callback: CallbackQuery) -> None:
    cid = int(callback.data.split(":")[-1])
    container = get_container()
    async with SessionLocal() as session:
        await CampaignService(session, container.guard, container.sender_service).stop(cid)
    await callback.answer("Остановлено")


@router.callback_query(F.data.startswith("cmp:report:"))
async def cmp_report(callback: CallbackQuery) -> None:
    cid = int(callback.data.split(":")[-1])
    from app.services.report_service import ReportService

    async with SessionLocal() as session:
        summary = await ReportService(session).build_campaign_summary(cid)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            f"📊 Отчёт #{cid}\n"
            f"Отправлено: {summary.get('sent_ok', 0)}\n"
            f"Ошибки: {summary.get('failed', 0)}\n"
            f"Пропущено: {summary.get('skipped', 0)}"
        )
