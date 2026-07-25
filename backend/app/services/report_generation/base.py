import uuid
from dataclasses import dataclass
from typing import Protocol

from app.services.campaign_analytics import CampaignAnalytics
from app.services.comment_summary import CommentSentimentSummary


@dataclass(frozen=True)
class ReportData:
    """Every fact a narrative is allowed to reference — assembled entirely from
    already-verified data (Phase 6's CampaignAnalytics, Phase 7's
    CommentSentimentSummary, and campaign metadata). Generators receive this
    and nothing else; there is no path from here to raw database access, which
    is what makes the number-fabrication guardrail (validation.py) able to
    enumerate every number a *correct* narrative could possibly contain.
    """

    campaign_id: uuid.UUID
    brand_name: str
    platforms: list[str]
    target_views: int
    performance_window_days: int
    analytics: CampaignAnalytics
    comment_summary: CommentSentimentSummary


class NarrativeGenerator(Protocol):
    async def generate(self, data: ReportData) -> str: ...
