"""
Handlers для команд /start и /help.
"""

import logging
from decimal import Decimal
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, InaccessibleMessage, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.main_menu import (
    MainMenuCB,
    OnboardingCB,
    get_advertiser_menu_kb,
    get_main_menu,
    get_owner_menu_kb,
)
from src.bot.states.onboarding import OnboardingStates
from src.bot.utils.safe_callback import safe_callback_edit
from src.config.settings import settings
from src.core.services.analytics_service import analytics_service
from src.core.services.user_role_service import UserRoleService
from src.services import get_user_service

logger = logging.getLogger(__name__)

# Пути к изображениям
BASE_DIR = Path(__file__).parent.parent
BANNER_PATH = BASE_DIR / "assets" / "images" / "bot" / "banner.jpg"

router = Router()


async def send_banner_with_menu(
    message: Message,
    user_credits: int,
    user_id: int,
    caption: str = None,
    role: str = "new",
    pending_count: int = 0,
    active_campaigns: int = 0,
    channels_count: int = 0,
    available_payout: int = 0,
) -> None:
    """
    Отправить баннер с главным меню.

    Args:
        message: Сообщение для ответа.
        user_credits: Баланс пользователя в кредитах.
        user_id: ID пользователя для проверки админа.
        caption: Текст под баннером (опционально).
        role: Роль пользователя для построения меню.
        pending_count: Количество ожидающих заявок.
        active_campaigns: Количество активных кампаний.
        channels_count: Количество каналов.
        available_payout: Сумма доступная к выводу.
    """
    try:
        if BANNER_PATH.exists():
            banner = FSInputFile(BANNER_PATH)
            caption_text = caption if caption else "Выберите действие:"
            await message.answer_photo(
                photo=banner,
                caption=caption_text,
                reply_markup=get_main_menu(
                    credits=user_credits,
                    user_id=user_id,
                    role=role,
                    pending_count=pending_count,
                    active_campaigns=active_campaigns,
                    channels_count=channels_count,
                    available_payout=available_payout,
                ),
            )
        else:
            logger.warning(f"Banner not found: {BANNER_PATH}")
            await message.answer(
                caption_text or "Выберите действие:",
                reply_markup=get_main_menu(
                    credits=user_credits,
                    user_id=user_id,
                    role=role,
                    pending_count=pending_count,
                    active_campaigns=active_campaigns,
                    channels_count=channels_count,
                    available_payout=available_payout,
                ),
            )
    except Exception as e:
        logger.error(f"Error sending banner: {e}")
        await message.answer(
            caption_text or "Выберите действие:",
            reply_markup=get_main_menu(
                credits=user_credits,
                user_id=user_id,
                role=role,
                pending_count=pending_count,
                active_campaigns=active_campaigns,
                channels_count=channels_count,
                available_payout=available_payout,
            ),
        )


@router.callback_query(MainMenuCB.filter(F.action == "create_campaign_ai"))
async def start_ai_campaign(callback: CallbackQuery, state: FSMContext) -> None:
    """Запуск создания кампании с AI."""
    # Импортируем функцию создания с новым флоу
    from src.bot.handlers.campaign_create_ai import start_campaign_create

    await start_campaign_create(callback, state)


@router.callback_query(MainMenuCB.filter(F.action == "create_menu"))
async def show_create_menu(callback: CallbackQuery) -> None:
    """
    Показать sub-меню выбора способа создания кампании.

    Args:
        callback: Callback query.
    """
    text = (
        "📣 <b>Создание кампании</b>\n\n"
        "Выберите способ:\n\n"
        "✍️ <b>Вручную</b> — пошаговый мастер (5 шагов)\n"
        "🤖 <b>С помощью AI</b> — нейросеть создаст текст за вас\n"
        "📄 <b>Из шаблона</b> — готовый текст для вашей тематики"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Вручную", callback_data=MainMenuCB(action="create_campaign"))
    builder.button(text="🤖 С помощью AI", callback_data=MainMenuCB(action="create_campaign_ai"))
    builder.button(text="📄 Из шаблона", callback_data=MainMenuCB(action="templates"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1, 1, 1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())


@router.message(Command("start"))
async def handle_start(message: Message, state: FSMContext, command: CommandObject) -> None:
    """
    Обработчик команды /start.
    """
    await _handle_start(message, state, command.args if command.args else None)


async def _handle_start(message: Message, state: FSMContext, ref_code: str | None) -> None:
    """
    Общая логика обработки /start.
    """
    # Сначала проверяем, находится ли пользователь в процессе онбординга
    current_state = await state.get_state()

    # Если пользователь в состоянии онбординга, показываем роль-зависимое меню
    # Это предотвращает возврат к онбордингу после выбора роли
    if current_state == OnboardingStates.role_selected.state:
        # Получаем данные пользователя
        async with get_user_service() as svc:
            user = await svc._user_repo.get_by_telegram_id(message.from_user.id)  # type: ignore[union-attr]
            if not user:
                await message.answer("Ошибка. Попробуйте позже.")
                return

            # Получаем контекст — но используем роль из состояния, а не из БД
            user_role_service = UserRoleService()
            user_context = await user_role_service.get_user_context(user.id)

            # Если у пользователя уже есть каналы или кампании, сбрасываем состояние
            if user_context.has_channels or user_context.has_campaigns:
                await state.clear()
                # Продолжаем обычную логику ниже
            else:
                # Пользователь всё ещё в онбординге — показываем меню без онбординга
                plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan
                text = (
                    f"👋 <b>С возвращением, {message.from_user.first_name or user.username or 'друг'}!</b>\n\n"  # type: ignore[union-attr]
                    f"💳 Баланс: <b>{user.credits:,} кр</b>\n"  # type: ignore[union-attr]
                    f"📦 Тариф: <b>{plan_value}</b>\n\n"
                    f"Выберите действие в меню ниже:"
                )
                # Показываем меню рекламодателя (по умолчанию)
                await send_banner_with_menu(
                    message,
                    user.credits,  # type: ignore[union-attr]
                    message.from_user.id,  # type: ignore[union-attr]
                    caption=text,
                    role="advertiser",
                )
                return

    await state.clear()

    async with get_user_service() as svc:
        user, is_new = await svc.get_or_create(  # type: ignore[union-attr]
            telegram_id=message.from_user.id,  # type: ignore[union-attr]
            username=message.from_user.username,  # type: ignore[union-attr]
            first_name=message.from_user.first_name,  # type: ignore[union-attr]
            last_name=message.from_user.last_name,  # type: ignore[union-attr]
            language_code=message.from_user.language_code,  # type: ignore[union-attr]
        )

        if user is None:
            logger.error(f"Failed to create/get user {message.from_user.id}")  # type: ignore[union-attr]
            await message.answer("Ошибка. Попробуйте позже.")
            return

        # user гарантированно не None после проверки выше
        user_id = user.id  # type: ignore[union-attr]
        telegram_id = message.from_user.id  # type: ignore[union-attr]

        # Логирование для отладки регистрации
        logger.info(
            f"User /start: telegram_id={telegram_id}, username={message.from_user.username}, is_new={is_new}, user_id={user_id}"  # type: ignore[union-attr]
        )

        # Обработка реферального кода для новых пользователей
        if ref_code and is_new:
            referrer = await svc._user_repo.get_by_referral_code(ref_code)
            if referrer and referrer.id != user.id:
                # Начисляем реферальный бонус
                from src.core.services.billing_service import billing_service

                bonus_amount = 50.0  # 50₽ бонус за реферала
                await billing_service.apply_referral_bonus(
                    referrer_id=referrer.id,
                    referred_user_id=user.id,
                    bonus_amount=Decimal(str(bonus_amount)),
                )
                logger.info(f"Referral bonus applied: {referrer.id} -> {user.id}")

    # Получаем контекст роли пользователя
    user_role_service = UserRoleService()
    user_context = await user_role_service.get_user_context(user_id)

    # Формируем приветственное сообщение
    plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan  # type: ignore[union-attr]

    # Получаем метрики платформы (асинхронно)
    stats_text = ""
    try:
        platform_stats = await analytics_service.get_platform_stats()
        stats_text = (
            f"\n\n📊 <b>Платформа:</b>\n"
            f"• Активных каналов: <b>{platform_stats.active_channels:,}</b>\n"
            f"• Охват: <b>{platform_stats.total_reach:,}</b>\n"
            f"• Кампаний запущено: <b>{platform_stats.campaigns_launched:,}</b>"
        )
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")

    if is_new and ref_code is None and user_context.role == "new":
        # Новый пользователь без реферала и без активности → показываем онбординг
        text = (
            "🏄 <b>Добро пожаловать в RekHarborBot!</b>\n\n"
            "Рекламная биржа внутри Telegram: рекламодатели\n"
            "размещают объявления в тематических каналах,\n"
            "а владельцы каналов зарабатывают — автоматически,\n"
            "без переписки и предоплат.\n\n"
            "<b>Как это работает:</b>\n"
            "→ Рекламодатель выбирает каналы и оплачивает\n"
            "→ Бот публикует пост без вашего участия\n"
            "→ Владелец получает 80% от стоимости поста\n\n"
            "Кем вы хотите быть на платформе?"
        )
        # Отправляем баннер с текстом и онбординг меню
        await send_banner_with_menu(
            message,
            user.credits,  # type: ignore[union-attr]
            telegram_id,
            caption=text,
            role="new",
        )
    else:
        # Возвращающийся пользователь или с рефералом → показываем роль-зависимое меню
        # Задача 1.5: Персонализированный заголовок
        first_name = message.from_user.first_name or "друг"  # type: ignore[union-attr]

        if user_context.role == "advertiser":
            # Для рекламодателя — показываем баланс и тариф
            text = (
                f"👋 <b>С возвращением, {first_name}!</b>\n\n"
                f"💳 Баланс: <b>{user.credits:,} кр</b>\n"  # type: ignore[union-attr]
                f"📦 Тариф: <b>{plan_value}</b>"
                f"{stats_text}\n\n"
                f"Выберите действие в меню ниже:"
            )
        elif user_context.role == "owner":
            # Для владельца — показываем количество каналов и заявок
            channels_count = user_context.channels_count if hasattr(user_context, 'channels_count') else 0
            pending = user_context.pending_requests_count

            if pending > 0:
                text = (
                    f"👋 <b>С возвращением, {first_name}!</b>\n\n"
                    f"🔔 <b>{pending} новых заявок на размещение!</b>\n\n"
                    f"📺 Ваших каналов: <b>{channels_count}</b>\n"
                    f"{stats_text}\n\n"
                    f"Выберите действие в меню ниже:"
                )
            else:
                text = (
                    f"👋 <b>С возвращением, {first_name}!</b>\n\n"
                    f"📺 Ваших каналов: <b>{channels_count}</b>\n"
                    f"💳 Баланс: <b>{user.credits:,} кр</b>\n"  # type: ignore[union-attr]
                    f"{stats_text}\n\n"
                    f"Выберите действие в меню ниже:"
                )
        else:
            # Для роли "both" или других
            text = (
                f"👋 <b>С возвращением, {first_name}!</b>\n\n"
                f"💳 Баланс: <b>{user.credits:,} кр</b>\n"  # type: ignore[union-attr]
                f"📦 Тариф: <b>{plan_value}</b>"
                f"{stats_text}\n\n"
                f"Выберите действие в меню ниже:"
            )

        # Отправляем баннер с роль-зависимым меню
        await send_banner_with_menu(
            message,
            user.credits,  # type: ignore[union-attr]
            telegram_id,
            caption=text,
            role=user_context.role.value,
            pending_count=user_context.pending_requests_count,
        )


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """
    Обработчик команды /help.

    Показывает список доступных команд.

    Args:
        message: Сообщение от пользователя.
    """
    text = (
        "ℹ️ <b>Доступные команды:</b>\n\n"
        "/start — Главное меню\n"
        "/help — Эта справка\n"
        "/cabinet — Личный кабинет\n"
        "/balance — Проверить баланс\n"
        "/campaigns — Мои кампании\n"
        "/analytics — Аналитика\n"
        "/addchat — Добавить канал для отслеживания\n\n"
        "📚 <b>Как это работает:</b>\n"
        "1. Создайте кампанию через меню\n"
        "2. Настройте таргетинг и бюджет\n"
        "3. Запустите рассылку по чатам\n\n"
        "🆘 <b>Нужна помощь?</b>\n"
        "Напишите в поддержку: @marketbot_support"
    )
    await message.answer(text)


@router.message(Command("cabinet"))
async def handle_cabinet_command(message: Message) -> None:
    """
    Обработчик команды /cabinet.

    Перенаправляет на handler кабинета.

    Args:
        message: Сообщение от пользователя.
    """
    # Импортируем здесь чтобы избежать circular imports
    from src.bot.handlers.cabinet import show_cabinet

    await show_cabinet(message)


@router.message(Command("balance"))
async def handle_balance_command(message: Message) -> None:
    """
    Обработчик команды /balance.

    Показывает текущий баланс.

    Args:
        message: Сообщение от пользователя.
    """
    async with get_user_service() as svc:
        user = await svc._user_repo.get_by_telegram_id(message.from_user.id)  # type: ignore[union-attr]

        if user:
            user_credits = user.credits  # type: ignore[union-attr]
            text = (
                f"💳 <b>Ваш баланс</b>\n\n"
                f"Текущая сумма: <b>{user_credits:,} кр</b>\n\n"
                f"Для пополнения нажмите «Пополнить» в главном меню."
            )
            from src.bot.keyboards.billing import get_amount_kb

            await message.answer(text, reply_markup=get_amount_kb())
        else:
            await message.answer("❌ Пользователь не найден. Нажмите /start")


@router.callback_query(MainMenuCB.filter(F.action == "main_menu"))
async def main_menu_callback(callback: CallbackQuery) -> None:
    """
    Callback handler для кнопки «вернуться в меню».

    Args:
        callback: Callback query.
    """
    async with get_user_service() as svc:
        user = await svc._user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем контекст роли
        user_role_service = UserRoleService()
        user_context = await user_role_service.get_user_context(user.id)

        plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan

        text = (
            f"👋 <b>С возвращением, {callback.from_user.first_name or user.username or 'друг'}!</b>\n\n"
            f"💳 Баланс: <b>{user.credits:,} кр</b>\n"
            f"📦 Тариф: <b>{plan_value}</b>\n\n"
            f"Выберите действие в меню ниже:"
        )

        await safe_callback_edit(
            callback,
            text,
            reply_markup=get_main_menu(
                credits=user.credits,
                user_id=callback.from_user.id,
                role=user_context.role.value,
                pending_count=user_context.pending_requests_count,
                active_campaigns=user_context.has_campaigns,  # Упрощённо: 0 или 1
                channels_count=user_context.has_channels,  # Упрощённо: 0 или 1
                available_payout=0,  # TODO: получить из payout_repo
            ),
        )


@router.callback_query(MainMenuCB.filter(F.action == "admin_panel"))
async def admin_panel_redirect(callback: CallbackQuery) -> None:
    """
    Перенаправить в админ-панель через кнопку главного меню.
    Только для пользователей из ADMIN_IDS.
    """
    from src.config.settings import settings

    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    from src.bot.keyboards.admin import get_admin_main_kb

    await safe_callback_edit(
        callback,
        "🔐 <b>Панель администратора</b>\n\n"
        f"Добро пожаловать, <b>{callback.from_user.first_name}</b>!",
        reply_markup=get_admin_main_kb(),
    )
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "feedback"))
async def feedback_redirect(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Перенаправить в меню обратной связи.
    """
    from src.bot.handlers.feedback import handle_feedback_menu

    await handle_feedback_menu(callback, state)


@router.callback_query(MainMenuCB.filter(F.action == "change_role"))
async def change_role(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Показать меню выбора роли (для пользователей которые хотят сменить роль).
    """
    if callback.message is None:
        return

    # Сбрасываем состояние онбординга если оно было
    await state.clear()

    text = (
        "🔄 <b>Смена роли</b>\n\n"
        "Выберите новую роль:\n\n"
        "📣 <b>Рекламодатель</b> — запуск рекламных кампаний в Telegram-каналах\n"
        "📺 <b>Владелец канала</b> — монетизация своего канала\n\n"
        "Ваш прогресс (каналы, кампании, баланс) сохранится."
    )

    builder = InlineKeyboardBuilder()
    builder.button(
        text="📣 Хочу размещать рекламу",
        callback_data=OnboardingCB(role="advertiser"),
    )
    builder.button(
        text="📺 У меня есть Telegram-канал",
        callback_data=OnboardingCB(role="owner"),
    )
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1, 1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.message(Command("app"))
async def handle_app_command(message: Message) -> None:
    """Открыть Mini App по команде /app."""
    if not settings.mini_app_url:
        await message.answer(
            "📱 Mini App пока не настроен.\nИспользуйте кнопки меню для управления ботом."
        )
        return

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Открыть кабинет",
                    web_app=WebAppInfo(url=settings.mini_app_url),
                )
            ]
        ]
    )

    await message.answer(
        "📱 <b>Market Bot — Личный кабинет</b>\n\n"
        "Управляйте кампаниями, пополняйте баланс "
        "и смотрите аналитику в удобном интерфейсе.",
        reply_markup=keyboard,
    )


# ─────────────────────────────────────────────
# Новые action обработчики для роль-зависимого меню
# ─────────────────────────────────────────────

@router.callback_query(MainMenuCB.filter(F.action == "my_channels"))
async def go_to_my_channels(callback: CallbackQuery) -> None:
    """Перенаправить на /my_channels из главного меню."""
    from src.bot.handlers.channel_owner import cmd_my_channels

    await cmd_my_channels(callback.message)  # type: ignore
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "my_requests"))
async def go_to_my_requests(callback: CallbackQuery) -> None:
    """Показать входящие заявки на размещение для владельцев каналов."""
    if callback.message is None:
        return

    # Получаем количество pending заявок
    async with get_user_service() as svc:
        user = await svc._user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        from src.db.repositories.log_repo import MailingLogRepository
        from src.db.session import async_session_factory

        async with async_session_factory() as session:
            mailing_log_repo = MailingLogRepository(session)
            pending_count = await mailing_log_repo.count_pending_for_owner(user.id)

    text = (
        "📋 <b>Входящие заявки на размещение</b>\n\n"
        f"У вас есть <b>{pending_count} заявок</b>, ожидающих одобрения.\n\n"
        "Для просмотра и одобрения заявок:\n"
        "1. Перейдите в «Мои каналы»\n"
        "2. Выберите канал\n"
        "3. Нажмите «Заявки» в меню канала\n\n"
        "Заявки автоматически одобряются через 24 часа, "
        "если вы не приняли решение вручную."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📺 Мои каналы", callback_data=MainMenuCB(action="my_channels"))
    builder.button(text="➕ Добавить канал", callback_data=MainMenuCB(action="add_channel"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(2, 1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "add_channel"))
async def go_to_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    """Запустить флоу добавления канала."""
    from src.bot.handlers.channel_owner import cmd_add_channel

    await cmd_add_channel(callback.message, state)  # type: ignore
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "payouts"))
async def go_to_payouts(callback: CallbackQuery) -> None:
    """Показать экран выплат владельца."""
    if callback.message is None:
        return

    text = (
        "💸 <b>Выплаты</b>\n\n"
        "Управление выплатами доступно в разделе «Мои каналы».\n\n"
        "Выплаты автоматически создаются после публикации "
        "рекламного поста в вашем канале.\n"
        "80% от стоимости размещения поступает вам, "
        "20% — комиссия платформы."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📺 Мои каналы", callback_data=MainMenuCB(action="my_channels"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1, 1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "b2b"))
async def go_to_b2b(callback: CallbackQuery) -> None:
    """Перейти в B2B-маркетплейс."""
    if callback.message is None:
        return

    text = (
        "💼 <b>B2B-пакеты</b>\n\n"
        "Готовые наборы каналов для комплексного размещения.\n\n"
        "Доступные ниши:\n"
        "• IT и технологии\n"
        "• Бизнес и предпринимательство\n"
        "• Недвижимость\n"
        "• Криптовалюты\n"
        "• Маркетинг\n"
        "• Финансы\n\n"
        "Скидка 10-25% по сравнению с разовыми размещениями."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📡 Каталог каналов", callback_data=MainMenuCB(action="channels_db"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1, 1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "platform_stats"))
async def show_platform_stats(callback: CallbackQuery) -> None:
    """Показать публичную статистику платформы."""
    if callback.message is None:
        return

    try:
        platform_stats = await analytics_service.get_platform_stats()

        text = (
            "📊 <b>RekHarborBot — платформа в цифрах</b>\n\n"
            f"🏪 Каналов на платформе: <b>{platform_stats.active_channels:,}</b>\n"
            f"📣 Кампаний запущено: <b>{platform_stats.campaigns_launched:,}</b>\n"
            f"💸 Выплачено владельцам: <b>{platform_stats.total_payouts:,.0f} кр</b>\n\n"
            f"<i>Данные обновляются в реальном времени.</i>"
        )
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")
        text = "📊 <b>Статистика платформы</b>\n\n" "Временно недоступна. Попробуйте позже."

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "noop"))
async def noop_callback(callback: CallbackQuery) -> None:
    """Заголовочные кнопки-разделители — ничего не делают."""
    await callback.answer()


# ─────────────────────────────────────────────
# Онбординг
# ─────────────────────────────────────────────

@router.callback_query(OnboardingCB.filter())
async def handle_onboarding(callback: CallbackQuery, callback_data: OnboardingCB, state: FSMContext) -> None:
    """
    Обработка выбора роли при первом входе.
    Показывает подходящий следующий шаг и сохраняет состояние.
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        await callback.answer("Сообщение устарело", show_alert=True)
        return

    role = callback_data.role
    user_id = callback.from_user.id

    # Сохраняем состояние — пользователь выбрал роль
    await state.update_data(role=role)
    await state.set_state(OnboardingStates.role_selected)

    if role == "advertiser":
        # Задача 1.3: Сообщение перед показом меню рекламодателя
        await callback.message.answer(
            "📣 <b>Отлично! Вы выбрали роль рекламодателя.</b>\n\n"
            "<b>Быстрый старт — 4 шага:</b>\n\n"
            "1️⃣ Пополните баланс (от 100 кредитов)\n"
            "2️⃣ Выберите каналы в каталоге или нажмите\n"
            '   "Создать кампанию" → автоподбор по бюджету\n'
            "3️⃣ Загрузите текст объявления или попросите AI\n"
            "4️⃣ Оплатите — бот опубликует и пришлёт отчёт\n\n"
            "💡 <b>Деньги замораживаются до факта публикации.</b>\n"
            "   Если пост не вышел — средства вернутся на баланс.\n\n"
            "<b>Главное меню рекламодателя:</b>",
            parse_mode="HTML",
        )

        # Показать меню рекламодателя
        keyboard = get_advertiser_menu_kb(credits=0, user_id=user_id)
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=keyboard,
        )

    elif role == "owner":
        # Задача 1.4: Сообщение перед показом меню владельца
        await callback.message.answer(
            "📺 <b>Отлично! Подключим ваш канал к бирже.</b>\n\n"
            "<b>Что вас ждёт:</b>\n"
            "→ Рекламодатели присылают заявки с текстом поста\n"
            "→ Вы одобряете или отклоняете каждую заявку\n"
            "→ Бот публикует в согласованное время\n"
            "→ 80% от цены поста — ваш заработок\n\n"
            "<b>Требования к каналу:</b>\n"
            "• Публичный (не приватный, есть @username)\n"
            "• Не менее 500 подписчиков\n"
            "• Преимущественно русскоязычная аудитория\n\n"
            "🔒 <b>Бот получает только право публиковать посты.</b>\n"
            "   Управлять каналом он не может.\n\n"
            "<b>Нажмите \"Добавить канал\" чтобы начать:</b>",
            parse_mode="HTML",
        )

        # Показать меню владельца
        keyboard = get_owner_menu_kb(credits=0)
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=keyboard,
        )

    await callback.answer()
