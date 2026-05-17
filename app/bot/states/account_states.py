from aiogram.fsm.state import State, StatesGroup


class AccountUploadState(StatesGroup):
    waiting_file = State()
