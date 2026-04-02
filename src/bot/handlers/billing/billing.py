"""Billing handlers."""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.billing.topup import (
    topup_amounts_kb,
    topup_confirm_kb,
    topup_payment_kb,
    topup_success_kb,
)
from src.bot.states.billing import TopupStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

_PLAN_PRICES = {"starter": 490, "pro": 1490, "business": 4990}
_PLAN_NAMES = {"free": "Free 🆓", "starter": "Starter 🚀", "pro": "Pro 💎", "business": "Agency 🏢"}

USER_NOT_FOUND = "Пользователь не найден."
CABINET_SCENE = "main:cabinet"

router = Router()


@router.callback_query(lambda c: c.data == "billing:topup_start")
async def topup_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать пополнение."""
    if not isinstance(callback.message, Message):
        return
    await state.set_state(TopupStates.entering_amount)
    await callback.answer("Выберите сумму")
    await callback.message.answer("💰 Выберите сумму пополнения:", reply_markup=topup_amounts_kb())


@router.callback_query(lambda c: c.data.startswith("topup:amount:"))
async def topup_select_amount(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбрать сумму пополнения."""
    amount = (callback.data or "").split(":")[-1]
    await state.update_data(amount=amount)
    await state.set_state(TopupStates.confirming)
    text = f"Пополнение на {amount} ₽\nКомиссия: {Decimal(amount) * Decimal('0.035'):.2f} ₽\nК оплате: {Decimal(amount) * Decimal('1.035'):.2f} ₽"
    await safe_callback_edit(callback, text, reply_markup=topup_confirm_kb())


@router.callback_query(F.data == "topup:pay", TopupStates.confirming)
async def topup_pay(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Создать платёж ЮKassa."""
    if not isinstance(callback.message, Message):
        return
    data = await state.get_data()
    amount = Decimal(str(data["amount"]))
    gross = (amount * Decimal("1.035")).quantize(Decimal("0.01"))
    credits = int(amount)

    await callback.message.edit_text(
        f"⏳ *Создаём платёж...*\n\nСумма к оплате: *{gross} ₽*",
        parse_mode="Markdown",
    )

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer(USER_NOT_FOUND, show_alert=True)
        return

    from src.core.services.yookassa_service import yookassa_service

    try:
        record = await yookassa_service.create_payment(
            amount_rub=gross,
            credits=credits,
            user_id=user.id,
        )
        await state.update_data(payment_id=record.payment_id)
        await state.set_state(TopupStates.waiting_payment)
        await callback.message.edit_text(
            "💳 *Оплата*\n\n"
            "Перейдите по ссылке для оплаты.\n\n"
            "⏱ Ссылка действует 15 минут.",
            reply_markup=topup_payment_kb(record.payment_url or "", record.payment_id),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error("YooKassa error for user %s: %s", user.id, e)
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад", callback_data="billing:topup_start")
        await callback.message.edit_text(
            "❌ Ошибка создания платежа. Попробуйте позже.\n\n"
            "Если проблема повторяется — обратитесь в поддержку.",
            reply_markup=builder.as_markup(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("topup:check:"))
async def topup_check(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Проверить статус платежа."""
    if not isinstance(callback.message, Message):
        return
    payment_id = (callback.data or "").split(":")[-1]
    from src.core.services.yookassa_service import yookassa_service

    try:
        status = await yookassa_service.get_payment_status(payment_id)
        if status == "succeeded":
            user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
            await state.clear()
            balance = user.balance_rub if user else 0
            await callback.message.edit_text(
                f"✅ *Баланс пополнен!*\n\nНовый баланс: *{balance} ₽*",
                reply_markup=topup_success_kb(),
                parse_mode="Markdown",
            )
        elif status == "pending":
            await callback.answer("⏳ Платёж ещё не получен. Подождите немного.", show_alert=True)
            return
        else:
            await callback.answer("❌ Платёж не прошёл.", show_alert=True)
            return
    except Exception as e:
        logger.error("YooKassa check error: %s", e)
        await callback.answer("❌ Ошибка проверки платежа.", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data.startswith("topup:cancel:"))
async def topup_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменить пополнение."""
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 В кабинет", callback_data=CABINET_SCENE)
    await callback.message.edit_text("❌ Пополнение отменено.", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "billing:plans")
async def show_plans(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать тарифные планы."""
    if not isinstance(callback.message, Message):
        return
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer(USER_NOT_FOUND, show_alert=True)
        return
    current = _PLAN_NAMES.get(user.plan, user.plan)

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    for plan in ("starter", "pro", "business"):
        if user.plan != plan:
            builder.button(text=f"{_PLAN_NAMES[plan]} — {_PLAN_PRICES[plan]} ₽/мес", callback_data=f"plan:buy:{plan}")
    builder.button(text="🔙 В кабинет", callback_data=CABINET_SCENE)
    builder.adjust(1)

    await callback.message.edit_text(
        f"⭐ *Тарифные планы*\n\n"
        f"Ваш текущий тариф: *{current}*\n\n"
        f"──────────────────\n"
        f"🆓 *Free* — 0 ₽/мес\n• 1 активная кампания\n• Формат: Пост 24ч\n\n"
        f"🚀 *Starter* — 490 ₽/мес\n• 5 кампаний\n• Форматы: Пост 24ч, 48ч\n• AI-генерация × 3/мес\n\n"
        f"💎 *Pro* — 1 490 ₽/мес\n• 20 кампаний\n• Форматы: Пост 24ч, 48ч, 7 дней\n• AI × 20/мес\n\n"
        f"🏢 *Agency* — 4 990 ₽/мес\n• Безлимит кампаний и AI\n• Все 5 форматов (включая закрепы!)",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("plan:buy:"))
async def buy_plan(callback: CallbackQuery, session: AsyncSession) -> None:
    """Купить тарифный план."""
    if not isinstance(callback.message, Message):
        return
    plan = (callback.data or "").split(":")[-1]
    if plan not in _PLAN_PRICES:
        await callback.answer("❌ Неверный тариф.", show_alert=True)
        return

    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer(USER_NOT_FOUND, show_alert=True)
        return

    price = _PLAN_PRICES[plan]
    if user.balance_rub < price:
        needed = price - user.balance_rub
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Пополнить баланс", callback_data="billing:topup_start")
        builder.button(text="🔙 Назад", callback_data="billing:plans")
        builder.adjust(1)
        await callback.message.edit_text(
            f"❌ *Недостаточно средств*\n\n"
            f"Тариф *{_PLAN_NAMES[plan]}* стоит *{price} ₽/мес*\n"
            f"Ваш баланс: *{user.balance_rub} ₽*\n"
            f"Не хватает: *{needed} ₽*",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )
        await callback.answer()
        return

    await UserRepository(session).update_balance(user.id, -Decimal(str(price)))
    user.plan = plan
    user.plan_expires_at = datetime.now(UTC) + timedelta(days=30)
    session.add(
        Transaction(
            user_id=user.id,
            type=TransactionType.credits_buy,
            amount=Decimal(str(price)),
            description=f"Покупка тарифа {_PLAN_NAMES[plan]}",
        )
    )
    await session.commit()

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text="📣 Меню рекламодателя", callback_data="main:adv_menu")
    builder.button(text="👤 Кабинет", callback_data=CABINET_SCENE)
    builder.adjust(1)
    await callback.message.edit_text(
        f"✅ *Тариф активирован!*\n\n"
        f"⭐ Тариф: *{_PLAN_NAMES[plan]}*\n"
        f"📅 Действует до: *{user.plan_expires_at.strftime('%d.%m.%Y')}*\n"
        f"💳 Списано: *{price} ₽*",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()
