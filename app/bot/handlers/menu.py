from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers import ui_wizard
from app.bot.keyboards.menu import (
    BTN_ACCOUNTS,
    BTN_CAMPAIGN_NEW,
    BTN_CAMPAIGNS,
    BTN_CANCEL,
    BTN_CHATS,
    BTN_HELP,
    BTN_HOME,
    BTN_TEMPLATES,
    MAIN_MENU_BUTTONS,
    main_menu_keyboard,
    section_accounts_keyboard,
    section_chats_keyboard,
    section_templates_keyboard,
)
from app.bot.texts import ru as texts

router = Router()


@router.message(Command("start", "menu", "help"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.WELCOME, reply_markup=main_menu_keyboard())


@router.message(F.text == BTN_HOME)
@router.message(F.text == BTN_CANCEL, StateFilter("*"))
async def btn_home_or_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.text == BTN_CANCEL:
        await message.answer(texts.CANCELLED, reply_markup=main_menu_keyboard())
    else:
        await message.answer("🏠 Главное меню", reply_markup=main_menu_keyboard())


@router.message(F.text.in_(MAIN_MENU_BUTTONS), StateFilter(None))
async def main_menu_buttons(message: Message, state: FSMContext) -> None:
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
    elif text == BTN_HELP:
        await message.answer(texts.HELP, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "nav:home")
async def cb_nav_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.answer("🏠 Главное меню", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "acc:upload")
async def cb_acc_upload(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ui_wizard.start_account_upload(callback, state)


@router.callback_query(F.data == "acc:list")
async def cb_acc_list(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await ui_wizard.show_accounts_section(callback.message)


@router.callback_query(F.data == "cht:add")
async def cb_cht_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ui_wizard.start_chat_add(callback, state)


@router.callback_query(F.data == "cht:list")
async def cb_cht_list(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await ui_wizard.show_chats_section(callback.message)


@router.callback_query(F.data == "tpl:add")
async def cb_tpl_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await ui_wizard.start_template_add(callback, state)


@router.callback_query(F.data == "tpl:list")
async def cb_tpl_list(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await ui_wizard.show_templates_section(callback.message)
