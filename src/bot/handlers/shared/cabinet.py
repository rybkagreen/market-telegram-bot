"""
Handlers личного кабинета пользователя.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from src.bot.keyboards.advertiser.campaign import CampaignCB
from src.bot.keyboards.billing.billing import BillingCB, get_plans_kb
from src.bot.keyboards.shared.cabinet import CabinetCB, get_cabinet_kb
from src.bot.keyboards.shared.main_menu import MainMenuCB
from src.bot.keyboards.shared.pagination import PaginationCB
from src.bot.utils.message_utils import safe_edit_message
from src.core.services.badge_service import badge_service
from src.core.services.user_role_service import UserRoleService
from src.core.services.xp_service import xp_service
from src.db.models.campaign import CampaignStatus
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()

# Задача 5.1: Словарь имён уровней (ОБЩИЙ — для обратной совместимости)
LEVEL_NAMES = {
    1: "Новичок 🌱",
    2: "Участник ⭐",
    3: "Активный 🔥",
    4: "Опытный 💎",
    5: "Профи 🚀",
    6: "Эксперт 🎯",
    7: "Мастер 👑",
}

# Задача 5.1: Привилегии следующего уровня (ОБЩИЕ)
LEVEL_NEXT_PRIVILEGE = {
    1: "расширенные фильтры в каталоге каналов",
    2: "скидка 3% на все размещения",
    3: "скидка 7% + персональный менеджер",
    4: "скидка 10% + ранний доступ к B2B",
    5: "скидка 15% + белый лейбл отчётов",
    6: "API-доступ",
    7: None,
}

# Спринт 5: Раздельные привилегии для рекламодателей
ADVERTISER_LEVEL_NAMES = {
    1: "Новичок 🌱",
    2: "Активный ⭐",
    3: "Профи 🔥",
    4: "Эксперт 💎",
    5: "Мастер 🚀",
    6: "Легенда 🎯",
    7: "Бог рекламы 👑",
}

ADVERTISER_NEXT_PRIVILEGE = {
    1: "расширенные фильтры в каталоге",
    2: "скидка 3% на размещения",
    3: "скидка 7% + приоритетная поддержка",
    4: "скидка 10% + белый лейбл отчётов",
    5: "скидка 15% + персональный менеджер",
    6: "API-доступ для автоматизации",
    7: None,
}

# Спринт 5: Раздельные привилегии для владельцев
OWNER_LEVEL_NAMES = {
    1: "Новичок 🌱",
    2: "Популярный ⭐",
    3: "Избранный 🔥",
    4: "Топовый 💎",
    5: "Легенда 🚀",
    6: "Влиятельный 🎯",
    7: "Медиамагнат 👑",
}

OWNER_NEXT_PRIVILEGE = {
    1: "аналитика канала",
    2: "бейдж 'Проверенный канал'",
    3: "приоритет в каталоге",
    4: "повышенная выплата (85%)",
    5: "персональный менеджер",
    6: "премиум размещение в топ-10",
    7: None,
}

# Задача 5.1: Порог XP для каждого уровня
LEVEL_XP = {1: 0, 2: 500, 3: 1500, 4: 3500, 5: 7500, 6: 15000, 7: 30000}

# Эмодзи статусов кампании
STATUS_EMOJI = {
    CampaignStatus.DRAFT: "📝",
    CampaignStatus.QUEUED: "⏳",
    CampaignStatus.RUNNING: "🔄",
    CampaignStatus.DONE: "✅",
    CampaignStatus.ERROR: "❌",
    CampaignStatus.PAUSED: "⏸️",
    CampaignStatus.CANCELLED: "🚫",
}


# Задача 5.2: Функция для генерации прогресс-бара XP
def build_xp_progress_bar(current_xp: int, level: int) -> str:
    """
    Построить прогресс-бар XP.

    Args:
        current_xp: Текущее количество XP.
        level: Текущий уровень.

    Returns:
        Строка прогресс-бара.
    """
    if level >= 7:
        return "MAX ████████████ 100%"

    current_level_xp = LEVEL_XP[level]
    next_level_xp = LEVEL_XP.get(level + 1, 30000)
    progress_xp = current_xp - current_level_xp
    total_needed = next_level_xp - current_level_xp

    percent = min(100, int(progress_xp / total_needed * 100)) if total_needed > 0 else 0
    filled = percent // 10
    empty = 10 - filled

    bar = "█" * filled + "░" * empty
    remaining = next_level_xp - current_xp

    return f"{current_xp} XP  {bar}  {percent}%  →  до ур.{level + 1}: {remaining} XP"


async def show_cabinet(message: Message | CallbackQuery) -> None:
    """
    Показать личный кабинет пользователя.
    Задача 5.3: Разные версии для рекламодателя и владельца.

    Args:
        message: Сообщение или callback query.
    """
    # Получаем telegram_id
    if isinstance(message, CallbackQuery):
        telegram_id = message.from_user.id  # type: ignore[union-attr]
        answer_method = message.message.answer if message.message else message.answer
    else:
        telegram_id = message.from_user.id  # type: ignore[union-attr]
        answer_method = message.answer

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_id)

        if not user:
            await answer_method("❌ Пользователь не найден. Нажмите /start")
            return

        # Задача 5.3: Определяем роль пользователя
        user_role_service = UserRoleService()
        user_context = await user_role_service.get_user_context(user.id)
        role = user_context.role

        # Спринт 5: Получаем раздельные данные геймификации
        if role == "advertiser":
            level = user.advertiser_level
            xp_points = user.advertiser_xp
            level_names = ADVERTISER_LEVEL_NAMES
            level_privileges = ADVERTISER_NEXT_PRIVILEGE
        elif role == "owner":
            level = user.owner_level
            xp_points = user.owner_xp
            level_names = OWNER_LEVEL_NAMES
            level_privileges = OWNER_NEXT_PRIVILEGE
        else:
            # Для new/both используем общие значения
            xp_stats = await xp_service.get_user_stats(telegram_id)
            level = xp_stats.get("level", 1)
            xp_points = xp_stats.get("xp_points", 0)
            level_names = LEVEL_NAMES
            level_privileges = LEVEL_NEXT_PRIVILEGE

        # Задача 5.1: Имя уровня из словаря
        level_name = level_names.get(level, f"Уровень {level}")

        # Задача 5.2: Прогресс-бар XP
        xp_bar = build_xp_progress_bar(xp_points, level)

        # Задача 5.3: Привилегия следующего уровня
        next_privilege = level_privileges.get(level)
        next_level_name = level_names.get(level + 1, "")

        # Получаем доступную сумму к выводу (для владельца)
        available_payout = Decimal("0")
        if role in ("owner", "both"):
            from src.db.repositories.payout_repo import get_available_payout_amount

            available_payout = await get_available_payout_amount(user.id)

        # Задача 5.3: Формируем текст в зависимости от роли
        if role in ("advertiser", "both"):
            # Для рекламодателя
            # Дата истечения тарифа — получаем из user.plan_expires_at
            plan_expires_at = getattr(user, "plan_expires_at", None)
            days_left = None
            if plan_expires_at:
                days_left = (plan_expires_at - datetime.now(UTC)).days

            # Осталось кампаний — получаем из БД
            from src.db.repositories.campaign_repo import CampaignRepository

            campaign_repo = CampaignRepository(session)
            total_campaigns = await campaign_repo.get_user_campaigns_count(user.id)
            remaining_campaigns = total_campaigns  # Заглушка — в будущем нужно считать лимит
            plan_limit = 5  # Заглушка для STARTER

            plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan

            text = (
                f"👤 <b>Кабинет  •  {user.first_name or user.username}</b>\n\n"
                f"━━━━ БАЛАНСЫ ━━━━\n"
                f"💵 Рублёвый баланс: <b>{user.balance_rub:,} ₽</b>\n"
                f"🎯 Кредиты (подписки): <b>{user.credits:,} ₽</b>\n"
            )

            # Для роли "both" показываем также заработок владельца
            if role == "both":
                text += f"💸 Заработано к выводу: <b>{user.earned_rub:,} ₽</b>\n"
                text += "📋 Не забудьте задекларировать доход самостоятельно\n"

            text += f"📦 Тариф: {plan_value}"

            if days_left is not None and days_left > 0 and plan_expires_at is not None:
                text += f"  •  до {plan_expires_at.strftime('%d.%m')} ({days_left} дней)\n"
                text += f"   Осталось кампаний: {remaining_campaigns} из {plan_limit}\n"
            else:
                text += "\n"

            text += f"\n━━━━ УРОВЕНЬ ━━━━\n{level_name}  Уровень {level}\n   {xp_bar}\n"

            if next_privilege and level < 7:
                text += f"\nНа уровне {level + 1} — {next_level_name}:\n→ {next_privilege}\n"

            # TASK 8.7: Стрики активности
            streak_days = user.login_streak_days or 0
            max_streak = user.max_streak_days or 0

            text += "\n━━━━ 🔥 СТРИКИ ━━━━\n"
            text += f"Текущая серия: <b>{streak_days} дн.</b>\n"
            text += f"Максимальная: <b>{max_streak} дн.</b>\n"

            # Прогресс до следующего бонуса (каждые 7 дней)
            if streak_days > 0:
                streak_progress = streak_days % 7
                next_bonus_in = 7 - streak_progress if streak_progress > 0 else 7
                streak_bar = "█" * streak_progress + "░" * (7 - streak_progress)
                text += f"   {streak_bar}  до бонуса: {next_bonus_in} дн.\n"

        elif role == "owner":
            # Для владельца — показываем earned_rub
            text = (
                f"👤 <b>Кабинет  •  {user.first_name or user.username}</b>\n\n"
                f"━━━━ БАЛАНСЫ ━━━━\n"
                f"💵 Рублёвый баланс: <b>{user.balance_rub:,} ₽</b>\n"
                f"🎯 Кредиты (подписки): <b>{user.credits:,} ₽</b>\n"
                f"💸 Заработано к выводу: <b>{user.earned_rub:,} ₽</b>\n"
                f"📋 Вы самостоятельно несёте ответственность за уплату налогов\n"
                f"\n━━━━ ПРОГРЕСС ВЛАДЕЛЬЦА ━━━━\n"
                f"{level_name}  Уровень {level}\n"
                f"   {xp_bar}\n"
            )

            if next_privilege and level < 7:
                text += f"\nНа уровне {level + 1} — {next_level_name}:\n→ {next_privilege}\n"

        else:
            # Для new или других
            plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan
            text = (
                f"👤 <b>Кабинет  •  {user.first_name or user.username}</b>\n\n"
                f"━━━━ БАЛАНСЫ ━━━━\n"
                f"💵 Рублёвый баланс: <b>{user.balance_rub:,} ₽</b>\n"
                f"🎯 Кредиты (подписки): <b>{user.credits:,} ₽</b>\n"
                f"📦 Тариф: <b>{plan_value}</b>\n\n"
                f"━━━━ УРОВЕНЬ ━━━━\n"
                f"{level_name}  Уровень {level}\n"
                f"   {xp_bar}\n"
            )

        # Добавляем профиль
        text += (
            f"\n👤 <b>Профиль:</b>\n"
            f"Имя: {user.full_name}\n"
            f"Telegram: @{user.username or 'не указан'}\n"
        )

        # Задача 5.4: Расширенная клавиатура в зависимости от роли
        await answer_method(
            text,
            reply_markup=get_cabinet_kb(
                notifications_enabled=user.notifications_enabled,
                role=role.value if hasattr(role, "value") else role,
                available_payout=int(available_payout),
            ),
        )


@router.callback_query(MainMenuCB.filter(F.action == "cabinet"))
async def cabinet_callback(callback: CallbackQuery) -> None:
    """
    Callback handler для открытия кабинета.

    Args:
        callback: Callback query.
    """
    await show_cabinet(callback)


@router.callback_query(CabinetCB.filter(F.action == "toggle_notifications"))
async def toggle_notifications_handler(callback: CallbackQuery) -> None:
    """
    Переключить уведомления пользователя.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        new_state = await user_repo.toggle_notifications(callback.from_user.id)

    status_text = "включены 🔔" if new_state else "выключены 🔕"
    await callback.answer(f"Уведомления {status_text}", show_alert=False)

    # Обновить кнопку без перерисовки всего сообщения
    await callback.message.edit_reply_markup(  # type: ignore[union-attr]
        reply_markup=get_cabinet_kb(notifications_enabled=new_state)
    )


@router.callback_query(BillingCB.filter(F.action == "referral"))
async def referral_callback(callback: CallbackQuery) -> None:
    """
    Показать реферальную информацию.

    Args:
        callback: Callback query.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем количество рефералов
        referrer_count = await user_repo.get_referrers_count(user.id)

        # Получаем список рефералов для отображения
        referrers = await user_repo.get_referrers(user.id, limit=5)
        referrers_text = ""
        if referrers:
            referrers_text = "\n\n" + "\n".join(
                [f"• {r.full_name or r.username or 'User'}" for r in referrers]
            )
            if referrer_count > 5:
                referrers_text += f"\n... и ещё {referrer_count - 5}"

        # Реферальная ссылка
        bot = callback.bot
        if bot is None:
            logger.error("Bot instance is None in cabinet handler")
            await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)
            return
        bot_info = await bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user.referral_code}"

        text = (
            f"👥 <b>Реферальная программа</b>\n\n"
            f"Ваша ссылка:\n"
            f"<code>{ref_link}</code>\n\n"
            f"🎁 Бонус за каждого друга: <b>50₽</b>\n"
            f"👥 Приглашено пользователей: <b>{referrer_count}</b>"
            f"{referrers_text}\n\n"
            f"💡 <b>Как это работает:</b>\n"
            f"1. Отправьте ссылку другу\n"
            f"2. Друг нажимает /start и регистрируется\n"
            f"3. Вы получаете 50₽ на баланс\n\n"
            f"🏆 <b>Ваш реферальный код:</b>\n"
            f"<code>{user.referral_code}</code>"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="🔗 Копировать ссылку", url=ref_link)
        builder.button(text="🔙 Назад", callback_data=MainMenuCB(action="cabinet"))
        builder.adjust(1)

        await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


@router.callback_query(BillingCB.filter(F.action == "plans"))
async def plans_callback(callback: CallbackQuery) -> None:
    """
    Показать тарифные планы.

    Args:
        callback: Callback query.
    """
    text = (
        "📦 <b>Тарифные планы</b>\n\n"
        "🆓 <b>FREE</b> — 0₽/мес\n"
        "  • 0 кампаний в месяц\n"
        "  • 0 чатов на кампанию\n\n"
        "🚀 <b>STARTER</b> — 299₽/мес\n"
        "  • 5 кампаний в месяц\n"
        "  • 50 чатов на кампанию\n\n"
        "💎 <b>PRO</b> — 999₽/мес\n"
        "  • 20 кампаний в месяц\n"
        "  • 200 чатов на кампанию\n\n"
        "🏢 <b>BUSINESS</b> — 2999₽/мес\n"
        "  • 100 кампаний в месяц\n"
        "  • 1000 чатов на кампанию\n\n"
        "Выберите тариф для перехода:"
    )

    await safe_edit_message(callback.message, text, reply_markup=get_plans_kb())


@router.callback_query(MainMenuCB.filter(F.action == "my_campaigns"))
async def my_campaigns_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Показать список кампаний пользователя.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await show_campaigns_list(callback, page=1)


async def show_campaigns_list(callback: CallbackQuery, page: int = 1) -> None:
    """
    Показать список кампаний с пагинацией.

    Args:
        callback: Callback query.
        page: Номер страницы.
    """
    page_size = 5

    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        campaigns, total = await campaign_repo.get_by_user(
            user_id=callback.from_user.id,
            page=page,
            page_size=page_size,
        )

        logger.info(
            f"show_campaigns_list: telegram_id={callback.from_user.id}, total={total}, campaigns={len(campaigns)}"
        )

        total_pages = max(1, (total + page_size - 1) // page_size)

        if not campaigns:
            logger.warning(
                f"show_campaigns_list: no campaigns found for user {callback.from_user.id}"
            )
            text = (
                "📋 <b>У вас пока нет кампаний</b>\n\nСоздайте первую кампанию через главное меню!"
            )
            builder = InlineKeyboardBuilder()
            builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
            builder.adjust(1)
            # Используем edit_message_caption для совместимости с фото
            try:
                await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
            except Exception:
                await callback.message.edit_message_caption(  # type: ignore[union-attr]
                    caption=text, reply_markup=builder.as_markup()
                )
            return

        # Формируем список кампаний
        text = f"📋 <b>Ваши кампании</b> ({total} всего)\n\n"

        for campaign in campaigns:
            # campaign.status может быть строкой или enum
            status_value = (
                campaign.status if isinstance(campaign.status, str) else campaign.status.value
            )
            emoji = STATUS_EMOJI.get(status_value, "📝")
            progress = campaign.progress

            # Форматируем дату
            created = campaign.created_at.strftime("%d.%m.%Y") if campaign.created_at else "—"

            text += (
                f"{emoji} <b>{campaign.title}</b>\n"
                f"   Статус: {status_value}  |  Прогресс: {progress:.0f}%\n"
                f"   Создана: {created}\n"
                f"   Отправлено: {campaign.sent_count}/{campaign.total_chats}\n\n"
            )

        # Кнопки навигации + кнопка детальной страницы
        builder = InlineKeyboardBuilder()

        # Добавляем кнопки для каждой кампании
        for campaign in campaigns:
            campaign_id = campaign.id
            title = campaign.title[:30] + "..." if len(campaign.title) > 30 else campaign.title
            builder.button(
                text=f"{STATUS_EMOJI.get(campaign.status if isinstance(campaign.status, str) else campaign.status.value, '📝')} {title}",
                callback_data=CampaignCB(action="show_detail", value=str(campaign_id)),
            )

        builder.adjust(1)  # Одна кнопка под другой

        if page > 1:
            builder.button(
                text="◀ Пред", callback_data=PaginationCB(prefix="campaigns", page=page - 1)
            )

        builder.button(
            text=f"{page}/{total_pages}", callback_data=PaginationCB(prefix="campaigns", page=page)
        )

        if page < total_pages:
            builder.button(
                text="След ▶", callback_data=PaginationCB(prefix="campaigns", page=page + 1)
            )

        builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
        builder.adjust(2, 1, 1)

        await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


# ─────────────────────────────────────────────
# Геймификация — значки (Спринт 4)
# ─────────────────────────────────────────────


@router.callback_query(CabinetCB.filter(F.action == "badges"))
async def show_badges(callback: CallbackQuery) -> None:
    """
    Показать значки пользователя.
    """
    if callback.message is None:
        return

    user_badges = await badge_service.get_user_badges(callback.from_user.id)

    if not user_badges:
        text = (
            "🏅 <b>Ваши значки</b>\n\n"
            "У вас пока нет значков.\n\n"
            "Получайте значки за:\n"
            "• Запуск кампаний\n"
            "• Активность в боте\n"
            "• Достижение уровней\n"
            "• Ежедневный вход"
        )
    else:
        text = "🏅 <b>Ваши значки</b>\n\n"
        for badge in user_badges[:10]:  # Показываем до 10 последних
            text += f"{badge['icon_emoji']} <b>{badge['name']}</b>\n"
            text += f"   {badge['description'][:50]}...\n"
            text += f"   +{badge['xp_reward']} XP | {badge['earned_at'][:10]}\n\n"

        if len(user_badges) > 10:
            text += f"... и ещё {len(user_badges) - 10} значков\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 В кабинет", callback_data=CabinetCB(action="main"))
    builder.adjust(1)

    await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


@router.callback_query(PaginationCB.filter(F.prefix == "campaigns"))
async def campaigns_pagination_callback(
    callback: CallbackQuery, callback_data: PaginationCB
) -> None:
    """
    Callback handler для пагинации кампаний.

    Args:
        callback: Callback query.
        callback_data: Данные пагинации.
    """
    await show_campaigns_list(callback, page=callback_data.page)


# ─────────────────────────────────────────────
# TASK 4: Детальная страница кампании + управление
# ─────────────────────────────────────────────


@router.callback_query(CampaignCB.filter(F.action == "show_detail"))
async def show_campaign_detail(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """
    Показать детальную страницу кампании.
    """
    if callback.message is None:
        return

    campaign_id = int(callback_data.value)

    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return

        # Проверяем что кампания принадлежит пользователю
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user or campaign.user_id != user.id:
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return

        # Статус кампании
        status_value = (
            campaign.status.value if hasattr(campaign.status, "value") else campaign.status
        )
        emoji = STATUS_EMOJI.get(status_value, "📝")  # type: ignore[arg-type]  # status.value or status str

        # Прогресс
        progress = campaign.progress
        sent = campaign.sent_count
        total = campaign.total_chats

        # Стоимость
        cost = campaign.cost or 0

        # Тематика
        topic = campaign.topic or "Не указана"

        # Текст (первые 200 символов)
        text_preview = campaign.text[:200] + "..." if len(campaign.text) > 200 else campaign.text

        # Дата создания
        created = campaign.created_at.strftime("%d.%m.%Y %H:%M") if campaign.created_at else "—"

        text = (
            f"{emoji} <b>Кампания: {campaign.title}</b>\n\n"
            f"📊 <b>Статус:</b> {status_value}\n"
            f"📈 <b>Прогресс:</b> {progress:.0f}% ({sent}/{total} чатов)\n"
            f"💰 <b>Стоимость:</b> {cost:.0f} ₽\n"
            f"🏷 <b>Тематика:</b> {topic}\n"
            f"📅 <b>Создана:</b> {created}\n\n"
            f"📝 <b>Текст:</b>\n"
            f"<tg-spoiler>{text_preview}</tg-spoiler>\n\n"
        )

        # Клавиатура по статусу
        from src.bot.keyboards.advertiser.campaign import get_campaign_detail_kb

        keyboard = get_campaign_detail_kb(campaign_id, status_value)

        await safe_edit_message(callback.message, text, reply_markup=keyboard)


@router.callback_query(CampaignCB.filter(F.action == "launch"))
async def launch_campaign(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """
    Запустить кампанию из черновика.
    """
    if callback.message is None:
        return

    campaign_id = int(callback_data.value)

    async with async_session_factory() as session:
        from src.core.services.billing_service import billing_service
        from src.db.models.campaign import CampaignStatus
        from src.tasks.mailing_tasks import send_campaign

        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return

        # Проверяем владельца
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user or campaign.user_id != user.id:
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return

        # ✅ ЗАЩИТА ОТ DOUBLE-CLICK — проверяем статус
        if campaign.status == CampaignStatus.RUNNING:
            await callback.answer("⚠️ Кампания уже запущена", show_alert=True)
            return

        if campaign.status == CampaignStatus.DONE:
            await callback.answer("⚠️ Кампания уже завершена", show_alert=True)
            return

        if campaign.status == CampaignStatus.CANCELLED:
            await callback.answer("⚠️ Кампания отменена", show_alert=True)
            return

        # Замораживаем средства
        if campaign.cost > 0:
            frozen = await billing_service.freeze_campaign_funds(campaign_id)
            if not frozen:
                await callback.answer("❌ Недостаточно средств для запуска", show_alert=True)
                return

        # Обновляем статус
        await campaign_repo.update_status(campaign_id, CampaignStatus.RUNNING)

        # ⚠️ ФИКС 7: Запускаем рассылку и сохраняем task_id
        task = send_campaign.delay(campaign_id)

        meta = campaign.meta_json or {}
        meta["celery_task_id"] = task.id
        campaign.meta_json = meta
        await session.commit()

    await callback.answer("✅ Кампания запущена!")
    await show_campaign_detail(callback, callback_data)


@router.callback_query(CampaignCB.filter(F.action == "pause"))
async def pause_campaign(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """
    Поставить кампанию на паузу.
    """
    if callback.message is None:
        return

    campaign_id = int(callback_data.value)

    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return

        # Проверяем владельца
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user or campaign.user_id != user.id:
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return

        # ⚠️ ФИКС 7: Отозвать Celery задачу при паузе
        meta = campaign.meta_json or {}
        task_id = meta.get("celery_task_id")

        if task_id:
            try:
                from celery.result import AsyncResult

                task_result = AsyncResult(task_id)
                task_result.revoke(terminate=True)
                logger.info(f"Revoked Celery task {task_id} for campaign {campaign_id}")
                # Очищаем task_id чтобы не пытаться отозвать повторно
                meta["celery_task_id"] = None
                campaign.meta_json = meta
            except Exception as e:
                logger.warning(f"Failed to revoke task {task_id} for campaign {campaign_id}: {e}")

        # Обновляем статус
        await campaign_repo.update_status(campaign_id, CampaignStatus.PAUSED)
        await session.commit()

    await callback.answer("⏸ Кампания на паузе")
    await show_campaign_detail(callback, callback_data)


@router.callback_query(CampaignCB.filter(F.action == "resume"))
async def resume_campaign(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """
    Возобновить кампанию с паузы.
    """
    if callback.message is None:
        return

    campaign_id = int(callback_data.value)

    async with async_session_factory() as session:
        from src.tasks.mailing_tasks import send_campaign

        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return

        # Проверяем владельца
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user or campaign.user_id != user.id:
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return

        # ⚠️ ФИКС 7: Запустить новую задачу и сохранить task_id
        task = send_campaign.delay(campaign_id)

        meta = campaign.meta_json or {}
        meta["celery_task_id"] = task.id
        campaign.meta_json = meta

        # Обновляем статус
        await campaign_repo.update_status(campaign_id, CampaignStatus.RUNNING)
        await session.commit()

    await callback.answer("▶️ Кампания возобновлена")
    await show_campaign_detail(callback, callback_data)


@router.callback_query(CampaignCB.filter(F.action == "cancel_campaign"))
async def cancel_campaign_action(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """
    Отменить кампанию (queued/running/paused).
    Возврат средств только за незавершённые placements.
    """
    if callback.message is None:
        return

    campaign_id = int(callback_data.value)

    async with async_session_factory() as session:
        from src.core.services.billing_service import billing_service
        from src.db.models.mailing_log import MailingLog, MailingStatus

        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return

        # Проверяем владельца
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user or campaign.user_id != user.id:
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return

        # Проверка статуса — можно отменять только queued/running/paused
        status_value = (
            campaign.status.value if hasattr(campaign.status, "value") else campaign.status
        )
        if status_value not in ("queued", "running", "paused"):
            await callback.answer("❌ Кампанию нельзя отменить в текущем статусе", show_alert=True)
            return

        # ⚠️ ИСПРАВЛЕНИЕ: возврат только за незавершённые placements
        stmt = select(MailingLog).where(
            MailingLog.campaign_id == campaign_id,
            MailingLog.status.in_(
                [
                    MailingStatus.PENDING_APPROVAL,
                    MailingStatus.QUEUED,
                    MailingStatus.PENDING,
                ]
            ),
        )
        result = await session.execute(stmt)
        pending_placements = list(result.scalars().all())

        # Отмена каждого незавершённого placement с возвратом
        refunded_total = 0
        for placement in pending_placements:
            # Помечаем как failed для триггера возврата
            placement.status = MailingStatus.FAILED
            await session.flush()

            # Вызываем возврат средств
            success = await billing_service.refund_failed_placement(placement.id)
            if success:
                refunded_total += placement.cost or 0

        # Обновляем статус кампании
        await campaign_repo.update_status(campaign_id, CampaignStatus.CANCELLED)
        await session.commit()

    await callback.answer(f"❌ Кампания отменена. Возвращено: {refunded_total} ₽")
    await show_campaign_detail(callback, callback_data)


@router.callback_query(CampaignCB.filter(F.action == "delete"))
async def delete_campaign(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """
    Удалить кампанию (только черновики).
    """
    if callback.message is None:
        return

    campaign_id = int(callback_data.value)

    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        campaign = await campaign_repo.get_by_id(campaign_id)

        if not campaign:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return

        # Проверяем владельца и статус
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user or campaign.user_id != user.id:
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return

        status_value = (
            campaign.status.value if hasattr(campaign.status, "value") else campaign.status
        )
        if status_value != "draft":
            await callback.answer("❌ Можно удалять только черновики", show_alert=True)
            return

        # Удаляем
        await campaign_repo.delete(campaign_id)

    await callback.answer("🗑 Кампания удалена")
    await show_campaigns_list(callback, page=1)


@router.callback_query(CampaignCB.filter(F.action == "duplicate"))
async def duplicate_campaign(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """
    Дублировать кампанию (создать черновик с теми же данными).
    """
    if callback.message is None:
        return

    campaign_id = int(callback_data.value)

    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        original = await campaign_repo.get_by_id(campaign_id)

        if not original:
            await callback.answer("❌ Кампания не найдена", show_alert=True)
            return

        # Проверяем владельца
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user or original.user_id != user.id:
            await callback.answer("❌ Доступ запрещён", show_alert=True)
            return

        # Создаём копию
        new_campaign = await campaign_repo.create(
            {
                "user_id": user.id,
                "title": f"{original.title} (копия)",
                "topic": original.topic,
                "header": original.header,
                "text": original.text,
                "image_file_id": original.image_file_id,
                "ai_description": original.ai_description,
                "status": CampaignStatus.DRAFT,
                "filters_json": original.filters_json,
                "scheduled_at": None,
                "cost": 0,
            }
        )

    await callback.answer("📋 Кампания продублирована")
    await show_campaign_detail(
        callback, CampaignCB(action="show_detail", value=str(new_campaign.id))
    )
