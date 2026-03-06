"""
Handlers для биллинга и платежей: кредиты, CryptoBot, Telegram Stars.
"""

import logging
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.billing import (  # type: ignore[attr-defined]
    CREDIT_PACKAGES,
    BillingCB,
    get_currency_kb,
    get_packages_kb,
    get_plans_kb,
    get_topup_methods_kb,
)
from src.bot.keyboards.main_menu import MainMenuCB
from src.bot.utils.safe_callback import safe_callback_edit
from src.config.settings import settings
from src.core.services.cryptobot_service import cryptobot_service
from src.db.models.crypto_payment import CryptoPayment, PaymentMethod, PaymentStatus
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = Router()


# ─── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ────────────────────────────────────────────────


def _get_package_info(credits_str: str) -> tuple[int, int, str]:
    """Вернуть (credits, bonus, label) для пакета по значению кредитов."""
    for label, credits, bonus, value in CREDIT_PACKAGES:
        if value == credits_str:
            return credits, bonus, label
    raise ValueError(f"Unknown package: {credits_str}")


def _format_balance(credits: int) -> str:
    """Форматировать баланс с разделителями тысяч."""
    return f"{credits:,}".replace(",", " ")


# ─── ГЛАВНАЯ СТРАНИЦА БАЛАНСА ────────────────────────────────────────────────


@router.callback_query(MainMenuCB.filter(F.action == "balance"))
async def show_balance(callback: CallbackQuery) -> None:
    """Показать баланс и варианты пополнения."""
    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Конвертируем plan из строки в Enum если нужно
        from src.db.models.user import UserPlan

        plan = user.plan if isinstance(user.plan, UserPlan) else UserPlan(user.plan)
        plan_value = plan.value.upper()

        # Информация о тарифе
        plan_expires = ""
        if user.plan_expires_at:
            expires_str = user.plan_expires_at.strftime("%d.%m.%Y")
            plan_expires = f"\n📅 Тариф активен до: <b>{expires_str}</b>"

        # ИИ генерации (для PRO/BUSINESS)
        ai_info = ""
        included = user.get_included_ai_generations()
        if included > 0:
            used = user.ai_generations_used
            ai_info = f"\n🤖 ИИ-генерации: <b>{used}/{included}</b> использовано"

        text = (
            f"💳 <b>Ваш баланс</b>\n\n"
            f"Кредиты: <b>{_format_balance(user.credits)} кр</b>\n"
            f"Тариф: <b>{plan_value}</b>"
            f"{plan_expires}"
            f"{ai_info}\n\n"
            f"<b>Что такое кредиты?</b>\n"
            f"1 кредит ≈ 1₽. Используются для оплаты тарифов и ИИ-генерации.\n\n"
            f"Выберите способ пополнения:"
        )
        await safe_callback_edit(callback, text, reply_markup=get_topup_methods_kb())


# ─── CRYPTO BOT ──────────────────────────────────────────────────────────────


@router.callback_query(BillingCB.filter(F.action == "topup_crypto"))
async def show_crypto_packages(callback: CallbackQuery) -> None:
    """Показать пакеты кредитов для крипто-оплаты."""
    text = (
        "💎 <b>Пополнение через CryptoBot</b>\n\n"
        "Поддерживаемые валюты: USDT, TON, BTC, ETH, LTC\n\n"
        "Выберите пакет кредитов:\n\n"
    )
    for label, credits, bonus, _ in CREDIT_PACKAGES:
        bonus_text = f" (+{bonus} бонус)" if bonus > 0 else ""
        usdt_amount = round(credits / settings.credits_per_usdt, 1)
        text += f"• <b>{label}{bonus_text}</b> — ~{usdt_amount} USDT\n"

    await safe_callback_edit(callback, text, reply_markup=get_packages_kb("crypto"))


@router.callback_query(BillingCB.filter(F.action == "pkg_crypto"))
async def select_crypto_package(callback: CallbackQuery, callback_data: BillingCB) -> None:
    """Выбран пакет — показать выбор валюты."""
    credits_str = callback_data.value
    credits, bonus, label = _get_package_info(credits_str)
    total = credits + bonus

    text = (
        f"💎 <b>Пакет: {label}</b>\n\n"
        f"Кредитов: <b>{credits:,}</b>"
        + (f"\nБонус: <b>+{bonus}</b>" if bonus > 0 else "")
        + f"\nИтого: <b>{total:,} кр</b>\n\n"
        f"Выберите валюту для оплаты:\n\n"
    )

    for currency in ["USDT", "TON", "BTC", "ETH", "LTC"]:
        rate = settings.currency_rates.get(currency, 1)
        amount = round(credits / rate, 6)
        text += f"• {currency}: <b>{amount}</b>\n"

    await safe_callback_edit(callback, text, reply_markup=get_currency_kb(credits))


@router.callback_query(BillingCB.filter(F.action == "pay_crypto"))
async def create_crypto_invoice(callback: CallbackQuery, callback_data: BillingCB) -> None:
    """Создать счёт CryptoBot для выбранной валюты."""
    if not settings.cryptobot_token:
        await callback.answer(
            "❌ CryptoBot не настроен. Обратитесь к администратору.",
            show_alert=True,
        )
        return

    parts = callback_data.value.split("_")
    credits_str, currency = parts[0], parts[1]
    credits, bonus, label = _get_package_info(credits_str)

    rate = settings.currency_rates.get(currency, 1)
    amount = round(credits / rate, 6)

    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        try:
            payload_str = f"uid:{user.id}:credits:{credits}:bonus:{bonus}"
            logger.info(f"Creating CryptoBot invoice: {currency} {amount} for {credits} credits")
            invoice = await cryptobot_service.create_invoice(
                currency=currency,
                amount=amount,
                payload=payload_str,
                description=f"Market Bot: {label} ({credits} кр)",
            )
            logger.info(f"Invoice created: {invoice.invoice_id} - {invoice.pay_url}")
        except Exception as e:
            logger.error(f"CryptoBot invoice creation failed: {e}", exc_info=True)
            await callback.answer(f"❌ Ошибка создания счёта: {str(e)}", show_alert=True)
            return

        payment = CryptoPayment(
            user_id=user.id,
            method=PaymentMethod.CRYPTOBOT,
            invoice_id=invoice.invoice_id,
            pay_url=invoice.pay_url,
            currency=currency,
            amount=amount,
            credits=credits,
            bonus_credits=bonus,
            status=PaymentStatus.PENDING,
        )
        session.add(payment)
        await session.commit()
    logger.info(f"Payment created: invoice_id={invoice.invoice_id}, pay_url={invoice.pay_url}")

    total_credits = credits + bonus
    text = (
        f"💎 <b>Счёт создан!</b>\n\n"
        f"Пакет: <b>{label}</b>\n"
        f"Итого кредитов: <b>{total_credits:,} кр</b>\n"
        f"Сумма: <b>{amount} {currency}</b>\n\n"
        f"⏱ Счёт действителен 1 час.\n\n"
        f"Нажмите «Оплатить» — вас перенаправит в @CryptoBot."
    )

    builder = InlineKeyboardBuilder()
    builder.button(
        text=f"💳 Оплатить {amount} {currency}",
        callback_data=BillingCB(action="pay_crypto_url", value=invoice.invoice_id),
    )
    builder.button(
        text="🔄 Проверить оплату",
        callback_data=BillingCB(action="check_invoice", value=invoice.invoice_id),
    )
    builder.button(text="🔙 Назад", callback_data=BillingCB(action="topup_crypto"))
    builder.adjust(1, 1, 1)

    logger.info(f"Sending message with pay_url: {invoice.pay_url}")
    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    logger.info("Message sent successfully")


@router.callback_query(BillingCB.filter(F.action == "pay_crypto_url"))
async def send_payment_url(callback: CallbackQuery, callback_data: BillingCB) -> None:
    """Отправить ссылку на оплату. URL берётся из БД по invoice_id."""
    invoice_id = callback_data.value

    async with async_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(CryptoPayment).where(CryptoPayment.invoice_id == invoice_id)
        )
        payment = result.scalar_one_or_none()

    if not payment:
        await callback.answer("❌ Счёт не найден", show_alert=True)
        return

    if not payment.pay_url:
        await callback.answer("❌ Ссылка на оплату недоступна", show_alert=True)
        return

    if payment.status == PaymentStatus.PAID:
        await callback.answer("✅ Этот счёт уже оплачен", show_alert=True)
        return

    if payment.status in (PaymentStatus.EXPIRED, PaymentStatus.CANCELLED):
        await callback.answer("❌ Счёт истёк или отменён. Создайте новый.", show_alert=True)
        return

    await callback.message.answer(  # type: ignore[union-attr]
        f"💳 <b>Счёт на оплату</b>\n\n"
        f"Нажмите на ссылку:\n"
        f"<a href='{payment.pay_url}'>Оплатить счёт</a>\n\n"
        f"Или скопируйте ссылку:\n"
        f"<code>{payment.pay_url}</code>\n\n"
        f"⏱ Счёт действителен 1 час.",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer("✅ Ссылка отправлена!")


@router.callback_query(BillingCB.filter(F.action == "check_invoice"))
async def check_invoice_status(callback: CallbackQuery, callback_data: BillingCB) -> None:
    """Проверить статус счёта CryptoBot вручную."""
    invoice_id = callback_data.value

    async with async_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(CryptoPayment).where(CryptoPayment.invoice_id == invoice_id)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            await callback.answer("❌ Счёт не найден", show_alert=True)
            return

        if payment.status == PaymentStatus.PAID:
            await callback.answer(
                f"✅ Уже оплачено! {payment.total_credits} кр зачислены.",
                show_alert=True,
            )
            return

        try:
            invoice = await cryptobot_service.get_invoice(invoice_id)
        except Exception as e:
            await callback.answer(f"❌ Ошибка проверки: {e}", show_alert=True)
            return

        if invoice.status == "paid":
            user_repo = UserRepository(session)
            total = payment.total_credits
            await user_repo.update_credits(payment.user_id, total)

            from sqlalchemy import update

            await session.execute(
                update(CryptoPayment)
                .where(CryptoPayment.id == payment.id)
                .values(status=PaymentStatus.PAID, credited_at=datetime.now(UTC))
            )
            await session.commit()

            await callback.answer(
                f"✅ Оплата прошла! Зачислено {total:,} кредитов.", show_alert=True
            )
        elif invoice.status in ("expired", "cancelled"):
            from sqlalchemy import update

            await session.execute(
                update(CryptoPayment)
                .where(CryptoPayment.id == payment.id)
                .values(status=PaymentStatus[invoice.status.upper()].value)
            )
            await session.commit()
            await callback.answer(f"❌ Счёт {invoice.status}. Создайте новый.", show_alert=True)
        else:
            await callback.answer("⏳ Ожидаем оплату...", show_alert=True)


# ─── TELEGRAM STARS ──────────────────────────────────────────────────────────


@router.callback_query(BillingCB.filter(F.action == "topup_stars"))
async def show_stars_packages(callback: CallbackQuery) -> None:
    """Показать пакеты для оплаты Stars."""
    text = (
        "⭐ <b>Пополнение через Telegram Stars</b>\n\n"
        f"Курс: 1 ⭐ = {settings.credits_per_star} кредита\n\n"
        "Выберите пакет:\n\n"
    )
    for label, credits, bonus, _ in CREDIT_PACKAGES:
        stars_needed = credits // settings.credits_per_star
        bonus_text = f" (+{bonus} бонус)" if bonus > 0 else ""
        text += f"• <b>{label}{bonus_text}</b> — {stars_needed} ⭐\n"

    await safe_callback_edit(callback, text, reply_markup=get_packages_kb("stars"))


@router.callback_query(BillingCB.filter(F.action == "pkg_stars"))
async def create_stars_invoice(callback: CallbackQuery, callback_data: BillingCB) -> None:
    """Создать Stars invoice через Telegram Payments API."""
    if not settings.stars_enabled:
        await callback.answer("❌ Telegram Stars не настроены.", show_alert=True)
        return

    credits_str = callback_data.value
    credits, bonus, label = _get_package_info(credits_str)
    stars_amount = credits // settings.credits_per_star

    async with async_session_factory() as session:
        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        payment = CryptoPayment(
            user_id=user.id,
            method=PaymentMethod.STARS,
            stars_amount=stars_amount,
            credits=credits,
            bonus_credits=bonus,
            status=PaymentStatus.PENDING,
        )
        session.add(payment)
        await session.commit()

    total = credits + bonus
    await callback.message.answer_invoice(  # type: ignore[union-attr]
        title=f"Market Bot: {label}",
        description=f"Пополнение баланса на {total:,} кредитов",
        payload=f"stars:{payment.id}",
        currency="XTR",
        prices=[LabeledPrice(label=f"{total:,} кредитов", amount=stars_amount)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def stars_pre_checkout(pre_checkout_query) -> None:
    """Подтвердить Stars платёж (обязательный шаг Telegram API)."""
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def stars_payment_success(message: Message) -> None:
    """Обработать успешный Stars платёж."""
    payment = message.successful_payment
    if payment is None:
        logger.error("successful_payment is None in stars payment handler")
        return
    payload = payment.invoice_payload

    if not payload.startswith("stars:"):
        return

    payment_db_id = int(payload.split(":")[1])

    async with async_session_factory() as session:
        from sqlalchemy import select, update

        result = await session.execute(
            select(CryptoPayment).where(CryptoPayment.id == payment_db_id)
        )
        db_payment = result.scalar_one_or_none()

        if not db_payment or db_payment.status == PaymentStatus.PAID:
            return

        user_repo = UserRepository(session)
        total = db_payment.total_credits
        await user_repo.update_credits(db_payment.user_id, total)

        if payment is not None:
            await session.execute(
                update(CryptoPayment)
                .where(CryptoPayment.id == payment_db_id)
                .values(
                    status=PaymentStatus.PAID,
                    telegram_payment_charge_id=payment.telegram_payment_charge_id,
                    credited_at=datetime.now(UTC),
                )
            )
        await session.commit()

    await message.answer(
        f"✅ <b>Оплата прошла!</b>\n\n"
        f"Зачислено: <b>{total:,} кредитов</b> ⭐\n\n"
        f"Спасибо! Ваш баланс пополнен."
    )


# ─── ТАРИФЫ ──────────────────────────────────────────────────────────────────


@router.callback_query(BillingCB.filter(F.action == "plans"))
async def show_plans(callback: CallbackQuery) -> None:
    """Показать тарифные планы с ценами в кредитах."""
    text = (
        "📦 <b>Тарифные планы</b>\n\n"
        "🆓 <b>FREE</b> — 0 кр/мес\n"
        "  • Ознакомление с ботом\n"
        "  • Без кампаний\n\n"
        "🚀 <b>STARTER</b> — 299 кр/мес\n"
        "  • 5 кампаний в месяц\n"
        "  • 50 чатов/кампанию\n"
        "  • ИИ-генерация за кредиты\n\n"
        "💎 <b>PRO</b> — 999 кр/мес\n"
        "  • 20 кампаний в месяц\n"
        "  • 200 чатов/кампанию\n"
        "  • 5 ИИ-генераций включено\n\n"
        "🏢 <b>BUSINESS</b> — 2 999 кр/мес\n"
        "  • 100 кампаний в месяц\n"
        "  • 1 000 чатов/кампанию\n"
        "  • 20 ИИ-генераций включено\n\n"
        "💡 Тариф автоматически продлевается каждые 30 дней.\n"
        "При нехватке кредитов — план сбросится на FREE."
    )
    await safe_callback_edit(callback, text, reply_markup=get_plans_kb())


@router.callback_query(BillingCB.filter(F.action == "plan"))
async def plan_selected(callback: CallbackQuery, callback_data: BillingCB) -> None:
    """Выбрать и активировать тариф (списывает кредиты)."""
    plan_name = callback_data.value
    plan_costs = {"free": 0, "starter": 299, "pro": 999, "business": 2999}
    plan_cost = plan_costs.get(plan_name, 0)

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        if plan_name == "free":
            await user_repo.update(
                user.id, {"plan": "free", "plan_expires_at": None, "ai_generations_used": 0}
            )
            await session.commit()
            await callback.answer("✅ Переключились на FREE", show_alert=True)
            return

        if user.credits < plan_cost:
            await callback.answer(
                f"❌ Недостаточно кредитов!\nНужно: {plan_cost} кр\nУ вас: {user.credits} кр",
                show_alert=True,
            )
            return

        from datetime import timedelta

        await user_repo.update_credits(user.id, -plan_cost)
        await user_repo.reset_ai_usage(user.id)
        expires_at = datetime.now(UTC) + timedelta(days=30)
        await user_repo.update(user.id, {"plan": plan_name, "plan_expires_at": expires_at})
        await session.commit()

    await callback.answer(
        f"✅ Тариф {plan_name.upper()} активирован на 30 дней!",
        show_alert=True,
    )


# ─── ИСТОРИЯ ТРАНЗАКЦИЙ ──────────────────────────────────────────────────────


@router.callback_query(BillingCB.filter(F.action == "history"))
async def show_history(callback: CallbackQuery) -> None:
    """История пополнений кредитов."""
    async with async_session_factory() as session:
        from sqlalchemy import desc, select

        user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        result = await session.execute(
            select(CryptoPayment)
            .where(
                CryptoPayment.user_id == user.id,
                CryptoPayment.status == PaymentStatus.PAID,
            )
            .order_by(desc(CryptoPayment.credited_at))
            .limit(10)
        )
        payments = result.scalars().all()

        if not payments:
            text = "📋 <b>История пополнений пуста</b>\n\nВаши пополнения будут отображаться здесь."
        else:
            text = "📋 <b>Последние пополнения</b>\n\n"
            for p in payments:
                date = p.credited_at.strftime("%d.%m.%Y %H:%M") if p.credited_at else "—"
                total = p.total_credits
                method = "⭐ Stars" if p.method == PaymentMethod.STARS else f"💎 {p.currency}"
                text += f"✅ +{total:,} кр — {method} — {date}\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 К балансу", callback_data=MainMenuCB(action="balance"))
    builder.adjust(1)
    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())


# ─── ОБРАБОТКА КНОПКИ "ПОПОЛНИТЬ" ИЗ КАБИНЕТА ─────────────────────────────────


@router.callback_query(BillingCB.filter(F.action == "topup"))
async def topup_from_cabinet(callback: CallbackQuery) -> None:
    """
    Обработчик кнопки 'Пополнить' из личного кабинета.
    Показывает меню выбора метода пополнения.
    """
    await show_balance(callback)


# ─── ПУНКТ МЕНЮ (обратная совместимость) ─────────────────────────────────────


@router.callback_query(BillingCB.filter(F.action == "topup_menu"))
async def topup_menu(callback: CallbackQuery) -> None:
    """Вернуться в меню пополнения."""
    await show_balance(callback)
