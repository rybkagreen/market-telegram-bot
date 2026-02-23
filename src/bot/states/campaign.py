"""
FSM состояния для wizard'а создания кампании.
"""

from aiogram.fsm.state import State, StatesGroup


class CampaignStates(StatesGroup):
    """
    Состояния для создания рекламной кампании.

    States:
        waiting_title: Ожидание названия кампании
        waiting_text: Ожидание текста (выбор: вручную или ИИ)
        waiting_ai_description: Ожидание описания для ИИ-генерации
        waiting_topic: Ожидание выбора тематики
        waiting_member_count: Ожидание выбора размера аудитории
        waiting_schedule: Ожидание выбора расписания
        waiting_confirm: Ожидание подтверждения запуска
    """

    waiting_title = State()
    waiting_text = State()
    waiting_ai_description = State()
    waiting_topic = State()
    waiting_member_count = State()
    waiting_schedule = State()
    waiting_confirm = State()
