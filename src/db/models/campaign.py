"""Campaign model alias for v4.2 compatibility.

In v4.2, Campaign model was replaced with PlacementRequest.
This file provides backward compatibility for legacy code.

Usage:
    from src.db.models.campaign import Campaign, CampaignStatus

Maps to:
    Campaign → PlacementRequest
    CampaignStatus → PlacementStatus
"""

from src.db.models.placement_request import PlacementRequest as Campaign
from src.db.models.placement_request import PlacementStatus as CampaignStatus

__all__ = ["Campaign", "CampaignStatus"]
