"""
Category Repository для работы с категориями каналов.
Расширяет BaseRepository специфичными методами для TopicCategory.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.category import TopicCategory
from src.db.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[TopicCategory]):
    """
    Репозиторий для работы с категориями.

    Методы:
        get_subcategories: Получить подкатегории для топика
        get_all_topics: Получить все уникальные топики
        get_display_name: Получить отображаемое название
        get_all_active: Получить все активные категории
    """

    model = TopicCategory

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        super().__init__(session)

    async def get_subcategories(self, topic: str) -> list[TopicCategory]:
        """
        Получить подкатегории для указанного топика.

        Args:
            topic: Название топика.

        Returns:
            Список подкатегорий.
        """
        return await self.find_many(
            TopicCategory.topic == topic,
            TopicCategory.is_active == True,  # noqa: E712
            order_by=TopicCategory.sort_order,
        )

    async def get_all_topics(self) -> list[str]:
        """
        Получить все уникальные топики.

        Returns:
            Список уникальных топиков.
        """
        stmt = select(TopicCategory.topic).distinct()
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_display_name(self, topic: str, subcategory: str) -> str | None:
        """
        Получить отображаемое название для пары topic/subcategory.

        Args:
            topic: Название топика.
            subcategory: Название подкатегории.

        Returns:
            Отображаемое название или None.
        """
        category = await self.find_one(
            TopicCategory.topic == topic,
            TopicCategory.subcategory == subcategory,
        )
        return category.display_name_ru if category else None

    async def get_all_active(self) -> list[TopicCategory]:
        """
        Получить все активные категории.

        Returns:
            Список активных категорий.
        """
        return await self.find_many(
            TopicCategory.is_active == True,  # noqa: E712
            order_by=[TopicCategory.topic, TopicCategory.sort_order],
        )

    async def get_categories_dict(self) -> dict[str, dict[str, str]]:
        """
        Получить категории в виде вложенного dict {topic: {subcategory: display_name}}.

        Returns:
            Вложенный словарь.
        """
        categories = await self.get_all_active()
        result: dict[str, dict[str, str]] = {}

        for cat in categories:
            if cat.topic not in result:
                result[cat.topic] = {}
            result[cat.topic][cat.subcategory] = cat.display_name_ru

        return result
