"""Arbitration states."""

from aiogram.fsm.state import State, StatesGroup


class ArbitrationStates(StatesGroup):
    """Состояния арбитража заявок."""

    viewing_request = State()
    waiting_reject_comment = State()
    counter_offering = State()
    entering_counter_price = State()
    entering_counter_time = State()
    entering_counter_comment = State()
