"""Handler'ы для публичной страницы медиакита."""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, InaccessibleMessage

from src.bot.keyboards.channels import get_active_filters_bar
from src.bot.keyboards.mediakit import get_public_mediakit_kb
from src.bot.utils.safe_callback import safe_callback_edit
from src.core.services.mediakit_service import mediakit_service
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("channel_mediakit_public:"))
async def show_public_mediakit(callback: CallbackQuery) -> None:
    """Показать публичную страницу медиакита (для рекламодателей)."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    async with async_session_factory() as session:
        from src.db.models.analytics import TelegramChat
        from src.db.models.channel_mediakit import ChannelMediakit

        # Получить канал
        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        # Получить медиакит
        mediakit = await session.get(ChannelMediakit, channel_id)
        if not mediakit:
            # Создать если нет
            mediakit = await mediakit_service.get_or_create_mediakit(channel_id)

        # Проверить публичность
        if not mediakit.is_public:
            await callback.answer("❌ Медиакит недоступен", show_alert=True)
            return

        # Засчитать просмотр
        mediakit.views_count += 1
        await session.flush()

        # Получить данные
        mediakit_data = await mediakit_service.get_mediakit_data(channel_id)

    # Сформировать текст
    filters_text = get_active_filters_bar(
        categories=[mediakit_data["channel"].get("topic")]
        if mediakit_data["channel"].get("topic")
        else [],
        tariffs=[],
    )

    metrics = mediakit_data.get("metrics", {})
    price = mediakit_data.get("price", {})
    reviews = mediakit_data.get("reviews", {})

    text = (
        f"{filters_text}\n"
        f"📊 <b>Медиакит канала</b>\n\n"
        f"📡 <b>{mediakit_data['channel']['title'] or mediakit_data['channel']['username']}</b>\n"
        f"@{mediakit_data['channel']['username'] or '—'}\n\n"
    )

    # Описание
    description = mediakit_data["mediakit"].get("custom_description")
    if not description:
        description = mediakit_data["channel"].get("description", "")

    if description:
        text += f"{description}\n\n"

    # Метрики
    show_metrics = mediakit_data["mediakit"].get("show_metrics", {})

    text += "<b>━━ МЕТРИКИ ━━</b>\n"

    if show_metrics.get("subscribers", True):
        text += f"👥 Подписчики: <b>{metrics.get('subscribers', 0):,}</b>\n"

    if show_metrics.get("avg_views", True):
        text += f"👁 Средние просмотры: <b>{metrics.get('avg_views', 0):,}</b>\n"

    if show_metrics.get("er", True):
        text += f"📈 ER: <b>{metrics.get('er', 0.0):.1f}%</b>\n"

    if show_metrics.get("post_frequency", True):
        text += f"📝 Постов в день: <b>{metrics.get('post_frequency', 0.0):.1f}</b>\n"

    if show_metrics.get("price", True):
        text += f"💰 Цена за пост: <b>{price.get('amount', 0)} {price.get('currency', 'кр')}</b>\n"

    # Отзывы
    if reviews.get("count", 0) > 0:
        text += f"\n⭐ Рейтинг: <b>{reviews.get('average_rating', 0):.1f}/5</b> ({reviews.get('count', 0)} отзывов)\n"

    # Просмотры медиакита
    text += f"\n👁 Медиакит просмотрен: <b>{mediakit.views_count}</b> раз\n"

    keyboard = get_public_mediakit_kb(channel_id)

    await safe_callback_edit(callback, text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("mediakit_download_public:"))
async def download_public_mediakit_pdf(callback: CallbackQuery) -> None:
    """Скачать PDF медиакита (публичная страница)."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])

    await callback.answer("⏳ Генерирую PDF...", show_alert=False)

    async with async_session_factory() as session:
        # Получить медиакит
        mediakit = await mediakit_service.get_or_create_mediakit(channel_id)

        # Проверить публичность
        if not mediakit.is_public:
            await callback.answer("❌ Медиакит недоступен", show_alert=True)
            return

        # Получить данные
        mediakit_data = await mediakit_service.get_mediakit_data(channel_id)

        # Сгенерировать PDF
        from src.utils.mediakit_pdf import generate_mediakit_pdf

        pdf_bytes = generate_mediakit_pdf(mediakit_data)

        # Отправить файл
        await callback.message.answer_document(
            document=BufferedInputFile(pdf_bytes, filename=f"mediakit_{channel_id}.pdf"),
            caption=f"📊 Медиакит канала\n\nСгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        )

        # Засчитать скачивание
        mediakit.downloads_count += 1
        await session.commit()
