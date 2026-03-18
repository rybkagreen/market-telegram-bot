"""Shared cabinet handler."""

from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.shared.cabinet import cabinet_kb, gamification_kb, referral_kb
from src.db.models.badge import UserBadge
from src.db.models.reputation_score import ReputationScore
from src.db.models.user import User
from src.db.repositories.user_repo import UserRepository

router = Router()

_PLAN_NAMES = {
    "free": "Free",
    "starter": "Starter 🚀",
    "pro": "Pro 💎",
    "business": "Agency 🏢",
}


@router.callback_query(F.data == "main:cabinet")
async def show_cabinet(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать кабинет."""
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    rep = await session.get(ReputationScore, user.id)
    adv_score = rep.advertiser_score if rep else 5.0
    own_score = rep.owner_score if rep else 5.0

    plan_name = _PLAN_NAMES.get(user.plan, user.plan)

    tax_block = ""
    if user.earned_rub > 0 and user.current_role in ("owner", "both"):
        month = datetime.now().strftime("%B %Y")
        tax_block = (
            f"\n\n💡 Заработок за {month}: *{user.earned_rub} ₽*\n"
            "Не забудьте задекларировать доход в приложении «Мой налог»."
        )

    text = (
        f"👤 *Кабинет*\n\n"
        f"💳 Баланс (рекламодатель): *{user.balance_rub} ₽*\n"
        f"💰 Заработок (владелец): *{user.earned_rub} ₽*\n\n"
        f"📊 Репутация рекл.: *{adv_score:.1f}/10* | "
        f"Репутация вл.: *{own_score:.1f}/10*\n\n"
        f"⭐ Тариф: *{plan_name}*\n"
        f"🏆 Ур. рекл.: *{user.advertiser_level}* ({user.advertiser_xp} XP) | "
        f"Ур. вл.: *{user.owner_level}* ({user.owner_xp} XP)\n\n"
        f"🆔 ID: `{user.id}`"
        f"{tax_block}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=cabinet_kb(user.current_role, user.earned_rub),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "cabinet:referral")
async def show_referral(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать реферальную программу."""
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    result = await session.execute(select(func.count()).where(User.referred_by_id == user.id))
    ref_count = result.scalar_one()
    await callback.message.edit_text(
        f"🎁 *Реферальная программа*\n\n"
        f"Приглашайте друзей и получайте бонусы!\n\n"
        f"🔗 Ваша ссылка:\n"
        f"`t.me/RekHarborBot?start=REF_{user.referral_code}`\n\n"
        f"👥 Приглашено: *{ref_count}* чел.\n"
        f"💰 Начислено бонусов: *0 ₽*\n\n"
        f"📋 Условия:\n"
        f"• За каждого приглашённого рекламодателя — +50 ₽ на баланс\n"
        f"• Бонус начисляется после первого пополнения реферала",
        reply_markup=referral_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "cabinet:referral:copy")
async def referral_copy(callback: CallbackQuery, session: AsyncSession) -> None:
    """Скопировать реферальную ссылку (показать в alert)."""
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    link = f"t.me/RekHarborBot?start=REF_{user.referral_code}"
    await callback.answer(f"Ссылка: {link}", show_alert=True)


@router.callback_query(F.data == "cabinet:gamification")
async def show_gamification(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать геймификацию."""
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    adv_xp_next = user.advertiser_level * 100
    own_xp_next = user.owner_level * 100
    badges_result = await session.execute(
        select(UserBadge).where(UserBadge.user_id == user.id).limit(10)
    )
    badges = badges_result.scalars().all()
    badges_list = "\n".join([f"🏅 {b.badge_type}" for b in badges]) if badges else "Пока нет бейджей"
    await callback.message.edit_text(
        f"🏆 *Геймификация*\n\n"
        f"─── Рекламодатель ───\n"
        f"⭐ Уровень: *{user.advertiser_level}*\n"
        f"📊 XP: *{user.advertiser_xp}* / *{adv_xp_next}* (до след. уровня)\n\n"
        f"─── Владелец ───\n"
        f"⭐ Уровень: *{user.owner_level}*\n"
        f"📊 XP: *{user.owner_xp}* / *{own_xp_next}*\n\n"
        f"─── Бейджи ───\n"
        f"{badges_list}\n\n"
        f"─── Как получить XP ───\n"
        f"• Завершённое размещение: +50 XP (оба)\n"
        f"• Отзыв 5★ от рекламодателя: +20 XP (владелец)\n"
        f"• Успешный вывод: +10 XP (владелец)\n"
        f"• Новая кампания: +10 XP (рекламодатель)",
        reply_markup=gamification_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()
