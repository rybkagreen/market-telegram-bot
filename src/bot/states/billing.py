from aiogram.fsm.state import State, StatesGroup


class TopupStates(StatesGroup):
    """Состояния процесса пополнения баланса."""

    entering_amount = State()
    confirming = State()
    waiting_payment = State()
