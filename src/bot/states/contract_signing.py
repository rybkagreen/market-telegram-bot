"""Contract signing FSM states."""

from aiogram.fsm.state import State, StatesGroup


class ContractSigningStates(StatesGroup):
    """Состояния подписания договора."""

    review = State()
    enter_sms_code = State()
    complete = State()
