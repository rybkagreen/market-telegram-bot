"""OrdRegistrationRepo for OrdRegistration model operations."""

from sqlalchemy import select

from src.db.models.ord_registration import OrdRegistration
from src.db.repositories.base import BaseRepository


class OrdRegistrationRepo(BaseRepository[OrdRegistration]):
    """Репозиторий для работы с регистрациями ОРД."""

    model = OrdRegistration

    async def get_by_placement(self, placement_request_id: int) -> OrdRegistration | None:
        """Получить регистрацию по placement_request_id."""
        result = await self.session.execute(
            select(OrdRegistration).where(
                OrdRegistration.placement_request_id == placement_request_id
            )
        )
        return result.scalar_one_or_none()

    async def update_status(self, id: int, status: str, **kwargs: object) -> OrdRegistration:
        """Обновить статус регистрации."""
        registration = await self.get_by_id(id)
        if registration is None:
            raise ValueError(f"OrdRegistration id={id} not found")
        registration.status = status
        for key, value in kwargs.items():
            setattr(registration, key, value)
        await self.session.flush()
        await self.session.refresh(registration)
        return registration

    async def get_erid(self, placement_request_id: int) -> str | None:
        """Получить erid для placement_request_id."""
        registration = await self.get_by_placement(placement_request_id)
        return registration.erid if registration else None
