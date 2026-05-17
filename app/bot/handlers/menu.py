from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers import agent as agent_handlers
from app.bot.handlers import logs as logs_handlers
from app.bot.handlers import settings as settings_handlers
from app.bot.handlers import ui_wizard
from app.bot.keyboards.builders import section_agent_keyboard
from app.bot.keyboards.menu import (
    BTN_ACCOUNTS,
    BTN_CAMPAIGN_NEW,
    BTN_CAMPAIGNS,
    BTN_CANCEL,
    BTN_CHATS,
    BTN_AGENT,
    BTN_HELP,
    BTN_HOME,
    BTN_STATUS,
    BTN_TEMPLATES,
    MAIN_MENU_BUTTONS,
    main_menu_keyboard,
)
from app.bot.texts import ru as texts

router = Router()


@router.message(Command("start", "menu"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await ui_wizard.show_dashboard(message)


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.HELP, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "go:campaigns")
async def cb_go_campaigns(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await ui_wizard.show_campaigns_list(callback.message, edit=True)


@router.callback_query(F.data == "go:agent")
async def cb_go_agent(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.message:
        await agent_handlers.open_agent_menu(callback.message, state)


@router.callback_query(F.data == "tool:settings")
async def cb_tool_settings(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await settings_handlers.send_settings_screen(callback.message, edit=True)


@router.callback_query(F.data == "tool:logs")
async def cb_tool_logs(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await logs_handlers.send_logs_screen(callback.message, edit=True)


@router.message(F.text == BTN_HOME)
@router.message(F.text == BTN_CANCEL)
async def btn_home_or_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.text == BTN_CANCEL:
        await message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())
    else:
        await ui_wizard.show_dashboard(message)


@router.message(F.text.in_(MAIN_MENU_BUTTONS))
async def main_menu_buttons(message: Message, state: FSMContext) -> None:
    if await state.get_state() is not None:
        await state.clear()

    text = message.text
    if text == BTN_CAMPAIGN_NEW:
        await ui_wizard.start_campaign_wizard(message, state)
    elif text == BTN_CAMPAIGNS:
        await ui_wizard.show_campaigns_list(message)
    elif text == BTN_ACCOUNTS:
        await ui_wizard.show_accounts_section(message)
    elif text == BTN_CHATS:
        await ui_wizard.show_chats_section(message)
    elif text == BTN_TEMPLATES:
        await ui_wizard.show_templates_section(message)
    elif text == BTN_STATUS:
        await ui_wizard.show_dashboard(message)
    elif text == BTN_AGENT:
        from app.bot.handlers import agent as agent_handlers

        await agent_handlers.cmd_agent(message, state)
    elif text == BTN_HELP:
        await message.answer(texts.HELP, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "nav:home")
async def cb_nav_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await ui_wizard.show_dashboard(callback.message, edit=True)


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "go:campaign")
async def cb_go_campaign(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.message:
        await ui_wizard.start_campaign_wizard(callback.message, state)


@router.callback_query(F.data == "go:acc")
async def cb_go_acc(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if callback.message:
        await ui_wizard.show_accounts_section(callback.message, edit=True)


@router.callback_query(F.data == "go:cht")
async def cb_go_cht(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ui_wizard.start_chat_add(callback, state)


@router.callback_query(F.data == "go:tpl")
async def cb_go_tpl(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ui_wizard.start_template_add(callback, state)


@router.callback_query(F.data == "acc:upload")
async def cb_acc_upload(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ui_wizard.start_account_upload(callback, state)


@router.callback_query(F.data == "acc:proxy_menu")
async def cb_acc_proxy_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await ui_wizard.show_proxy_menu(callback)


@router.callback_query(F.data == "acc:proxy_bulk")
async def cb_acc_proxy_bulk(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ui_wizard.start_proxy_bulk(callback, state)


@router.callback_query(F.data == "acc:proxy_all")
async def cb_acc_proxy_all(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ui_wizard.start_proxy_all(callback, state)


@router.callback_query(F.data == "acc:proxy")
async def cb_acc_proxy(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ui_wizard.start_account_proxy(callback, state)


@router.callback_query(F.data.startswith("acc:list:p:"))
async def cb_acc_list_page(callback: CallbackQuery) -> None:
    page = int(callback.data.rsplit(":", 1)[-1])
    await callback.answer()
    if callback.message:
        await ui_wizard.show_accounts_section(callback.message, page=page, edit=True)


@router.callback_query(F.data == "cht:add")
async def cb_cht_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ui_wizard.start_chat_add(callback, state)


@router.callback_query(F.data.startswith("cht:list:p:"))
async def cb_cht_list_page(callback: CallbackQuery) -> None:
    page = int(callback.data.rsplit(":", 1)[-1])
    await callback.answer()
    if callback.message:
        await ui_wizard.show_chats_section(callback.message, page=page, edit=True)


@router.callback_query(F.data == "tpl:add")
async def cb_tpl_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ui_wizard.start_template_add(callback, state)


@router.callback_query(F.data.startswith("tpl:list:p:"))
async def cb_tpl_list_page(callback: CallbackQuery) -> None:
    page = int(callback.data.rsplit(":", 1)[-1])
    await callback.answer()
    if callback.message:
        await ui_wizard.show_templates_section(callback.message, page=page, edit=True)
