"""
Pydantic схемы для API операций с каналами.

Схемы используются для:
- Проверки канала перед добавлением (POST /api/channels/check)
- Создания канала (POST /api/channels/)
- Ответов API с информацией о канале
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChannelCheckRequest(BaseModel):
    """
    Запрос на проверку канала перед добавлением.

    Attributes:
        username: Username канала без @ (3-32 символа). Либо chat_id.
        chat_id: ID канала (начинается с -100). Либо username.
    """

    model_config = ConfigDict(extra="forbid")
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
        description="Username канала без @",
        examples=["durov", "tech_channel"],
    )
    chat_id: int | None = Field(
        default=None,
        description="ID канала (начинается с -100)",
        examples=[-1001234567890],
    )


class ChannelCheckResponse(BaseModel):
    """
    Ответ на проверку канала.

    Attributes:
        valid: Канал существует и бот имеет права администратора
        channel: Информация о канале (id, title, username, member_count)
        bot_permissions: Права бота в канале (is_admin, post_messages, delete_messages, pin_messages)
        missing_permissions: Список отсутствующих прав
        is_already_added: Канал уже добавлен этим пользователем
        rules_valid: Канал соответствует правилам платформы
        rules_violations: Список нарушений правил платформы
        language_valid: Канал преимущественно на русском языке
        language_warnings: Предупреждения о языке канала
        category: AI классифицированная категория канала
    """

    valid: bool = Field(..., description="Канал существует и бот имеет права администратора")
    channel: dict[str, Any] = Field(
        default_factory=dict,
        description="Информация о канале",
        examples=[
            {"id": 12345, "title": "Channel Name", "username": "channel", "member_count": 5000}
        ],
    )
    bot_permissions: dict[str, bool | None] = Field(
        default_factory=dict,
        description="Права бота в канале",
        examples=[
            {"is_admin": True, "post_messages": True, "delete_messages": True, "pin_messages": True}
        ],
    )
    missing_permissions: list[str] = Field(
        default_factory=list,
        description="Список отсутствующих прав",
        examples=[["delete_messages", "pin_messages"]],
    )
    is_already_added: bool = Field(
        default=False,
        description="Канал уже добавлен этим пользователем",
    )
    # Новые поля для валидаций (P3)
    rules_valid: bool = Field(
        default=True,
        description="Канал соответствует правилам платформы",
    )
    rules_violations: list[str] = Field(
        default_factory=list,
        description="Список нарушений правил платформы",
    )
    rules_warnings: list[str] = Field(
        default_factory=list,
        description="Предупреждения о правилах платформы (для админов)",
    )
    language_valid: bool = Field(
        default=True,
        description="Канал преимущественно на русском языке",
    )
    language_warnings: list[str] = Field(
        default_factory=list,
        description="Предупреждения о языке канала",
    )
    category: str | None = Field(
        default=None,
        description="AI классифицированная категория канала",
    )

    model_config = {"from_attributes": True}


class ChannelCreateRequest(BaseModel):
    """
    Запрос на создание канала.

    Attributes:
        username: Username канала без @ (3-32 символа)
        is_test: Флаг тестового канала (только для админов, по умолчанию False)
    """

    model_config = ConfigDict(extra="forbid")
    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        description="Username канала без @",
        examples=["durov", "tech_channel"],
    )
    is_test: bool = Field(
        default=False,
        description="Флаг тестового канала (только для админов)",
    )
    category: str | None = Field(None, description="Slug категории из таблицы categories")


class ChannelCategoryUpdateRequest(BaseModel):
    """Запрос на обновление категории канала."""

    category: str = Field(..., description="Slug категории")


class ChannelResponse(BaseModel):
    """
    Ответ с информацией о канале.

    Attributes:
        id: ID канала в БД
        telegram_id: Telegram chat ID
        username: Username канала
        title: Название канала
        owner_id: ID владельца
        member_count: Количество подписчиков
        last_er: ER (Engagement Rate)
        avg_views: Среднее количество просмотров
        rating: Рейтинг канала
        category: Категория канала
        is_active: Активен ли канал
        created_at: Дата создания
    """

    id: int = Field(..., description="ID канала в БД")
    telegram_id: int = Field(..., description="Telegram chat ID")
    username: str = Field(..., description="Username канала")
    title: str = Field(..., description="Название канала")
    owner_id: int = Field(..., description="ID владельца")
    member_count: int = Field(default=0, description="Количество подписчиков")
    last_er: float = Field(default=0.0, description="ER (Engagement Rate)")
    avg_views: int = Field(default=0, description="Среднее количество просмотров")
    rating: float = Field(default=0.0, description="Рейтинг канала")
    category: str | None = Field(None, description="Категория канала")
    is_active: bool = Field(default=True, description="Активен ли канал")
    is_test: bool = Field(default=False, description="Тестовый канал (только для админов)")
    created_at: str = Field(..., description="Дата создания (ISO 8601)")

    model_config = {"from_attributes": True}
