"""Payout states."""

from aiogram.fsm.state import State, StatesGroup


class PayoutStates(StatesGroup):
    """Состояния процесса вывода средств."""

    entering_amount = State()
    confirming = State()
    entering_requisites = State()
