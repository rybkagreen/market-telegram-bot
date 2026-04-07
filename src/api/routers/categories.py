"""
Роутер для получения списка категорий каналов.
Публичный эндпоинт — не требует авторизации.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db_session
from src.db.repositories.category_repo import CategoryRepo

logger = logging.getLogger(__name__)

router = APIRouter(tags=["categories"])


class CategoryResponse(BaseModel):
    key: str
    name: str
    emoji: str


@router.get("/")
async def get_categories(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CategoryResponse]:
    """Вернуть все активные категории платформы."""
    repo = CategoryRepo(session)
    categories = await repo.get_all_active()
    return [CategoryResponse(key=cat.slug, name=cat.name_ru, emoji=cat.emoji) for cat in categories]


@router.get(
    "/{slug}",
    responses={404: {"description": "Not found"}},
)
async def get_category(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CategoryResponse:
    """Вернуть категорию по slug."""
    repo = CategoryRepo(session)
    category = await repo.get_by_slug(slug)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Category '{slug}' not found"
        )
    return CategoryResponse(key=category.slug, name=category.name_ru, emoji=category.emoji)
