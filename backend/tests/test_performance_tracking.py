import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.core.platform_capabilities import PlatformCapabilities
from app.models.social_post import SocialPost
from app.services.auto_settlement import auto_settle_expired_slots
from tests.factories import fund_and_confirm_campaign, register_brand_with_ready_ad, register_influencer_token
from tests.test_admin_flow import _make_admin_token
from tests.test_campaigns import _create_draft_campaign


async def _claimed_and_published_slot(
    client, tiny_video_bytes, *, brand_email: str, inf_email: str, inf_username: str,
    platform: str = "tiktok", target_views: int = 250,
):
    brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email=brand_email)
    create_resp = await _create_draft_campaign(
        client, brand_token, ad_id, platforms=[platform], slot_count=1, target_views=target_views
    )
    campaign_id = create_resp.json()["id"]
    body = await fund_and_confirm_campaign(client, brand_token, campaign_id, phone_number="0788321321")
    slot = body["slots"][0]

    inf_token = await register_influencer_token(client, email=inf_email, username=inf_username)
    claim_resp = await client.post(f"/api/v1/slots/{slot['id']}/claim", headers={"Authorization": f"Bearer {inf_token}"})
    assert claim_resp.status_code == 200

    return brand_token, inf_token, campaign_id, slot


async def _backdate_post_publish_time(slot_id: str, *, days_ago: int) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SocialPost).where(SocialPost.campaign_slot_id == uuid.UUID(slot_id)))
        post = result.scalar_one()
        post.published_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
        await db.commit()


class TestCampaignActiveTransition:
    async def test_campaign_becomes_active_on_first_claim(self, client, tiny_video_bytes):
        brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="active-brand@example.com")
        create_resp = await _create_draft_campaign(client, brand_token, ad_id, platforms=["tiktok"], slot_count=1)
        campaign_id = create_resp.json()["id"]
        body = await fund_and_confirm_campaign(client, brand_token, campaign_id, phone_number="0788322322")
        assert body["status"] == "listed"

        inf_token = await register_influencer_token(client, email="active-inf@example.com", username="activeinf")
        await client.post(f"/api/v1/slots/{body['slots'][0]['id']}/claim", headers={"Authorization": f"Bearer {inf_token}"})

        detail = await client.get(f"/api/v1/campaigns/{campaign_id}", headers={"Authorization": f"Bearer {brand_token}"})
        assert detail.json()["status"] == "active"


class TestAutoSettlement:
    async def test_verifiable_platform_settles_automatically_and_completes_campaign(self, client, tiny_video_bytes):
        brand_token, inf_token, campaign_id, slot = await _claimed_and_published_slot(
            client, tiny_video_bytes, brand_email="autosettle-brand@example.com",
            inf_email="autosettle-inf@example.com", inf_username="autosettleinf", target_views=250,
        )
        account_resp = await client.get("/api/v1/social-accounts/connect/tiktok", headers={"Authorization": f"Bearer {inf_token}"})
        query = parse_qs(urlparse(account_resp.json()["authorization_url"]).query)
        callback = await client.post(
            "/api/v1/social-accounts/callback/tiktok",
            json={"code": query["code"][0], "state": query["state"][0]},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        account_id = callback.json()["id"]

        post_resp = await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": account_id, "caption": "auto settlement test"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert post_resp.json()["status"] == "published"  # mock capability auto-publishes

        # One poll records a snapshot of 500 views (mock's count=1 * 500) against
        # a 250-view target — comfortably over 100%, so this should complete.
        await client.get(f"/api/v1/slots/{slot['id']}/post/metrics", headers={"Authorization": f"Bearer {inf_token}"})

        await _backdate_post_publish_time(slot["id"], days_ago=10)

        async with AsyncSessionLocal() as db:
            result = await auto_settle_expired_slots(db)
        assert result == {"auto_settled": 1, "needs_review": 0}

        slots_resp = await client.get("/api/v1/slots/mine", headers={"Authorization": f"Bearer {inf_token}"})
        settled_slot = next(s for s in slots_resp.json() if s["id"] == slot["id"])
        assert settled_slot["status"] == "completed"

        wallet_resp = await client.get("/api/v1/influencers/me/wallet", headers={"Authorization": f"Bearer {inf_token}"})
        assert Decimal(str(wallet_resp.json()["balance"])) == Decimal(str(slot["budget_allocated"]))

        campaign_resp = await client.get(
            f"/api/v1/campaigns/{campaign_id}", headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert campaign_resp.json()["status"] == "completed"

    async def test_unverifiable_platform_is_left_untouched_and_queued_for_review(
        self, client, tiny_video_bytes, monkeypatch
    ):
        no_capability = PlatformCapabilities(
            can_auto_publish=False, can_schedule=False, can_fetch_metrics=False, can_fetch_comments=False
        )
        monkeypatch.setattr("app.services.social_posting.get_capabilities", lambda platform: no_capability)
        monkeypatch.setattr("app.services.auto_settlement.get_capabilities", lambda platform: no_capability)

        brand_token, inf_token, campaign_id, slot = await _claimed_and_published_slot(
            client, tiny_video_bytes, brand_email="review-brand@example.com",
            inf_email="review-inf@example.com", inf_username="reviewinf",
        )
        account_resp = await client.get("/api/v1/social-accounts/connect/tiktok", headers={"Authorization": f"Bearer {inf_token}"})
        query = parse_qs(urlparse(account_resp.json()["authorization_url"]).query)
        callback = await client.post(
            "/api/v1/social-accounts/callback/tiktok",
            json={"code": query["code"][0], "state": query["state"][0]},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        account_id = callback.json()["id"]

        post_resp = await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": account_id, "caption": "manual"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert post_resp.json()["publish_mode"] == "manual"
        await client.patch(
            f"/api/v1/slots/{slot['id']}/post/submit-url",
            json={"post_url": "https://www.tiktok.com/@reviewinf/video/1"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )

        await _backdate_post_publish_time(slot["id"], days_ago=10)

        async with AsyncSessionLocal() as db:
            result = await auto_settle_expired_slots(db)
        assert result == {"auto_settled": 0, "needs_review": 1}

        slots_resp = await client.get("/api/v1/slots/mine", headers={"Authorization": f"Bearer {inf_token}"})
        untouched_slot = next(s for s in slots_resp.json() if s["id"] == slot["id"])
        assert untouched_slot["status"] == "published", "should be left alone, not auto-failed, when unverifiable"

        admin_token = await _make_admin_token(email="review-admin@clout-platform.com")
        queue_resp = await client.get(
            "/api/v1/admin/slots/awaiting-settlement", headers={"Authorization": f"Bearer {admin_token}"}
        )
        queue_slot_ids = [item["slot_id"] for item in queue_resp.json()]
        assert slot["id"] in queue_slot_ids

        queued_item = next(item for item in queue_resp.json() if item["slot_id"] == slot["id"])
        assert queued_item["influencer_username"] == "reviewinf"
        assert queued_item["post_url"] == "https://www.tiktok.com/@reviewinf/video/1"

        # Admin resolves it manually — should then drop off the queue.
        await client.post(
            f"/api/v1/admin/slots/{slot['id']}/settle",
            json={"delivered_pct": "80"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        queue_after = await client.get(
            "/api/v1/admin/slots/awaiting-settlement", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert slot["id"] not in [item["slot_id"] for item in queue_after.json()]


class TestCampaignAnalytics:
    async def test_analytics_aggregates_verified_metrics_across_slots(self, client, tiny_video_bytes):
        brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="analytics-brand@example.com")
        create_resp = await _create_draft_campaign(
            client, brand_token, ad_id, platforms=["tiktok", "instagram"], slot_count=1, target_views=100
        )
        campaign_id = create_resp.json()["id"]
        body = await fund_and_confirm_campaign(client, brand_token, campaign_id, phone_number="0788323323")
        slots_by_platform = {s["platform"]: s for s in body["slots"]}

        inf_a = await register_influencer_token(client, email="analytics-inf-a@example.com", username="analyticsinfa")
        inf_b = await register_influencer_token(client, email="analytics-inf-b@example.com", username="analyticsinfb")

        async def _claim_connect_publish(inf_token, slot, platform):
            await client.post(f"/api/v1/slots/{slot['id']}/claim", headers={"Authorization": f"Bearer {inf_token}"})
            connect_resp = await client.get(f"/api/v1/social-accounts/connect/{platform}", headers={"Authorization": f"Bearer {inf_token}"})
            query = parse_qs(urlparse(connect_resp.json()["authorization_url"]).query)
            callback = await client.post(
                f"/api/v1/social-accounts/callback/{platform}",
                json={"code": query["code"][0], "state": query["state"][0]},
                headers={"Authorization": f"Bearer {inf_token}"},
            )
            account_id = callback.json()["id"]
            await client.post(
                f"/api/v1/slots/{slot['id']}/post",
                json={"social_account_id": account_id, "caption": "analytics"},
                headers={"Authorization": f"Bearer {inf_token}"},
            )

        await _claim_connect_publish(inf_a, slots_by_platform["tiktok"], "tiktok")
        await _claim_connect_publish(inf_b, slots_by_platform["instagram"], "instagram")

        # A's post polled once (500 views), B's polled twice (1000 views) — makes
        # the platform totals distinguishable rather than tied.
        await client.get(f"/api/v1/slots/{slots_by_platform['tiktok']['id']}/post/metrics", headers={"Authorization": f"Bearer {inf_a}"})
        await client.get(f"/api/v1/slots/{slots_by_platform['instagram']['id']}/post/metrics", headers={"Authorization": f"Bearer {inf_b}"})
        await client.get(f"/api/v1/slots/{slots_by_platform['instagram']['id']}/post/metrics", headers={"Authorization": f"Bearer {inf_b}"})

        analytics_resp = await client.get(
            f"/api/v1/campaigns/{campaign_id}/analytics", headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert analytics_resp.status_code == 200
        analytics = analytics_resp.json()

        assert analytics["total_verified_views"] == 1500
        assert analytics["views_by_platform"]["tiktok"] == 500
        assert analytics["views_by_platform"]["instagram"] == 1000
        assert analytics["top_platform"] == "instagram"
        assert analytics["top_influencer_username"] == "analyticsinfb"
        assert len(analytics["influencer_performance"]) == 2
        assert analytics["total_target_views"] == 200  # 100 per platform x 2 platforms
        assert analytics["progress_pct"] == 750.0  # 1500 / 200 * 100
