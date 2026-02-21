from aiogram.fsm.state import State, StatesGroup


class CampaignStates(StatesGroup):
    """Состояния для FSM wizard создания рекламной кампании."""
    
    waiting_title = State()
    waiting_text = State()
    waiting_ai_description = State()
    waiting_topic = State()
    waiting_member_count = State()
    waiting_schedule = State()
    waiting_confirm = State()
