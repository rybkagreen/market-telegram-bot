"""
Handlers для раздела "Помощь".
Задача 8.1: Создать файл с обработчиками callback помощи.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.main_menu import MainMenuCB
from src.bot.utils.safe_callback import safe_callback_edit

logger = logging.getLogger(__name__)

router = Router(name="help")


@router.callback_query(MainMenuCB.filter(F.action == "help"))
async def handle_help_menu(callback: CallbackQuery) -> None:
    """
    Задача 8.1: Главное меню раздела Помощь.
    """
    text = (
        "❓ <b>Помощь</b>\n\n"
        "Выберите раздел:"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Быстрый старт", callback_data="help:quickstart")
    builder.button(text="💰 Оплата и выплаты", callback_data="help:billing")
    builder.button(text="🔒 Гарантии и безопасность", callback_data="help:safety")
    builder.button(text="📊 Как считается рейтинг", callback_data="help:rating")
    builder.button(text="📺 Подключение канала", callback_data="help:add_channel")
    builder.button(text="✉️ Написать в поддержку", callback_data=MainMenuCB(action="feedback"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1, 1, 1, 1, 1, 1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "quickstart"))
async def handle_quickstart(callback: CallbackQuery) -> None:
    """
    Задача 8.1: Быстрый старт.
    """
    text = (
        "🚀 <b>Быстрый старт</b>\n\n"
        "<b>Для рекламодателей:</b>\n"
        "1. Пополните баланс (от 100 кредитов)\n"
        "2. Нажмите «Создать кампанию»\n"
        "3. Выберите способ создания:\n"
        "   • Вручную — пошаговый мастер\n"
        "   • С помощью AI — нейросеть создаст текст\n"
        "   • Из шаблона — готовый текст для тематики\n"
        "4. Настройте таргетинг и бюджет\n"
        "5. Запустите рассылку\n\n"
        "<b>Для владельцев каналов:</b>\n"
        "1. Нажмите «Добавить канал»\n"
        "2. Введите @username канала\n"
        "3. Добавьте бота администратором\n"
        "4. Укажите цену за пост\n"
        "5. Выберите тематики\n"
        "6. Канал появится в каталоге\n\n"
        "💡 <b>Совет:</b> начните с пополнения баланса и создания первой кампании."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Пополнить баланс", callback_data=MainMenuCB(action="balance"))
    builder.button(text="📣 Создать кампанию", callback_data=MainMenuCB(action="create_menu"))
    builder.button(text="📺 Добавить канал", callback_data=MainMenuCB(action="add_channel"))
    builder.button(text="🔙 Назад", callback_data="main:help")
    builder.adjust(1, 1, 1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "billing"))
async def handle_billing_help(callback: CallbackQuery) -> None:
    """
    Задача 8.1: Вопросы оплаты.
    """
    text = (
        "💰 <b>Оплата и выплаты</b>\n\n"
        "<b>Пополнение баланса:</b>\n"
        "• Криптовалюты: USDT, TON, BTC, ETH, LTC\n"
        "• Telegram Stars\n"
        "• Минимальная сумма: 100 кредитов\n\n"
        "<b>Курс кредитов:</b>\n"
        "• 1 USDT = 90 кредитов\n"
        "• 1 TON = 400 кредитов\n"
        "• 1 Star = 2 кредита\n\n"
        "<b>Выплаты владельцам каналов:</b>\n"
        "• 80% от стоимости поста — вам\n"
        "• 20% — комиссия платформы\n"
        "• Минимальная сумма вывода: 500 кредитов\n"
        "• Выплаты автоматически после публикации\n\n"
        "<b>Возврат средств:</b>\n"
        "• Если пост не вышел — средства вернутся\n"
        "• При отклонении заявки — возврат рекламодателю\n"
        "• При запросе правок — средства замораживаются"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Пополнить баланс", callback_data=MainMenuCB(action="balance"))
    builder.button(text="💸 Выплаты", callback_data=MainMenuCB(action="payouts"))
    builder.button(text="🔙 Назад", callback_data="main:help")
    builder.adjust(1, 1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "safety"))
async def handle_safety_help(callback: CallbackQuery) -> None:
    """
    Задача 8.1: Гарантии и безопасность.
    """
    text = (
        "🔒 <b>Как мы защищаем обе стороны</b>\n\n"
        "<b>Рекламодатель:</b>\n"
        "✅ Деньги замораживаются — не уходят сразу\n"
        "✅ Пост не вышел → средства вернутся на баланс\n"
        "✅ Рейтинг надёжности канала виден до покупки\n"
        "✅ Детектор накрутки помечает подозрительные каналы\n\n"
        "<b>Владелец канала:</b>\n"
        "✅ Выплата после факта публикации — гарантирована\n"
        "✅ Предпросмотр поста перед одобрением\n"
        "✅ Контент-фильтр: реклама проверяется до вас\n"
        "✅ Право отклонить любую заявку без объяснений\n"
        "✅ Бот имеет только право публиковать\n\n"
        "<b>Безопасность данных:</b>\n"
        "• Шифрование всех транзакций\n"
        "• Резервное копирование каждые 6 часов\n"
        "• Защита от DDoS-атак"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📺 Добавить канал", callback_data=MainMenuCB(action="add_channel"))
    builder.button(text="📣 Создать кампанию", callback_data=MainMenuCB(action="create_menu"))
    builder.button(text="🔙 Назад", callback_data="main:help")
    builder.adjust(1, 1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "rating"))
async def handle_rating_help(callback: CallbackQuery) -> None:
    """
    Задача 8.1: Как считается рейтинг.
    """
    text = (
        "📊 <b>Как считается рейтинг канала</b>\n\n"
        "<b>Рейтинговый балл (0–100)</b> считается ежедневно:\n\n"
        "• <b>Охват аудитории — 30%</b>\n"
        "  (просмотры / подписчики)\n\n"
        "• <b>Engagement Rate — 25%</b>\n"
        "  (реакции + комментарии / просмотры)\n\n"
        "• <b>Прирост аудитории — 15%</b>\n"
        "  (органический рост за 30 дней)\n\n"
        "• <b>Частота публикаций — 10%</b>\n"
        "  (оптимум: 1–3 поста в день)\n\n"
        "• <b>Надёжность размещений — 15%</b>\n"
        "  (доля размещений без отмен)\n\n"
        "• <b>Возраст канала — 5%</b>\n"
        "  (бонус для каналов старше 6 месяцев)\n\n"
        "<b>Рейтинг надёжности (1–5★)</b> — отдельная метрика.\n"
        "Растёт при быстром одобрении заявок и падает\n"
        "при отменах и задержках."
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📺 Добавить канал", callback_data=MainMenuCB(action="add_channel"))
    builder.button(text="📊 Аналитика", callback_data=MainMenuCB(action="analytics"))
    builder.button(text="🔙 Назад", callback_data="main:help")
    builder.adjust(1, 1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(MainMenuCB.filter(F.action == "add_channel"))
async def handle_add_channel_help(callback: CallbackQuery) -> None:
    """
    Задача 8.1: Подключение канала.
    """
    text = (
        "📺 <b>Подключение канала</b>\n\n"
        "<b>Требования к каналу:</b>\n"
        "• Публичный (не приватный, есть @username)\n"
        "• Не менее 500 подписчиков\n"
        "• Преимущественно русскоязычная аудитория\n\n"
        "<b>Как добавить бота администратором:</b>\n"
        "1. Откройте ваш канал @{username}\n"
        "2. Нажмите на название → «Управление каналом»\n"
        "3. Перейдите в «Администраторы»\n"
        "4. Нажмите «Добавить администратора»\n"
        "5. Найдите @RekHarborBot\n"
        "6. Оставьте включённым ТОЛЬКО\n"
        "   «Публикация сообщений»\n"
        "7. Нажмите «Сохранить»\n\n"
        "🔒 <b>Бот не может:</b>\n"
        "• Удалять посты\n"
        "• Управлять участниками\n"
        "• Редактировать описание канала\n"
        "• Только публиковать рекламные посты"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить канал", callback_data=MainMenuCB(action="add_channel"))
    builder.button(text="🔙 Назад", callback_data="main:help")
    builder.adjust(1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()
