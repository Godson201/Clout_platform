import json

import httpx

from app.core.config import get_settings
from app.services.report_generation.base import ReportData

settings = get_settings()

MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicConfigurationError(RuntimeError):
    pass


def _facts_payload(data: ReportData) -> dict:
    analytics = data.analytics
    return {
        "brand_name": data.brand_name,
        "platforms": data.platforms,
        "target_views_per_platform": data.target_views,
        "performance_window_days": data.performance_window_days,
        "total_target_views": analytics.total_target_views,
        "total_verified_views": analytics.total_verified_views,
        "progress_pct": analytics.progress_pct,
        "total_engagement": analytics.total_engagement,
        "views_by_platform": analytics.views_by_platform,
        "engagement_by_platform": analytics.engagement_by_platform,
        "top_platform": analytics.top_platform,
        "top_influencer_username": analytics.top_influencer_username,
        "slot_status_counts": analytics.slot_status_counts,
        "comment_total": data.comment_summary.total_comments,
        "comment_category_counts": data.comment_summary.category_counts,
        "average_comment_sentiment": data.comment_summary.average_sentiment_score,
    }


class AnthropicNarrativeGenerator:
    """Real Claude-backed narrative generator. Never exercised in this
    codebase's tests — no API key exists in this environment — but every
    number it's allowed to use is fixed in the prompt itself, and its output
    is never trusted directly: campaign_reports.py runs it through
    validate_narrative_numbers and falls back to TemplateNarrativeGenerator on
    any number the prompt's facts don't account for.
    """

    async def generate(self, data: ReportData) -> str:
        if not settings.ANTHROPIC_API_KEY:
            raise AnthropicConfigurationError("ANTHROPIC_API_KEY is not configured — set it to use AI-written reports")

        facts = _facts_payload(data)
        prompt = (
            "You are writing a short, persuasive campaign performance summary for a brand's marketing team. "
            "Use ONLY the verified facts in the JSON below — never state a number, percentage, or statistic "
            "that isn't given here, and never estimate, round unpredictably, or extrapolate beyond them. "
            "Write 2-3 short paragraphs in a confident, factual tone.\n\n"
            f"Verified facts (JSON): {json.dumps(facts)}"
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                MESSAGES_URL,
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": ANTHROPIC_VERSION,
                    "content-type": "application/json",
                },
                json={
                    "model": settings.ANTHROPIC_MODEL,
                    "max_tokens": 600,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            body = resp.json()

        return "".join(block["text"] for block in body.get("content", []) if block.get("type") == "text")
