import logging
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.campaign_report import CampaignReport
from app.models.enums import ReportGeneratorMode
from app.services.campaign_analytics import compute_campaign_analytics
from app.services.comment_summary import compute_comment_summary
from app.services.report_generation import get_narrative_generator
from app.services.report_generation.base import ReportData
from app.services.report_generation.template import TemplateNarrativeGenerator
from app.services.report_generation.validation import validate_narrative_numbers

logger = logging.getLogger("clout")
settings = get_settings()


async def generate_campaign_report(db: AsyncSession, *, campaign: Campaign) -> CampaignReport:
    """Assembles ReportData entirely from verified, already-computed sources
    (Phase 6's analytics, Phase 7's comment summary) and asks the configured
    generator for a narrative. If that generator is Anthropic and its output
    contains a number that doesn't trace back to `data` — the fabrication
    guardrail — this falls back to the template generator instead of ever
    persisting an unverifiable narrative. A new row is created on every call
    (never overwritten), same append-only philosophy as the ledger and metric
    snapshots, so a campaign's report history stays intact.
    """
    brand_result = await db.execute(select(Brand).where(Brand.id == campaign.brand_id))
    brand = brand_result.scalar_one()

    analytics = await compute_campaign_analytics(db, campaign_id=campaign.id)
    comment_summary = await compute_comment_summary(db, campaign_id=campaign.id)

    data = ReportData(
        campaign_id=campaign.id,
        brand_name=brand.business_name,
        platforms=list(campaign.platforms),
        target_views=campaign.target_views,
        performance_window_days=campaign.performance_window_days,
        analytics=analytics,
        comment_summary=comment_summary,
    )

    generator = get_narrative_generator()
    mode = ReportGeneratorMode(settings.REPORT_GENERATOR_MODE)
    narrative = await generator.generate(data)

    if mode == ReportGeneratorMode.ANTHROPIC and not validate_narrative_numbers(narrative, data):
        logger.warning(
            "AI-generated report for campaign %s contained an unverifiable number — falling back to template",
            campaign.id,
        )
        narrative = await TemplateNarrativeGenerator().generate(data)
        mode = ReportGeneratorMode.TEMPLATE

    analytics_snapshot = asdict(analytics)
    for perf in analytics_snapshot["influencer_performance"]:
        perf["influencer_id"] = str(perf["influencer_id"])  # uuid.UUID isn't JSON-serializable as-is

    report = CampaignReport(
        campaign_id=campaign.id,
        narrative=narrative,
        data_snapshot={"analytics": analytics_snapshot, "comment_summary": asdict(comment_summary)},
        generator=mode,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report
