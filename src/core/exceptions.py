"""
Custom exceptions for Market Bot.
Спринт 4 — стандартизация обработки ошибок.
"""


class RekHarborError(Exception):
    """Базовый класс для всех исключений проекта."""

    pass


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


class InsufficientPermissionsError(PermissionError):
    """Недостаточно прав для выполнения операции."""

    pass


class PlanLimitError(PermissionError):
    """Превышен лимит тарифного плана."""

    pass


class EscrowError(RuntimeError):
    """Ошибка работы с эскроу."""

    pass
