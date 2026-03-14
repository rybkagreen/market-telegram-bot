"""
FSM States для выплат владельцам каналов.
"""

from aiogram.fsm.state import State, StatesGroup


class PayoutStates(StatesGroup):
    """Состояния для оформления выплаты."""

    entering_amount = State()  # ввод суммы выплаты
    confirming = State()  # подтверждение суммы (gross/fee/net)
    entering_requisites = State()  # ввод реквизитов для выплаты
