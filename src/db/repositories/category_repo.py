"""CategoryRepository for Category model operations."""

from sqlalchemy import select

from src.db.models.category import Category
from src.db.repositories.base import BaseRepository


class CategoryRepo(BaseRepository[Category]):
    """Репозиторий для работы с категориями каналов."""

    model = Category

    async def get_all_active(self) -> list[Category]:
        """Получить все активные категории, отсортированные по sort_order."""
        result = await self.session.execute(
            select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order)
        )
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Category | None:
        """Получить категорию по slug."""
        result = await self.session.execute(select(Category).where(Category.slug == slug))
        return result.scalar_one_or_none()

    async def get_active_slugs(self) -> list[str]:
        """Получить список slug всех активных категорий."""
        result = await self.session.execute(
            select(Category.slug).where(Category.is_active.is_(True)).order_by(Category.sort_order)
        )
        return list(result.scalars().all())
