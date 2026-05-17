from aiogram.fsm.state import State, StatesGroup


class CampaignWizardState(StatesGroup):
    pick_accounts = State()
    pick_chats = State()
    pick_template = State()
    pick_settings = State()
    preflight = State()
    confirm = State()
