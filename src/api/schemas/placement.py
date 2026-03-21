"""
Placement request schemas.

Contains Pydantic models for placement request operations:
- Create placement request
- Placement request response
- Placement list response
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.db.models.placement_request import PublicationFormat, PlacementStatus


class PlacementRequestCreate(BaseModel):
    """
    Request to create a placement request.

    Attributes:
        channel_id: ID of the channel
        publication_format: Publication format (post_24h, post_48h, etc.)
        ad_text: Advertisement text
        proposed_price: Proposed price
        proposed_schedule: Proposed schedule (ISO datetime)
        is_test: Test campaign flag (admin only, default False)
        test_label: Custom test label (optional, max 64 chars)
    """

    model_config = ConfigDict(extra='forbid')
    channel_id: int = Field(..., description="ID канала")
    publication_format: PublicationFormat = Field(
        default=PublicationFormat.post_24h,
        description="Формат публикации",
    )
    ad_text: str = Field(..., min_length=1, max_length=5000, description="Текст рекламы")
    proposed_price: str = Field(..., description="Предлагаемая цена")
    proposed_schedule: str | None = Field(
        default=None,
        description="Предлагаемое время публикации (ISO)",
    )
    # Test mode fields (admin only)
    is_test: bool = Field(
        default=False,
        description="Тестовая кампания (без оплаты)",
    )
    test_label: str | None = Field(
        default=None,
        max_length=64,
        description="Пометка теста",
    )


class PlacementRequestResponse(BaseModel):
    """
    Placement request response.

    Attributes:
        id: Placement request ID
        advertiser_id: Advertiser user ID
        owner_id: Channel owner user ID
        channel_id: Channel ID
        status: Placement status
        publication_format: Publication format
        ad_text: Advertisement text
        proposed_price: Proposed price
        final_price: Final price (may be None)
        is_test: Test campaign flag
        test_label: Test label (if any)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: int
    advertiser_id: int
    owner_id: int
    channel_id: int
    status: PlacementStatus
    publication_format: PublicationFormat
    ad_text: str
    proposed_price: str
    final_price: str | None = None
    is_test: bool = False
    test_label: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlacementRequestListResponse(BaseModel):
    """
    Placement request list response.

    Attributes:
        items: List of placement requests
        total: Total count
    """

    items: list[PlacementRequestResponse]
    total: int = 0
