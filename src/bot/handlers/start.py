"""
Handlers для команд /start и /help.
"""

import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.keyboards.main_menu import get_main_menu
from src.db.repositories.user import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /start.

    Создает или обновляет пользователя, обрабатывает реферальный код,
    показывает главное меню.

    Args:
        message: Сообщение от пользователя.
        state: FSM контекст.
    """
    await state.clear()

    # Парсим аргументы команды (реферальный код)
    args = message.text.split(maxsplit=1) if message.text else []
    ref_code = args[1] if len(args) > 1 and args[1].startswith("ref_") else None

    async with async_session_factory() as session:
        user_repo = UserRepository(session)

        # Создаем или обновляем пользователя
        user = await user_repo.create_or_update(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code,
        )

        # Обработка реферального кода для новых пользователей
        if ref_code and user.created_at == user.updated_at:  # Только что создан
            referrer = await user_repo.get_by_referral_code(ref_code)
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
    if user.created_at == user.updated_at and ref_code is None:
        # Новый пользователь без реферала
        text = (
            f"🚀 <b>Добро пожаловать в Market Bot!</b>\n\n"
            f"Привет, <b>{message.from_user.first_name or 'друг'}</b>!\n"
            f"Здесь вы можете запускать рекламные кампании в Telegram-чатах.\n\n"
            f"💳 Ваш баланс: <b>{user.balance}₽</b>\n\n"
            f"Нажмите «Создать кампанию», чтобы начать!"
        )
    else:
        # Возвращающийся пользователь
        text = (
            f"👋 <b>С возвращением, {message.from_user.first_name or user.username or 'друг'}!</b>\n\n"
            f"💳 Баланс: <b>{user.balance}₽</b>\n"
            f"📦 Тариф: <b>{user.plan.value}</b>\n\n"
            f"Выберите действие в меню ниже:"
        )

    await message.answer(text, reply_markup=get_main_menu(user.balance))


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
        "/campaigns — Мои кампании\n\n"
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
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(message.from_user.id)

        if user:
            text = (
                f"💳 <b>Ваш баланс</b>\n\n"
                f"Текущая сумма: <b>{user.balance}₽</b>\n\n"
                f"Для пополнения нажмите «Пополнить» в главном меню."
            )
            from src.bot.keyboards.billing import get_amount_kb
            await message.answer(text, reply_markup=get_amount_kb())
        else:
            await message.answer("❌ Пользователь не найден. Нажмите /start")
