"""LegalProfileRepo for LegalProfile model operations."""

from sqlalchemy import select, update

from src.db.models.legal_profile import LegalProfile
from src.db.repositories.base import BaseRepository

_SCAN_FIELDS = frozenset({
    "inn_scan_file_id",
    "passport_scan_file_id",
    "self_employed_cert_file_id",
    "company_doc_file_id",
})


class LegalProfileRepo(BaseRepository[LegalProfile]):
    """Репозиторий для работы с юридическими профилями пользователей."""

    model = LegalProfile

    async def get_by_user_id(self, user_id: int) -> LegalProfile | None:
        """Получить профиль по user_id."""
        result = await self.session.execute(
            select(LegalProfile).where(LegalProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: int, **kwargs: object) -> LegalProfile:  # type: ignore[override]
        """Создать новый юридический профиль."""
        profile = LegalProfile(user_id=user_id, **kwargs)
        self.session.add(profile)
        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def update(self, user_id: int, **kwargs: object) -> LegalProfile:  # type: ignore[override]
        """Обновить юридический профиль по user_id."""
        profile = await self.get_by_user_id(user_id)
        if profile is None:
            raise ValueError(f"LegalProfile for user_id={user_id} not found")
        for key, value in kwargs.items():
            setattr(profile, key, value)
        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def update_scan(self, user_id: int, scan_field: str, file_id: str) -> None:
        """Обновить файл скана (inn_scan_file_id, passport_scan_file_id, etc.)."""
        if scan_field not in _SCAN_FIELDS:
            raise ValueError(f"Invalid scan_field: {scan_field!r}. Must be one of {_SCAN_FIELDS}")
        await self.session.execute(
            update(LegalProfile)
            .where(LegalProfile.user_id == user_id)
            .values({scan_field: file_id})
        )
        await self.session.flush()
