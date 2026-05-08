"""Billing handlers."""

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.utils.portal_deeplink import PortalDeeplinkError, build_portal_deeplink
from src.config.settings import settings
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

_PLAN_PRICES = {
    "starter": settings.tariff_cost_starter,
    "pro": settings.tariff_cost_pro,
    "business": settings.tariff_cost_business,
}
_PLAN_NAMES = {"free": "Free 🆓", "starter": "Starter 🚀", "pro": "Pro 💎", "business": "Agency 🏢"}

USER_NOT_FOUND = "Пользователь не найден."
CABINET_SCENE = "main:cabinet"

router = Router()


@router.callback_query(F.data == "billing:topup_start")
async def topup_start(callback: CallbackQuery) -> None:
    """Topup flow moved к web portal (T1.2.5f). Mints portal deeplink and renders inline button."""
    if not isinstance(callback.message, Message):
        return
    try:
        topup_url = await build_portal_deeplink(
            telegram_id=callback.from_user.id,
            redirect_path="/topup",
        )
    except PortalDeeplinkError as exc:
        logger.warning(
            "topup_redirect_failed",
            extra={
                "event": "topup_redirect_failed",
                "telegram_id": callback.from_user.id,
                "error": str(exc),
            },
        )
        await callback.answer("Не удалось открыть портал. Попробуйте ещё раз.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "Пополнение баланса перенесено в веб-портал.\nОткройте по ссылке ниже:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🌐 Открыть веб-портал", url=topup_url)]]
        ),
    )


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
            builder.button(
                text=f"{_PLAN_NAMES[plan]} — {_PLAN_PRICES[plan]} ₽/мес",
                callback_data=f"plan:buy:{plan}",
            )
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

        topup_url: str | None = None
        try:
            topup_url = await build_portal_deeplink(
                telegram_id=user.telegram_id,
                redirect_path="/topup",
            )
        except PortalDeeplinkError as exc:
            logger.warning(
                "plan_buy_topup_button_skipped",
                extra={
                    "event": "plan_buy_topup_button_skipped",
                    "telegram_id": user.telegram_id,
                    "error": str(exc),
                },
            )

        builder = InlineKeyboardBuilder()
        if topup_url:
            builder.button(text="💳 Пополнить баланс", url=topup_url)
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
            type=TransactionType.plan_purchase,
            amount=Decimal(str(price)),
            description=f"Покупка тарифа {_PLAN_NAMES[plan]}",
        )
    )

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
