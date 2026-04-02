"""FastAPI роутер для AI-функций: генерация рекламных текстов."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import CurrentUser, get_db_session
from src.db.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai"])


class GenerateAdTextRequest(BaseModel):
    category: str = Field(default="", description="Тематика канала")
    channel_names: list[str] = Field(default_factory=list, description="Usernames каналов")
    description: str = Field(..., min_length=5, description="Описание продукта/услуги")
    max_length: int = Field(default=600, ge=100, le=1000)


class GenerateAdTextResponse(BaseModel):
    variants: list[str]


@router.post(
    "/generate-ad-text",
    responses={
        404: {"description": "Not found"},
        502: {"description": "Bad Gateway"},
        503: {"description": "Service Unavailable"},
    },
)
async def generate_ad_text(
    body: GenerateAdTextRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GenerateAdTextResponse:
    """Сгенерировать 3 варианта рекламного текста через Mistral AI."""
    # Проверка лимитов по тарифу
    user: User | None = await session.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    from src.config.settings import settings as app_settings

    if not app_settings.mistral_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI-генерация временно недоступна",
        )

    try:
        from src.core.services.mistral_ai_service import MistralAIService

        ai = MistralAIService()
        topic = body.category or None
        variants = await ai.generate_ab_variants(
            description=body.description,
            count=3,
            topic=topic,
        )
        return GenerateAdTextResponse(variants=variants)
    except RuntimeError as e:
        logger.error(f"AI generation error for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Ошибка генерации текста. Попробуйте позже.",
        ) from e
