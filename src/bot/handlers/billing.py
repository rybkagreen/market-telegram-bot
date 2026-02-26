"""
Handlers для биллинга и платежей.
"""

import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.billing import BillingCB, get_amount_kb
from src.bot.keyboards.main_menu import MainMenuCB
from src.bot.keyboards.pagination import PaginationCB
from src.core.services.billing_service import billing_service
from src.db.models.transaction import TransactionType
from src.db.repositories.transaction_repo import TransactionRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()


class PaymentStates(StatesGroup):
    """Состояния для ввода суммы пополнения."""

    waiting_amount = State()


# Эмодзи для типов транзакций
TRANSACTION_EMOJI = {
    TransactionType.TOPUP: "💚",
    TransactionType.SPEND: "🔴",
    TransactionType.BONUS: "🎁",
    TransactionType.REFUND: "↩️",
    TransactionType.ADJUSTMENT: "⚙️",
}


@router.callback_query(MainMenuCB.filter(F.action == "balance"))
async def show_balance(callback: CallbackQuery) -> None:
    """
    Показать баланс пользователя.

    Args:
        callback: Callback query.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        text = (
            f"💳 <b>Ваш баланс</b>\n\n"
            f"Текущая сумма: <b>{user.balance}₽</b>\n\n"
            f"Выберите сумму пополнения:"
        )

        await callback.message.edit_text(text, reply_markup=get_amount_kb())


@router.callback_query(BillingCB.filter(F.action == "topup"))
async def topup_selected(callback: CallbackQuery, callback_data: BillingCB, state: FSMContext) -> None:
    """
    Выбрана сумма пополнения.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
        state: FSM контекст.
    """
    amount_str = callback_data.value

    if amount_str == "custom":
        # Запрос произвольной суммы
        await state.set_state(PaymentStates.waiting_amount)

        text = (
            "💳 <b>Пополнение баланса</b>\n\n"
            "Введите сумму пополнения (от 50₽ до 100 000₽):\n\n"
            "Пример: 500"
        )

        await callback.message.edit_text(text)
        return

    # Предустановленная сумма
    try:
        amount = Decimal(amount_str)
    except Exception:
        await callback.answer("❌ Неверная сумма", show_alert=True)
        return

    await process_topup(callback, amount, state)


@router.message(PaymentStates.waiting_amount)
async def handle_custom_amount(message: Message, state: FSMContext) -> None:
    """
    Обработать ввод произвольной суммы.

    Args:
        message: Сообщение с суммой.
        state: FSM контекст.
    """
    amount_str = message.text.strip()

    # Удаляем символы рубля и пробелы
    amount_str = amount_str.replace("₽", "").replace("₽", "").strip()

    try:
        amount = Decimal(amount_str)
    except Exception:
        await message.answer(
            "❌ Неверный формат суммы.\n\n"
            "Введите числовое значение (например, 500):"
        )
        return

    # Валидация диапазона
    if amount < 50:
        await message.answer(
            "❌ Минимальная сумма: 50₽\n\n"
            "Введите сумму больше:"
        )
        return

    if amount > 100000:
        await message.answer(
            "❌ Максимальная сумма: 100 000₽\n\n"
            "Введите сумму меньше:"
        )
        return

    await state.clear()

    # Создаем платеж
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(message.from_user.id)

        if not user:
            await message.answer("❌ Пользователь не найден")
            return

    await process_topup(message, amount, state, user_balance=user.balance if user else Decimal("0"))


async def process_topup(
    target: Message | CallbackQuery,
    amount: Decimal,
    state: FSMContext,
    user_balance: Decimal | None = None,
) -> None:
    """
    Обработать пополнение баланса.

    Args:
        target: Сообщение или callback query.
        amount: Сумма пополнения.
        state: FSM контекст.
        user_balance: Баланс пользователя (опционально).
    """
    await state.clear()

    # Создаем платеж через billing_service
    try:
        payment_data = await billing_service.create_payment(
            user_id=target.from_user.id,
            amount=amount,
            payment_method="yookassa",
        )

        payment_id = payment_data["payment_id"]
        payment_url = payment_data["payment_url"]

        text = (
            f"💳 <b>Пополнение баланса</b>\n\n"
            f"Сумма: <b>{amount}₽</b>\n\n"
            f"Нажмите «Оплатить» для перехода к платежу."
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Оплатить", url=payment_url)
        builder.button(
            text="🔄 Проверить статус",
            callback_data=BillingCB(action="check_payment", value=payment_id)
        )
        builder.button(text="🔙 Отмена", callback_data=MainMenuCB(action="balance"))
        builder.adjust(2, 1)

        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=builder.as_markup())
        else:
            await target.answer(text, reply_markup=builder.as_markup())

        # Сохраняем payment_id в состоянии для проверки
        await state.update_data(payment_id=payment_id, payment_amount=str(amount))

    except Exception as e:
        logger.error(f"Payment creation error: {e}")

        text = (
            "❌ Ошибка создания платежа\n\n"
            "Попробуйте снова или выберите другую сумму."
        )

        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=get_amount_kb())
        else:
            await target.answer(text, reply_markup=get_amount_kb())


@router.callback_query(BillingCB.filter(F.action == "check_payment"))
async def check_payment_status(callback: CallbackQuery, callback_data: BillingCB) -> None:
    """
    Проверить статус платежа.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
    """
    payment_id = callback_data.value

    try:
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(callback.from_user.id)

            if not user:
                await callback.answer("❌ Пользователь не найден", show_alert=True)
                return

            payment_data = await billing_service.check_payment(
                payment_id=payment_id,
                user_id=user.id,
            )

        status = payment_data.get("status", "unknown")
        amount = payment_data.get("amount", "0")
        credited = payment_data.get("credited", False)

        if status == "succeeded" and credited:
            text = (
                f"✅ <b>Оплата прошла успешно!</b>\n\n"
                f"Сумма: <b>{amount}₽</b>\n"
                f"Средства зачислены на ваш баланс."
            )
        elif status == "succeeded":
            text = (
                f"⏳ <b>Оплата подтверждена</b>\n\n"
                f"Сумма: <b>{amount}₽</b>\n"
                f"Средства будут зачислены в ближайшее время."
            )
        elif status == "pending":
            text = (
                f"⏳ <b>Ожидаем подтверждение оплаты</b>\n\n"
                f"Сумма: <b>{amount}₽</b>\n\n"
                f"Если вы уже оплатили, подождите несколько минут."
            )
        elif status == "cancelled":
            text = (
                f"❌ <b>Платёж отменён</b>\n\n"
                f"Сумма: <b>{amount}₽</b>\n\n"
                f"Вы можете создать новый платёж."
            )
        else:
            text = (
                f"❓ <b>Неизвестный статус платежа</b>\n\n"
                f"Сумма: <b>{amount}₽</b>\n"
                f"Статус: {status}"
            )

        builder = InlineKeyboardBuilder()
        if status not in ("succeeded", "cancelled"):
            builder.button(
                text="🔄 Обновить",
                callback_data=BillingCB(action="check_payment", value=payment_id)
            )
        builder.button(text="🔙 К балансу", callback_data=MainMenuCB(action="balance"))
        builder.adjust(2)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"Payment check error: {e}")
        await callback.answer(f"❌ Ошибка проверки: {e}", show_alert=True)


@router.callback_query(BillingCB.filter(F.action == "history"))
async def show_transaction_history(callback: CallbackQuery) -> None:
    """
    Показать историю транзакций.

    Args:
        callback: Callback query.
    """
    await show_transactions_list(callback, page=1)


async def show_transactions_list(callback: CallbackQuery, page: int = 1) -> None:
    """
    Показать список транзакций с пагинацией.

    Args:
        callback: Callback query.
        page: Номер страницы.
    """
    page_size = 10

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        transaction_repo = TransactionRepository(session)
        transactions, total = await transaction_repo.get_by_user(
            user_id=user.id,
            page=page,
            page_size=page_size,
        )

        total_pages = max(1, (total + page_size - 1) // page_size)

        if not transactions:
            text = "📋 <b>История транзакций пуста</b>\n\n"
            text += "У вас пока не было операций с балансом."

            builder = InlineKeyboardBuilder()
            builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
            builder.adjust(1)

            await callback.message.edit_text(text, reply_markup=builder.as_markup())
            return

        # Формируем список транзакций
        text = f"📋 <b>История транзакций</b> ({total} всего)\n\n"

        for tx in transactions:
            emoji = TRANSACTION_EMOJI.get(tx.type, "📝")
            sign = "+" if tx.type in (TransactionType.TOPUP, TransactionType.BONUS) else "-"

            # Форматируем дату
            created = tx.created_at.strftime("%d.%m.%Y %H:%M") if tx.created_at else "—"

            # Описание
            description = tx.description or tx.meta_json.get("description", "") if tx.meta_json else ""
            if not description and tx.type == TransactionType.SPEND:
                description = "Списание за кампанию"
            elif not description and tx.type == TransactionType.BONUS:
                description = tx.meta_json.get("type", "Бонус") if tx.meta_json else "Бонус"

            text += (
                f"{emoji} <b>{sign}{tx.amount}₽</b>\n"
                f"   {description}\n"
                f"   {created}\n\n"
            )

        # Кнопки навигации
        builder = InlineKeyboardBuilder()

        if page > 1:
            builder.button(
                text="◀ Пред",
                callback_data=PaginationCB(prefix="transactions", page=page - 1)
            )

        builder.button(
            text=f"{page}/{total_pages}",
            callback_data=PaginationCB(prefix="transactions", page=page)
        )

        if page < total_pages:
            builder.button(
                text="След ▶",
                callback_data=PaginationCB(prefix="transactions", page=page + 1)
            )

        builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
        builder.adjust(2, 1, 1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(PaginationCB.filter(F.prefix == "transactions"))
async def transactions_pagination_callback(callback: CallbackQuery, callback_data: PaginationCB) -> None:
    """
    Callback handler для пагинации транзакций.

    Args:
        callback: Callback query.
        callback_data: Данные пагинации.
    """
    await show_transactions_list(callback, page=callback_data.page)


@router.callback_query(BillingCB.filter(F.action == "plan"))
async def plan_selected(callback: CallbackQuery, callback_data: BillingCB) -> None:
    """
    Выбран тарифный план.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
    """
    plan = callback_data.value

    plans_info = {
        "free": ("🆓 FREE", "0₽/мес", "0 кампаний, 0 чатов"),
        "starter": ("🚀 STARTER", "299₽/мес", "5 кампаний, 50 чатов"),
        "pro": ("💎 PRO", "999₽/мес", "20 кампаний, 200 чатов"),
        "business": ("🏢 BUSINESS", "2999₽/мес", "100 кампаний, 1000 чатов"),
    }

    if plan not in plans_info:
        await callback.answer("❌ Неверный тариф", show_alert=True)
        return

    name, price, limits = plans_info[plan]

    # Извлекаем цену из строки (например "299₽/мес" -> 299)
    price_value = int(price.replace("₽/мес", "").replace("₽", ""))

    text = (
        f"📦 <b>Смена тарифа</b>\n\n"
        f"Вы выбрали: <b>{name}</b>\n"
        f"Стоимость: <b>{price}</b>\n"
        f"Лимиты: {limits}\n\n"
        f"Для активации тарифа необходимо оплатить {price_value}₽."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить и подключить", callback_data=BillingCB(action="plan_pay", value=plan))
    builder.button(text="🔙 Назад", callback_data=BillingCB(action="plans", value="0"))
    builder.adjust(2)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(BillingCB.filter(F.action == "plan_pay"))
async def plan_pay(callback: CallbackQuery, callback_data: BillingCB) -> None:
    """
    Оплата и подключение тарифа.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
    """
    plan = callback_data.value

    # Цены тарифов
    plan_prices = {
        "free": 0,
        "starter": 299,
        "pro": 999,
        "business": 2999,
    }

    if plan not in plan_prices:
        await callback.answer("❌ Неверный тариф", show_alert=True)
        return

    price = plan_prices[plan]

    if price == 0:
        # Бесплатный тариф - меняем сразу
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(callback.from_user.id)

            if not user:
                await callback.answer("❌ Пользователь не найден", show_alert=True)
                return

            await user_repo.update(user.id, {"plan": plan})
            await user_repo.refresh(user)

        text = (
            f"✅ <b>Тариф изменён!</b>\n\n"
            f"Ваш новый тариф: <b>{plan}</b>"
        )
    else:
        # Создаём платёж
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(callback.from_user.id)

            if not user:
                await callback.answer("❌ Пользователь не найден", show_alert=True)
                return

            from decimal import Decimal

            from src.core.services.billing_service import billing_service

            payment_data = await billing_service.create_payment(
                user_id=user.id,
                amount=Decimal(price),
                payment_method="yookassa",
            )

            payment_url = payment_data["payment_url"]
            payment_id = payment_data["payment_id"]

        text = (
            f"💳 <b>Оплата тарифа {plan}</b>\n\n"
            f"Сумма: <b>{price}₽</b>\n\n"
            f"Нажмите «Оплатить» для перехода к платежу."
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Оплатить", url=payment_url)
        builder.button(
            text="🔄 Проверить статус",
            callback_data=BillingCB(action="check_payment", value=payment_id)
        )
        builder.button(text="🔙 Отмена", callback_data=MainMenuCB(action="cabinet"))
        builder.adjust(2, 1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 В кабинет", callback_data=MainMenuCB(action="cabinet"))
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
