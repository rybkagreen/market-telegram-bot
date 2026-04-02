"""Legal profile FSM states."""

from aiogram.fsm.state import State, StatesGroup


class LegalProfileStates(StatesGroup):
    """Состояния заполнения юридического профиля."""

    select_status = State()
    enter_legal_name = State()
    enter_inn = State()
    enter_kpp = State()
    enter_ogrn = State()
    select_tax_regime = State()
    enter_bank_name = State()
    enter_bank_account = State()
    enter_bank_bik = State()
    enter_yoomoney = State()
    enter_passport_series = State()
    enter_passport_number = State()
    enter_passport_issued = State()
    upload_scan = State()
    confirm = State()
