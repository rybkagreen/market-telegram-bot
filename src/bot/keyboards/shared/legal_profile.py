"""Legal profile keyboards."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

_SCAN_REQUIREMENTS: dict[str, list[str]] = {
    "legal_entity": ["inn", "company_doc"],
    "individual_entrepreneur": ["inn"],
    "self_employed": ["self_employed_cert"],
    "individual": ["passport"],
}

_SCAN_LABELS: dict[str, str] = {
    "inn": "Скан ИНН",
    "company_doc": "Устав / выписка ЕГРЮЛ",
    "self_employed_cert": "Справка самозанятого",
    "passport": "Скан паспорта",
}


def legal_status_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора юридического статуса."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🏢 Юридическое лицо", callback_data="legal:status:legal_entity")
    builder.button(
        text="👤 Индивидуальный предприниматель",
        callback_data="legal:status:individual_entrepreneur",
    )
    builder.button(text="📱 Самозанятый", callback_data="legal:status:self_employed")
    builder.button(text="🙋 Физическое лицо", callback_data="legal:status:individual")
    builder.button(text="⏭ Заполнить позже", callback_data="legal:skip")
    builder.adjust(1)
    return builder.as_markup()


def first_start_legal_prompt_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура первичного запроса заполнения юридического профиля."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Заполнить сейчас", callback_data="legal:start")
    builder.button(text="⏭ Заполнить позже", callback_data="legal:skip_first_start")
    builder.adjust(1)
    return builder.as_markup()


def tax_regime_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора налогового режима."""
    builder = InlineKeyboardBuilder()
    builder.button(text="ОСНО (общая)", callback_data="legal:tax:osno")
    builder.button(text="УСН доходы", callback_data="legal:tax:usn_d")
    builder.button(text="УСН доходы-расходы", callback_data="legal:tax:usn_dr")
    builder.button(text="Патент (ПСН)", callback_data="legal:tax:patent")
    builder.adjust(1)
    return builder.as_markup()


def scan_upload_keyboard(legal_status: str, uploaded: dict[str, bool]) -> InlineKeyboardMarkup:
    """Клавиатура загрузки сканов документов."""
    builder = InlineKeyboardBuilder()
    required_scans = _SCAN_REQUIREMENTS.get(legal_status, [])
    all_uploaded = True
    for scan_type in required_scans:
        is_done = uploaded.get(scan_type, False)
        if not is_done:
            all_uploaded = False
        label = ("✅ " if is_done else "📎 Загрузить: ") + _SCAN_LABELS[scan_type]
        builder.button(text=label, callback_data=f"legal:scan:{scan_type}")
        builder.adjust(1)
    if all_uploaded and required_scans:
        builder.button(text="✅ Готово", callback_data="legal:confirm")
        builder.adjust(1)
    return builder.as_markup()


def legal_profile_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения юридического профиля."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="legal:confirm")
    builder.button(text="✏️ Редактировать", callback_data="legal:edit")
    builder.adjust(1)
    return builder.as_markup()
