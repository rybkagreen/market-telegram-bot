"""
Handlers и утилиты для уведомлений PlacementRequest.

Этот модуль содержит:
- Форматировщики уведомлений для каждого перехода статуса
- Дедупликация через Redis (CR2 паттерн)
- Async функции для вызова из PlacementRequestService
"""

import logging
from datetime import datetime
from decimal import Decimal

from aiogram import Bot
from redis.asyncio import Redis

from src.config.settings import settings
from src.db.models.placement_request import PlacementRequest
from src.db.models.user import User

logger = logging.getLogger(__name__)

# Redis клиент для дедупликации уведомлений
redis_client = Redis.from_url(settings.celery_broker_url, decode_responses=True)

# TTL для дедупликации (5 минут)
DEDUP_TTL_SECONDS = 300

# Маппинг причин отклонения
REJECTION_REASON_MAP = {
    "topic_mismatch": "Не подходит тематика",
    "low_quality": "Низкое качества текста",
    "bad_timing": "Неудобное время размещения",
    "low_price": "Предложенная цена слишком низкая",
    "paused": "Канал временно не принимает рекламу",
    "other": "Другая причина",
}


# =============================================================================
# ОБЩИЙ ХЕЛПЕР
# =============================================================================


async def _send_notification(
    telegram_id: int,
    text: str,
    placement_id: int,
    event_key: str,
) -> bool:
    """
    Отправить уведомление пользователю с дедупликацией.

    Args:
        telegram_id: Telegram ID пользователя.
        text: Текст сообщения.
        placement_id: ID заявки.
        event_key: Ключ события (например, 'new_request').

    Returns:
        True если уведомление отправлено успешно.
    """
    # Дедупликация (CR2 паттерн)
    dedup_key = f"notif:placement:{placement_id}:{event_key}"

    if await redis_client.exists(dedup_key):
        logger.debug(f"Notification {dedup_key} already sent, skipping")
        return False

    await redis_client.setex(dedup_key, DEDUP_TTL_SECONDS, "1")

    bot = Bot(token=settings.bot_token)

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode="HTML",
        )
        logger.info(f"Notification sent to user {telegram_id}: {event_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to {telegram_id}: {e}")
        return False
    finally:
        await bot.session.close()


# =============================================================================
# ФОРМАТЧИКИ ТЕКСТОВ
# =============================================================================


def _format_owner_payout(amount: Decimal) -> Decimal:
    """Вычислить доход владельца (80%)."""
    return amount * Decimal("0.80")


def _truncate_text(text: str, max_len: int = 300) -> str:
    """Обрезать текст до max_len символов."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _format_datetime(dt: datetime | None) -> str:
    """Форматировать дату."""
    if not dt:
        return "Не указана"
    return dt.strftime("%d.%m.%Y %H:%M")


# =============================================================================
# УВЕДОМЛЕНИЯ
# =============================================================================


async def notify_new_request(
    placement: PlacementRequest,
    advertiser: User,
    owner: User,
    channel_username: str,
) -> tuple[bool, bool]:
    """
    Новая заявка поступила владельцу (pending_owner).

    Args:
        placement: Заявка.
        advertiser: Рекламодатель.
        owner: Владелец канала.
        channel_username: Username канала.

    Returns:
        (sent_to_owner, sent_to_advertiser)
    """
    owner_payout = _format_owner_payout(placement.proposed_price)
    post_preview = _truncate_text(placement.final_text)
    scheduled = _format_datetime(placement.proposed_schedule)

    text_owner = "\n".join([
        "📋 <b>Новая заявка на размещение!</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"💰 Предложенная цена: <b>{placement.proposed_price} ₽</b>",
        f"  → Вы получите: <b>{owner_payout} ₽</b> (80%)",
        f"📅 Дата публикации: {scheduled}",
        "⏱ Ответьте в течение <b>24 часов</b>",
        "",
        "📝 Текст поста:",
        f"<blockquote>{post_preview}</blockquote>",
        "",
        "Откройте приложение для ответа 👇",
    ])

    sent_owner = await _send_notification(
        owner.telegram_id,
        text_owner,
        placement.id,
        "new_request",
    )

    return (sent_owner, False)


async def notify_counter_offer(
    placement: PlacementRequest,
    advertiser: User,
    channel_username: str,
    counter_comment: str | None = None,
) -> bool:
    """
    Владелец сделал встречное предложение (counter_offer).

    Args:
        placement: Заявка.
        advertiser: Рекламодатель.
        channel_username: Username канала.
        counter_comment: Комментарий к контр-предложению.

    Returns:
        True если отправлено.
    """
    counter_price = placement.final_price or placement.proposed_price
    comment = counter_comment or "—"
    max_rounds = 3

    text = "\n".join([
        "💱 <b>Владелец предложил другую цену</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"💰 Ваша цена: <s>{placement.proposed_price} ₽</s>",
        f"💰 Встречная цена: <b>{counter_price} ₽</b>",
        f"💬 Комментарий: {comment}",
        "⏱ Ответьте в течение <b>24 часов</b>",
        f"🔄 Раунд переговоров: {placement.counter_offer_count}/{max_rounds}",
        "",
        "Принять или предложить свои условия 👇",
    ])

    return await _send_notification(
        advertiser.telegram_id,
        text,
        placement.id,
        "counter_offer",
    )


async def notify_counter_accepted(
    placement: PlacementRequest,
    advertiser: User,
    owner: User,
    channel_username: str,
) -> tuple[bool, bool]:
    """
    Рекламодатель принял контр-предложение (pending_payment).

    Args:
        placement: Заявка.
        advertiser: Рекламодатель.
        owner: Владелец.
        channel_username: Username канала.

    Returns:
        (sent_to_owner, sent_to_advertiser)
    """
    final_price = placement.final_price or placement.proposed_price
    owner_payout = _format_owner_payout(final_price)

    text_owner = "\n".join([
        "✅ <b>Рекламодатель принял ваше предложение!</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"💰 Согласованная цена: <b>{final_price} ₽</b>",
        f"  → Вы получите: <b>{owner_payout} ₽</b>",
        "⏳ Ожидаем оплату от рекламодателя (до 24 ч)",
    ])

    sent_owner = await _send_notification(
        owner.telegram_id,
        text_owner,
        placement.id,
        "counter_accepted",
    )

    return (sent_owner, False)


async def notify_owner_accepted(
    placement: PlacementRequest,
    advertiser: User,
    channel_username: str,
) -> bool:
    """
    Владелец принял заявку (pending_payment).

    Args:
        placement: Заявка.
        advertiser: Рекламодатель.
        channel_username: Username канала.

    Returns:
        True если отправлено.
    """
    final_price = placement.final_price or placement.proposed_price
    scheduled = _format_datetime(placement.final_schedule)

    text = "\n".join([
        "✅ <b>Владелец принял вашу заявку!</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"💰 Сумма к оплате: <b>{final_price} ₽</b>",
        f"📅 Дата публикации: {scheduled}",
        "⏱ Оплатите в течение <b>24 часов</b>",
        "",
        "Перейдите в приложение для оплаты 👇",
    ])

    return await _send_notification(
        advertiser.telegram_id,
        text,
        placement.id,
        "owner_accepted",
    )


async def notify_payment_received(
    placement: PlacementRequest,
    advertiser: User,
    owner: User,
    channel_username: str,
) -> tuple[bool, bool]:
    """
    Рекламодатель оплатил, средства заморожены (escrow).

    Args:
        placement: Заявка.
        advertiser: Рекламодатель.
        owner: Владелец.
        channel_username: Username канала.

    Returns:
        (sent_to_owner, sent_to_advertiser)
    """
    final_price = placement.final_price or placement.proposed_price
    owner_payout = _format_owner_payout(final_price)
    scheduled = _format_datetime(placement.final_schedule)

    text_owner = "\n".join([
        "🔒 <b>Средства заморожены — публикация запланирована</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"💰 Ваш доход: <b>{owner_payout} ₽</b> (будет начислен после публикации)",
        f"📅 Публикация: <b>{scheduled}</b>",
        "",
        "Подготовьте канал к размещению рекламы ✅",
    ])

    text_advertiser = "\n".join([
        "🔒 <b>Средства заморожены — всё готово!</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"💰 Зарезервировано: <b>{final_price} ₽</b>",
        f"📅 Публикация: <b>{scheduled}</b>",
        "",
        "Мы уведомим вас когда пост выйдет 🔔",
    ])

    sent_owner = await _send_notification(
        owner.telegram_id,
        text_owner,
        placement.id,
        "payment_received",
    )

    sent_advertiser = await _send_notification(
        advertiser.telegram_id,
        text_advertiser,
        placement.id,
        "escrow_confirmed",
    )

    return (sent_owner, sent_advertiser)


async def notify_published(
    placement: PlacementRequest,
    advertiser: User,
    owner: User,
    channel_username: str,
) -> tuple[bool, bool]:
    """
    Пост опубликован (published).

    Args:
        placement: Заявка.
        advertiser: Рекламодатель.
        owner: Владелец.
        channel_username: Username канала.

    Returns:
        (sent_to_owner, sent_to_advertiser)
    """
    final_price = placement.final_price or placement.proposed_price
    owner_payout = _format_owner_payout(final_price)
    published = _format_datetime(placement.published_at)

    text_advertiser = "\n".join([
        "🎉 <b>Ваш пост опубликован!</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"📅 Опубликован: {published}",
        f"💰 Списано: {final_price} ₽",
        "",
        "Успешной рекламной кампании! 🚀",
    ])

    text_owner = "\n".join([
        "✅ <b>Пост опубликован — доход начислен!</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"💰 Начислено: <b>+{owner_payout} ₽</b>",
        f"📅 Дата: {published}",
        "",
        "Спасибо за качественное сотрудничество 🤝",
    ])

    sent_advertiser = await _send_notification(
        advertiser.telegram_id,
        text_advertiser,
        placement.id,
        "published",
    )

    sent_owner = await _send_notification(
        owner.telegram_id,
        text_owner,
        placement.id,
        "published_owner",
    )

    return (sent_owner, sent_advertiser)


async def notify_rejected(
    placement: PlacementRequest,
    advertiser: User,
    channel_username: str,
    rejection_reason: str | None = None,
) -> bool:
    """
    Владелец отклонил заявку (failed).

    Args:
        placement: Заявка.
        advertiser: Рекламодатель.
        channel_username: Username канала.
        rejection_reason: Код причины отклонения.

    Returns:
        True если отправлено.
    """
    reason_ru = REJECTION_REASON_MAP.get(rejection_reason or "", rejection_reason or "Не указана")
    refund_amount = placement.proposed_price

    text = "\n".join([
        "❌ <b>Владелец отклонил заявку</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"📝 Причина: {reason_ru}",
        f"💰 Возврат: <b>{refund_amount} ₽</b> зачислен на баланс",
        "",
        "Попробуйте другой канал 👇",
    ])

    return await _send_notification(
        advertiser.telegram_id,
        text,
        placement.id,
        "rejected",
    )


async def notify_sla_expired(
    placement: PlacementRequest,
    advertiser: User,
    owner: User,
    channel_username: str,
) -> tuple[bool, bool]:
    """
    SLA истёк — владелец не ответил (failed).

    Args:
        placement: Заявка.
        advertiser: Рекламодатель.
        owner: Владелец.
        channel_username: Username канала.

    Returns:
        (sent_to_owner, sent_to_advertiser)
    """
    refund_amount = placement.proposed_price

    text_owner = "\n".join([
        f"⚠️ <b>Заявка #{placement.id} просрочена</b>",
        "",
        "Вы не ответили на заявку в течение 24 часов.",
        f"📺 Канал: @{channel_username}",
        "",
        "Заявка автоматически отклонена.",
        "Частые просрочки снижают репутацию канала.",
    ])

    text_advertiser = "\n".join([
        "⏱ <b>Владелец не ответил вовремя</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"💰 Возврат: <b>{refund_amount} ₽</b> зачислен на баланс",
        "",
        "Попробуйте разместить рекламу в другом канале 👇",
    ])

    sent_owner = await _send_notification(
        owner.telegram_id,
        text_owner,
        placement.id,
        "sla_expired_owner",
    )

    sent_advertiser = await _send_notification(
        advertiser.telegram_id,
        text_advertiser,
        placement.id,
        "sla_expired_advertiser",
    )

    return (sent_owner, sent_advertiser)


async def notify_cancelled(
    placement: PlacementRequest,
    advertiser: User,
    owner: User,
    channel_username: str,
    reputation_delta: float = 0.0,
) -> tuple[bool, bool]:
    """
    Рекламодатель отменил заявку (cancelled).

    Args:
        placement: Заявка.
        advertiser: Рекламодатель.
        owner: Владелец.
        channel_username: Username канала.
        reputation_delta: Изменение репутации.

    Returns:
        (sent_to_owner, sent_to_advertiser)
    """
    refund_amount = placement.proposed_price
    scheduled = _format_datetime(placement.proposed_schedule)

    text_advertiser = "\n".join([
        "🚫 <b>Заявка отменена</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"💰 Возврат: <b>{refund_amount} ₽</b>",
        f"📉 Изменение репутации: <b>{reputation_delta}</b>",
    ])

    text_owner = "\n".join([
        "ℹ️ <b>Рекламодатель отменил заявку</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"📅 Планировалось: {scheduled}",
        "",
        "Слот свободен для новых размещений.",
    ])

    sent_advertiser = await _send_notification(
        advertiser.telegram_id,
        text_advertiser,
        placement.id,
        "cancelled_advertiser",
    )

    sent_owner = await _send_notification(
        owner.telegram_id,
        text_owner,
        placement.id,
        "cancelled_owner",
    )

    return (sent_owner, sent_advertiser)


async def notify_publication_failed(
    placement: PlacementRequest,
    advertiser: User,
    owner: User,
    channel_username: str,
) -> tuple[bool, bool]:
    """
    Ошибка публикации (failed).

    Args:
        placement: Заявка.
        advertiser: Рекламодатель.
        owner: Владелец.
        channel_username: Username канала.

    Returns:
        (sent_to_owner, sent_to_advertiser)
    """
    refund_amount = (placement.final_price or placement.proposed_price) * Decimal("0.50")

    text_advertiser = "\n".join([
        "❌ <b>Ошибка публикации</b>",
        "",
        f"📺 Канал: @{channel_username}",
        f"💰 Возврат: <b>{refund_amount} ₽</b> (50% от суммы)",
        "",
        "Возможно бот был удалён из канала.",
        "Обратитесь в поддержку если вопросы остались.",
    ])

    text_owner = "\n".join([
        "❌ <b>Не удалось опубликовать пост</b>",
        "",
        f"📺 Канал: @{channel_username}",
        "Проверьте что бот является администратором канала",
        "и имеет право публиковать сообщения.",
        "",
        "⚠️ Рекламодателю возвращено 50% средств.",
    ])

    sent_advertiser = await _send_notification(
        advertiser.telegram_id,
        text_advertiser,
        placement.id,
        "publication_failed_advertiser",
    )

    sent_owner = await _send_notification(
        owner.telegram_id,
        text_owner,
        placement.id,
        "publication_failed_owner",
    )

    return (sent_owner, sent_advertiser)


# =============================================================================
# YOOKASSA УВЕДОМЛЕНИЯ
# =============================================================================


def format_yookassa_payment_success(
    amount_rub: Decimal,
    credits: int,
    new_balance: int,
) -> str:
    """
    Текст уведомления об успешном пополнении через ЮKassa.

    Args:
        amount_rub: Сумма в рублях.
        credits: Количество зачисленных кредитов.
        new_balance: Новый баланс пользователя.

    Returns:
        str: Форматированный текст уведомления.
    """
    return (
        f"✅ <b>Баланс пополнен!</b>\n\n"
        f"💳 Оплачено: {amount_rub} ₽\n"
        f"💎 Зачислено: +{credits} кредитов\n"
        f"📊 Текущий баланс: {new_balance} ₽"
    )
