"""
FastAPI роутер статистики базы каналов.

Endpoints:
  GET /api/channels/stats   — публичная статистика (без JWT)
  GET /api/channels/preview — предпросмотр каналов для пользователя (с JWT)
"""

import json
import logging
from datetime import datetime, timedelta

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot

from src.api.dependencies import CurrentUser, get_bot, get_db_session
from src.api.schemas.channel import (
    ChannelCheckRequest,
    ChannelCheckResponse,
    ChannelCreateRequest,
    ChannelResponse,
)
from src.config.settings import settings
from src.constants.tariffs import (
    PREMIUM_SUBSCRIBER_THRESHOLD,
    TARIFF_LABELS,
    TARIFF_MIN_RATING,
    TARIFF_SUBSCRIBER_LIMITS,
    TARIFF_TOPICS,
)
from src.db.models.telegram_chat import TelegramChat
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(tags=["channels"])

CACHE_KEY = "channels:stats:v1"
CACHE_TTL = 3600  # 1 час


# ─── Мой канал ──────────────────────────────────────────────────────


@router.get("/", response_model=None)
async def get_my_channels(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> list[TelegramChat]:
    """
    Получить мои каналы.

    Args:
        current_user: Текущий пользователь
        session: DB session

    Returns:
        list[TelegramChat]: Список каналов пользователя
    """
    result = await session.execute(
        select(TelegramChat).where(TelegramChat.owner_id == current_user.id)
    )
    return list(result.scalars().all())


# ─── Проверка и добавление канала ──────────────────────────────────


@router.post("/check", response_model=ChannelCheckResponse)
async def check_channel(
    body: ChannelCheckRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    bot: Bot = Depends(get_bot),
) -> ChannelCheckResponse:
    """
    Проверить канал перед добавлением.

    Проверяет:
    1. Существует ли канал
    2. Является ли чат каналом (не группа/личка)
    3. Является ли бот администратором канала
    4. Наличие необходимых прав (post, delete, pin)
    5. Не добавлен ли канал уже этим пользователем
    6. Соответствие канала правилам платформы (P3)
    7. Язык канала (P3)
    8. AI классификация тематики (P3, опционально)

    Args:
        body: Запрос с username или chat_id канала
        current_user: Текущий пользователь
        session: DB session
        bot: Telegram Bot экземпляр

    Returns:
        ChannelCheckResponse с результатами проверки

    Raises:
        HTTPException 400: Канал не найден или не соответствует правилам
        HTTPException 403: Бот не является администратором канала
    """
    from telegram import ChatMemberAdministrator

    from src.core.services.channel_service import ChannelService
    from src.utils.telegram.channel_rules_checker import ChannelRulesChecker
    from src.utils.telegram.russian_lang_detector import RussianLangDetector

    # 1. Проверка существования канала (по username или chat_id)
    try:
        if body.chat_id:
            logger.info(f"Checking channel by ID: {body.chat_id}")
            chat = await bot.get_chat(body.chat_id)
        elif body.username:
            # Очищаем username от @ и пробелов, затем добавляем @ для Telegram API
            clean_username = body.username.strip().lstrip('@')
            logger.info(f"Checking channel by username: @{clean_username} (original: {body.username!r})")
            chat = await bot.get_chat(f"@{clean_username}")  # ✅ Добавляем @ для Telegram API
            logger.info(f"Bot API get_chat response: type={type(chat).__name__}, id={chat.id}, username={chat.username}")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Укажите username или chat_id канала",
            )
        logger.info(f"Successfully found chat: {chat.title} (id={chat.id}, type={chat.type})")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Channel not found: {type(e).__name__}: {e} | Input username: {body.username!r}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Канал не найден. Убедитесь, что username/chat_id указан правильно и бот добавлен в канал как администратор. (Debug: {type(e).__name__})",
        ) from e

    # 2. Проверка типа чата (должен быть канал)
    if chat.type != "channel":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"@{body.username} не является каналом (тип: {chat.type})",
        )

    # 3. Проверка прав бота через get_chat_member
    try:
        chat_member = await bot.get_chat_member(chat.id, bot.id)
        logger.info(f"Bot chat_member type: {type(chat_member).__name__}")
        logger.info(f"Bot chat_member status: {chat_member.status}")
        logger.info(f"Is ChatMemberAdministrator: {isinstance(chat_member, ChatMemberAdministrator)}")
    except Exception as e:
        logger.error(f"Cannot get chat member for {body.username}: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Не удалось проверить права бота в канале",
        ) from e

    # 4. Проверка что бот является администратором
    if not isinstance(chat_member, ChatMemberAdministrator):
        logger.error(f"Bot is NOT admin! chat_member type: {type(chat_member).__name__}, status: {chat_member.status}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Бот не является администратором канала",
        )

    # 5. Проверка необходимых прав
    required_permissions = {
        "post_messages": chat_member.can_post_messages,
        "delete_messages": chat_member.can_delete_messages,
        "pin_messages": chat_member.can_pin_messages,
    }

    missing_permissions = [
        perm for perm, has in required_permissions.items() if not has
    ]

    bot_permissions = {
        "is_admin": True,
        **required_permissions,
    }

    # 6. Проверка на дубликат канала
    is_already_added = False
    result = await session.execute(
        select(TelegramChat).where(
            TelegramChat.owner_id == current_user.id,
            TelegramChat.username == body.username.lstrip("@"),
            TelegramChat.is_active.is_(True),
        )
    )
    existing_channel = result.scalar_one_or_none()
    if existing_channel:
        is_already_added = True

    # 7. Проверка правил платформы (P3)
    rules_valid, rules_violations, rules_warnings = await ChannelRulesChecker.check_channel(
        chat,
        is_admin=current_user.is_admin,
    )

    # Если есть нарушения правил — блокируем добавление (кроме админов)
    if not rules_valid and rules_violations and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Канал не соответствует правилам платформы",
                "violations": rules_violations,
            },
        )

    # 8. Проверка языка канала (P3) — предупреждение, не блокирует
    language_valid, language_warnings = RussianLangDetector.check_channel(
        chat.title or "",
        getattr(chat, "description", "") or "",
    )

    # 9. AI классификация тематики (P3) — опционально, не блокирует
    category: str | None = None
    try:
        category = await ChannelService.classify_channel_topic(chat)
    except Exception as e:
        logger.warning(f"AI classification failed: {e}")
        # Не блокируем если AI не сработал

    # Формируем ответ
    channel_info = {
        "id": chat.id,
        "title": chat.title or "Без названия",
        "username": chat.username or body.username,
        "member_count": (await chat.get_member_count() if hasattr(chat, "get_member_count") else 0),
    }

    # valid = права бота в порядке И нет дубликата И правила соблюдены (или админ)
    # Для админов — пропускаем проверки (тестовый режим)
    permissions_ok = len(missing_permissions) == 0 or current_user.is_admin
    rules_ok = rules_valid or current_user.is_admin
    valid = permissions_ok and not is_already_added and rules_ok

    return ChannelCheckResponse(
        valid=valid,
        channel=channel_info,
        bot_permissions=bot_permissions,
        missing_permissions=missing_permissions,
        is_already_added=is_already_added,
        rules_valid=rules_valid,
        rules_violations=rules_violations,
        rules_warnings=rules_warnings,
        language_valid=language_valid,
        language_warnings=language_warnings,
        category=category,
    )


@router.post("/", response_model=ChannelResponse)
async def create_channel(
    body: ChannelCreateRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
    bot: Bot = Depends(get_bot),
) -> ChannelResponse:
    """
    Добавить канал пользователя.

    Args:
        body: Запрос с username канала
        current_user: Текущий пользователь
        session: DB session
        bot: Telegram Bot экземпляр

    Returns:
        ChannelResponse с информацией о канале

    Raises:
        HTTPException 400: Канал не найден или уже добавлен
        HTTPException 403: Бот не является администратором канала
    """
    from telegram import ChatMemberAdministrator

    # 1. Проверка существования канала
    try:
        chat = await bot.get_chat(f"@{body.username}")
    except Exception as e:
        logger.warning(f"Channel not found @{body.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Канал @{body.username} не найден",
        ) from e

    # 2. Проверка типа чата
    if chat.type != "channel":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"@{body.username} не является каналом",
        )

    # 3. Проверка прав бота
    try:
        chat_member = await bot.get_chat_member(chat.id, bot.id)
    except Exception as e:
        logger.warning(f"Cannot get chat member for @{body.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Не удалось проверить права бота",
        ) from e

    if not isinstance(chat_member, ChatMemberAdministrator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Бот не является администратором канала",
        )

    # 4. Проверка на дубликат
    username_clean = body.username.lstrip("@")
    result = await session.execute(
        select(TelegramChat).where(
            TelegramChat.owner_id == current_user.id,
            TelegramChat.username == username_clean,
            TelegramChat.is_active.is_(True),
        )
    )
    existing_channel = result.scalar_one_or_none()
    if existing_channel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот канал уже добавлен",
        )

    # 5. Создаём канал в БД
    from src.db.repositories.telegram_chat_repo import TelegramChatRepository

    repo = TelegramChatRepository(session)

    # Получаем member_count
    member_count = 0
    try:
        member_count = await chat.get_member_count() if hasattr(chat, "get_member_count") else 0
    except Exception:
        logger.warning(f"Cannot get member count for @{body.username}")

    # is_test может быть установлен только админом
    is_test = body.is_test and current_user.is_admin

    new_channel = await repo.create({
        "telegram_id": chat.id,
        "username": username_clean,
        "title": chat.title or "Без названия",
        "owner_id": current_user.id,
        "member_count": member_count,
        "is_test": is_test,
    })
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Конфликт данных: запись уже существует или нарушено ограничение",
        ) from e

    return ChannelResponse(
        id=new_channel.id,
        telegram_id=new_channel.telegram_id,
        username=new_channel.username,
        title=new_channel.title,
        owner_id=new_channel.owner_id,
        member_count=new_channel.member_count,
        last_er=new_channel.last_er,
        avg_views=new_channel.avg_views,
        rating=new_channel.rating,
        category=new_channel.category,
        subcategory=new_channel.subcategory,
        is_active=new_channel.is_active,
    )


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """
    Удалить канал пользователя.

    Args:
        channel_id: ID канала
        current_user: Текущий пользователь
        session: DB session

    Raises:
        HTTPException 404: Канал не найден
        HTTPException 403: Канал принадлежит другому пользователю
    """
    from src.db.models.telegram_chat import TelegramChat
    from src.db.repositories.telegram_chat_repo import TelegramChatRepository

    # Проверка что канал существует и принадлежит пользователю
    channel = await session.get(TelegramChat, channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    if channel.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not channel owner")

    # Удаляем канал (каскадно удалит settings, mediakit, placement_requests)
    repo = TelegramChatRepository(session)
    await repo.delete(channel_id)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Конфликт данных: запись уже существует или нарушено ограничение",
        ) from e


# ─── Схемы ──────────────────────────────────────────────────────


class TariffStatsItem(BaseModel):
    tariff: str
    label: str
    available: int
    percent_of_total: float
    premium_count: int


class TopChannelItem(BaseModel):
    id: int
    title: str
    username: str | None
    subscribers: int


class CategoryStatsItem(BaseModel):
    category: str
    total: int
    available_by_tariff: dict[str, int]
    top_channels: list[TopChannelItem]


class DatabaseStatsResponse(BaseModel):
    total_channels: int
    total_categories: int
    added_last_7d: int
    last_updated: str
    tariff_stats: list[TariffStatsItem]
    categories: list[CategoryStatsItem]


class ChannelPreviewItem(BaseModel):
    id: int
    title: str
    username: str | None
    subscribers: int
    topic: str | None
    rating: float | None
    is_premium: bool
    is_accessible: bool


class ChannelsPreviewResponse(BaseModel):
    total_accessible: int
    total_locked: int
    channels: list[ChannelPreviewItem]


# ─── Хелпер: фильтры по тарифу ──────────────────────────────────


def _tariff_conditions(tariff: str) -> list:
    """
    SQLAlchemy условия фильтрации каналов по тарифу.
    Использует реальные поля TelegramChat: is_active, member_count, rating, topic.
    """
    conds = [TelegramChat.is_active == true()]

    sub_limit = TARIFF_SUBSCRIBER_LIMITS.get(tariff, -1)
    if sub_limit != -1:
        conds.append(TelegramChat.member_count <= sub_limit)

    min_rating = TARIFF_MIN_RATING.get(tariff, 0.0)
    if min_rating > 0:
        conds.append(TelegramChat.rating >= min_rating)

    topics = TARIFF_TOPICS.get(tariff)
    if topics is not None:
        conds.append(TelegramChat.topic.in_(topics))

    # PRO не видит premium каналы
    if tariff == "pro":
        conds.append(TelegramChat.member_count < PREMIUM_SUBSCRIBER_THRESHOLD)

    return conds


# ─── Endpoints ──────────────────────────────────────────────────


@router.get("/stats", response_model=DatabaseStatsResponse)
async def get_channel_stats() -> DatabaseStatsResponse:
    """
    Публичная статистика базы каналов.
    Доступна БЕЗ авторизации.
    Кэшируется в Redis на 1 час (дорогой запрос).
    """
    # ── Redis кэш ────────────────────────────────────────────────
    redis_client = None
    try:
        redis_client = aioredis.from_url(str(settings.redis_url))
        cached = await redis_client.get(CACHE_KEY)
        if cached:
            return DatabaseStatsResponse(**json.loads(cached))
    except Exception as e:
        logger.warning(f"Redis cache read error: {e}")

    # ── Считаем статистику ───────────────────────────────────────
    async with async_session_factory() as session:
        # Всего активных каналов
        total_r = await session.execute(
            select(func.count(TelegramChat.id)).where(TelegramChat.is_active == true())
        )
        total = total_r.scalar() or 0

        # Добавлено за 7 дней
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_r = await session.execute(
            select(func.count(TelegramChat.id)).where(
                TelegramChat.is_active == true(),
                TelegramChat.created_at >= week_ago,
            )
        )
        added_7d = new_r.scalar() or 0

        # Группировка по топику — один запрос вместо N+1
        cat_r = await session.execute(
            select(
                TelegramChat.topic.label("topic"),
                func.count(TelegramChat.id).label("total"),
            )
            .where(TelegramChat.is_active == true())
            .group_by(TelegramChat.topic)
            .order_by(func.count(TelegramChat.id).desc())
        )
        cat_rows = cat_r.all()

        # Категории + топ каналы + доступность по тарифам
        categories: list[CategoryStatsItem] = []
        for row in cat_rows:
            if not row.topic:
                continue

            # Топ-3 канала по подписчикам
            top_r = await session.execute(
                select(
                    TelegramChat.id,
                    TelegramChat.title,
                    TelegramChat.username,
                    TelegramChat.member_count,
                )
                .where(
                    TelegramChat.is_active == true(),
                    TelegramChat.topic == row.topic,
                )
                .order_by(TelegramChat.member_count.desc())
                .limit(3)
            )
            top_channels = [
                TopChannelItem(
                    id=r.id,
                    title=r.title or "Без названия",
                    username=r.username,
                    subscribers=r.member_count or 0,
                )
                for r in top_r.all()
            ]

            # Доступность по каждому тарифу
            available_by_tariff: dict[str, int] = {}
            for tariff in ("free", "starter", "pro", "business"):
                conds = _tariff_conditions(tariff)
                conds.append(TelegramChat.topic == row.topic)
                cnt_r = await session.execute(
                    select(func.count(TelegramChat.id)).where(and_(*conds))
                )
                available_by_tariff[tariff] = cnt_r.scalar() or 0

            categories.append(
                CategoryStatsItem(
                    category=row.topic,
                    total=row.total or 0,
                    available_by_tariff=available_by_tariff,
                    top_channels=top_channels,
                )
            )

        # Статистика по тарифам
        tariff_stats: list[TariffStatsItem] = []
        for tariff in ("free", "starter", "pro", "business"):
            conds = _tariff_conditions(tariff)
            cnt_r = await session.execute(select(func.count(TelegramChat.id)).where(and_(*conds)))
            available = cnt_r.scalar() or 0

            # Premium каналы (>1M) — только для business
            premium_count = 0
            if tariff == "business":
                prem_r = await session.execute(
                    select(func.count(TelegramChat.id)).where(
                        TelegramChat.is_active == true(),
                        TelegramChat.member_count >= PREMIUM_SUBSCRIBER_THRESHOLD,
                    )
                )
                premium_count = prem_r.scalar() or 0

            tariff_stats.append(
                TariffStatsItem(
                    tariff=tariff,
                    label=TARIFF_LABELS[tariff],
                    available=available,
                    percent_of_total=round(available / total * 100, 1) if total > 0 else 0.0,
                    premium_count=premium_count,
                )
            )

    result = DatabaseStatsResponse(
        total_channels=total,
        total_categories=len(categories),
        added_last_7d=added_7d,
        last_updated=datetime.utcnow().isoformat(),
        tariff_stats=tariff_stats,
        categories=categories,
    )

    # ── Записать в Redis ─────────────────────────────────────────
    try:
        if redis_client:
            await redis_client.setex(CACHE_KEY, CACHE_TTL, result.model_dump_json())
    except Exception as e:
        logger.warning(f"Redis cache write error: {e}")
    finally:
        if redis_client:
            await redis_client.close()

    return result


@router.get("/preview", response_model=ChannelsPreviewResponse)
async def get_channels_preview(
    current_user: CurrentUser,
    topic: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> ChannelsPreviewResponse:
    """
    Предпросмотр каналов с учётом тарифа пользователя.
    Требует JWT. Показывает доступные и заблокированные каналы.
    """
    plan_str = (
        current_user.plan.value if hasattr(current_user.plan, "value") else str(current_user.plan)
    )

    async with async_session_factory() as session:
        # Все каналы по фильтру
        base_conds = [TelegramChat.is_active == true()]
        if topic:
            base_conds.append(TelegramChat.topic == topic)

        all_r = await session.execute(
            select(
                TelegramChat.id,
                TelegramChat.title,
                TelegramChat.username,
                TelegramChat.member_count,
                TelegramChat.topic,
                TelegramChat.rating,
            )
            .where(and_(*base_conds))
            .order_by(TelegramChat.member_count.desc())
            .limit(limit)
        )
        all_rows = all_r.all()

        # ID каналов доступных пользователю
        user_conds = _tariff_conditions(plan_str)
        if topic:
            user_conds.append(TelegramChat.topic == topic)

        acc_r = await session.execute(select(TelegramChat.id).where(and_(*user_conds)))
        accessible_ids = {r.id for r in acc_r.all()}

    channels = [
        ChannelPreviewItem(
            id=row.id,
            title=row.title or "Без названия",
            username=row.username,
            subscribers=row.member_count or 0,
            topic=row.topic,
            rating=row.rating,
            is_premium=(row.member_count or 0) >= PREMIUM_SUBSCRIBER_THRESHOLD,
            is_accessible=row.id in accessible_ids,
        )
        for row in all_rows
    ]

    accessible = sum(1 for c in channels if c.is_accessible)
    return ChannelsPreviewResponse(
        total_accessible=accessible,
        total_locked=len(channels) - accessible,
        channels=channels,
    )


# ─── Endpoint для подкатегорий ──────────────────────────────────


@router.get("/subcategories/{parent_topic}")
async def get_subcategory_stats(parent_topic: str) -> dict:
    """
    Детальная статистика по подкатегориям внутри топика.
    Например: GET /api/channels/subcategories/it
    """
    from fastapi import HTTPException

    from src.utils.categories import SUBCATEGORIES

    subcats = SUBCATEGORIES.get(parent_topic)
    if not subcats:
        raise HTTPException(status_code=404, detail=f"Topic '{parent_topic}' not found")

    async with async_session_factory() as session:
        result = await session.execute(
            select(
                TelegramChat.subcategory.label("subcat"),
                func.count(TelegramChat.id).label("total"),
                func.max(TelegramChat.member_count).label("max_subs"),
                func.avg(TelegramChat.member_count).label("avg_subs"),
            )
            .where(
                TelegramChat.is_active == true(),  # noqa: E712
                TelegramChat.topic == parent_topic,
                TelegramChat.subcategory.in_(list(subcats.keys())),
            )
            .group_by(TelegramChat.subcategory)
            .order_by(func.count(TelegramChat.id).desc())
        )
        rows = result.all()

    return {
        "topic": parent_topic,
        "subcategories": [
            {
                "code": row.subcat,
                "name": subcats.get(row.subcat, row.subcat),
                "total": row.total,
                "max_subscribers": row.max_subs or 0,
                "avg_subscribers": round(row.avg_subs or 0),
            }
            for row in rows
            if row.subcat
        ],
    }


# ─── Сравнение каналов ──────────────────────────────────────────


class ChannelIdsRequest(BaseModel):
    channel_ids: list[int]


class ComparisonChannelItem(BaseModel):
    id: int
    username: str | None
    title: str | None
    member_count: int
    avg_views: int
    er: float
    post_frequency: float
    price_per_post: float
    price_per_1k_subscribers: float
    is_best: dict[str, bool]


class ComparisonRecommendation(BaseModel):
    channel_id: int
    channel_name: str
    reason: str


class ComparisonResponse(BaseModel):
    channels: list[ComparisonChannelItem]
    best_values: dict[str, float]
    recommendation: ComparisonRecommendation


@router.post("/compare", response_model=ComparisonResponse)
async def compare_channels(
    request: ChannelIdsRequest,
    current_user: CurrentUser,
) -> ComparisonResponse:
    """
    Сравнить 2-5 каналов по метрикам.

    Body: {"channel_ids": [1, 2, 3]}
    """
    from src.core.services.comparison_service import ComparisonService

    if len(request.channel_ids) < 2:
        raise HTTPException(status_code=400, detail="Минимум 2 канала для сравнения")
    if len(request.channel_ids) > 5:
        raise HTTPException(status_code=400, detail="Максимум 5 каналов для сравнения")

    service = ComparisonService()
    channels_data = await service.get_channels_for_comparison(request.channel_ids)

    if len(channels_data) < 2:
        raise HTTPException(status_code=404, detail="Недостаточно каналов найдено")

    result = service.calculate_comparison_metrics(channels_data)
    return ComparisonResponse(**result)  # type: ignore[arg-type]  # dict unpacking to Response model


@router.get("/compare/preview")
async def compare_channels_preview(
    ids: str,  # "1,2,3"
    current_user: CurrentUser,
) -> ComparisonResponse:
    """GET /channels/compare/preview?ids=1,2,3"""
    try:
        channel_ids = [int(x) for x in ids.split(",")]
    except ValueError as err:
        raise HTTPException(400, "Неверный формат ids") from err

    return await compare_channels(
        ChannelIdsRequest(channel_ids=channel_ids),
        current_user,
    )
