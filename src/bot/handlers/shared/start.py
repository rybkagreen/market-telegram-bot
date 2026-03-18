"""Shared start handler."""

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.advertiser.adv_menu import adv_menu_kb
from src.bot.keyboards.owner.own_menu import own_menu_kb
from src.bot.keyboards.shared.main_menu import main_menu_kb, role_select_kb, tos_kb
from src.db.repositories.placement_request_repo import PlacementRequestRepository
from src.db.repositories.user_repo import UserRepository

router = Router()

_PLAN_NAMES = {
    "free": "Free",
    "starter": "Starter 🚀",
    "pro": "Pro 💎",
    "business": "Agency 🏢",
}

TOS_TEXT = (
    "📋 *Условия использования*\n\n"
    "Для продолжения необходимо принять условия использования платформы.\n\n"
    "🔹 Платформа не является налоговым агентом для владельцев каналов\n"
    "🔹 Вы самостоятельно несёте ответственность за уплату налогов\n"
    "🔹 Минимальный возраст: 18 лет\n\n"
    "[Ознакомиться с полными условиями](https://rekharbor.ru/terms)"
)

WELCOME_TEXT = (
    "👋 Привет, *{first_name}*\\!\n\n"
    "Добро пожаловать в *RekHarborBot* — рекламную биржу Telegram\\-каналов\\.\n\n"
    "🔹 Рекламодатели размещают рекламу в каналах\n"
    "🔹 Владельцы каналов зарабатывают на публикациях\n"
    "🔹 Платформа берёт 15% комиссии"
)


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    """Обработка /start."""
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name or "User"

    user, _ = await UserRepository(session).get_or_create(
        telegram_id,
        defaults={
            "username": message.from_user.username,
            "first_name": first_name,
            "referral_code": f"ref_{telegram_id}",
        },
    )

    if user.terms_accepted_at is None:
        await message.answer(TOS_TEXT, reply_markup=tos_kb(), parse_mode="Markdown")
        return

    await message.answer(
        WELCOME_TEXT.format(first_name=first_name),
        reply_markup=main_menu_kb(),
        parse_mode="MarkdownV2",
    )


@router.message(Command("help"))
async def show_help_cmd(message: Message) -> None:
    """Показать помощь."""
    await message.answer("Помощь: /start — главное меню")


@router.callback_query(F.data == "terms:accept")
async def cb_tos_accept(callback: CallbackQuery, session: AsyncSession) -> None:
    """Принятие условий использования."""
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    user.terms_accepted_at = datetime.utcnow()
    first_name = callback.from_user.first_name or "User"
    await callback.message.edit_text(
        WELCOME_TEXT.format(first_name=first_name),
        reply_markup=main_menu_kb(),
        parse_mode="MarkdownV2",
    )
    await callback.answer()


@router.callback_query(F.data == "terms:decline")
async def cb_tos_decline(callback: CallbackQuery) -> None:
    """Отклонение условий использования."""
    await callback.message.edit_text(
        "❌ Без принятия условий использование платформы невозможно.\n\n"
        "Если вы хотите продолжить, нажмите /start и примите условия.",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "main:main_menu")
async def cb_main_menu(callback: CallbackQuery) -> None:
    """Вернуться в главное меню."""
    await callback.message.edit_text("🏠 Главное меню", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "main:change_role")
async def cb_change_role(callback: CallbackQuery) -> None:
    """Показать выбор роли."""
    await callback.message.edit_text("Выберите роль:", reply_markup=role_select_kb())
    await callback.answer()


@router.callback_query(F.data == "role:advertiser")
async def cb_role_advertiser(callback: CallbackQuery, session: AsyncSession) -> None:
    """Установить роль рекламодателя и показать меню рекламодателя."""
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    user.current_role = "advertiser"
    plan_name = _PLAN_NAMES.get(user.plan, user.plan)
    await callback.message.edit_text(
        f"📣 *Меню рекламодателя*\n\n"
        f"💳 Баланс: *{user.balance_rub} ₽* | ⭐ Тариф: *{plan_name}*",
        reply_markup=adv_menu_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "role:owner")
async def cb_role_owner(callback: CallbackQuery, session: AsyncSession) -> None:
    """Установить роль владельца и показать меню владельца."""
    repo = UserRepository(session)
    user = await repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    user.current_role = "owner"
    pending = await PlacementRequestRepository(session).get_pending_for_owner(user.id)
    pending_count = len(pending)
    await callback.message.edit_text(
        "📺 *Меню владельца канала*",
        reply_markup=own_menu_kb(pending_count=pending_count),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "main:adv_menu")
async def go_to_adv_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Перейти в меню рекламодателя (для кнопок «Назад»)."""
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    plan_name = _PLAN_NAMES.get(user.plan, user.plan)
    await callback.message.edit_text(
        f"📣 *Меню рекламодателя*\n\n"
        f"💳 Баланс: *{user.balance_rub} ₽* | ⭐ Тариф: *{plan_name}*",
        reply_markup=adv_menu_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "main:own_menu")
async def go_to_own_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Перейти в меню владельца (для кнопок «Назад»)."""
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    pending = await PlacementRequestRepository(session).get_pending_for_owner(user.id)
    await callback.message.edit_text(
        "📺 *Меню владельца канала*",
        reply_markup=own_menu_kb(pending_count=len(pending)),
        parse_mode="Markdown",
    )
    await callback.answer()
