"""Legal profile handler."""

from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.shared.legal_profile import (
    legal_profile_confirm_keyboard,
    legal_status_keyboard,
    scan_upload_keyboard,
    tax_regime_keyboard,
)
from src.bot.states.legal_profile import LegalProfileStates
from src.core.services.legal_profile_service import LegalProfileService
from src.db.models.user import User
from src.db.repositories.legal_profile_repo import LegalProfileRepo
from src.db.repositories.user_repo import UserRepository

legal_profile_router = Router()

_STATUS_LABELS = {
    "legal_entity": "Юридическое лицо",
    "individual_entrepreneur": "ИП",
    "self_employed": "Самозанятый",
    "individual": "Физическое лицо",
}

_VALID_STATUSES = {"legal_entity", "individual_entrepreneur", "self_employed", "individual"}
_VALID_SCANS = {"inn", "passport", "self_employed_cert", "company_doc"}


def _build_profile_summary(data: dict) -> str:
    """Собрать читаемое резюме юридического профиля из FSM-данных."""
    lines = []
    if data.get("legal_status"):
        lines.append(f"Статус: {_STATUS_LABELS.get(data['legal_status'], data['legal_status'])}")
    for field, label in [
        ("legal_name", "Наименование/ФИО"),
        ("inn", "ИНН"),
        ("kpp", "КПП"),
        ("ogrn", "ОГРН"),
        ("ogrnip", "ОГРНИП"),
        ("bank_name", "Банк"),
        ("bank_account", "Р/С"),
        ("bank_bik", "БИК"),
        ("yoomoney_wallet", "ЮMoney"),
    ]:
        if data.get(field):
            lines.append(f"{label}: {data[field]}")
    return "\n".join(lines) if lines else "Нет данных"


# ── Callback handlers ─────────────────────────────────────────────────────────


@legal_profile_router.callback_query(F.data == "legal:start")
async def cb_legal_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать заполнение юридического профиля."""
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    await callback.message.answer(
        "Выберите юридический статус:", reply_markup=legal_status_keyboard()
    )
    await callback.answer()


@legal_profile_router.callback_query(F.data == "legal:skip_first_start")
async def cb_legal_skip_first_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Пропустить заполнение профиля на первом старте."""
    if not isinstance(callback.message, Message):
        return
    db_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if db_user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    now = datetime.now(UTC)
    await session.execute(
        sa_update(User)
        .where(User.id == db_user.id)
        .values(legal_profile_prompted_at=now, legal_profile_skipped_at=now)
    )
    await session.commit()
    await state.clear()
    await callback.message.answer(
        "Вы можете заполнить профиль позже в личном кабинете.\n\nДля этого перейдите в 👤 Кабинет."
    )
    from src.bot.keyboards.shared.main_menu import main_menu_kb

    await callback.message.answer("🏠 Главное меню", reply_markup=main_menu_kb())
    await callback.answer()


@legal_profile_router.callback_query(F.data == "legal:skip")
async def cb_legal_skip(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропустить заполнение профиля."""
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    await callback.message.answer("Хорошо. Вернитесь позже через 👤 Кабинет.")
    await callback.answer()


@legal_profile_router.callback_query(F.data.startswith("legal:status:"))
async def cb_legal_status(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор юридического статуса."""
    if not isinstance(callback.message, Message):
        return
    status = (callback.data or "").split(":")[2]
    if status not in _VALID_STATUSES:
        await callback.answer("Неверный статус")
        return
    await state.update_data(legal_status=status)
    await state.set_state(LegalProfileStates.enter_legal_name)
    _name_prompts = {
        "legal_entity": "Введите полное наименование организации:",
        "individual_entrepreneur": "Введите ФИО предпринимателя:",
        "self_employed": "Введите ваше ФИО:",
        "individual": "Введите ваше ФИО:",
    }
    await callback.message.answer(_name_prompts[status])
    await callback.answer()


@legal_profile_router.callback_query(F.data.startswith("legal:tax:"))
async def cb_legal_tax(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор налогового режима."""
    if not isinstance(callback.message, Message):
        return
    regime = (callback.data or "").split(":")[2]
    await state.update_data(tax_regime=regime)
    await state.set_state(LegalProfileStates.enter_bank_name)
    await callback.message.answer("Введите название банка:")
    await callback.answer()


@legal_profile_router.callback_query(F.data == "legal:confirm")
async def cb_legal_confirm(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Подтвердить и сохранить юридический профиль."""
    if not isinstance(callback.message, Message):
        return
    data = await state.get_data()
    db_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if db_user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    svc = LegalProfileService(session)
    existing = await LegalProfileRepo(session).get_by_user_id(db_user.id)
    if existing is not None:
        await svc.update_profile(db_user.id, data)
    else:
        await svc.create_profile(db_user.id, data)
    await session.commit()
    await state.clear()
    await callback.message.answer("✅ Юридический профиль сохранён!")
    await callback.answer()


@legal_profile_router.callback_query(F.data == "legal:edit")
async def cb_legal_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Редактировать юридический профиль."""
    if not isinstance(callback.message, Message):
        return
    await state.set_state(LegalProfileStates.select_status)
    await callback.message.answer(
        "Выберите юридический статус:", reply_markup=legal_status_keyboard()
    )
    await callback.answer()


@legal_profile_router.callback_query(F.data.startswith("legal:scan:"))
async def cb_legal_scan(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать загрузку скана документа."""
    if not isinstance(callback.message, Message):
        return
    scan_type = (callback.data or "").split(":")[2]
    if scan_type not in _VALID_SCANS:
        await callback.answer("Неизвестный тип скана")
        return
    await state.update_data(expected_scan_type=scan_type)
    await state.set_state(LegalProfileStates.upload_scan)
    _scan_names = {
        "inn": "скан ИНН",
        "passport": "скан паспорта",
        "self_employed_cert": "справку самозанятого",
        "company_doc": "устав или выписку ЕГРЮЛ",
    }
    await callback.message.answer(f"Отправьте {_scan_names[scan_type]} (фото или документ):")
    await callback.answer()


# ── Message handlers ──────────────────────────────────────────────────────────


@legal_profile_router.message(LegalProfileStates.enter_legal_name)
async def msg_legal_name(message: Message, state: FSMContext) -> None:
    """Принять наименование / ФИО."""
    if message.text is None:
        return
    await state.update_data(legal_name=message.text.strip())
    await state.set_state(LegalProfileStates.enter_inn)
    await message.answer("Введите ИНН:")


@legal_profile_router.message(LegalProfileStates.enter_inn)
async def msg_legal_inn(message: Message, state: FSMContext) -> None:
    """Принять ИНН с валидацией."""
    if message.text is None:
        return
    inn = message.text.strip()
    valid, _ = LegalProfileService.validate_inn(inn)
    if not valid:
        await message.answer(
            "❌ Неверный формат или контрольная сумма ИНН. Проверьте и введите снова:"
        )
        return
    await state.update_data(inn=inn)
    data = await state.get_data()
    status = data.get("legal_status", "")
    if status == "legal_entity":
        await state.set_state(LegalProfileStates.enter_kpp)
        await message.answer("Введите КПП (9 цифр):")
    elif status == "individual_entrepreneur":
        await state.set_state(LegalProfileStates.enter_ogrn)
        await message.answer("Введите ОГРНИП (15 цифр):")
    elif status == "self_employed":
        await state.set_state(LegalProfileStates.enter_yoomoney)
        await message.answer("Введите номер кошелька ЮMoney:")
    else:  # individual
        await state.set_state(LegalProfileStates.enter_passport_series)
        await message.answer("Введите серию паспорта (4 цифры):")


@legal_profile_router.message(LegalProfileStates.enter_kpp)
async def msg_legal_kpp(message: Message, state: FSMContext) -> None:
    """Принять КПП с валидацией."""
    if message.text is None:
        return
    kpp = message.text.strip()
    if not (kpp.isdigit() and len(kpp) == 9):
        await message.answer("❌ КПП должен содержать ровно 9 цифр. Введите снова:")
        return
    await state.update_data(kpp=kpp)
    await state.set_state(LegalProfileStates.enter_ogrn)
    await message.answer("Введите ОГРН (13 цифр):")


@legal_profile_router.message(LegalProfileStates.enter_ogrn)
async def msg_legal_ogrn(message: Message, state: FSMContext) -> None:
    """Принять ОГРН / ОГРНИП с валидацией."""
    if message.text is None:
        return
    ogrn = message.text.strip()
    data = await state.get_data()
    status = data.get("legal_status", "")
    expected_len = 13 if status == "legal_entity" else 15
    field_name = "ogrn" if status == "legal_entity" else "ogrnip"
    if not (ogrn.isdigit() and len(ogrn) == expected_len):
        await message.answer(
            f"❌ {field_name.upper()} должен содержать {expected_len} цифр. Введите снова:"
        )
        return
    await state.update_data({field_name: ogrn})
    if status == "individual_entrepreneur":
        await state.set_state(LegalProfileStates.select_tax_regime)
        await message.answer("Выберите налоговый режим:", reply_markup=tax_regime_keyboard())
    else:
        await state.set_state(LegalProfileStates.enter_bank_name)
        await message.answer("Введите название банка:")


@legal_profile_router.message(LegalProfileStates.enter_bank_name)
async def msg_legal_bank_name(message: Message, state: FSMContext) -> None:
    """Принять название банка."""
    if message.text is None:
        return
    await state.update_data(bank_name=message.text.strip())
    await state.set_state(LegalProfileStates.enter_bank_account)
    await message.answer("Введите расчётный счёт (20 цифр):")


@legal_profile_router.message(LegalProfileStates.enter_bank_account)
async def msg_legal_bank_account(message: Message, state: FSMContext) -> None:
    """Принять расчётный счёт с валидацией."""
    if message.text is None:
        return
    acc = message.text.strip()
    if not (acc.isdigit() and len(acc) == 20):
        await message.answer("❌ Расчётный счёт должен содержать ровно 20 цифр. Введите снова:")
        return
    await state.update_data(bank_account=acc)
    await state.set_state(LegalProfileStates.enter_bank_bik)
    await message.answer("Введите БИК банка (9 цифр):")


@legal_profile_router.message(LegalProfileStates.enter_bank_bik)
async def msg_legal_bank_bik(message: Message, state: FSMContext) -> None:
    """Принять БИК с валидацией и показать подтверждение."""
    if message.text is None:
        return
    bik = message.text.strip()
    if not (bik.isdigit() and len(bik) == 9):
        await message.answer("❌ БИК должен содержать ровно 9 цифр. Введите снова:")
        return
    await state.update_data(bank_bik=bik)
    data = await state.get_data()
    await state.set_state(LegalProfileStates.confirm)
    summary = _build_profile_summary(data)
    await message.answer(
        f"📋 Проверьте данные:\n\n{summary}", reply_markup=legal_profile_confirm_keyboard()
    )


@legal_profile_router.message(LegalProfileStates.enter_yoomoney)
async def msg_legal_yoomoney(message: Message, state: FSMContext) -> None:
    """Принять кошелёк ЮMoney и показать подтверждение."""
    if message.text is None:
        return
    await state.update_data(yoomoney_wallet=message.text.strip())
    data = await state.get_data()
    await state.set_state(LegalProfileStates.confirm)
    summary = _build_profile_summary(data)
    await message.answer(
        f"📋 Проверьте данные:\n\n{summary}", reply_markup=legal_profile_confirm_keyboard()
    )


@legal_profile_router.message(LegalProfileStates.enter_passport_series)
async def msg_legal_passport_series(message: Message, state: FSMContext) -> None:
    """Принять серию паспорта с валидацией."""
    if message.text is None:
        return
    s = message.text.strip()
    if not (s.isdigit() and len(s) == 4):
        await message.answer("❌ Серия паспорта — 4 цифры. Введите снова:")
        return
    await state.update_data(passport_series=s)
    await state.set_state(LegalProfileStates.enter_passport_number)
    await message.answer("Введите номер паспорта (6 цифр):")


@legal_profile_router.message(LegalProfileStates.enter_passport_number)
async def msg_legal_passport_number(message: Message, state: FSMContext) -> None:
    """Принять номер паспорта с валидацией."""
    if message.text is None:
        return
    n = message.text.strip()
    if not (n.isdigit() and len(n) == 6):
        await message.answer("❌ Номер паспорта — 6 цифр. Введите снова:")
        return
    await state.update_data(passport_number=n)
    await state.set_state(LegalProfileStates.enter_passport_issued)
    await message.answer("Кем выдан паспорт? (например: ОВД Ленинского района г. Москвы)")


@legal_profile_router.message(LegalProfileStates.enter_passport_issued)
async def msg_legal_passport_issued(message: Message, state: FSMContext) -> None:
    """Принять орган выдачи паспорта и показать подтверждение."""
    if message.text is None:
        return
    await state.update_data(passport_issued_by=message.text.strip())
    data = await state.get_data()
    await state.set_state(LegalProfileStates.confirm)
    summary = _build_profile_summary(data)
    await message.answer(
        f"📋 Проверьте данные:\n\n{summary}\n\n(Дата выдачи паспорта будет запрошена при верификации)",
        reply_markup=legal_profile_confirm_keyboard(),
    )


@legal_profile_router.message(LegalProfileStates.upload_scan)
async def msg_legal_scan(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Принять скан документа."""
    if message.from_user is None:
        return
    file_id: str | None = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    if not file_id:
        await message.answer("Пожалуйста, отправьте фото или документ.")
        return
    data = await state.get_data()
    scan_type = data.get("expected_scan_type")
    if not scan_type:
        await message.answer("Ошибка: тип документа не определён. Начните заново.")
        await state.clear()
        return
    db_user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if db_user is None:
        await message.answer("Пользователь не найден.")
        await state.clear()
        return
    svc = LegalProfileService(session)
    await svc.upload_scan(db_user.id, scan_type, file_id)
    await session.commit()
    uploaded: dict[str, bool] = data.get("uploaded_scans", {})
    uploaded[scan_type] = True
    await state.update_data(uploaded_scans=uploaded)
    await message.answer("✅ Документ загружен.")
    legal_status = data.get("legal_status", "")
    await message.answer(
        "Загрузите остальные документы:", reply_markup=scan_upload_keyboard(legal_status, uploaded)
    )
