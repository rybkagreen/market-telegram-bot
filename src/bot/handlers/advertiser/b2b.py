"""
Handlers для B2B-маркетплейса.
Спринт 3 — пакетные предложения для агентств и крупных рекламодателей.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InaccessibleMessage,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.core.services.b2b_package_service import b2b_package_service

logger = logging.getLogger(__name__)
router = Router(name="b2b")


@router.message(Command("b2b"))
async def cmd_b2b(message: Message) -> None:
    """
    Показать B2B-маркетплейс — пакетные предложения.
    """
    text = (
        "🏢 <b>B2B-маркетплейс</b>\n\n"
        "Пакетные предложения для агентств и крупных рекламодателей.\n\n"
        "Выберите нишу для просмотра пакетов:"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💻 IT", callback_data="b2b_niche:it"),
                InlineKeyboardButton(text="💼 Бизнес", callback_data="b2b_niche:business"),
            ],
            [
                InlineKeyboardButton(text="🏠 Недвижимость", callback_data="b2b_niche:realestate"),
                InlineKeyboardButton(text="🔗 Крипта", callback_data="b2b_niche:crypto"),
            ],
            [
                InlineKeyboardButton(text="📈 Маркетинг", callback_data="b2b_niche:marketing"),
                InlineKeyboardButton(text="💰 Финансы", callback_data="b2b_niche:finance"),
            ],
        ]
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("b2b_niche:"))
async def show_niche_packages(callback: CallbackQuery) -> None:
    """
    Показать пакеты выбранной ниши.
    """
    niche = (callback.data or "").split(":")[1]

    # Получаем описание ниши
    niche_desc = b2b_package_service.NICHE_DESCRIPTIONS.get(niche, "Описание недоступно")

    # Получаем пакеты
    packages = await b2b_package_service.get_packages_by_niche(niche)

    if not packages:
        text = (
            f"{niche_desc}\n\n❌ В этой нише пока нет доступных пакетов.\n\nВыберите другую нишу:"
        )
    else:
        text = f"{niche_desc}\n\n📦 <b>Доступные пакеты ({len(packages)})</b>\n\n"

        for pkg in packages:
            text += (
                f"🔹 <b>{pkg['name']}</b>\n"
                f"   Каналов: {pkg['channels_count']}\n"
                f"   Охват: {pkg['guaranteed_reach']:,}\n"
                f"   Мин. ER: {pkg['min_er']}%\n"
                f"   Цена: {pkg['price']:,.0f} ₽ (-{pkg['discount_pct']}%)\n\n"
            )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к нишам", callback_data="b2b_back")],
        ]
    )

    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    if isinstance(callback.message, InaccessibleMessage):
        await callback.answer("Ошибка: сообщение недоступно")
        return
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "b2b_back")
async def b2b_back(callback: CallbackQuery) -> None:
    """
    Вернуться к выбору ниш.
    """
    text = (
        "🏢 <b>B2B-маркетплейс</b>\n\n"
        "Пакетные предложения для агентств и крупных рекламодателей.\n\n"
        "Выберите нишу для просмотра пакетов:"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💻 IT", callback_data="b2b_niche:it"),
                InlineKeyboardButton(text="💼 Бизнес", callback_data="b2b_niche:business"),
            ],
            [
                InlineKeyboardButton(text="🏠 Недвижимость", callback_data="b2b_niche:realestate"),
                InlineKeyboardButton(text="🔗 Крипта", callback_data="b2b_niche:crypto"),
            ],
            [
                InlineKeyboardButton(text="📈 Маркетинг", callback_data="b2b_niche:marketing"),
                InlineKeyboardButton(text="💰 Финансы", callback_data="b2b_niche:finance"),
            ],
        ]
    )

    if callback.message is None:
        await callback.answer("Ошибка: сообщение недоступно")
        return
    if isinstance(callback.message, InaccessibleMessage):
        await callback.answer("Ошибка: сообщение недоступно")
        return
    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )
