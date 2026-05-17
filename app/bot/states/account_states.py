from aiogram.fsm.state import State, StatesGroup


class AccountUploadState(StatesGroup):
    waiting_file = State()


class AccountProxyState(StatesGroup):
    pick_account = State()
    waiting_proxy = State()
    waiting_bulk = State()
    waiting_all = State()
