from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.builders import section_agent_keyboard
from app.bot.keyboards.menu import BTN_AGENT, BTN_CANCEL, cancel_row_keyboard, main_menu_keyboard
from app.bot.states.agent_states import AgentAskState
from app.bot.texts import ru as texts
from app.bot.texts.errors_ru import humanize_error
from app.config import get_settings
from app.infrastructure.ai_provider.factory import build_ai_provider
from app.infrastructure.agent.sandbox import AgentSandbox
from app.infrastructure.db.session import SessionLocal
from app.services.project_agent_service import ProjectAgentService

router = Router()


def _agent_enabled() -> bool:
    return get_settings().ai_agent_enabled


def _make_service(session) -> ProjectAgentService:
    settings = get_settings()
    sandbox = AgentSandbox(settings.project_root)
    provider = build_ai_provider(settings)
    return ProjectAgentService(session, settings, provider, sandbox)


async def open_agent_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not _agent_enabled():
        await message.answer("🤖 AI-агент отключён на сервере.")
        return
    await message.answer(
        "🤖 <b>AI-агент</b>\n\n"
        "Разбор ошибок и отчёты — кнопками ниже.\n"
        "Отчёты сохраняются на сервере (папка reports).",
        reply_markup=section_agent_keyboard(),
    )


@router.message(F.text == BTN_AGENT)
async def btn_agent(message: Message, state: FSMContext) -> None:
    await open_agent_menu(message, state)


@router.callback_query(F.data == "ag:status")
async def ag_status(callback: CallbackQuery) -> None:
    await callback.answer()
    if not _agent_enabled():
        return
    async with SessionLocal() as session:
        status = await _make_service(session).status()
    runtime = status["runtime"]
    text = (
        "🤖 <b>Статус агента</b>\n\n"
        f"Провайдер: <code>{status['provider']}</code>\n"
        f"Ошибок в БД: <b>{status['errors_in_db']}</b>\n"
        f"В памяти: <b>{status['memory_errors']}</b>\n\n"
        f"👤 {runtime['accounts']} · 💬 {runtime['chats']} · "
        f"📝 {runtime['templates']} · 📋 {runtime['campaigns_running']}\n\n"
        f"📁 {status['reports_dir']}"
    )
    if callback.message:
        await callback.message.answer(text, reply_markup=section_agent_keyboard())


@router.callback_query(F.data == "ag:diagnose")
async def ag_diagnose(callback: CallbackQuery) -> None:
    if not _agent_enabled():
        await callback.answer("Агент выключен", show_alert=True)
        return
    await callback.answer("Анализирую…")
    if callback.message:
        await callback.message.answer("⏳ Разбор последних ошибок…")
    async with SessionLocal() as session:
        result = await _make_service(session).diagnose_errors()
    text = ProjectAgentService.format_telegram_report(result)
    if callback.message:
        await callback.message.answer(text, reply_markup=section_agent_keyboard())


@router.callback_query(F.data == "ag:report")
async def ag_report(callback: CallbackQuery) -> None:
    if not _agent_enabled():
        await callback.answer("Агент выключен", show_alert=True)
        return
    await callback.answer("Готовлю отчёт…")
    if callback.message:
        await callback.message.answer("⏳ Полный отчёт по проекту…")
    async with SessionLocal() as session:
        result = await _make_service(session).full_report()
    text = ProjectAgentService.format_telegram_report(result)
    if callback.message:
        await callback.message.answer(text, reply_markup=section_agent_keyboard())


@router.callback_query(F.data == "ag:ask")
async def ag_ask_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not _agent_enabled():
        await callback.answer("Агент выключен", show_alert=True)
        return
    await state.set_state(AgentAskState.waiting_question)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "💬 Задайте вопрос по проекту, ошибке или настройке бота:",
            reply_markup=cancel_row_keyboard(),
        )


@router.message(StateFilter(AgentAskState.waiting_question), F.text == BTN_CANCEL)
async def ag_ask_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())


@router.message(StateFilter(AgentAskState.waiting_question))
async def ag_ask_question(message: Message, state: FSMContext) -> None:
    question = (message.text or "").strip()
    if not question:
        await message.answer("Введите вопрос текстом.")
        return
    actor_id = message.from_user.id if message.from_user else 0
    await message.answer("⏳ Думаю…")
    try:
        async with SessionLocal() as session:
            result = await _make_service(session).ask(question, actor_id=actor_id)
        await state.clear()
        await message.answer(
            ProjectAgentService.format_telegram_report(result),
            reply_markup=main_menu_keyboard(),
        )
    except Exception as error:  # noqa: BLE001
        await state.clear()
        await message.answer(
            f"❌ {humanize_error(error)}",
            reply_markup=main_menu_keyboard(),
        )


