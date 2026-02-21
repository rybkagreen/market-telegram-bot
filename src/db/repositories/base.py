"""
Generic Base Repository для SQLAlchemy моделей.
Реализует паттерн Repository с базовыми CRUD операциями.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Базовый репозиторий с универсальными CRUD операциями.

    Usage:
        class UserRepository(BaseRepository[User]):
            model = User

        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(1)
    """

    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализация репозитория.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session

    async def get_by_id(self, id: int) -> T | None:
        """
        Получить запись по ID.

        Args:
            id: Первичный ключ записи.

        Returns:
            Запись или None, если не найдена.
        """
        return await self.session.get(self.model, id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """
        Получить все записи с пагинацией.

        Args:
            limit: Максимальное количество записей.
            offset: Смещение.

        Returns:
            Список записей.
        """
        query = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, attributes: dict[str, Any]) -> T:
        """
        Создать новую запись.

        Args:
            attributes: Атрибуты для создания записи.

        Returns:
            Созданная запись.
        """
        instance = self.model(**attributes)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: int, attributes: dict[str, Any]) -> T | None:
        """
        Обновить запись по ID.

        Args:
            id: Первичный ключ записи.
            attributes: Атрибуты для обновления.

        Returns:
            Обновленная запись или None.
        """
        instance = await self.get_by_id(id)
        if instance is None:
            return None

        for key, value in attributes.items():
            setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: int) -> bool:
        """
        Удалить запись по ID.

        Args:
            id: Первичный ключ записи.

        Returns:
            True если запись удалена, False если не найдена.
        """
        instance = await self.get_by_id(id)
        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def count(self, where: Any = None) -> int:
        """
        Получить количество записей.

        Args:
            where: Условие WHERE (опционально).

        Returns:
            Количество записей.
        """
        query = select(func.count()).select_from(self.model)
        if where is not None:
            query = query.where(where)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def paginate(self, page: int = 1, page_size: int = 20) -> tuple[list[T], int]:
        """
        Получить записи с пагинацией и общим количеством.

        Args:
            page: Номер страницы (1-based).
            page_size: Размер страницы.

        Returns:
            Кортеж (записи, общее количество).
        """
        offset = (page - 1) * page_size
        items = await self.get_all(limit=page_size, offset=offset)
        total = await self.count()
        return items, total

    async def find_one(self, *filters: Any) -> T | None:
        """
        Найти одну запись по фильтрам.

        Args:
            filters: Условия фильтрации.

        Returns:
            Запись или None.
        """
        query = select(self.model)
        for filter_condition in filters:
            query = query.where(filter_condition)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def find_many(
        self,
        *filters: Any,
        limit: int = 100,
        offset: int = 0,
        order_by: Any = None,
    ) -> list[T]:
        """
        Найти несколько записей по фильтрам.

        Args:
            filters: Условия фильтрации.
            limit: Максимальное количество записей.
            offset: Смещение.
            order_by: Сортировка (опционально).

        Returns:
            Список записей.
        """
        query = select(self.model)
        for filter_condition in filters:
            query = query.where(filter_condition)
        if order_by is not None:
            query = query.order_by(order_by)
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def exists(self, *filters: Any) -> bool:
        """
        Проверить существование записи.

        Args:
            filters: Условия фильтрации.

        Returns:
            True если запись существует.
        """
        query = select(1).select_from(self.model)
        for filter_condition in filters:
            query = query.where(filter_condition)
        query = query.limit(1)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def refresh(self, instance: T) -> T:
        """
        Обновить состояние записи из БД.

        Args:
            instance: Экземпляр модели для обновления.

        Returns:
            Обновленный экземпляр.
        """
        await self.session.refresh(instance)
        return instance

    def get_query(self) -> Select[tuple[T]]:
        """
        Получить базовый query для построения сложных запросов.

        Returns:
            SQLAlchemy Select query.
        """
        return select(self.model)
