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
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select, true

from src.api.dependencies import CurrentUser
from src.config.settings import settings
from src.constants.tariffs import (
    PREMIUM_SUBSCRIBER_THRESHOLD,
    TARIFF_LABELS,
    TARIFF_MIN_RATING,
    TARIFF_SUBSCRIBER_LIMITS,
    TARIFF_TOPICS,
)
from src.db.models.analytics import TelegramChat
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/channels", tags=["channels"])

CACHE_KEY = "channels:stats:v1"
CACHE_TTL = 3600  # 1 час


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
