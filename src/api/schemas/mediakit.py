"""Pydantic schemas for advertiser-readable mediakit endpoint (B.5.1)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MediakitAdvertiserResponse(BaseModel):
    """Advertiser-readable mediakit view.

    Excludes internal control fields (is_published flag, owner_user_id, counters).
    Returned only when underlying ChannelMediakit.is_published is True;
    otherwise the route returns 404 (no draft-existence leak).
    """

    description: str | None = None
    audience_description: str | None = None
    logo_file_id: str | None = None
    theme_color: str | None = None
    avg_post_reach: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
