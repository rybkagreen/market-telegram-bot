"""
Handlers для выбора модели ИИ (/models).

Для админов: полный выбор провайдера и модели.
Для пользователей: просмотр текущей модели на основе тарифа.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.main_menu import ModelCB, get_main_menu
from src.config.settings import settings
from src.db.models.user import User, UserPlan
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()

# Доступные провайдеры и модели
AI_PROVIDERS = {
    "groq": {
        "name": "Groq (бесплатный)",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ],
    },
    "openai": {
        "name": "OpenAI (production)",
        "models": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
    },
    "openrouter": {
        "name": "OpenRouter (универсальный)",
        "models": [
            "anthropic/claude-sonnet-4-20250514",
            "anthropic/claude-3-5-sonnet",
            "anthropic/claude-3-opus",
            "meta-llama/llama-3-70b-instruct",
            "mistralai/mistral-large",
            "google/gemma-7b-it",
        ],
    },
}

# Модели по тарифам
TARIFF_MODELS = {
    UserPlan.FREE: {"provider": "groq", "model": "llama-3.3-70b-versatile"},
    UserPlan.STARTER: {"provider": "groq", "model": "llama-3.3-70b-versatile"},
    UserPlan.PRO: {"provider": "openrouter", "model": "anthropic/claude-sonnet-4-20250514"},
    UserPlan.BUSINESS: {"provider": "openrouter", "model": "anthropic/claude-sonnet-4-20250514"},
    UserPlan.ADMIN: {"provider": "openrouter", "model": "nousresearch/hermes-3-llama-3.1-405b:free"},  # ADMIN — бесплатная модель
}


def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь админом."""
    return user_id in settings.admin_ids


@router.message(Command("models"))
async def handle_models(message: Message) -> None:
    """
    Обработчик команды /models.

    Для админов: показывает меню выбора модели.
    Для пользователей: показывает текущую модель на основе тарифа.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(message.from_user.id)

        if not user:
            await message.answer("❌ Пользователь не найден. Нажмите /start")
            return

        if is_admin(message.from_user.id):
            await show_admin_models_menu(message, user)
        else:
            await show_user_models_info(message, user)


async def show_admin_models_menu(message: Message | CallbackQuery, user: User) -> None:
    """Показать меню выбора модели для админа."""
    answer_method = message.message.answer if isinstance(message, CallbackQuery) else message.answer

    current_provider = settings.ai_provider
    current_model = settings.ai_model

    text = (
        f"🤖 <b>Настройки ИИ (Админ-панель)</b>\n\n"
        f"📌 <b>Глобальные настройки:</b>\n"
        f"Провайдер: <code>{current_provider}</code>\n"
        f"Модель: <code>{current_model}</code>\n\n"
        f"⚙️ <b>Как изменить:</b>\n"
        f"Измените переменные окружения в .env:\n"
        f"<code>AI_PROVIDER=groq</code>\n"
        f"<code>AI_MODEL=llama-3.3-70b-versatile</code>\n\n"
        f"📋 <b>Доступные провайдеры:</b>\n"
    )

    builder = InlineKeyboardBuilder()

    for provider_key, provider_info in AI_PROVIDERS.items():
        status = "✅" if provider_key == current_provider else "⚪"
        builder.button(
            text=f"{status} {provider_info['name']}", callback_data=ModelCB(provider=provider_key)
        )

    builder.button(text="🔙 В меню", callback_data=ModelCB(provider="back"))
    builder.adjust(1)

    await answer_method(text, reply_markup=builder.as_markup())


async def show_user_models_info(message: Message | CallbackQuery, user: User) -> None:
    """Показать информацию о модели для пользователя."""
    answer_method = message.message.answer if isinstance(message, CallbackQuery) else message.answer

    # Получаем модель пользователя на основе тарифа
    user_provider = user.get_ai_provider()
    user_model = user.get_ai_model()

    plan_value = user.plan.value if hasattr(user.plan, "value") else user.plan

    # Преобразуем строку в Enum если нужно
    user_plan = user.plan if hasattr(user.plan, "value") else UserPlan(plan_value)
    tariff_info = TARIFF_MODELS.get(user_plan, TARIFF_MODELS[UserPlan.STARTER])

    text = (
        f"🤖 <b>Ваша ИИ модель</b>\n\n"
        f"📦 <b>Тариф:</b> <code>{plan_value.upper()}</code>\n\n"
        f"⚙️ <b>Текущие настройки:</b>\n"
        f"Провайдер: <code>{user_provider}</code>\n"
        f"Модель: <code>{user_model}</code>\n\n"
    )

    # Если у пользователя кастомные настройки
    if user.ai_provider or user.ai_model:
        text += (
            "✨ <b>Персональные настройки:</b>\nУ вас установлены индивидуальные настройки ИИ.\n\n"
        )
    else:
        text += (
            f"📋 <b>Модель по тарифу:</b>\n"
            f"Ваш тариф автоматически использует:\n"
            f"• Провайдер: <code>{tariff_info['provider']}</code>\n"
            f"• Модель: <code>{tariff_info['model']}</code>\n\n"
        )

    # Информация о доступных моделях по тарифам
    text += (
        "📊 <b>Модели по тарифам:</b>\n"
        "FREE/STARTER → Groq (Llama 3.3 70B)\n"
        "PRO/BUSINESS → OpenRouter (Claude Sonnet 4)\n\n"
        "💡 <b>Хотите сменить модель?</b>\n"
        "Обновите тарифный план в разделе «Кабинет»."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Сменить тариф", callback_data=ModelCB(provider="tariff_info"))
    builder.button(text="🔙 В меню", callback_data=ModelCB(provider="back"))
    builder.adjust(1, 1)

    await answer_method(text, reply_markup=builder.as_markup())


@router.callback_query(ModelCB.filter(F.provider == "tariff_info"))
async def tariff_info_callback(callback: CallbackQuery) -> None:
    """Показать информацию о тарифах."""
    text = (
        "📦 <b>Тарифные планы и ИИ модели</b>\n\n"
        "🆓 <b>FREE</b> — 0₽/мес\n"
        "  • Groq (Llama 3.3 70B)\n"
        "  • Базовая генерация\n\n"
        "🚀 <b>STARTER</b> — 299₽/мес\n"
        "  • Groq (Llama 3.3 70B)\n"
        "  • 5 кампаний в месяц\n"
        "  • 50 чатов на кампанию\n\n"
        "💎 <b>PRO</b> — 999₽/мес\n"
        "  • OpenRouter (Claude Sonnet 4)\n"
        "  • 20 кампаний в месяц\n"
        "  • 200 чатов на кампанию\n\n"
        "🏢 <b>BUSINESS</b> — 2999₽/мес\n"
        "  • OpenRouter (Claude Sonnet 4)\n"
        "  • 100 кампаний в месяц\n"
        "  • 1000 чатов на кампанию\n\n"
        "💡 <b>Для админов:</b>\n"
        "Используйте команду /models для выбора глобальной модели."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data=ModelCB(provider="back"))
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(ModelCB.filter(F.provider == "select"))
async def models_select_callback(callback: CallbackQuery) -> None:
    """Callback handler для кнопки выбора модели ИИ (админ)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ только для админов", show_alert=True)
        return

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        await show_admin_models_menu(callback, user)


@router.callback_query(ModelCB.filter(F.provider == "back"))
async def models_back_callback(callback: CallbackQuery) -> None:
    """Callback handler для возврата в главное меню."""
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

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


@router.callback_query(
    ModelCB.filter(
        (F.provider != "select") & (F.provider != "back") & (F.provider != "tariff_info")
    )
)
async def model_provider_callback(callback: CallbackQuery, callback_data: ModelCB) -> None:
    """Callback handler для выбора провайдера (только админ)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ только для админов", show_alert=True)
        return

    provider = callback_data.provider
    provider_info = AI_PROVIDERS.get(provider)

    if not provider_info:
        await callback.answer("❌ Неизвестный провайдер", show_alert=True)
        return

    current_model = settings.ai_model
    current_provider = settings.ai_provider

    # Формируем текст с моделями провайдера
    text = (
        f"🤖 <b>{provider_info['name']}</b>\n\n"
        f"📌 <b>Текущий провайдер:</b> <code>{current_provider}</code>\n"
        f"📌 <b>Текущая модель:</b> <code>{current_model}</code>\n\n"
        f"💡 <b>Доступные модели:</b>\n"
    )

    for model in provider_info["models"]:
        is_current = "✅" if model == current_model and provider == current_provider else "⚪"
        text += f"{is_current} <code>{model}</code>\n"

    text += (
        f"\n⚠️ <b>Внимание:</b>\n"
        f"Для смены провайдера измените <code>AI_PROVIDER</code> в .env файле:\n"
        f"<code>AI_PROVIDER={provider}</code>\n\n"
        f"После изменения перезапустите бота."
    )

    builder = InlineKeyboardBuilder()

    for model in provider_info["models"]:
        is_current = "✅" if model == current_model and provider == current_provider else ""
        builder.button(
            text=f"{is_current} {model}",
            callback_data=ModelCB(provider=f"model_{provider}_{model}"),
        )

    builder.button(text="🔙 К провайдерам", callback_data=ModelCB(provider="select"))
    builder.button(text="🔙 В меню", callback_data=ModelCB(provider="back"))
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
