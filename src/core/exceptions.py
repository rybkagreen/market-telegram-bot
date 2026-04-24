"""
Custom exceptions for Market Bot.
Спринт 4 — стандартизация обработки ошибок.
plan-05 (2026-04-21) — типизированная иерархия с http_status / error_code,
которую глобальный handler в src/api/main.py сериализует как
{"error_code": ..., "detail": ..., "error_type": ...}.
"""

from __future__ import annotations

from typing import Any


class RekHarborError(Exception):
    """Base for all domain exceptions surfaced through the public API.

    Subclasses (or class-attr overrides) carry:
      * `http_status` — HTTP code the global handler maps to.
      * `error_code`  — stable machine-readable identifier for the
                        frontend (i18n / branching), independent of the
                        free-form `detail` message.
      * `extra`       — optional dict added to the response under
                        "extra" (e.g. {"payout_id": 42}).
    """

    http_status: int = 500
    error_code: str = "rekharbor_error"

    def __init__(self, message: str = "", *, extra: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.extra: dict[str, Any] = extra or {}


# ══════════════════════════════════════════════════════════════
# HTTP-group bases (plan-05) — choose by intent, not by message text.
# Subclasses inherit http_status / error_code unless they override.
# ══════════════════════════════════════════════════════════════


class NotFoundError(RekHarborError):
    """Resource does not exist."""

    http_status = 404
    error_code = "not_found"


class ConflictError(RekHarborError):
    """Resource is in a state that forbids the requested transition."""

    http_status = 409
    error_code = "conflict"


class ValidationError(RekHarborError):
    """Request payload failed business-level validation (after Pydantic)."""

    http_status = 400
    error_code = "validation_error"


class ForbiddenError(RekHarborError):
    """Caller lacks the required role / ownership for the resource."""

    http_status = 403
    error_code = "forbidden"


# ══════════════════════════════════════════════════════════════
# Existing exceptions — kept for backwards compatibility.
# ══════════════════════════════════════════════════════════════


class InsufficientBalanceError(RekHarborError):
    """Недостаточно средств на балансе."""

    pass


class CampaignNotFoundError(RekHarborError):
    """Кампания не найдена."""

    pass


class PayoutError(RekHarborError):
    """Ошибка выплаты."""

    pass


class ContentFilterError(RekHarborError):
    """Ошибка контент-фильтра."""

    pass


class AIServiceError(RekHarborError):
    """Ошибка AI сервиса."""

    pass


class RateLimitError(RekHarborError):
    """Превышен лимит запросов."""

    pass


class UserNotFoundError(RekHarborError):
    """Пользователь не найден."""

    pass


class ChannelNotFoundError(RekHarborError):
    """Канал не найден."""

    pass


class InvalidStateError(RekHarborError):
    """Некорректное состояние FSM."""

    pass


# ══════════════════════════════════════════════════════════════
# S-02: Новые исключения для финансовой модели v4.2
# ══════════════════════════════════════════════════════════════


class SelfDealingError(ValueError):
    """Попытка разместить рекламу на собственном канале."""

    pass


class VelocityCheckError(PermissionError):
    """Превышен лимит вывода средств (velocity check)."""

    pass


class InsufficientFundsError(RekHarborError):
    """Недостаточно средств для выплаты."""

    pass


class PayoutAPIError(RekHarborError):
    """Ошибка API выплаты."""

    pass


class InsufficientPermissionsError(PermissionError):
    """Недостаточно прав для выполнения операции."""

    pass


class PlanLimitError(PermissionError):
    """Превышен лимит тарифного плана."""

    pass


class EscrowError(RuntimeError):
    """Ошибка работы с эскроу."""

    pass


# ══════════════════════════════════════════════════════════════
# S-07: Publication exceptions
# ══════════════════════════════════════════════════════════════


class BotNotAdminError(InsufficientPermissionsError):
    """Бот не является администратором канала."""

    pass


class PostDeletionError(RuntimeError):
    """Ошибка удаления публикации."""

    pass


# ══════════════════════════════════════════════════════════════
# plan-05 (2026-04-21) — domain-specific subclasses with stable
# error_code values consumed by the web_portal frontend.
# ══════════════════════════════════════════════════════════════


# ── Payouts ────────────────────────────────────────────────
class PayoutNotFoundError(NotFoundError):
    error_code = "payout_not_found"


class PayoutAlreadyFinalizedError(ConflictError):
    error_code = "payout_already_finalized"


# ── Placements ─────────────────────────────────────────────
class PlacementNotFoundError(NotFoundError):
    error_code = "placement_not_found"


class PlacementStatusConflictError(ConflictError):
    """Заявка не в том статусе для запрошенного действия."""

    error_code = "placement_status_conflict"


class PlacementAccessError(ForbiddenError):
    """Caller — не владелец канала / не advertiser заявки."""

    error_code = "placement_access_denied"


class PlacementValidationError(ValidationError):
    """Payload не прошёл бизнес-валидацию (нерелевантная цена,
    пустое reason при reject, и т.п.)."""

    error_code = "placement_validation_error"
