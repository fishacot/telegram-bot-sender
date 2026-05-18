from __future__ import annotations

import math
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards.builders import (
    dashboard_inline_keyboard,
    CAMPAIGNS_PER_PAGE,
    PER_PAGE_DEFAULT,
    accounts_pick_keyboard,
    campaign_confirm_keyboard,
    campaign_detail_keyboard,
    campaign_preset_keyboard,
    campaigns_list_keyboard,
    chats_multiselect_keyboard,
    paginated_section_keyboard,
    section_accounts_keyboard,
    section_chats_keyboard,
    section_proxy_keyboard,
    section_templates_keyboard,
    setup_gap_keyboard,
    templates_pick_keyboard,
)
from app.bot.keyboards.menu import (
    BTN_CANCEL,
    cancel_row_keyboard,
    main_menu_keyboard,
)
from app.bot.states.account_states import AccountProxyState, AccountUploadState
from app.bot.states.ui_states import CampaignUIState, ChatUIState, TemplateUIState
from app.bot.texts import ru as texts
from app.bot.texts.errors_ru import humanize_error
from app.bot.ui.formatters import (
    build_setup_status,
    format_accounts_section,
    format_campaign_confirm,
    format_campaigns_list,
    format_chats_section,
    format_dashboard,
    format_templates_section,
    wizard_step,
)
from app.bot.ui.telegram_io import send_screen
from app.config import get_settings
from app.container import get_container
from app.infrastructure.db.models import Account, Campaign, Chat, Template
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.chat_repository import ChatRepository
from app.services.audit_service import AuditService
from app.services.campaign_service import CampaignService
from app.services.compliance_guard import ComplianceError
from app.services.joiner_service import JoinerService

router = Router()

PRESETS = {
    "safe": {"min_delay_msg": 15, "max_delay_msg": 30, "max_per_acc_hour": 5, "mode": "single"},
    "fast": {"min_delay_msg": 10, "max_delay_msg": 20, "max_per_acc_hour": 10, "mode": "single"},
}

WIZARD_TOTAL = 4


async def _load_accounts() -> list[Account]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Account).where(Account.is_active.is_(True)).order_by(Account.id)
        )
        return list(result.scalars().all())


async def _load_chats() -> list[Chat]:
    async with SessionLocal() as session:
        return await ChatRepository(session).list_compliant_chats()


async def _load_templates() -> list[Template]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Template).where(Template.is_active.is_(True)).order_by(Template.id)
        )
        return list(result.scalars().all())


async def _load_campaigns() -> list[Campaign]:
    container = get_container()
    async with SessionLocal() as session:
        service = CampaignService(session, container.guard, container.sender_service)
        return await service.list_campaigns()


async def _load_setup_status():
    accounts = await _load_accounts()
    chats = await _load_chats()
    templates = await _load_templates()
    campaigns = await _load_campaigns()
    return accounts, chats, templates, campaigns, build_setup_status(accounts, chats, templates, campaigns)


async def show_dashboard(message: Message, *, edit: bool = False) -> None:
    _, _, _, _, status = await _load_setup_status()
    steps = texts.FIRST_RUN_STEPS if not status.is_ready else ""
    text = format_dashboard(status, steps_text=steps)
    if edit:
        await send_screen(message, text, dashboard_inline_keyboard(), edit=True)
    else:
        await message.answer(text, reply_markup=main_menu_keyboard())


async def show_accounts_section(message: Message, *, page: int = 0, edit: bool = False) -> None:
    accounts = await _load_accounts()
    per_page = PER_PAGE_DEFAULT
    total_pages = max(1, math.ceil(len(accounts) / per_page)) if accounts else 1
    page = min(page, total_pages - 1)
    body = format_accounts_section(accounts, page=page, per_page=per_page, total_pages=total_pages)
    markup = paginated_section_keyboard("acc", page, total_pages, section_accounts_keyboard())
    await send_screen(message, body, markup, edit=edit)


async def show_chats_section(message: Message, *, page: int = 0, edit: bool = False) -> None:
    chats = await _load_chats()
    per_page = PER_PAGE_DEFAULT
    total_pages = max(1, math.ceil(len(chats) / per_page)) if chats else 1
    page = min(page, total_pages - 1)
    body = format_chats_section(chats, page=page, per_page=per_page, total_pages=total_pages)
    markup = paginated_section_keyboard("cht", page, total_pages, section_chats_keyboard())
    await send_screen(message, body, markup, edit=edit)


async def show_templates_section(message: Message, *, page: int = 0, edit: bool = False) -> None:
    templates = await _load_templates()
    per_page = PER_PAGE_DEFAULT
    total_pages = max(1, math.ceil(len(templates) / per_page)) if templates else 1
    page = min(page, total_pages - 1)
    body = format_templates_section(templates, page=page, per_page=per_page, total_pages=total_pages)
    markup = paginated_section_keyboard("tpl", page, total_pages, section_templates_keyboard())
    await send_screen(message, body, markup, edit=edit)


async def show_proxy_menu(callback: CallbackQuery) -> None:
    accounts = await _load_accounts()
    if not accounts:
        if callback.message:
            await callback.message.answer(texts.NO_ACCOUNTS, reply_markup=main_menu_keyboard())
        return
    preview = "\n".join(f"{i + 1}. #{a.id} {a.name}" for i, a in enumerate(accounts[:12]))
    extra = f"\n… ещё {len(accounts) - 12}" if len(accounts) > 12 else ""
    if callback.message:
        await send_screen(
            callback.message,
            "🌐 <b>Прокси</b>\n\n"
            f"Аккаунтов: <b>{len(accounts)}</b>\n\n"
            "<b>🔄 N прокси → все</b> — 5 строк прокси разойдутся по всем аккаунтам по кругу.\n"
            "<b>📋 1 строка = 1 аккаунт</b> — строго по порядку:\n"
            f"<pre>{preview}</pre>{extra}",
            section_proxy_keyboard(),
            edit=True,
        )


async def start_proxy_rotate_message(message: Message, state: FSMContext) -> None:
    accounts = await _load_accounts()
    if not accounts:
        await message.answer(texts.NO_ACCOUNTS, reply_markup=main_menu_keyboard())
        return
    await state.set_state(AccountProxyState.waiting_bulk_rotate)
    await message.answer(
        "🔄 <b>Распределить прокси на все аккаунты</b>\n\n"
        f"Аккаунтов: <b>{len(accounts)}</b>. Отправьте <b>5–20 строк</b> прокси "
        "(каждый сервер с новой строки).\n\n"
        "Пример: 5 прокси → каждый аккаунт получит один из них по кругу.\n\n"
        "Текстом или файлом <code>.txt</code>.",
        reply_markup=cancel_row_keyboard(),
    )


async def start_proxy_bulk_message(message: Message, state: FSMContext) -> None:
    accounts = await _load_accounts()
    if not accounts:
        await message.answer(texts.NO_ACCOUNTS, reply_markup=main_menu_keyboard())
        return
    await state.set_state(AccountProxyState.waiting_bulk)
    preview = "\n".join(f"{i + 1}. #{a.id} {a.name}" for i, a in enumerate(accounts[:10]))
    await message.answer(
        "📋 <b>Список прокси</b>\n\n"
        f"Строк: до <b>{len(accounts)}</b> (1 строка = 1 аккаунт)\n<pre>{preview}</pre>\n\n"
        "Текстом или файлом <code>.txt</code>\n"
        "SOCKS5 / MTProto / <code>tg://proxy?...</code>",
        reply_markup=cancel_row_keyboard(),
    )


async def start_proxy_bulk(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message:
        await start_proxy_bulk_message(callback.message, state)


async def start_proxy_all(callback: CallbackQuery, state: FSMContext) -> None:
    accounts = await _load_accounts()
    if not accounts:
        if callback.message:
            await callback.message.answer(texts.NO_ACCOUNTS, reply_markup=main_menu_keyboard())
        return
    await state.set_state(AccountProxyState.waiting_all)
    if callback.message:
        await callback.message.answer(
            f"♻️ Один прокси на <b>{len(accounts)}</b> аккаунтов.\nОтправьте одну строку:",
            reply_markup=cancel_row_keyboard(),
        )


async def start_account_proxy(callback: CallbackQuery, state: FSMContext) -> None:
    accounts = await _load_accounts()
    if not accounts:
        if callback.message:
            await callback.message.answer(texts.NO_ACCOUNTS, reply_markup=main_menu_keyboard())
        return
    await state.set_state(AccountProxyState.pick_account)
    if callback.message:
        await callback.message.answer(
            "👤 Выберите аккаунт:",
            reply_markup=accounts_pick_keyboard(
                accounts, prefix="accproxy", back="acc:proxy_menu"
            ),
        )


async def start_account_upload(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AccountUploadState.waiting_file)
    await state.update_data(session_name=None, role="lead")
    if callback.message:
        await callback.message.answer(
            "📎 Файл <code>.session</code>\n\n"
            "Подпись: <code>acc1</code> или <code>acc1 support</code>",
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
            "👤 Какой аккаунт вступит в группу?",
            reply_markup=accounts_pick_keyboard(
                accounts, prefix="chat", back="cht:list:p:0"
            ),
        )


async def start_template_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TemplateUIState.wait_name)
    if callback.message:
        await callback.message.answer(
            "📝 Название шаблона (например: promo):",
            reply_markup=cancel_row_keyboard(),
        )


async def start_campaign_wizard(message: Message, state: FSMContext) -> None:
    accounts, chats, templates, _, status = await _load_setup_status()
    if not status.is_ready:
        await message.answer(texts.SETUP_BLOCK, reply_markup=setup_gap_keyboard())
        return

    await state.clear()
    await state.set_state(CampaignUIState.pick_account)
    await state.update_data(
        selected_chat_ids=[],
        account_id=None,
        template_id=None,
        chat_page=0,
        tpl_page=0,
    )
    sent = await message.answer(
        wizard_step(1, WIZARD_TOTAL, "Новая рассылка") + "\n\n👤 Выберите аккаунт-отправитель:",
        reply_markup=accounts_pick_keyboard(accounts, prefix="cu", page=0),
    )
    await state.update_data(wizard_message_id=sent.message_id)


async def show_campaigns_list(message: Message, *, page: int = 0, edit: bool = False) -> None:
    campaigns = await _load_campaigns()
    per_page = CAMPAIGNS_PER_PAGE
    total_pages = max(1, math.ceil(len(campaigns) / per_page)) if campaigns else 1
    page = min(page, total_pages - 1)
    body = format_campaigns_list(campaigns, page=page, per_page=per_page, total_pages=total_pages)
    markup = campaigns_list_keyboard(campaigns, page=page)
    await send_screen(message, body, markup, edit=edit)


async def _edit_wizard(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    markup,
) -> None:
    if callback.message:
        await send_screen(callback.message, text, markup, edit=True)
        await state.update_data(wizard_message_id=callback.message.message_id)


# --- Campaign wizard ---


@router.callback_query(F.data.startswith("cu:list:p:"))
async def cu_accounts_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.rsplit(":", 1)[-1])
    accounts = await _load_accounts()
    await callback.answer()
    await _edit_wizard(
        callback,
        state,
        wizard_step(1, WIZARD_TOTAL, "Новая рассылка") + "\n\n👤 Выберите аккаунт:",
        accounts_pick_keyboard(accounts, prefix="cu", page=page),
    )


@router.callback_query(F.data.startswith("cu:acc:"))
async def cu_pick_account(callback: CallbackQuery, state: FSMContext) -> None:
    account_id = int(callback.data.split(":")[-1])
    await state.update_data(account_id=account_id, selected_chat_ids=[], chat_page=0)
    await state.set_state(CampaignUIState.pick_chats)
    chats = await _load_chats()
    await callback.answer()
    await _edit_wizard(
        callback,
        state,
        wizard_step(2, WIZARD_TOTAL, "Новая рассылка")
        + "\n\n💬 Выберите чаты, затем «Готово»:",
        chats_multiselect_keyboard(chats, set(), page=0),
    )


@router.callback_query(F.data.startswith("cu:cht:list:p:"))
async def cu_chats_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.rsplit(":", 1)[-1])
    data = await state.get_data()
    selected = set(data.get("selected_chat_ids", []))
    await state.update_data(chat_page=page)
    chats = await _load_chats()
    await callback.answer()
    await _edit_wizard(
        callback,
        state,
        wizard_step(2, WIZARD_TOTAL, "Новая рассылка")
        + f"\n\n💬 Выбрано: <b>{len(selected)}</b>",
        chats_multiselect_keyboard(chats, selected, page=page),
    )


@router.callback_query(F.data == "cu:cht:clear")
async def cu_clear_chats(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    chat_page = int(data.get("chat_page", 0))
    await state.update_data(selected_chat_ids=[])
    chats = await _load_chats()
    await callback.answer("Сброшено")
    await _edit_wizard(
        callback,
        state,
        wizard_step(2, WIZARD_TOTAL, "Новая рассылка") + "\n\n💬 Выберите чаты:",
        chats_multiselect_keyboard(chats, set(), page=chat_page),
    )


@router.callback_query(F.data.startswith("cu:cht:all:"))
async def cu_select_all_on_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.rsplit(":", 1)[-1])
    data = await state.get_data()
    selected = set(data.get("selected_chat_ids", []))
    chats = await _load_chats()
    per_page = 10
    start = page * per_page
    chunk = chats[start : start + per_page]
    for chat in chunk:
        selected.add(chat.id)
    await state.update_data(selected_chat_ids=list(selected), chat_page=page)
    await callback.answer(f"+{len(chunk)}")
    await _edit_wizard(
        callback,
        state,
        wizard_step(2, WIZARD_TOTAL, "Новая рассылка") + f"\n\n💬 Выбрано: <b>{len(selected)}</b>",
        chats_multiselect_keyboard(chats, selected, page=page),
    )


@router.callback_query(F.data.startswith("cu:cht:"))
async def cu_toggle_chat(callback: CallbackQuery, state: FSMContext) -> None:
    part = callback.data.split(":")[-1]
    data = await state.get_data()
    selected = set(data.get("selected_chat_ids", []))
    chat_page = int(data.get("chat_page", 0))

    if part == "done":
        if not selected:
            await callback.answer("Выберите хотя бы один чат", show_alert=True)
            return
        await state.set_state(CampaignUIState.pick_template)
        templates = await _load_templates()
        await callback.answer()
        await _edit_wizard(
            callback,
            state,
            wizard_step(3, WIZARD_TOTAL, "Новая рассылка") + "\n\n📝 Выберите шаблон:",
            templates_pick_keyboard(templates, page=0),
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
    await _edit_wizard(
        callback,
        state,
        wizard_step(2, WIZARD_TOTAL, "Новая рассылка") + f"\n\n💬 Выбрано: <b>{len(selected)}</b>",
        chats_multiselect_keyboard(chats, selected, page=chat_page),
    )


@router.callback_query(F.data.startswith("cu:tpl:list:p:"))
async def cu_templates_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.rsplit(":", 1)[-1])
    templates = await _load_templates()
    await callback.answer()
    await _edit_wizard(
        callback,
        state,
        wizard_step(3, WIZARD_TOTAL, "Новая рассылка") + "\n\n📝 Выберите шаблон:",
        templates_pick_keyboard(templates, page=page),
    )


@router.callback_query(F.data.startswith("cu:tpl:"))
async def cu_pick_template(callback: CallbackQuery, state: FSMContext) -> None:
    template_id = int(callback.data.split(":")[-1])
    await state.update_data(template_id=template_id)
    await state.set_state(CampaignUIState.pick_preset)
    await callback.answer()
    await _edit_wizard(
        callback,
        state,
        wizard_step(4, WIZARD_TOTAL, "Новая рассылка") + "\n\n⏱ Скорость отправки:",
        campaign_preset_keyboard(),
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
        "active_hours": "0-23",
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
    account_name = "?"
    template_name = "?"
    proxy_warning = ""
    async with SessionLocal() as session:
        account = await session.get(Account, int(data["account_id"]))
        template = await session.get(Template, int(data["template_id"]))
        if account:
            account_name = account.name
            if not account.proxy:
                proxy_warning = "⚠️ <i>Прокси не задан — из РФ отправка может не работать</i>"
        if template:
            template_name = template.name
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
    delay_label = f"{settings['min_delay_msg']}–{settings['max_delay_msg']} сек"
    await _edit_wizard(
        callback,
        state,
        format_campaign_confirm(
            account_id=int(data["account_id"]),
            account_name=account_name,
            template_id=int(data["template_id"]),
            template_name=template_name,
            selected_count=len(data.get("selected_chat_ids", [])),
            allowed_count=len(allowed),
            excluded_count=len(excluded),
            delay_label=delay_label,
            proxy_warning=proxy_warning,
        ),
        campaign_confirm_keyboard(),
    )


@router.callback_query(F.data == "cu:back:cht")
async def cu_back_to_account(callback: CallbackQuery, state: FSMContext) -> None:
    accounts = await _load_accounts()
    await state.set_state(CampaignUIState.pick_account)
    await callback.answer()
    await _edit_wizard(
        callback,
        state,
        wizard_step(1, WIZARD_TOTAL, "Новая рассылка") + "\n\n👤 Выберите аккаунт:",
        accounts_pick_keyboard(accounts, prefix="cu", page=0),
    )


@router.callback_query(F.data == "cu:back:tpl")
async def cu_back_to_chats(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected = set(data.get("selected_chat_ids", []))
    chat_page = int(data.get("chat_page", 0))
    chats = await _load_chats()
    await state.set_state(CampaignUIState.pick_chats)
    await callback.answer()
    await _edit_wizard(
        callback,
        state,
        wizard_step(2, WIZARD_TOTAL, "Новая рассылка") + f"\n\n💬 Выбрано: <b>{len(selected)}</b>",
        chats_multiselect_keyboard(chats, selected, page=chat_page),
    )


@router.callback_query(F.data == "cu:back:preset")
async def cu_back_to_template(callback: CallbackQuery, state: FSMContext) -> None:
    templates = await _load_templates()
    await state.set_state(CampaignUIState.pick_template)
    await callback.answer()
    await _edit_wizard(
        callback,
        state,
        wizard_step(3, WIZARD_TOTAL, "Новая рассылка") + "\n\n📝 Выберите шаблон:",
        templates_pick_keyboard(templates, page=0),
    )


@router.callback_query(F.data == "cu:back:confirm")
async def cu_back_to_preset(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CampaignUIState.pick_preset)
    await callback.answer()
    await _edit_wizard(
        callback,
        state,
        wizard_step(4, WIZARD_TOTAL, "Новая рассылка") + "\n\n⏱ Скорость отправки:",
        campaign_preset_keyboard(),
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
            campaign = await service.create_campaign(
                name=f"Рассылка {datetime.utcnow():%d.%m %H:%M}",
                mode=data.get("campaign_mode", "single"),
                template_id=int(data["template_id"]),
                created_by=actor_id,
                account_ids=[int(data["account_id"])],
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
            await callback.message.answer(
                f"❌ {humanize_error(error)}",
                reply_markup=main_menu_keyboard(),
            )
        await state.clear()
        return
    except Exception as error:  # noqa: BLE001
        await callback.answer("Ошибка запуска", show_alert=True)
        if callback.message:
            await callback.message.answer(
                f"❌ {humanize_error(error)}",
                reply_markup=main_menu_keyboard(),
            )
        await state.clear()
        return

    await state.clear()
    await callback.answer("Запущено!")
    if callback.message:
        await send_screen(
            callback.message,
            f"✅ Рассылка <b>#{campaign.id}</b> запущена\n"
            f"В очереди: <b>{queued}</b> сообщ.\n\n"
            "📋 <b>Мои рассылки</b> — пауза и отчёт",
            edit=True,
        )
        await callback.message.answer("👇", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "cu:cancel")
async def cu_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    if callback.message:
        await show_dashboard(callback.message, edit=True)


# --- Campaigns list ---


@router.callback_query(F.data.startswith("cmp:list:p:"))
async def cmp_list_page(callback: CallbackQuery) -> None:
    page = int(callback.data.rsplit(":", 1)[-1])
    await callback.answer()
    if callback.message:
        await show_campaigns_list(callback.message, page=page, edit=True)


@router.callback_query(F.data.startswith("cmp:open:"))
async def cmp_open_detail(callback: CallbackQuery) -> None:
    cid = int(callback.data.split(":")[-1])
    container = get_container()
    async with SessionLocal() as session:
        campaign = await session.get(Campaign, cid)
        if not campaign:
            await callback.answer("Не найдено", show_alert=True)
            return
        service = CampaignService(session, container.guard, container.sender_service)
        all_campaigns = await service.list_campaigns()
    page = 0
    for index, item in enumerate(all_campaigns):
        if item.id == cid:
            page = index // CAMPAIGNS_PER_PAGE
            break
    await callback.answer()
    if callback.message:
        await send_screen(
            callback.message,
            f"📋 <b>#{campaign.id}</b> {campaign.name}\n"
            f"Режим: {campaign.mode}\n"
            f"Статус: <b>{campaign.status}</b>",
            campaign_detail_keyboard(cid, list_page=page),
            edit=True,
        )


@router.callback_query(F.data.startswith("cmp:pause:"))
async def cmp_pause(callback: CallbackQuery) -> None:
    cid = int(callback.data.split(":")[-1])
    container = get_container()
    async with SessionLocal() as session:
        await CampaignService(session, container.guard, container.sender_service).pause(cid)
    await callback.answer("⏸ Пауза")


@router.callback_query(F.data.startswith("cmp:resume:"))
async def cmp_resume(callback: CallbackQuery) -> None:
    cid = int(callback.data.split(":")[-1])
    container = get_container()
    async with SessionLocal() as session:
        await CampaignService(session, container.guard, container.sender_service).resume(cid)
    await callback.answer("▶️ Продолжено")


@router.callback_query(F.data.startswith("cmp:stop:"))
async def cmp_stop(callback: CallbackQuery) -> None:
    cid = int(callback.data.split(":")[-1])
    container = get_container()
    async with SessionLocal() as session:
        await CampaignService(session, container.guard, container.sender_service).stop(cid)
    await callback.answer("⏹ Остановлено")


@router.callback_query(F.data.startswith("cmp:report:"))
async def cmp_report(callback: CallbackQuery) -> None:
    from app.services.report_service import ReportService

    cid = int(callback.data.split(":")[-1])
    async with SessionLocal() as session:
        summary = await ReportService(session).build_campaign_summary(cid)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            f"📊 <b>Отчёт #{cid}</b>\n"
            f"✅ Отправлено: {summary.get('sent_ok', 0)}\n"
            f"❌ Ошибки: {summary.get('failed', 0)}\n"
            f"⏭ Пропущено: {summary.get('skipped', 0)}"
        )


# --- Account pick pagination (proxy, chat) ---


@router.callback_query(F.data.startswith("accproxy:list:p:"))
async def accproxy_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.rsplit(":", 1)[-1])
    accounts = await _load_accounts()
    await state.set_state(AccountProxyState.pick_account)
    await callback.answer()
    if callback.message:
        await callback.message.edit_reply_markup(
            reply_markup=accounts_pick_keyboard(
                accounts, prefix="accproxy", page=page, back="acc:proxy_menu"
            ),
        )


@router.callback_query(F.data.startswith("chat:list:p:"))
async def chat_pick_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.rsplit(":", 1)[-1])
    accounts = await _load_accounts()
    await state.set_state(ChatUIState.pick_account)
    await callback.answer()
    if callback.message:
        await callback.message.edit_reply_markup(
            reply_markup=accounts_pick_keyboard(
                accounts, prefix="chat", page=page, back="cht:list:p:0"
            ),
        )


# --- Chat / template flows ---


@router.callback_query(F.data == "chat:cancel")
async def chat_flow_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отменено")
    if callback.message:
        await show_chats_section(callback.message, edit=True)


@router.callback_query(F.data.startswith("chat:acc:"))
async def chat_pick_account(callback: CallbackQuery, state: FSMContext) -> None:
    account_id = int(callback.data.split(":")[-1])
    await state.update_data(account_id=account_id)
    await state.set_state(ChatUIState.wait_link)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "💬 Ссылка или @username:\n"
            "• @mygroup · t.me/mygroup · t.me/+invite",
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
            _, chat, parsed = await service.join_and_add(account_id, raw)
            await AuditService(session).log(
                actor_id,
                "chat.add.ui",
                {"chat_id": chat.id, "target": parsed.storage_key},
            )
        await state.clear()
        if chat.can_send:
            hint = "Можно включать в <b>📤 Новая рассылка</b>."
        else:
            hint = (
                "В рассылку не попадёт, пока нет права писать.\n"
                "Проверьте права в группе или добавьте чат другим аккаунтом."
            )
        await message.answer(
            f"✅ Чат <b>#{chat.id}</b> {chat.title}\n"
            f"Писать: <b>{'да' if chat.can_send else 'нет'}</b>\n\n{hint}",
            reply_markup=main_menu_keyboard(),
        )
    except Exception as error:  # noqa: BLE001
        await message.answer(f"❌ {humanize_error(error)}", reply_markup=main_menu_keyboard())
        await state.clear()


@router.message(StateFilter(TemplateUIState.wait_name))
async def template_wait_name(message: Message, state: FSMContext) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())
        return
    name = (message.text or "").strip()
    if not name or len(name) > 64:
        await message.answer("Короткое название, до 64 символов.")
        return
    await state.update_data(template_name=name)
    await state.set_state(TemplateUIState.wait_body)
    await message.answer("📝 Текст сообщения для рассылки:")


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
        f"✅ Шаблон <b>#{template.id}</b> «{template.name}» сохранён.",
        reply_markup=main_menu_keyboard(),
    )
