import re
from decimal import Decimal, InvalidOperation

from app.services.report_generation.base import ReportData

_NUMBER_RE = re.compile(r"\d[\d,]*\.?\d*")

# Small numbers show up constantly in ordinary prose ("one of the top 3
# platforms", "a handful of comments") without referencing any tracked
# statistic — treating every number under this as automatically benign avoids
# false-positive rejections on harmless phrasing, while every figure that
# actually matters (view counts, percentages, engagement totals) is well above it.
_ALWAYS_ALLOWED = {Decimal(n) for n in range(0, 10)}


def _collect_allowed_numbers(data: ReportData) -> set[Decimal]:
    analytics = data.analytics
    raw_values: list[float | int] = [
        data.target_views,
        data.performance_window_days,
        len(data.platforms),
        analytics.total_target_views,
        analytics.total_verified_views,
        analytics.progress_pct,
        analytics.total_engagement,
        data.comment_summary.total_comments,
    ]
    raw_values += list(analytics.views_by_platform.values())
    raw_values += list(analytics.engagement_by_platform.values())
    raw_values += list(analytics.slot_status_counts.values())
    raw_values += list(data.comment_summary.category_counts.values())
    for perf in analytics.influencer_performance:
        raw_values += [perf.views, perf.likes, perf.comments, perf.shares]
    if data.comment_summary.average_sentiment_score is not None:
        raw_values.append(data.comment_summary.average_sentiment_score)

    allowed: set[Decimal] = set(_ALWAYS_ALLOWED)
    for value in raw_values:
        decimal_value = Decimal(str(value))
        allowed.add(decimal_value)
        allowed.add(decimal_value.quantize(Decimal("1")))  # narratives often round to whole numbers
    return allowed


def validate_narrative_numbers(narrative: str, data: ReportData) -> bool:
    """The guardrail: every number-looking token in an AI-generated narrative
    must trace back to something in `data` — CLOUT's own commitment that "the
    AI should never fabricate metrics." Returns False on the first number that
    can't be explained, which the caller (campaign_reports.py) treats as a hard
    reject, falling back to the template generator rather than showing a brand
    a number nobody can verify.
    """
    allowed = _collect_allowed_numbers(data)

    for match in _NUMBER_RE.findall(narrative):
        try:
            value = Decimal(match.replace(",", ""))
        except InvalidOperation:
            continue
        if value not in allowed:
            return False
    return True
