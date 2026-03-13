"""
FSM States для биллинга.
S-09: TopupStates для двухшагового пополнения баланса.
"""

from aiogram.fsm.state import State, StatesGroup


class TopupStates(StatesGroup):
    """Состояния для пополнения баланса."""

    entering_amount = State()  # пользователь вводит желаемую сумму
    confirming = State()  # показ расчёта (desired/fee/gross) перед оплатой
    waiting_payment = State()  # ожидание вебхука от ЮKassa
