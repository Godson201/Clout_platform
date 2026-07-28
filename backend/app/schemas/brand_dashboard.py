import uuid
from datetime import date

from pydantic import BaseModel


class DailyViewsRead(BaseModel):
    day: date
    views: int


class TopCampaignRead(BaseModel):
    campaign_id: uuid.UUID
    title: str
    platforms: list[str]
    influencer_avatars: list[str | None]
    total_views: int
    progress_pct: float
    status: str


class BrandDashboardSummaryRead(BaseModel):
    total_campaigns: int
    total_campaigns_mom_pct: float | None
    total_views: int
    total_views_mom_pct: float | None
    total_engagement: int
    total_engagement_mom_pct: float | None
    total_spent: float
    total_spent_mom_pct: float | None
    currency: str
    views_over_time: list[DailyViewsRead]
    views_by_platform: dict[str, int]
    top_campaigns: list[TopCampaignRead]
