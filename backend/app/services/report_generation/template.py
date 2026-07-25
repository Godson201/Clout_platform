from app.services.report_generation.base import ReportData


class TemplateNarrativeGenerator:
    """Always available, needs no API key, and can never fabricate a number —
    every figure it writes is interpolated directly from `data`, not generated.
    This is both the test-suite default and the production fallback whenever
    the Anthropic generator's output fails validation (see campaign_reports.py).
    """

    async def generate(self, data: ReportData) -> str:
        analytics = data.analytics
        platforms_str = ", ".join(p.title() for p in data.platforms) if data.platforms else "no platforms"

        lines = [
            f"This campaign for {data.brand_name} targeted {data.target_views:,} views per platform "
            f"across {platforms_str}, with a {data.performance_window_days}-day performance window per slot.",
            f"So far it has delivered {analytics.total_verified_views:,} verified views against a total "
            f"target of {analytics.total_target_views:,} ({analytics.progress_pct}% of target), with "
            f"{analytics.total_engagement:,} combined likes, comments, and shares tracked.",
        ]

        if analytics.top_platform:
            lines.append(f"{analytics.top_platform.title()} was the strongest-performing platform by views.")
        if analytics.top_influencer_username:
            lines.append(f"@{analytics.top_influencer_username} was the top-performing influencer by views.")

        summary = data.comment_summary
        if summary.total_comments > 0:
            sentiment_note = (
                f", averaging a sentiment score of {summary.average_sentiment_score}"
                if summary.average_sentiment_score is not None
                else ""
            )
            lines.append(f"{summary.total_comments} comments were tracked and analyzed{sentiment_note}.")

            question_count = summary.category_counts.get("question", 0)
            complaint_count = summary.category_counts.get("complaint", 0)
            if question_count:
                lines.append(f"{question_count} asked a question worth a reply.")
            if complaint_count:
                lines.append(f"{complaint_count} raised a complaint worth reviewing.")
        else:
            lines.append("No comments have been tracked for this campaign yet.")

        return " ".join(lines)
