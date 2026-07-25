import uuid
from urllib.parse import parse_qs, urlparse

from app.core.db import AsyncSessionLocal
from app.models.enums import CommentCategory
from app.services.campaign_analytics import compute_campaign_analytics
from app.services.comment_analysis import get_classifier
from app.services.comment_summary import compute_comment_summary
from app.services.report_generation.base import ReportData
from app.services.report_generation.template import TemplateNarrativeGenerator
from app.services.report_generation.validation import validate_narrative_numbers
from tests.factories import fund_and_confirm_campaign, register_brand_with_ready_ad, register_influencer_token
from tests.test_campaigns import _create_draft_campaign


class TestRuleBasedClassifier:
    def test_classifies_question(self):
        result = get_classifier().classify("How much does this cost?")
        assert result.category == CommentCategory.QUESTION

    def test_classifies_suggestion(self):
        result = get_classifier().classify("You should add a discount code for loyal fans")
        assert result.category == CommentCategory.SUGGESTION

    def test_classifies_complaint(self):
        result = get_classifier().classify("This is a scam, I want my money back")
        assert result.category == CommentCategory.COMPLAINT
        assert result.sentiment_label.value == "negative"

    def test_classifies_positive(self):
        result = get_classifier().classify("This is amazing, I love it!!")
        assert result.category == CommentCategory.POSITIVE
        assert result.sentiment_score > 0

    def test_classifies_negative(self):
        result = get_classifier().classify("This product is bad and annoying")
        assert result.category == CommentCategory.NEGATIVE
        assert result.sentiment_score < 0

    def test_classifies_neutral(self):
        result = get_classifier().classify("meh, it's okay I guess")
        assert result.category == CommentCategory.NEUTRAL

    def test_empty_text_is_other(self):
        result = get_classifier().classify("😂😂😂")
        assert result.category == CommentCategory.OTHER

    def test_question_wins_over_positive_words(self):
        # Intent (question) is the more actionable signal than sentiment words
        # that happen to also appear in the same comment.
        result = get_classifier().classify("Is this really the best price you can offer?")
        assert result.category == CommentCategory.QUESTION


async def _published_slot_with_account(
    client, tiny_video_bytes, *, brand_email: str, inf_email: str, inf_username: str, platform: str = "tiktok"
):
    brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email=brand_email)
    create_resp = await _create_draft_campaign(client, brand_token, ad_id, platforms=[platform], slot_count=1)
    campaign_id = create_resp.json()["id"]
    body = await fund_and_confirm_campaign(client, brand_token, campaign_id, phone_number="0788456456")
    slot = body["slots"][0]

    inf_token = await register_influencer_token(client, email=inf_email, username=inf_username)
    await client.post(f"/api/v1/slots/{slot['id']}/claim", headers={"Authorization": f"Bearer {inf_token}"})

    connect_resp = await client.get(f"/api/v1/social-accounts/connect/{platform}", headers={"Authorization": f"Bearer {inf_token}"})
    query = parse_qs(urlparse(connect_resp.json()["authorization_url"]).query)
    callback = await client.post(
        f"/api/v1/social-accounts/callback/{platform}",
        json={"code": query["code"][0], "state": query["state"][0]},
        headers={"Authorization": f"Bearer {inf_token}"},
    )
    account_id = callback.json()["id"]

    post_resp = await client.post(
        f"/api/v1/slots/{slot['id']}/post",
        json={"social_account_id": account_id, "caption": "ai analysis test"},
        headers={"Authorization": f"Bearer {inf_token}"},
    )
    assert post_resp.json()["status"] == "published"

    return brand_token, inf_token, campaign_id, slot


class TestCommentPipeline:
    async def test_polling_comments_classifies_and_stores_them(self, client, tiny_video_bytes):
        _, inf_token, campaign_id, slot = await _published_slot_with_account(
            client, tiny_video_bytes, brand_email="comments-brand@example.com",
            inf_email="comments-inf@example.com", inf_username="commentsinf",
        )

        first_poll = await client.get(
            f"/api/v1/slots/{slot['id']}/post/comments", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert first_poll.status_code == 200
        comments = first_poll.json()
        assert len(comments) == 1
        assert comments[0]["analysis"] is not None
        assert comments[0]["analysis"]["category"] == "question"  # mock's first template

        second_poll = await client.get(
            f"/api/v1/slots/{slot['id']}/post/comments", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert len(second_poll.json()) == 2, "a second poll should reveal one more comment, not duplicate the first"
        assert second_poll.json()[0]["id"] == comments[0]["id"], "the first comment must stay the same across polls"

    async def test_comment_summary_appears_in_campaign_analytics(self, client, tiny_video_bytes):
        brand_token, inf_token, campaign_id, slot = await _published_slot_with_account(
            client, tiny_video_bytes, brand_email="analytics-comments-brand@example.com",
            inf_email="analytics-comments-inf@example.com", inf_username="analyticscommentsinf",
        )
        # Poll enough times to reveal a question, a suggestion, and a complaint
        # from the mock's fixed template pool (indices 0, 2, 5).
        for _ in range(6):
            await client.get(f"/api/v1/slots/{slot['id']}/post/comments", headers={"Authorization": f"Bearer {inf_token}"})

        analytics_resp = await client.get(
            f"/api/v1/campaigns/{campaign_id}/analytics", headers={"Authorization": f"Bearer {brand_token}"}
        )
        summary = analytics_resp.json()["comment_summary"]
        assert summary["total_comments"] == 6
        assert summary["category_counts"]["question"] == 2
        assert summary["category_counts"]["suggestion"] == 1
        assert summary["category_counts"]["complaint"] == 1
        assert summary["average_sentiment_score"] is not None
        assert len(summary["sample_questions"]) == 2


class TestReportGeneration:
    async def test_generates_template_report_with_real_numbers(self, client, tiny_video_bytes):
        brand_token, inf_token, campaign_id, slot = await _published_slot_with_account(
            client, tiny_video_bytes, brand_email="report-brand@example.com",
            inf_email="report-inf@example.com", inf_username="reportinf",
        )
        await client.get(f"/api/v1/slots/{slot['id']}/post/metrics", headers={"Authorization": f"Bearer {inf_token}"})
        await client.get(f"/api/v1/slots/{slot['id']}/post/comments", headers={"Authorization": f"Bearer {inf_token}"})

        report_resp = await client.post(
            f"/api/v1/campaigns/{campaign_id}/report", headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert report_resp.status_code == 201
        report = report_resp.json()
        assert report["generator"] == "template"
        assert "500" in report["narrative"]  # one poll's worth of mock views
        assert "Tiktok" in report["narrative"] or "tiktok" in report["narrative"].lower()

        get_resp = await client.get(
            f"/api/v1/campaigns/{campaign_id}/report", headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert get_resp.json()["id"] == report["id"]

    async def test_getting_report_before_generating_one_returns_404(self, client, tiny_video_bytes):
        brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="noreport-brand@example.com")
        create_resp = await _create_draft_campaign(client, brand_token, ad_id)
        campaign_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/campaigns/{campaign_id}/report", headers={"Authorization": f"Bearer {brand_token}"})
        assert resp.status_code == 404

    async def test_report_generation_falls_back_to_template_when_ai_fabricates_a_number(
        self, client, tiny_video_bytes, monkeypatch
    ):
        import app.services.campaign_reports as campaign_reports_module

        class _FabricatingGenerator:
            async def generate(self, data):
                return "This campaign was a massive success with 50000000 views recorded across all platforms!"

        monkeypatch.setattr(campaign_reports_module.settings, "REPORT_GENERATOR_MODE", "anthropic")
        monkeypatch.setattr(campaign_reports_module, "get_narrative_generator", lambda: _FabricatingGenerator())

        brand_token, inf_token, campaign_id, slot = await _published_slot_with_account(
            client, tiny_video_bytes, brand_email="fabricate-brand@example.com",
            inf_email="fabricate-inf@example.com", inf_username="fabricateinf",
        )

        report_resp = await client.post(
            f"/api/v1/campaigns/{campaign_id}/report", headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert report_resp.status_code == 201
        report = report_resp.json()
        assert report["generator"] == "template", "an unverifiable AI number must force a fallback to the template"
        assert "50000000" not in report["narrative"]


class TestNarrativeValidationGuardrail:
    async def test_template_output_always_passes_validation(self, client, tiny_video_bytes):
        brand_token, inf_token, campaign_id, slot = await _published_slot_with_account(
            client, tiny_video_bytes, brand_email="validate-brand@example.com",
            inf_email="validate-inf@example.com", inf_username="validateinf",
        )
        await client.get(f"/api/v1/slots/{slot['id']}/post/metrics", headers={"Authorization": f"Bearer {inf_token}"})

        async with AsyncSessionLocal() as db:
            analytics = await compute_campaign_analytics(db, campaign_id=uuid.UUID(campaign_id))
            comment_summary = await compute_comment_summary(db, campaign_id=uuid.UUID(campaign_id))

        data = ReportData(
            campaign_id=uuid.UUID(campaign_id),
            brand_name="Test Brand",
            platforms=["tiktok"],
            target_views=10_000,
            performance_window_days=3,
            analytics=analytics,
            comment_summary=comment_summary,
        )
        narrative = await TemplateNarrativeGenerator().generate(data)
        assert validate_narrative_numbers(narrative, data) is True

    async def test_fabricated_large_number_fails_validation(self, client, tiny_video_bytes):
        brand_token, inf_token, campaign_id, slot = await _published_slot_with_account(
            client, tiny_video_bytes, brand_email="invalidate-brand@example.com",
            inf_email="invalidate-inf@example.com", inf_username="invalidateinf",
        )

        async with AsyncSessionLocal() as db:
            analytics = await compute_campaign_analytics(db, campaign_id=uuid.UUID(campaign_id))
            comment_summary = await compute_comment_summary(db, campaign_id=uuid.UUID(campaign_id))

        data = ReportData(
            campaign_id=uuid.UUID(campaign_id),
            brand_name="Test Brand",
            platforms=["tiktok"],
            target_views=10_000,
            performance_window_days=3,
            analytics=analytics,
            comment_summary=comment_summary,
        )
        fabricated = "This campaign reached an incredible 123456789 views, far exceeding expectations."
        assert validate_narrative_numbers(fabricated, data) is False
