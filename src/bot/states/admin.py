"""
FSM States для администратора.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Состояния для административных действий."""

    entering_broadcast = State()  # ввод текста рассылки
    reviewing_dispute = State()  # просмотр диспута
    entering_resolution = State()  # ввод резолюции диспута


class AdminAIGenerateStates(StatesGroup):
    """Состояния для ИИ-генерации кампании."""

    waiting_topic = State()  # выбор темы
    waiting_description = State()  # описание кампании
    generating = State()  # генерация ИИ


class AdminFreeCampaignStates(StatesGroup):
    """Состояния для бесплатных кампаний."""

    waiting_title = State()
    waiting_topic = State()
    waiting_member_count = State()
    waiting_schedule = State()
    waiting_channel = State()
    waiting_text = State()
    waiting_post_text = State()
    confirming = State()


class AdminBanStates(StatesGroup):
    """Состояния для бана пользователя."""

    waiting_user_id = State()
    waiting_reason = State()
    confirming = State()


class AdminBroadcastStates(StatesGroup):
    """Состояния для рассылки."""

    waiting_message = State()
    waiting_confirm = State()
    entering_text = State()
    confirming = State()
    sending = State()


class AdminBalanceStates(StatesGroup):
    """Состояния для управления балансом."""

    waiting_user_id = State()
    waiting_amount = State()
    waiting_reason = State()
    confirming = State()
