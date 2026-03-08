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
