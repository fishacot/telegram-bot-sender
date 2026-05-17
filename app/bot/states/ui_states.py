from aiogram.fsm.state import State, StatesGroup


class CampaignUIState(StatesGroup):
    pick_account = State()
    pick_chats = State()
    pick_template = State()
    pick_preset = State()
    confirm = State()


class ChatUIState(StatesGroup):
    pick_account = State()
    wait_link = State()


class TemplateUIState(StatesGroup):
    wait_name = State()
    wait_body = State()
