"""
Handlers для команд /start и /help.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards.main_menu import MainMenuCB, get_main_menu
from src.services import get_user_service

logger = logging.getLogger(__name__)

router = Router()


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
            f"💳 Ваш баланс: <b>{user.balance}₽</b>\n\n"
            f"Нажмите «Создать кампанию», чтобы начать!"
        )
    else:
        # Возвращающийся пользователь или с рефералом
        text = (
            f"👋 <b>С возвращением, {message.from_user.first_name or user.username or 'друг'}!</b>\n\n"
            f"💳 Баланс: <b>{user.balance}₽</b>\n"
            f"📦 Тариф: <b>{plan_value}</b>\n\n"
            f"Выберите действие в меню ниже:"
        )

    await message.answer(text, reply_markup=get_main_menu(user.balance, user.id))


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
    async with get_user_service() as svc:
        user = await svc._user_repo.get_by_telegram_id(message.from_user.id)

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
            f"💳 Баланс: <b>{user.balance}₽</b>\n"
            f"📦 Тариф: <b>{plan_value}</b>\n\n"
            f"Выберите действие в меню ниже:"
        )

        await callback.message.edit_text(text, reply_markup=get_main_menu(user.balance, user.id))


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
