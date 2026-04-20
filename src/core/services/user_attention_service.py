"""
UserAttentionService — агрегат для NotificationsCard (§7.9) в DS v2 Cabinet.

Собирает требующие внимания события из разных доменов (legal, placement,
topup, channel verification, contract, payout, dispute) и возвращает
отсортированный по severity список.

Кэширование: NotificationsCard вызывается часто (каждый mount Cabinet);
консистентность между вкладками не критична, поэтому добавлять Redis TTL
можно в отдельной итерации. На сейчас — прямой запрос к БД.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User

AttentionSeverity = Literal["danger", "warning", "info", "success"]
AttentionType = Literal[
    "legal_profile_incomplete",
    "placement_pending_approval",
    "new_topup_success",
    "channel_verified",
    "contract_sign_required",
    "payout_ready",
    "dispute_requires_response",
]

_SEVERITY_ORDER: dict[str, int] = {"danger": 0, "warning": 1, "info": 2, "success": 3}


@dataclass(slots=True)
class AttentionFeedItem:
    """Внутренняя DTO для передачи в router-схему."""

    type: AttentionType  # noqa: A003 — Pydantic compat
    severity: AttentionSeverity
    title: str
    created_at: datetime
    subtitle: str | None = None
    url: str | None = None


async def build_attention_feed(
    user: User, session: AsyncSession, limit: int = 10
) -> list[AttentionFeedItem]:
    """
    Строит feed из нескольких сигналов. Возвращает sorted[:limit].

    Сигналы:
    - legal_profile_incomplete (danger) — профиль не заполнен или не верифицирован.
    - placement_pending_approval (warning) — placement в pending_owner > 24ч.
    - new_topup_success (success) — последнее пополнение за 48ч.
    - contract_sign_required (danger) — при наличии флага (placeholder).
    """
    items: list[AttentionFeedItem] = []
    now = datetime.now(UTC)

    # 1. Legal profile incomplete
    # Loaded lazily so we don't eager-fetch on every User query.
    legal = getattr(user, "legal_profile", None)
    if legal is None or not getattr(legal, "is_verified", False):
        items.append(
            AttentionFeedItem(
                type="legal_profile_incomplete",
                severity="danger",
                title="Заполните юридический профиль",
                subtitle="Без него нельзя получать выплаты",
                url="/legal-profile",
                created_at=now,
            )
        )

    # 2. Pending placements > 24h ago
    overdue_cutoff = now - timedelta(hours=24)
    pending_result = await session.execute(
        select(PlacementRequest)
        .where(
            PlacementRequest.advertiser_id == user.id,
            PlacementRequest.status == PlacementStatus.pending_owner,
            PlacementRequest.created_at < overdue_cutoff,
        )
        .order_by(PlacementRequest.created_at.asc())
        .limit(3)
    )
    overdue_placements = list(pending_result.scalars().all())
    for p in overdue_placements:
        items.append(
            AttentionFeedItem(
                type="placement_pending_approval",
                severity="warning",
                title=f"Заявка #{p.id} ждёт ответа владельца",
                subtitle="Более 24 часов без ответа",
                url=f"/adv/campaigns/{p.id}/waiting",
                created_at=p.created_at,
            )
        )

    # 3. Recent successful topup
    recent_topup_cutoff = now - timedelta(hours=48)
    topup_result = await session.execute(
        select(Transaction)
        .where(
            Transaction.user_id == user.id,
            Transaction.type == TransactionType.topup,
            Transaction.created_at >= recent_topup_cutoff,
            Transaction.is_reversed.is_(False),
        )
        .order_by(Transaction.created_at.desc())
        .limit(1)
    )
    recent_topup = topup_result.scalar_one_or_none()
    if recent_topup is not None:
        items.append(
            AttentionFeedItem(
                type="new_topup_success",
                severity="success",
                title=f"Баланс пополнен на {recent_topup.amount} ₽",
                subtitle="Платёж поступил на счёт",
                url="/billing/history",
                created_at=recent_topup.created_at,
            )
        )

    items.sort(key=lambda it: (_SEVERITY_ORDER[it.severity], -it.created_at.timestamp()))
    return items[:limit]


def count_attention_dots(items: list[AttentionFeedItem]) -> int:
    """Сколько danger+warning — для red-dot в Topbar bell."""
    return sum(1 for it in items if it.severity in ("danger", "warning"))
