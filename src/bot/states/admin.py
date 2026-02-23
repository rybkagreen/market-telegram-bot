"""
FSM состояния для админ-панели.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminBalanceStates(StatesGroup):
    """Состояния для управления балансом пользователя."""

    waiting_user_id = State()  # ввод telegram_id пользователя
    waiting_amount = State()  # ввод суммы (+ или -)
    waiting_reason = State()  # причина изменения (для лога)


class AdminBanStates(StatesGroup):
    """Состояния для бана/разбана пользователя."""

    waiting_user_id = State()
    waiting_reason = State()


class AdminBroadcastStates(StatesGroup):
    """Состояния для broadcast рассылки."""

    waiting_message = State()  # текст рассылки
    waiting_confirm = State()  # подтверждение перед отправкой


class AdminFreeCampaignStates(StatesGroup):
    """Состояния для бесплатной кампании администратора."""

    waiting_title = State()
    waiting_text = State()
    waiting_topic = State()
    waiting_member_count = State()
    waiting_schedule = State()
    waiting_confirm = State()
