"""FSM состояния для арбитража."""

from aiogram.fsm.state import State, StatesGroup


class ArbitrationStates(StatesGroup):
    """Состояния для арбитража."""

    waiting_rejection_reason = State()
    waiting_counter_price = State()
    waiting_counter_comment = State()
