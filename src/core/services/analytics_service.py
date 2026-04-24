"""AnalyticsService for campaign and user statistics aggregation."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.constants.payments import OWNER_SHARE
from src.core.services.mistral_ai_service import MistralAIService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.transaction import Transaction, TransactionType
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

# ─── Constants for unified AI insights ──────────────────────────
INSIGHTS_CACHE_TTL_SECONDS = 900  # 15 minutes
INSIGHTS_CACHE_VERSION = "v1"
INSIGHTS_MISTRAL_TIMEOUT_SECONDS = 8.0
INSIGHTS_MISTRAL_MAX_TOKENS = 1200

_InsightsRole = Literal["advertiser", "owner"]


@dataclass
class AdvertiserStats:
    """Статистика рекламодателя."""

    total_placements: int
    completed_placements: int
    total_spent: Decimal
    total_reach: int
    total_clicks: int
    avg_ctr: float


@dataclass
class OwnerStats:
    """Статистика владельца канала."""

    total_published: int
    total_earned: Decimal
    avg_check: Decimal


@dataclass
class PlatformStats:
    """Статистика платформы."""

    total_users: int
    total_placements: int
    total_revenue: Decimal


class AnalyticsService:
    """Сервис агрегации статистики кампаний и пользователей. Интегрирует AI инсайты."""

    def __init__(self) -> None:
        # Lazily constructed — instantiating Mistral client at service
        # construction time crashes every environment without MISTRAL_API_KEY
        # (tests, CI) and every endpoint that doesn't need AI (e.g. the
        # basic summary/cashflow/activity queries). Build on first .generate().
        self._ai_service: MistralAIService | None = None

    @property
    def ai_service(self) -> MistralAIService:
        if self._ai_service is None:
            self._ai_service = MistralAIService()
        return self._ai_service

    async def get_advertiser_stats(
        self, advertiser_id: int, session: AsyncSession
    ) -> AdvertiserStats:
        """Получить статистику рекламодателя."""
        total_result = await session.execute(
            select(func.count())
            .select_from(PlacementRequest)
            .where(PlacementRequest.advertiser_id == advertiser_id)
        )
        total_placements = total_result.scalar() or 0

        completed_result = await session.execute(
            select(func.count())
            .select_from(PlacementRequest)
            .where(
                PlacementRequest.advertiser_id == advertiser_id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        completed_placements = completed_result.scalar() or 0

        spent_result = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), Decimal("0"))).where(
                Transaction.user_id == advertiser_id,
                Transaction.type == TransactionType.escrow_release,
            )
        )
        total_spent = spent_result.scalar() or Decimal("0")

        reach_result = await session.execute(
            select(
                func.coalesce(func.sum(PlacementRequest.published_reach), 0),
                func.coalesce(func.sum(PlacementRequest.clicks_count), 0),
            ).where(
                PlacementRequest.advertiser_id == advertiser_id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        row = reach_result.one()
        total_reach = row[0] or 0
        total_clicks = row[1] or 0
        avg_ctr = (total_clicks / total_reach * 100) if total_reach > 0 else 0.0

        return AdvertiserStats(
            total_placements=total_placements,
            completed_placements=completed_placements,
            total_spent=total_spent,
            total_reach=total_reach,
            total_clicks=total_clicks,
            avg_ctr=avg_ctr,
        )

    async def get_owner_stats(self, owner_id: int, session: AsyncSession) -> OwnerStats:
        """Получить статистику владельца канала."""
        published_result = await session.execute(
            select(func.count())
            .select_from(PlacementRequest)
            .where(
                PlacementRequest.owner_id == owner_id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        total_published = published_result.scalar() or 0

        earned_result = await session.execute(
            select(
                func.coalesce(func.sum(PlacementRequest.final_price * OWNER_SHARE), Decimal("0"))
            ).where(
                PlacementRequest.owner_id == owner_id,
                PlacementRequest.status == PlacementStatus.published,
                PlacementRequest.final_price.isnot(None),
            )
        )
        total_earned = earned_result.scalar() or Decimal("0")
        avg_check = (total_earned / total_published) if total_published > 0 else Decimal("0")

        return OwnerStats(
            total_published=total_published,
            total_earned=total_earned,
            avg_check=avg_check,
        )

    async def get_top_channels_by_reach(
        self, advertiser_id: int, session: AsyncSession, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Топ каналов по published_reach для рекламодателя."""
        from src.db.models.telegram_chat import TelegramChat

        result = await session.execute(
            select(
                TelegramChat.id,
                TelegramChat.title,
                TelegramChat.username,
                func.sum(PlacementRequest.published_reach).label("total_reach"),
            )
            .join(PlacementRequest, PlacementRequest.channel_id == TelegramChat.id)
            .where(
                PlacementRequest.advertiser_id == advertiser_id,
                PlacementRequest.status == PlacementStatus.published,
                PlacementRequest.published_reach.isnot(None),
            )
            .group_by(TelegramChat.id, TelegramChat.title, TelegramChat.username)
            .order_by(func.sum(PlacementRequest.published_reach).desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            {
                "channel_id": row.id,
                "title": row.title,
                "username": row.username,
                "total_reach": row.total_reach or 0,
            }
            for row in rows
        ]

    async def generate_ai_insights(
        self, stats_dict: dict[str, Any], plan: str, session: AsyncSession
    ) -> dict[str, Any]:
        """Сгенерировать AI инсайты на основе статистики. Доступно только для pro/business."""
        allowed_plans = {"pro", "business"}
        if plan not in allowed_plans:
            return {
                "error": "AI insights available only for Pro and Business plans",
                "recommendations": [],
                "top_channels": [],
                "optimal_time": None,
            }

        prompt = f"Analyze advertising stats: placements={stats_dict.get('total_placements', 0)}, completed={stats_dict.get('completed_placements', 0)}, spent={stats_dict.get('total_spent', 0)}, reach={stats_dict.get('total_reach', 0)}, ctr={stats_dict.get('avg_ctr', 0):.2f}%. Provide 3 recommendations in Russian."

        try:
            response = await self.ai_service.generate(prompt)
            return {
                "recommendations": [response],
                "top_channels": [],
                "optimal_time": 14,
                "ai_analysis": response,
            }
        except Exception as e:
            return {
                "error": str(e),
                "recommendations": ["AI analysis temporarily unavailable"],
                "top_channels": [],
                "optimal_time": 14,
            }

    # ─── Unified AI insights (new /analytics screen) ────────────────

    async def generate_unified_insights(
        self,
        user_id: int,
        role: _InsightsRole,
        session: AsyncSession,
        *,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Produce structured AI/rule-based insights for the unified analytics screen.

        Pipeline:
          1. Redis cache lookup (15 min TTL, per user+role).
          2. Aggregate base stats from existing service methods.
          3. Try Mistral with a strict JSON prompt (8s timeout).
          4. Validate & return, caching on success.
          5. On any Mistral failure → deterministic rule-based fallback
             (still cached, shorter TTL is OK — same key).

        Returns a plain dict matching ``AIInsightsUnifiedResponse`` shape; the
        router wraps it with the Pydantic model.
        """
        cache_key = f"ai_insights:{user_id}:{role}:{INSIGHTS_CACHE_VERSION}"

        if not force_refresh:
            cached = await self._cache_get(cache_key)
            if cached is not None:
                return cached

        payload = await self._aggregate_insights_payload(user_id, role, session)

        mistral_result = await self._try_mistral_insights(role, payload)
        if mistral_result is not None:
            mistral_result["ai_backend"] = "mistral"
            mistral_result["generated_at"] = datetime.now(UTC).isoformat()
            mistral_result["cache_ttl_seconds"] = INSIGHTS_CACHE_TTL_SECONDS
            mistral_result["role"] = role
            await self._cache_set(cache_key, mistral_result, INSIGHTS_CACHE_TTL_SECONDS)
            return mistral_result

        rules_result = self._rules_based_insights(role, payload)
        rules_result["ai_backend"] = "rules"
        rules_result["generated_at"] = datetime.now(UTC).isoformat()
        rules_result["cache_ttl_seconds"] = INSIGHTS_CACHE_TTL_SECONDS
        rules_result["role"] = role
        await self._cache_set(cache_key, rules_result, INSIGHTS_CACHE_TTL_SECONDS)
        return rules_result

    async def _aggregate_insights_payload(
        self, user_id: int, role: _InsightsRole, session: AsyncSession
    ) -> dict[str, Any]:
        """Collect the raw stats needed by both the Mistral prompt and fallback."""
        if role == "advertiser":
            stats = await self.get_advertiser_stats(advertiser_id=user_id, session=session)
            top_channels = await self.get_top_channels_by_reach(
                advertiser_id=user_id, session=session, limit=5
            )
            return {
                "role": role,
                "total_placements": stats.total_placements,
                "completed_placements": stats.completed_placements,
                "total_spent": str(stats.total_spent),
                "total_reach": stats.total_reach,
                "total_clicks": stats.total_clicks,
                "avg_ctr": round(stats.avg_ctr, 2),
                "top_channels": top_channels,
            }

        # owner
        stats_o = await self.get_owner_stats(owner_id=user_id, session=session)
        owner_channels = await self._get_owner_channel_breakdown(user_id, session)
        return {
            "role": role,
            "total_published": stats_o.total_published,
            "total_earned": str(stats_o.total_earned),
            "avg_check": str(stats_o.avg_check),
            "channels": owner_channels,
        }

    async def _get_owner_channel_breakdown(
        self, owner_id: int, session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Publications + earnings per owned channel (up to 10)."""
        from src.db.models.telegram_chat import TelegramChat

        result = await session.execute(
            select(
                TelegramChat.id,
                TelegramChat.title,
                TelegramChat.username,
                TelegramChat.member_count,
                TelegramChat.rating,
                func.count(PlacementRequest.id).label("publications"),
                func.coalesce(
                    func.sum(PlacementRequest.final_price * OWNER_SHARE), Decimal("0")
                ).label("earned"),
            )
            .outerjoin(
                PlacementRequest,
                (PlacementRequest.channel_id == TelegramChat.id)
                & (PlacementRequest.status == PlacementStatus.published),
            )
            .where(TelegramChat.owner_id == owner_id)
            .group_by(
                TelegramChat.id,
                TelegramChat.title,
                TelegramChat.username,
                TelegramChat.member_count,
                TelegramChat.rating,
            )
            .order_by(func.coalesce(func.sum(PlacementRequest.final_price), Decimal("0")).desc())
            .limit(10)
        )
        rows = result.all()
        return [
            {
                "channel_id": row.id,
                "title": row.title,
                "username": row.username,
                "member_count": row.member_count,
                "rating": float(row.rating) if row.rating is not None else 0.0,
                "publications": int(row.publications or 0),
                "earned": str(row.earned or Decimal("0")),
            }
            for row in rows
        ]

    # ─── Mistral path ──────────────────────────────────────────────

    async def _try_mistral_insights(
        self, role: _InsightsRole, payload: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Call Mistral with a JSON-constrained prompt. Return None on any failure."""
        if not _has_mistral_key():
            return None

        system_prompt, user_prompt = _build_insights_prompt(role, payload)

        try:
            raw = await asyncio.wait_for(
                self._call_mistral_json(system_prompt, user_prompt),
                timeout=INSIGHTS_MISTRAL_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            logger.warning(
                "ai_insights: Mistral timeout after %.1fs", INSIGHTS_MISTRAL_TIMEOUT_SECONDS
            )
            return None
        except Exception as exc:
            logger.warning("ai_insights: Mistral call failed: %s", exc)
            return None

        try:
            parsed = json.loads(_strip_json_fence(raw))
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("ai_insights: invalid JSON from Mistral: %s", exc)
            return None

        validated = _sanitize_mistral_payload(parsed)
        if validated is None:
            return None
        return validated

    async def _call_mistral_json(self, system_prompt: str, user_prompt: str) -> str:
        """Call Mistral in JSON-mode via the raw client (bypassing `.generate`)."""
        from src.constants.ai import MISTRAL_MODEL

        response = await asyncio.to_thread(
            self.ai_service.client.chat.complete,
            model=MISTRAL_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=INSIGHTS_MISTRAL_MAX_TOKENS,
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("empty Mistral response")
        return content.strip() if isinstance(content, str) else str(content).strip()

    # ─── Rule-based fallback ───────────────────────────────────────

    def _rules_based_insights(self, role: _InsightsRole, payload: dict[str, Any]) -> dict[str, Any]:
        """Deterministic heuristics that mirror the Mistral output shape."""
        if role == "advertiser":
            return _rules_advertiser(payload)
        return _rules_owner(payload)

    # ─── Redis helpers ─────────────────────────────────────────────

    async def _cache_get(self, key: str) -> dict[str, Any] | None:
        client = await _get_redis()
        if client is None:
            return None
        try:
            raw = await client.get(key)
        except Exception as exc:
            logger.debug("ai_insights: redis get failed: %s", exc)
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def _cache_set(self, key: str, value: dict[str, Any], ttl: int) -> None:
        client = await _get_redis()
        if client is None:
            return
        try:
            await client.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception as exc:
            logger.debug("ai_insights: redis set failed: %s", exc)

    async def get_platform_stats(self, session: AsyncSession) -> PlatformStats:
        """Получить статистику платформы для администратора."""
        from src.db.models.platform_account import PlatformAccount
        from src.db.models.user import User

        users_result = await session.execute(select(func.count()).select_from(User))
        total_users = users_result.scalar() or 0

        placements_result = await session.execute(
            select(func.count()).select_from(PlacementRequest)
        )
        total_placements = placements_result.scalar() or 0

        platform_result = await session.execute(
            select(PlatformAccount.profit_accumulated).where(PlatformAccount.id == 1)
        )
        total_revenue = platform_result.scalar() or Decimal("0")

        return PlatformStats(
            total_users=total_users, total_placements=total_placements, total_revenue=total_revenue
        )

    async def get_public_stats(self) -> PlatformStats:
        """Получить публичную статистику платформы (без сессии)."""
        from decimal import Decimal

        from sqlalchemy import func, select

        from src.db.models.placement_request import PlacementRequest
        from src.db.models.platform_account import PlatformAccount
        from src.db.models.telegram_chat import TelegramChat

        async with async_session_factory() as session:
            try:
                # Total users
                users_result = await session.execute(
                    select(func.count())
                    .select_from(TelegramChat)
                    .where(TelegramChat.is_active.is_(True))
                )
                total_users = users_result.scalar() or 0

                # Total reach (sum of member_count)
                await session.execute(
                    select(func.sum(TelegramChat.member_count)).where(
                        TelegramChat.is_active.is_(True)
                    )
                )

                # Total placements
                placements_result = await session.execute(
                    select(func.count()).select_from(PlacementRequest)
                )
                total_placements = placements_result.scalar() or 0

                # Total revenue
                platform_result = await session.execute(
                    select(PlatformAccount.profit_accumulated).where(PlatformAccount.id == 1)
                )
                total_revenue = platform_result.scalar() or Decimal("0")

                return PlatformStats(
                    total_users=total_users,
                    total_placements=total_placements,
                    total_revenue=total_revenue,
                )
            except Exception:
                # Return default zeros if any error
                return PlatformStats(
                    total_users=0,
                    total_placements=0,
                    total_revenue=Decimal("0"),
                )


# ─── Module-level helpers for unified AI insights ──────────────────

_redis_client: Any = None


def _has_mistral_key() -> bool:
    """Cheap check — true when the configured Mistral key is non-empty."""
    from src.config.settings import settings

    key = getattr(settings, "mistral_api_key", None)
    return bool(key) and isinstance(key, str) and len(key.strip()) > 0


async def _get_redis() -> Any:
    """Lazily-constructed shared Redis client for insights caching.

    Returns None if Redis is unreachable — caching silently degrades.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        from redis.asyncio import from_url

        from src.config.settings import settings

        _redis_client = from_url(str(settings.redis_url), decode_responses=True)
        return _redis_client
    except Exception as exc:
        logger.debug("ai_insights: cannot initialise Redis client: %s", exc)
        return None


def _strip_json_fence(raw: str) -> str:
    """Remove markdown fences (```json ... ```) around a JSON payload."""
    text = raw.strip()
    if text.startswith("```json"):
        text = text[len("```json") :]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


_INSIGHTS_SYSTEM_PROMPT = (
    "Ты — аналитик Telegram-рекламной платформы RekHarbor. "
    "Генерируешь краткие, конкретные инсайты на русском языке. "
    "Отвечаешь СТРОГО валидным JSON без markdown-обёрток, без комментариев. "
    "Каждый action_item даёт конкретный шаг с оцифрованным ожидаемым эффектом, "
    "если это возможно."
)


def _build_insights_prompt(role: _InsightsRole, payload: dict[str, Any]) -> tuple[str, str]:
    """Construct (system, user) prompt pair for the insights JSON call."""
    if role == "advertiser":
        top_channels_lines = [
            f"  - {ch.get('title') or ch.get('username') or '—'}"
            f" (id={ch.get('channel_id')}): охват {ch.get('total_reach', 0)}"
            for ch in payload.get("top_channels", [])
        ] or ["  (каналов нет)"]
        user = (
            "Данные рекламодателя (суммарно за всё время):\n"
            f"- Всего кампаний: {payload.get('total_placements', 0)}"
            f" (завершено {payload.get('completed_placements', 0)})\n"
            f"- Общий охват: {payload.get('total_reach', 0)}\n"
            f"- Кликов: {payload.get('total_clicks', 0)}\n"
            f"- Средний CTR: {payload.get('avg_ctr', 0)}%\n"
            f"- Потрачено: {payload.get('total_spent', '0')} ₽\n"
            "- Топ каналов по охвату:\n" + "\n".join(top_channels_lines) + "\n\n"
            "Ответь JSON-объектом со следующими полями:\n"
            "{\n"
            '  "summary": "1-2 фразы о трендах и что выделяется",\n'
            '  "action_items": [  // 2-3 элемента\n'
            '    {"kind": "reallocate|scale|pause|experiment|optimize",\n'
            '     "title": "короткий заголовок",\n'
            '     "description": "подробнее, что именно сделать",\n'
            '     "impact_estimate": "например +18% ROI или null",\n'
            '     "channel_id": <id или null>,\n'
            '     "cta_type": "create_campaign|open_channel|open_placement|none"}\n'
            "  ],\n"
            '  "forecast": {"period_days": 7, "metric": "reach",'
            ' "expected_value": <число>, "confidence_pct": 0-100},\n'
            '  "anomalies": [  // 0-3 элемента\n'
            '    {"kind": "ctr_drop|ctr_spike|reach_drop|inactive_channel|other",\n'
            '     "channel_id": <id или null>, "severity": "low|medium|high",\n'
            '     "description": "суть аномалии"}\n'
            "  ],\n"
            '  "channel_flags": [  // по одному на каждый из топ-каналов\n'
            '    {"channel_id": <id>, "flag": "hot|warn|idle|neutral",\n'
            '     "reason": "коротко, почему"}\n'
            "  ]\n"
            "}"
        )
        return _INSIGHTS_SYSTEM_PROMPT, user

    # owner
    channels_lines = [
        f"  - {ch.get('title') or ch.get('username') or '—'}"
        f" (id={ch.get('channel_id')}): {ch.get('publications', 0)} публикаций,"
        f" заработано {ch.get('earned', '0')} ₽,"
        f" рейтинг {ch.get('rating', 0)}"
        for ch in payload.get("channels", [])
    ] or ["  (каналов нет)"]
    user = (
        "Данные владельца каналов (суммарно за всё время):\n"
        f"- Всего публикаций: {payload.get('total_published', 0)}\n"
        f"- Заработано: {payload.get('total_earned', '0')} ₽\n"
        f"- Средний чек: {payload.get('avg_check', '0')} ₽\n"
        "- По каналам:\n" + "\n".join(channels_lines) + "\n\n"
        "Ответь JSON-объектом со следующими полями:\n"
        "{\n"
        '  "summary": "1-2 фразы о каналах и что выделяется",\n'
        '  "action_items": [\n'
        '    {"kind": "scale|pause|experiment|optimize|reallocate|other",\n'
        '     "title": "коротко", "description": "что сделать",\n'
        '     "impact_estimate": "например +1500₽/нед или null",\n'
        '     "channel_id": <id или null>,\n'
        '     "cta_type": "open_channel|open_placement|none"}\n'
        "  ],\n"
        '  "forecast": {"period_days": 7, "metric": "earnings",'
        ' "expected_value": <число>, "confidence_pct": 0-100},\n'
        '  "anomalies": [\n'
        '    {"kind": "earnings_drop|inactive_channel|other",\n'
        '     "channel_id": <id или null>, "severity": "low|medium|high",\n'
        '     "description": "суть"}\n'
        "  ],\n"
        '  "channel_flags": [\n'
        '    {"channel_id": <id>, "flag": "hot|warn|idle|neutral",\n'
        '     "reason": "почему"}\n'
        "  ]\n"
        "}"
    )
    return _INSIGHTS_SYSTEM_PROMPT, user


_ALLOWED_ACTION_KINDS = {"reallocate", "pause", "scale", "experiment", "optimize", "other"}
_ALLOWED_CTA = {"create_campaign", "open_channel", "open_placement", "none"}
_ALLOWED_METRICS = {"earnings", "spend", "reach", "ctr"}
_ALLOWED_ANOMALY_KINDS = {
    "ctr_drop",
    "ctr_spike",
    "reach_drop",
    "earnings_drop",
    "inactive_channel",
    "other",
}
_ALLOWED_FLAGS = {"hot", "warn", "idle", "neutral"}
_ALLOWED_SEVERITY = {"low", "medium", "high"}


def _sanitize_mistral_payload(parsed: Any) -> dict[str, Any] | None:
    """Coerce loose LLM output into the strict AIInsightsUnifiedResponse shape.

    Any structural failure returns None → caller falls back to rules.
    """
    if not isinstance(parsed, dict):
        return None

    summary = str(parsed.get("summary", "")).strip()
    if not summary:
        return None

    action_items: list[dict[str, Any]] = []
    for item in parsed.get("action_items", []) or []:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind", "other")
        if kind not in _ALLOWED_ACTION_KINDS:
            kind = "other"
        cta = item.get("cta_type", "none")
        if cta not in _ALLOWED_CTA:
            cta = "none"
        title = str(item.get("title") or "").strip()
        description = str(item.get("description") or "").strip()
        if not title or not description:
            continue
        action_items.append({
            "kind": kind,
            "title": title[:120],
            "description": description[:400],
            "impact_estimate": (
                str(item["impact_estimate"])[:60] if item.get("impact_estimate") else None
            ),
            "channel_id": int(item["channel_id"]) if item.get("channel_id") else None,
            "cta_type": cta,
        })

    forecast_obj: dict[str, Any] | None = None
    forecast_raw = parsed.get("forecast")
    if isinstance(forecast_raw, dict):
        metric = forecast_raw.get("metric")
        if metric in _ALLOWED_METRICS:
            try:
                expected = Decimal(str(forecast_raw.get("expected_value", 0)))
                confidence = max(0, min(100, int(forecast_raw.get("confidence_pct", 50))))
                forecast_obj = {
                    "period_days": int(forecast_raw.get("period_days", 7)),
                    "metric": metric,
                    "expected_value": str(expected),
                    "confidence_pct": confidence,
                }
            except (ValueError, TypeError):
                forecast_obj = None

    anomalies: list[dict[str, Any]] = []
    for anom in parsed.get("anomalies", []) or []:
        if not isinstance(anom, dict):
            continue
        kind = anom.get("kind", "other")
        if kind not in _ALLOWED_ANOMALY_KINDS:
            kind = "other"
        severity = anom.get("severity", "low")
        if severity not in _ALLOWED_SEVERITY:
            severity = "low"
        description = str(anom.get("description") or "").strip()
        if not description:
            continue
        anomalies.append({
            "kind": kind,
            "channel_id": int(anom["channel_id"]) if anom.get("channel_id") else None,
            "severity": severity,
            "description": description[:400],
        })

    channel_flags: list[dict[str, Any]] = []
    for flag_obj in parsed.get("channel_flags", []) or []:
        if not isinstance(flag_obj, dict):
            continue
        flag = flag_obj.get("flag", "neutral")
        if flag not in _ALLOWED_FLAGS:
            flag = "neutral"
        reason = str(flag_obj.get("reason") or "").strip()
        channel_id = flag_obj.get("channel_id")
        if not reason or channel_id is None:
            continue
        try:
            channel_flags.append({
                "channel_id": int(channel_id),
                "flag": flag,
                "reason": reason[:120],
            })
        except (ValueError, TypeError):
            continue

    return {
        "summary": summary[:500],
        "action_items": action_items[:5],
        "forecast": forecast_obj,
        "anomalies": anomalies[:5],
        "channel_flags": channel_flags[:10],
    }


# ─── Rule-based fallback engine ────────────────────────────────────


def _rules_advertiser(payload: dict[str, Any]) -> dict[str, Any]:
    total = int(payload.get("total_placements", 0) or 0)
    completed = int(payload.get("completed_placements", 0) or 0)
    reach = int(payload.get("total_reach", 0) or 0)
    clicks = int(payload.get("total_clicks", 0) or 0)
    ctr = float(payload.get("avg_ctr", 0) or 0)
    spent = Decimal(str(payload.get("total_spent", "0") or "0"))
    top_channels = payload.get("top_channels", []) or []

    if total == 0:
        summary = "Кампаний ещё не было. Запустите первое размещение, чтобы увидеть инсайты."
        action_items = [
            {
                "kind": "experiment",
                "title": "Запустите первую кампанию",
                "description": (
                    "Чтобы получить содержательную аналитику, нужно минимум "
                    "одно размещение. Попробуйте небольшой бюджет в тематическом канале."
                ),
                "impact_estimate": None,
                "channel_id": None,
                "cta_type": "create_campaign",
            }
        ]
    else:
        summary = (
            f"Всего кампаний — {total}, завершено — {completed}, охват "
            f"{reach}, кликов {clicks}, средний CTR {ctr}%."
        )
        action_items = []
        if top_channels:
            best = top_channels[0]
            action_items.append({
                "kind": "scale",
                "title": f"Масштабируйте размещения в «{best.get('title') or best.get('username') or 'канал'}»",
                "description": (
                    f"Канал собрал {best.get('total_reach', 0)} охвата — это ваш лидер. "
                    "Увеличьте долю бюджета в него на 20-30% в следующей итерации."
                ),
                "impact_estimate": "+15–20% охвата",
                "channel_id": best.get("channel_id"),
                "cta_type": "create_campaign",
            })
        if ctr > 0 and ctr < 1.0:
            action_items.append({
                "kind": "optimize",
                "title": "CTR ниже 1% — проверьте креативы",
                "description": (
                    "Средний CTR низкий. Попробуйте переписать заголовок, усилить CTA "
                    "или сгенерировать несколько вариантов через ИИ."
                ),
                "impact_estimate": "+30–60% CTR при удачном варианте",
                "channel_id": None,
                "cta_type": "none",
            })
        if total > 0 and completed / max(total, 1) < 0.5:
            action_items.append({
                "kind": "optimize",
                "title": "Много незавершённых кампаний",
                "description": (
                    "Более половины размещений не дошли до публикации. Проверьте, "
                    "не зависают ли они на модерации владельцем и на оплате."
                ),
                "impact_estimate": None,
                "channel_id": None,
                "cta_type": "none",
            })
        if not action_items:
            action_items.append({
                "kind": "scale",
                "title": "Продолжайте в том же ритме",
                "description": "Метрики в норме — держите текущий бюджетный микс.",
                "impact_estimate": None,
                "channel_id": None,
                "cta_type": "create_campaign",
            })

    forecast = None
    if completed > 0:
        avg_reach_per_placement = reach / completed if completed else 0
        forecast = {
            "period_days": 7,
            "metric": "reach",
            "expected_value": str(int(avg_reach_per_placement * 2)),
            "confidence_pct": 55,
        }

    channel_flags = []
    for idx, ch in enumerate(top_channels):
        if idx == 0 and len(top_channels) > 1:
            flag = "hot"
            reason = "Лидер по охвату"
        elif idx == len(top_channels) - 1 and len(top_channels) > 2:
            flag = "warn"
            reason = "Наименьший вклад среди топа"
        else:
            flag = "neutral"
            reason = "Средние показатели"
        channel_flags.append({
            "channel_id": ch.get("channel_id"),
            "flag": flag,
            "reason": reason,
        })

    anomalies: list[dict[str, Any]] = []
    if spent > 0 and reach == 0:
        anomalies.append({
            "kind": "reach_drop",
            "channel_id": None,
            "severity": "high",
            "description": "Есть расходы, но нулевой охват — проверьте завершение публикаций.",
        })

    return {
        "summary": summary,
        "action_items": action_items[:3],
        "forecast": forecast,
        "anomalies": anomalies,
        "channel_flags": channel_flags,
    }


def _rules_owner(payload: dict[str, Any]) -> dict[str, Any]:
    total_pub = int(payload.get("total_published", 0) or 0)
    total_earned = Decimal(str(payload.get("total_earned", "0") or "0"))
    avg_check = Decimal(str(payload.get("avg_check", "0") or "0"))
    channels = payload.get("channels", []) or []

    if not channels:
        return {
            "summary": "Каналов ещё нет. Добавьте первый канал, чтобы начать зарабатывать.",
            "action_items": [
                {
                    "kind": "experiment",
                    "title": "Добавьте первый канал",
                    "description": "Подключите свой Telegram-канал к платформе, чтобы получать заявки на размещения.",
                    "impact_estimate": None,
                    "channel_id": None,
                    "cta_type": "open_channel",
                }
            ],
            "forecast": None,
            "anomalies": [],
            "channel_flags": [],
        }

    if total_pub == 0:
        summary = f"Подключено {len(channels)} каналов, но публикаций пока не было."
    else:
        summary = f"{total_pub} публикаций, заработано {total_earned} ₽, средний чек {avg_check} ₽."

    action_items: list[dict[str, Any]] = []

    sorted_channels = sorted(
        channels,
        key=lambda c: Decimal(str(c.get("earned", "0") or "0")),
        reverse=True,
    )
    best = sorted_channels[0]
    best_pub = int(best.get("publications", 0) or 0)
    if best_pub > 0:
        action_items.append({
            "kind": "scale",
            "title": f"«{best.get('title') or best.get('username')}» — ваш лидер",
            "description": (
                f"Канал принёс {best.get('earned')} ₽ за {best_pub} публикаций. "
                "Подумайте о повышении цены размещения в этом канале на 10-15%."
            ),
            "impact_estimate": f"+{int(float(best.get('earned', '0') or 0) * 0.12)} ₽/период",
            "channel_id": best.get("channel_id"),
            "cta_type": "open_channel",
        })

    idle_channels = [c for c in channels if int(c.get("publications", 0) or 0) == 0]
    if idle_channels and len(idle_channels) < len(channels):
        first_idle = idle_channels[0]
        action_items.append({
            "kind": "optimize",
            "title": f"«{first_idle.get('title') or first_idle.get('username')}» пока без публикаций",
            "description": (
                "Канал не получает заявок. Проверьте описание, тематику и цену — "
                "возможно, стоит снизить минимальную ставку, чтобы привлечь первых рекламодателей."
            ),
            "impact_estimate": None,
            "channel_id": first_idle.get("channel_id"),
            "cta_type": "open_channel",
        })

    low_rating = [c for c in channels if 0 < float(c.get("rating", 0) or 0) < 4.0]
    if low_rating:
        worst = min(low_rating, key=lambda c: float(c.get("rating", 0) or 0))
        action_items.append({
            "kind": "optimize",
            "title": f"Низкий рейтинг «{worst.get('title') or worst.get('username')}»",
            "description": (
                f"Рейтинг {worst.get('rating')} — ниже среднего. "
                "Пересмотрите контент и регулярность постов, чтобы улучшить позицию."
            ),
            "impact_estimate": None,
            "channel_id": worst.get("channel_id"),
            "cta_type": "open_channel",
        })

    if not action_items:
        action_items.append({
            "kind": "scale",
            "title": "Продолжайте в том же ритме",
            "description": "Каналы работают ровно — держите качество контента и принимайте релевантные заявки.",
            "impact_estimate": None,
            "channel_id": None,
            "cta_type": "none",
        })

    forecast = None
    if total_pub > 0:
        forecast = {
            "period_days": 7,
            "metric": "earnings",
            "expected_value": str(int(float(total_earned) / max(total_pub, 1) * 2)),
            "confidence_pct": 50,
        }

    channel_flags: list[dict[str, Any]] = []
    max_earned = max(
        (Decimal(str(c.get("earned", "0") or "0")) for c in channels),
        default=Decimal("0"),
    )
    for ch in channels:
        pub = int(ch.get("publications", 0) or 0)
        earned = Decimal(str(ch.get("earned", "0") or "0"))
        if max_earned > 0 and earned >= max_earned * Decimal("0.8"):
            flag, reason = "hot", "Топ по доходу"
        elif pub == 0:
            flag, reason = "idle", "Нет публикаций"
        elif float(ch.get("rating", 0) or 0) < 4.0:
            flag, reason = "warn", "Низкий рейтинг"
        else:
            flag, reason = "neutral", "Стабильные показатели"
        channel_flags.append({
            "channel_id": ch.get("channel_id"),
            "flag": flag,
            "reason": reason,
        })

    anomalies: list[dict[str, Any]] = []
    if idle_channels and len(idle_channels) >= max(1, len(channels) // 2):
        anomalies.append({
            "kind": "inactive_channel",
            "channel_id": idle_channels[0].get("channel_id"),
            "severity": "medium",
            "description": (
                f"{len(idle_channels)} из {len(channels)} каналов без публикаций — "
                "проверьте цены и тематическое описание."
            ),
        })

    return {
        "summary": summary,
        "action_items": action_items[:3],
        "forecast": forecast,
        "anomalies": anomalies,
        "channel_flags": channel_flags,
    }
