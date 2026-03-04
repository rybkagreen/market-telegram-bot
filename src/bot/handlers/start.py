"""
Handlers для команд /start и /help.
"""

import logging

from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.main_menu import MainMenuCB, get_main_menu
from src.config.settings import settings
from src.services import get_user_service

logger = logging.getLogger(__name__)

# Пути к изображениям
BASE_DIR = Path(__file__).parent.parent
BANNER_PATH = BASE_DIR / "assets" / "images" / "bot" / "banner.jpg"

router = Router()


async def send_banner_with_menu(message: Message, user_credits: int, user_id: int, caption: str = None) -> None:
    """
    Отправить баннер с главным меню.

    Args:
        message: Сообщение для ответа.
        user_credits: Баланс пользователя в кредитах.
        user_id: ID пользователя для проверки админа.
        caption: Текст под баннером (опционально).
    """
    try:
        if BANNER_PATH.exists():
            banner = FSInputFile(BANNER_PATH)
            caption_text = caption if caption else "Выберите действие:"
            await message.answer_photo(
                photo=banner,
                caption=caption_text,
                reply_markup=get_main_menu(user_credits, user_id)
            )
        else:
            logger.warning(f"Banner not found: {BANNER_PATH}")
            await message.answer(caption_text or "Выберите действие:", reply_markup=get_main_menu(user_credits, user_id))
    except Exception as e:
        logger.error(f"Error sending banner: {e}")
        await message.answer(caption_text or "Выберите действие:", reply_markup=get_main_menu(user_credits, user_id))


@router.callback_query(MainMenuCB.filter(F.action == "create_campaign_ai"))
async def start_ai_campaign(callback: CallbackQuery, state: FSMContext) -> None:
    """Запуск создания кампании с AI."""
    # Импортируем функцию создания
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

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


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
    await state.clear()

    async with get_user_service() as svc:
        user, is_new = await svc.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code,
        )

        # Логирование для отладки регистрации
        logger.info(f"User /start: telegram_id={message.from_user.id}, username={message.from_user.username}, is_new={is_new}")

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
                    bonus_amount=bonus_amount,
                )
                logger.info(f"Referral bonus applied: {referrer.id} -> {user.id}")

    # Формируем приветственное сообщение
    plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan

    if is_new and ref_code is None:
        # Новый пользователь без реферала
        text = (
            f"🚀 <b>Добро пожаловать в Market Bot!</b>\n\n"
            f"Привет, <b>{message.from_user.first_name or 'друг'}</b>!\n"
            f"Здесь вы можете запускать рекламные кампании в Telegram-чатах.\n\n"
            f"💳 Ваш баланс: <b>{user.credits:,} кр</b>\n\n"
            f"Нажмите «Создать кампанию», чтобы начать!"
        )
        # Отправляем баннер с текстом приветствия
        await send_banner_with_menu(message, user.credits, user.id, caption=text)
    else:
        # Возвращающийся пользователь или с рефералом
        text = (
            f"👋 <b>С возвращением, {message.from_user.first_name or user.username or 'друг'}!</b>\n\n"
            f"💳 Баланс: <b>{user.credits:,} кр</b>\n"
            f"📦 Тариф: <b>{plan_value}</b>\n\n"
            f"Выберите действие в меню ниже:"
        )
        # Отправляем баннер с текстом
        await send_banner_with_menu(message, user.credits, user.id, caption=text)


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
        user = await svc._user_repo.get_by_telegram_id(message.from_user.id)

        if user:
            text = (
                f"💳 <b>Ваш баланс</b>\n\n"
                f"Текущая сумма: <b>{user.credits:,} кр</b>\n\n"
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

        plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan

        text = (
            f"👋 <b>С возвращением, {callback.from_user.first_name or user.username or 'друг'}!</b>\n\n"
            f"💳 Баланс: <b>{user.credits:,} кр</b>\n"
            f"📦 Тариф: <b>{plan_value}</b>\n\n"
            f"Выберите действие в меню ниже:"
        )

        await callback.message.edit_text(text, reply_markup=get_main_menu(user.credits, user.id))


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

    await callback.message.edit_text(
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


@router.message(Command("app"))
async def handle_app_command(message: Message) -> None:
    """Открыть Mini App по команде /app."""
    if not settings.mini_app_url:
        await message.answer(
            "📱 Mini App пока не настроен.\n"
            "Используйте кнопки меню для управления ботом."
        )
        return

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="📱 Открыть кабинет",
            web_app=WebAppInfo(url=settings.mini_app_url),
        )
    ]])

    await message.answer(
        "📱 <b>Market Bot — Личный кабинет</b>\n\n"
        "Управляйте кампаниями, пополняйте баланс "
        "и смотрите аналитику в удобном интерфейсе.",
        reply_markup=keyboard,
    )
