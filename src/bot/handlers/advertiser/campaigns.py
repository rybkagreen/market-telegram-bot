"""Advertiser campaigns handler."""

from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.advertiser.my_campaigns import my_campaigns_kb
from src.bot.states.placement import PlacementStates
from src.bot.utils.safe_callback import safe_callback_edit

router = Router()


@router.callback_query(lambda c: c.data == "main:my_campaigns")
async def show_my_campaigns(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать мои кампании."""
    # TODO: Get campaigns from DB
    campaigns = []
    text = "📋 Мои кампании"
    await safe_callback_edit(callback, text, reply_markup=my_campaigns_kb(campaigns))


@router.callback_query(lambda c: c.data.startswith("camp:detail:"))
async def camp_detail(callback: CallbackQuery) -> None:
    """Детали кампании."""
    await callback.answer("Детали кампании", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("camp:cancel:"))
async def camp_cancel(callback: CallbackQuery) -> None:
    """Отменить кампанию."""
    await callback.answer("Кампания отменена", show_alert=True)


# ISSUE #11: Принять контр-предложение
@router.callback_query(F.data.startswith("camp:counter:accept:"))
async def camp_counter_accept(callback: CallbackQuery, session: AsyncSession) -> None:
    """Рекламодатель принимает контр-предложение владельца."""
    from src.db.models.placement_request import PlacementRequest, PlacementStatus

    request_id = int(callback.data.split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req or req.status != PlacementStatus.counter_offer:
        await callback.answer("❌ Контр-предложение недоступно", show_alert=True)
        return

    if req.counter_price:
        req.final_price = req.counter_price
    if req.counter_schedule:
        req.final_schedule = req.counter_schedule
    req.status = PlacementStatus.pending_payment

    from datetime import UTC, datetime, timedelta

    req.expires_at = datetime.now(UTC) + timedelta(hours=24)
    await session.commit()

    price = req.final_price or req.proposed_price
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💳 Оплатить {price:.0f} ₽", callback_data=f"camp:pay:{request_id}")
    builder.button(text="❌ Отменить", callback_data=f"camp:cancel:{request_id}")
    builder.adjust(1)

    schedule_str = req.final_schedule.strftime("%d.%m.%Y %H:%M") if req.final_schedule else "—"
    await callback.message.edit_text(
        f"✅ *Условия приняты!*\n\n"
        f"💰 Итоговая цена: *{price:.0f} ₽*\n"
        f"📅 Время публикации: *{schedule_str}*\n\n"
        f"⏱ Оплатите в течение 24 часов.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ISSUE #11: Начать раунд контр-переговоров
@router.callback_query(F.data.startswith("camp:counter:reply:"))
async def camp_counter_reply(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Рекламодатель отправляет встречное предложение по цене."""
    from src.db.models.placement_request import PlacementRequest

    request_id = int(callback.data.split(":")[-1])
    req = await session.get(PlacementRequest, request_id)
    if not req:
        await callback.answer("❌ Заявка не найдена", show_alert=True)
        return

    if req.counter_offer_count >= 3:
        await callback.answer("❌ Достигнут лимит раундов (3/3)", show_alert=True)
        return

    await state.update_data(counter_request_id=request_id)
    await state.set_state(PlacementStates.arbitrating)

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data=f"camp:cancel:{request_id}")

    price = req.counter_price or req.proposed_price
    await callback.message.edit_text(
        f"✏️ *Контр-предложение*\n\n"
        f"Раунд: *{req.counter_offer_count + 1}/3*\n"
        f"Текущая цена: *{price:.0f} ₽*\n\n"
        f"Введите вашу цену (число в рублях):",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ISSUE #11: Обработка ввода цены контр-предложения
@router.message(PlacementStates.arbitrating)
async def camp_counter_input(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Принять цену контр-предложения от рекламодателя."""
    from src.db.models.placement_request import PlacementRequest, PlacementStatus

    data = await state.get_data()
    request_id = data.get("counter_request_id")

    if not request_id:
        await state.clear()
        return

    try:
        new_price = Decimal(message.text.strip().replace(" ", ""))
        if new_price < Decimal("100"):
            await message.answer("❌ Минимальная цена 100 ₽")
            return
    except Exception:
        await message.answer("❌ Введите число (например: 450)")
        return

    req = await session.get(PlacementRequest, request_id)
    if not req:
        await state.clear()
        return

    req.counter_price = new_price
    req.counter_offer_count += 1
    req.status = PlacementStatus.pending_owner

    from datetime import UTC, datetime, timedelta

    req.expires_at = datetime.now(UTC) + timedelta(hours=24)
    await session.commit()
    await state.clear()

    # Уведомить владельца канала
    from src.bot.handlers.shared.notifications import notify_placement_new
    from src.db.models.user import User

    owner = await session.get(User, req.owner_id)
    if owner and message.bot:
        try:
            notify_kb = InlineKeyboardBuilder()
            notify_kb.button(text="👀 Посмотреть", callback_data=f"req:view:{request_id}")
            await notify_placement_new(message.bot, owner.telegram_id, request_id, notify_kb.as_markup())
        except Exception:
            pass

    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Мои кампании", callback_data="main:my_campaigns")

    await message.answer(
        f"✅ *Контр-предложение отправлено!*\n\n"
        f"💰 Ваша цена: *{new_price:.0f} ₽*\n"
        f"⏱ Владелец должен ответить в течение 24 часов.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
