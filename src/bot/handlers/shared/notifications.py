"""Notification functions (NOT a Router)."""

import contextlib
import html
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)


async def notify_owner_new_request(
    bot: Bot,
    owner_telegram_id: int,
    request_id: int,
    placement: Any = None,
    channel_title: str | None = None,
) -> None:
    """Владельцу: новая заявка на размещение."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Просмотреть заявку", callback_data=f"own:request:{request_id}")
    builder.adjust(1)

    if placement is not None:
        proposed_price = getattr(placement, "proposed_price", None)
        proposed_schedule = getattr(placement, "proposed_schedule", None)
        ad_text = getattr(placement, "ad_text", "") or ""
        media_type = getattr(placement, "media_type", "none") or "none"

        schedule_str = (
            proposed_schedule.strftime("%d.%m.%Y %H:%M")
            if proposed_schedule
            else "По договорённости"
        )
        channel_line = f"📢 Канал: {html.escape(channel_title)}\n" if channel_title else ""
        price_str = f"{proposed_price:.0f}" if proposed_price is not None else "—"
        media_line = "\n🎥 К объявлению прикреплено видео" if media_type == "video" else ""

        ad_text_preview = html.escape(ad_text[:500] + ("…" if len(ad_text) > 500 else ""))
        text = (
            f"📬 <b>Новая заявка #{request_id}</b>\n\n"
            f"{channel_line}"
            f"💰 Предложенная цена: <b>{price_str} ₽</b>\n"
            f"📅 Дата размещения: <b>{schedule_str}</b>\n\n"
            f"📝 Текст объявления:\n{ad_text_preview}"
            f"{media_line}"
        )
        parse_mode = "HTML"
    else:
        text = f"🔔 <b>Новая заявка на размещение!</b>\n\nЗаявка #{request_id} ожидает вашего рассмотрения."
        parse_mode = "HTML"

    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=owner_telegram_id,
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode=parse_mode,
        )

    if placement is not None and getattr(placement, "video_file_id", None):
        with contextlib.suppress(Exception):
            await bot.send_video(
                chat_id=owner_telegram_id,
                video=placement.video_file_id,
            )


async def notify_advertiser_accepted(
    bot: Bot,
    advertiser_telegram_id: int,
    request_id: int,
    channel_name: str,
    format_name: str,
    final_price: Decimal,
    final_schedule: str,
) -> None:
    """Рекламодателю: владелец принял заявку."""
    builder = InlineKeyboardBuilder()
    builder.button(text=f"💳 Оплатить {final_price:.0f} ₽", callback_data=f"camp:pay:{request_id}")
    builder.button(text="❌ Отменить", callback_data=f"camp:cancel:{request_id}")
    builder.adjust(1)
    try:
        await bot.send_message(
            chat_id=advertiser_telegram_id,
            text=(
                f"✅ *Владелец принял вашу заявку!*\n\n"
                f"📺 @{channel_name}\n"
                f"📄 Формат: *{format_name}*\n"
                f"💰 Итоговая цена: *{final_price:.0f} ₽*\n"
                f"⏰ Время публикации: *{final_schedule}*\n\n"
                f"⏱ Оплатите в течение 24 часов."
            ),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"notify_advertiser_accepted failed for {advertiser_telegram_id}: {e}")


async def notify_advertiser_counter(
    bot: Bot,
    advertiser_telegram_id: int,
    request_id: int,
    channel_name: str,
    counter_price: Decimal,
    counter_schedule: str,
    counter_round: int,
) -> None:
    """Рекламодателю: контр-предложение от владельца."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять условия", callback_data=f"camp:counter:accept:{request_id}")
    if counter_round < 3:
        builder.button(text="✏️ Контр-предложение", callback_data=f"camp:counter:reply:{request_id}")
    builder.button(text="❌ Отклонить и отменить", callback_data=f"camp:cancel:{request_id}")
    builder.adjust(1)
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=advertiser_telegram_id,
            text=(
                f"🔄 *Контр-предложение от владельца*\n\n"
                f"📺 @{channel_name}\n"
                f"💰 Новая цена: *{counter_price:.0f} ₽*\n"
                f"⏰ Время: *{counter_schedule}*\n"
                f"🔁 Раунд: {counter_round}/3"
            ),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )


async def notify_advertiser_rejected(
    bot: Bot,
    advertiser_telegram_id: int,
    request_id: int,
    channel_name: str,
) -> None:
    """Рекламодателю: владелец отклонил заявку."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📣 Создать новую кампанию", callback_data="main:create_campaign")
    builder.button(text="📋 Мои кампании", callback_data="main:my_campaigns")
    builder.adjust(1)
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=advertiser_telegram_id,
            text=(
                f"❌ *Заявка отклонена*\n\n"
                f"📺 @{channel_name}\n"
                f"Заявка #{request_id} была отклонена владельцем канала."
            ),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )


async def notify_advertiser_published(
    bot: Bot,
    advertiser_telegram_id: int,
    placement_id: int,
    channel_name: str,
    published_at: datetime | None = None,
) -> None:
    """Рекламодателю: реклама опубликована."""
    builder = InlineKeyboardBuilder()
    within_48h = (datetime.now(UTC) - published_at) < timedelta(hours=48) if published_at else False
    if within_48h:
        builder.button(text="⚠️ Пожаловаться", callback_data=f"dispute:open:{placement_id}")
    builder.button(text="📊 Мои кампании", callback_data="main:my_campaigns")
    builder.adjust(1)
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=advertiser_telegram_id,
            text=(
                f"📢 *Реклама опубликована!*\n\n"
                f"📺 @{channel_name}\n"
                f"Ваше размещение #{placement_id} успешно опубликовано."
            ),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )


async def notify_advertiser_completed(
    bot: Bot,
    advertiser_telegram_id: int,
    placement_id: int,
    channel_name: str,
) -> None:
    """Рекламодателю: кампания завершена."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Оставить отзыв", callback_data=f"review:create:{placement_id}")
    builder.button(text="📊 Статистика", callback_data="main:analytics")
    builder.button(text="📣 Создать ещё", callback_data="main:create_campaign")
    builder.adjust(1)
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=advertiser_telegram_id,
            text=(
                f"✅ *Кампания завершена!*\n\n"
                f"📺 @{channel_name}\n"
                f"Размещение #{placement_id} успешно завершено.\n\n"
                f"Оставьте отзыв о сотрудничестве!"
            ),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )


async def notify_owner_post_published(
    bot: Bot,
    owner_telegram_id: int,
    request_id: int,
    channel_name: str,
) -> None:
    """Владельцу: реклама опубликована в его канале."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Детали заявки", callback_data=f"own:request:{request_id}")
    builder.adjust(1)
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=owner_telegram_id,
            text=(
                f"📢 *Реклама опубликована в вашем канале!*\n\n"
                f"📺 @{channel_name}\n"
                f"Заявка #{request_id} успешно размещена."
            ),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )


async def notify_owner_post_completed(
    bot: Bot,
    owner_telegram_id: int,
    earned_rub: Decimal,
    channel_name: str,
) -> None:
    """Владельцу: оплата поступила на баланс."""
    builder = InlineKeyboardBuilder()
    builder.button(text="💸 Запросить вывод", callback_data="payout:request_start")
    builder.button(text="📊 Статистика", callback_data="main:owner_analytics")
    builder.adjust(1)
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=owner_telegram_id,
            text=(
                f"💰 *Оплата поступила!*\n\n"
                f"📺 @{channel_name}\n"
                f"На ваш баланс зачислено *{earned_rub:.0f} ₽*."
            ),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )


async def notify_owner_payout_done(
    bot: Bot,
    owner_telegram_id: int,
    net_amount: Decimal,
) -> None:
    """Владельцу: выплата обработана."""
    builder = InlineKeyboardBuilder()
    builder.button(text="✉️ Поддержка", callback_data="main:feedback")
    builder.adjust(1)
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=owner_telegram_id,
            text=(
                f"✅ *Выплата обработана!*\n\n"
                f"На ваши реквизиты переведено *{net_amount:.2f} ₽*.\n"
                f"Срок зачисления: до 24 часов."
            ),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )


async def notify_admin_new_payout(
    bot: Bot,
    admin_telegram_ids: list[int],
    payout_id: int,
    owner_telegram_id: int,
    gross_amount: Decimal,
    net_amount: Decimal,
    requisites: str,
) -> None:
    """Администраторам: новая заявка на выплату."""
    for admin_id in admin_telegram_ids:
        with contextlib.suppress(Exception):
            await bot.send_message(
                chat_id=admin_id,
                text=(
                    f"💰 *Новая заявка на выплату #{payout_id}*\n\n"
                    f"Владелец: {owner_telegram_id}\n"
                    f"Сумма: {gross_amount:.2f} ₽\n"
                    f"К выплате: {net_amount:.2f} ₽\n"
                    f"Реквизиты: {requisites}"
                ),
                parse_mode="Markdown",
            )


async def notify_admin_new_dispute(
    bot: Bot,
    admin_telegram_id: int,
    dispute_id: int,
    placement_id: int,
) -> None:
    """Администратору: открыт новый спор."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔎 Рассмотреть спор", callback_data=f"admin:dispute:{dispute_id}")
    builder.adjust(1)
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=admin_telegram_id,
            text=(f"⚠️ *Новый спор #{dispute_id}*\n\nРазмещение #{placement_id} оспорено."),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )


async def notify_dispute_opened_advertiser(
    bot: Bot,
    advertiser_telegram_id: int,
    dispute_id: int,
) -> None:
    """Рекламодателю: открыт спор."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Детали спора", callback_data=f"dispute:detail:{dispute_id}")
    builder.button(text="💬 Написать администратору", callback_data="main:feedback")
    builder.adjust(1)
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=advertiser_telegram_id,
            text=(
                f"⚠️ *Спор #{dispute_id} открыт*\n\nВаша жалоба принята и передана администратору."
            ),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )


async def notify_dispute_opened_owner(
    bot: Bot,
    owner_telegram_id: int,
    dispute_id: int,
) -> None:
    """Владельцу: открыт спор по его каналу."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📝 Объяснить ситуацию", callback_data=f"dispute:owner_explain:{dispute_id}"
    )
    builder.button(text="📋 Детали спора", callback_data=f"dispute:detail:{dispute_id}")
    builder.adjust(1)
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=owner_telegram_id,
            text=(
                f"⚠️ *По вашему каналу открыт спор #{dispute_id}*\n\n"
                f"Рекламодатель подал жалобу. Пожалуйста, объясните ситуацию."
            ),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )


async def notify_dispute_resolved(
    bot: Bot,
    telegram_id: int,
    dispute_id: int,
    resolution: str,
) -> None:
    """Уведомить сторону о разрешении спора."""
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 В кабинет", callback_data="main:cabinet")
    builder.adjust(1)
    with contextlib.suppress(Exception):
        await bot.send_message(
            chat_id=telegram_id,
            text=(f"✅ *Спор #{dispute_id} разрешён*\n\n{resolution}"),
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )


# ---------------------------------------------------------------------------
# Backward-compat aliases used by existing callers
# ---------------------------------------------------------------------------


async def notify_placement_new(
    bot: Bot,
    owner_telegram_id: int,
    request_id: int,
    kb=None,  # legacy callers pass their own keyboard — ignored, we build ours
) -> None:
    """Alias → notify_owner_new_request (backward compat)."""
    await notify_owner_new_request(bot, owner_telegram_id, request_id)


async def notify_payment_received(
    bot: Bot,
    owner_telegram_id: int,
    earned_rub: Decimal | float,
    channel_name: str = "",
) -> None:
    """Alias → notify_owner_post_completed (backward compat)."""
    await notify_owner_post_completed(
        bot, owner_telegram_id, Decimal(str(earned_rub)), channel_name
    )


# ---------------------------------------------------------------------------
# Feedback notifications
# ---------------------------------------------------------------------------


async def notify_new_request(placement, _advertiser, owner, channel_name: str) -> None:
    """Wrapper: уведомить владельца о новой заявке."""
    from src.bot.main import bot

    if bot is None:
        return

    await notify_owner_new_request(
        bot, owner.telegram_id, placement.id, placement=placement, channel_title=channel_name
    )


async def notify_owner_accepted(placement, _advertiser, channel_name: str) -> None:
    """Wrapper: уведомить рекламодателя о принятии заявки."""
    from src.bot.main import bot

    if bot is None:
        return

    await notify_advertiser_accepted(
        bot,
        _advertiser.telegram_id,
        placement.id,
        channel_name,
        str(
            placement.publication_format.value
            if hasattr(placement.publication_format, "value")
            else placement.publication_format
        ),
        placement.final_price or placement.proposed_price,
        str(placement.final_schedule or placement.proposed_schedule or ""),
    )


async def notify_counter_offer(placement, advertiser, channel_name: str) -> None:
    """Wrapper: уведомить рекламодателя о контр-предложении."""
    from src.bot.main import bot

    if bot is None:
        return

    await notify_advertiser_counter(
        bot,
        advertiser.telegram_id,
        placement.id,
        channel_name,
        placement.counter_price,
        str(placement.counter_schedule or ""),
        placement.counter_offer_count,
    )


async def notify_counter_accepted(placement, _advertiser, _owner, channel_name: str) -> None:
    """Wrapper: уведомить рекламодателя о принятии контр-предложения."""
    from src.bot.main import bot

    if bot is None:
        return

    await notify_advertiser_accepted(
        bot,
        _advertiser.telegram_id,
        placement.id,
        channel_name,
        str(
            placement.publication_format.value
            if hasattr(placement.publication_format, "value")
            else placement.publication_format
        ),
        placement.final_price or placement.proposed_price,
        str(placement.final_schedule or ""),
    )


async def notify_advertiser_counter_reply(placement, owner, channel_name: str) -> None:
    """FIX #20: Notify owner about advertiser's counter-reply."""
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from src.bot.main import bot

    if bot is None:
        return

    price = placement.advertiser_counter_price or placement.proposed_price
    comment = placement.advertiser_counter_comment

    builder = InlineKeyboardBuilder()
    builder.button(text="👀 Посмотреть", callback_data=f"own:request:{placement.id}")
    builder.adjust(1)

    text = (
        f"✏️ *Рекламодатель предложил встречную цену!*\n\n"
        f"📺 Канал: {channel_name}\n"
        f"💰 Ваша цена: {placement.counter_price or '—'} ₽\n"
        f"💵 Цена рекламодателя: *{price:.0f} ₽*\n"
        f"📅 Раунд: {placement.counter_offer_count}/3\n"
    )
    if comment:
        text += f"💬 Комментарий: {comment}\n"

    try:
        await bot.send_message(
            chat_id=owner.telegram_id,
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )
    except Exception as e:
        from src.bot.handlers.shared.notifications import logger

        logger.warning("notify_advertiser_counter_reply failed: %s", e)


async def notify_rejected(placement, advertiser, channel_name: str) -> None:
    """Wrapper: уведомить рекламодателя об отклонении заявки."""
    from src.bot.main import bot

    if bot is None:
        return

    await notify_advertiser_rejected(bot, advertiser.telegram_id, placement.id, channel_name)


async def notify_cancelled(
    placement, _advertiser, _owner, channel_name: str, _reputation_delta=None
) -> None:
    """Wrapper: уведомить рекламодателя об отмене заявки."""
    from src.bot.main import bot

    if bot is None:
        return

    await notify_advertiser_rejected(bot, _advertiser.telegram_id, placement.id, channel_name)


async def notify_sla_expired(placement, _advertiser, owner, channel_name: str) -> None:
    """Wrapper: уведомить при истечении SLA."""
    from src.bot.main import bot

    if bot is None:
        return

    await notify_owner_new_request(
        bot, owner.telegram_id, placement.id, placement=placement, channel_title=channel_name
    )


def format_yookassa_payment_success(
    amount_rub: float | Decimal,
    new_balance: float | Decimal,
) -> str:
    """Форматировать сообщение об успешном платеже ЮKassa."""
    return (
        f"✅ <b>Оплата получена!</b>\n\n"
        f"💳 Сумма: <b>{amount_rub:.2f} ₽</b>\n"
        f"💰 Баланс: <b>{new_balance:.2f} ₽</b>\n\n"
        f"Спасибо за пополнение!"
    )


async def notify_admins_new_feedback(
    bot: Bot,
    feedback_id: int,
    user_id: int,
    text: str,
) -> None:
    """Notify all admins about new feedback."""
    from src.config.settings import settings

    message = (
        f"📬 <b>Новый feedback #</b>{feedback_id}\n\n"
        f"👤 User ID: <code>{user_id}</code>\n\n"
        f"📝 <b>Текст:</b>\n"
        f"{text[:500]}{'...' if len(text) > 500 else ''}\n\n"
        f"/admin/feedback — просмотр"
    )

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                message,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id} about feedback {feedback_id}: {e}")
