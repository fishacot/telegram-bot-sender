from aiogram.fsm.state import State, StatesGroup


class AgentAskState(StatesGroup):
    waiting_question = State()
