"""Payout handlers."""

import logging
import re
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.states.payout import PayoutStates
from src.constants.payments import PAYOUT_FEE_RATE
from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.repositories.payout_repo import PayoutRepository
from src.db.repositories.user_repo import UserRepository

router = Router()
logger = logging.getLogger(__name__)

USER_NOT_FOUND = "❌ Пользователь не найден"
PAYOUT_START_SCENE = "payout:request_start"
CANCEL_BTN = "❌ Отмена"

MIN_PAYOUT = Decimal("1000")
_STATUS_EMOJI = {
    "pending": "⏳",
    "processing": "🔄",
    "paid": "✅",
    "rejected": "❌",
    "cancelled": "❌",
}


@router.callback_query(F.data == "main:payouts")
async def show_payouts(callback: CallbackQuery, session: AsyncSession) -> None:
    """Главный экран выплат."""
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer(USER_NOT_FOUND, show_alert=True)
        return

    payouts = await PayoutRepository(session).get_by_owner(user.id)
    if payouts:
        lines = []
        for p in payouts[:5]:
            s = p.status.value if hasattr(p.status, "value") else str(p.status)
            emoji = _STATUS_EMOJI.get(s, "•")
            date = p.created_at.strftime("%d.%m") if p.created_at else "—"
            lines.append(f"{emoji} {date}: {p.net_amount:.0f} ₽")
        history = "\n".join(lines)
    else:
        history = "Выплат пока не было"

    builder = InlineKeyboardBuilder()
    if user.earned_rub >= MIN_PAYOUT:
        builder.button(text="💸 Запросить вывод", callback_data=PAYOUT_START_SCENE)
    builder.button(text="🔙 Меню владельца", callback_data="main:own_menu")
    builder.adjust(1)

    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        f"💸 *Выплаты*\n\n"
        f"💰 Доступно: *{user.earned_rub:.0f} ₽*\n\n"
        f"📌 Мин. вывод: 1 000 ₽\n"
        f"📌 Комиссия: 1,5%\n"
        f"⏱ Срок: до 24 часов (09:00–22:00 МСК)\n\n"
        f"─── История ───\n{history}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == PAYOUT_START_SCENE)
async def payout_request_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Выбор суммы вывода."""
    # Load user by Telegram ID first — DB PK (user.id) needed for all service calls
    payout_user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if payout_user is None:
        await callback.answer(USER_NOT_FOUND, show_alert=True)
        return

    # --- Legal profile + contract checks (S3 addition) ---
    if not isinstance(callback.message, Message):
        return
    if not payout_user.legal_status_completed:
        from src.bot.keyboards.shared.legal_profile import first_start_legal_prompt_keyboard

        await callback.message.answer(
            "⚠️ Для запроса выплаты необходимо заполнить юридический профиль.\n\n"
            "Это нужно для расчёта налогов и оформления договора.",
            reply_markup=first_start_legal_prompt_keyboard(),
        )
        await callback.answer()
        return

    from src.core.services.contract_service import ContractService

    contract_svc = ContractService(session)
    if not await contract_svc.check_owner_contract(payout_user.id):
        contract = await contract_svc.generate_contract(payout_user.id, "owner_service")
        await session.commit()
        from src.bot.keyboards.shared.contract import contract_sign_keyboard

        await callback.message.answer(
            "📄 Для получения выплаты необходимо подписать договор оказания услуг.\n\n"
            "Ознакомьтесь с договором и подпишите его:",
            reply_markup=contract_sign_keyboard(contract.id),
        )
        await callback.answer()
        return
    # --- end checks ---

    user = payout_user  # Reuse already-loaded user (avoids duplicate DB query)

    if user.earned_rub < MIN_PAYOUT:
        await callback.answer("❌ Минимальная сумма вывода — 1 000 ₽", show_alert=True)
        return

    active = await PayoutRepository(session).get_active_for_owner(user.id)
    if active:
        await callback.answer("❌ У вас уже есть заявка в обработке", show_alert=True)
        return

    await state.set_state(PayoutStates.entering_amount)

    amounts = [1000, 3000, 5000, 10000]
    row_btns = [
        InlineKeyboardButton(
            text=f"{amt:,} ₽".replace(",", " "),
            callback_data=f"payout:amount:{amt}",
        )
        for amt in amounts
        if user.earned_rub >= amt
    ]

    builder = InlineKeyboardBuilder()
    if row_btns[:2]:
        builder.row(*row_btns[:2])
    if row_btns[2:]:
        builder.row(*row_btns[2:])
    builder.button(
        text=f"💯 Вся сумма ({user.earned_rub:.0f} ₽)",
        callback_data="payout:amount:all",
    )
    builder.button(text="✏️ Ввести сумму", callback_data="payout:amount:custom")
    builder.button(text=CANCEL_BTN, callback_data="main:payouts")
    builder.adjust(1)

    await callback.message.edit_text(
        f"💸 *Запрос вывода*\n\nДоступно: *{user.earned_rub:.0f} ₽*\n\nВыберите сумму:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("payout:amount:"), PayoutStates.entering_amount)
async def payout_select_amount(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Обработка выбора фиксированной / всей суммы; переход к custom-вводу."""
    amount_str = (callback.data or "").split(":")[-1]
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer(USER_NOT_FOUND, show_alert=True)
        return

    if not isinstance(callback.message, Message):
        return
    if amount_str == "custom":
        cancel_kb = InlineKeyboardBuilder()
        cancel_kb.button(text=CANCEL_BTN, callback_data=PAYOUT_START_SCENE)
        await callback.message.edit_text(
            f"💸 Введите сумму вывода (в рублях):\n\n"
            f"📌 Минимум: 1 000 ₽\n"
            f"📌 Максимум: {user.earned_rub:.0f} ₽",
            reply_markup=cancel_kb.as_markup(),
        )
        await callback.answer()
        return

    gross = user.earned_rub if amount_str == "all" else Decimal(amount_str)

    if gross < MIN_PAYOUT:
        await callback.answer("❌ Минимум 1 000 ₽", show_alert=True)
        return
    if gross > user.earned_rub:
        await callback.answer("❌ Недостаточно средств", show_alert=True)
        return

    await _show_amount_confirmation(callback.message, state, gross, edit=True)
    await callback.answer()


@router.message(PayoutStates.entering_amount)
async def payout_custom_input(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обработка произвольной суммы, введённой вручную."""
    try:
        gross = Decimal((message.text or "").strip().replace(" ", "").replace(",", "."))
    except Exception:
        await message.answer("❌ Введите число (например: 5000)")
        return

    if message.from_user is None:
        return
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer(USER_NOT_FOUND)
        return

    if gross < MIN_PAYOUT:
        await message.answer("❌ Минимальная сумма — 1 000 ₽")
        return
    if gross > user.earned_rub:
        await message.answer(f"❌ Недостаточно средств. Доступно: {user.earned_rub:.0f} ₽")
        return

    await _show_amount_confirmation(message, state, gross, edit=False)


async def _show_amount_confirmation(
    msg,
    state: FSMContext,
    gross: Decimal,
    *,
    edit: bool,
) -> None:
    """Показать экран подтверждения суммы."""
    fee = (gross * PAYOUT_FEE_RATE).quantize(Decimal("0.01"))
    net = gross - fee

    await state.update_data(gross_amount=str(gross), fee_amount=str(fee), net_amount=str(net))
    await state.set_state(PayoutStates.confirming)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Продолжить (ввод реквизитов)", callback_data="payout:confirm")
    builder.button(text="🔙 Изменить сумму", callback_data=PAYOUT_START_SCENE)
    builder.adjust(1)

    text = (
        f"💸 *Подтверждение вывода*\n\n"
        f"Запрашиваемая сумма: *{gross:.0f} ₽*\n"
        f"Комиссия (1,5%): *−{fee:.2f} ₽*\n"
        f"──────────────────\n"
        f"Будет переведено: *{net:.2f} ₽*"
    )
    markup = builder.as_markup()

    if edit:
        await msg.edit_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await msg.answer(text, reply_markup=markup, parse_mode="Markdown")


@router.callback_query(F.data == "payout:confirm", PayoutStates.confirming)
async def payout_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Переход к вводу реквизитов."""
    await state.set_state(PayoutStates.entering_requisites)

    builder = InlineKeyboardBuilder()
    builder.button(text=CANCEL_BTN, callback_data="main:payouts")
    builder.adjust(1)

    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        "💳 Введите реквизиты для получения:\n\n"
        "• Номер карты (16 цифр)\n"
        "• Или номер телефона для СБП (+7XXXXXXXXXX)",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.message(PayoutStates.entering_requisites)
async def payout_requisites_input(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Получить реквизиты и создать заявку на выплату."""
    requisites = (message.text or "").strip()
    clean = requisites.replace(" ", "").replace("-", "")

    is_card = bool(re.match(r"^\d{16}$", clean))
    is_phone = bool(re.match(r"^(\+7|8)\d{10}$", clean))

    if not is_card and not is_phone:
        await message.answer(
            "❌ Неверный формат.\n\nВведите 16-значный номер карты или телефон (+7XXXXXXXXXX)"
        )
        return

    data = await state.get_data()
    gross = Decimal(data["gross_amount"])
    fee = Decimal(data["fee_amount"])
    net = Decimal(data["net_amount"])

    if message.from_user is None:
        await state.clear()
        return
    user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer(USER_NOT_FOUND)
        await state.clear()
        return

    if user.earned_rub < gross:
        await message.answer("❌ Недостаточно средств на балансе")
        await state.clear()
        return

    try:
        payout = PayoutRequest(
            owner_id=user.id,
            gross_amount=gross,
            fee_amount=fee,
            net_amount=net,
            status=PayoutStatus.pending,
            requisites=requisites,
        )
        user.earned_rub -= gross
        session.add(payout)
        await session.commit()
        logger.info(f"PayoutRequest created: gross={gross} net={net} user={user.id}")
    except Exception as e:
        logger.error(f"payout create error for user {user.id}: {e}")
        await session.rollback()
        await message.answer("❌ Ошибка создания заявки. Попробуйте позже.")
        await state.clear()
        return

    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Меню владельца", callback_data="main:own_menu")
    builder.adjust(1)

    await message.answer(
        f"✅ *Заявка на вывод создана!*\n\n"
        f"К получению: *{net:.2f} ₽*\n"
        f"Комиссия: *{fee:.2f} ₽*\n"
        f"Реквизиты: `{requisites}`\n\n"
        f"⏱ Обработка до 24 часов (09:00–22:00 МСК).",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
