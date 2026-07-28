from urllib.parse import parse_qs, urlparse

from tests.factories import fund_and_confirm_campaign, register_brand_with_ready_ad, register_influencer_token
from tests.test_advertisements import _brand_token
from tests.test_campaigns import _create_draft_campaign


class TestBrandDashboardSummary:
    async def test_empty_brand_has_zero_stats(self, client):
        token = await _brand_token(client, email="dash-empty-brand@example.com")
        resp = await client.get("/api/v1/brands/me/dashboard-summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_campaigns"] == 0
        assert body["total_views"] == 0
        assert body["total_engagement"] == 0
        assert body["total_spent"] == 0
        assert body["total_campaigns_mom_pct"] is None
        assert body["top_campaigns"] == []
        assert body["views_by_platform"] == {}

    async def test_non_brand_cannot_access_dashboard_summary(self, client):
        inf_token = await register_influencer_token(client, email="dash-inf@example.com", username="dashinf")
        resp = await client.get("/api/v1/brands/me/dashboard-summary", headers={"Authorization": f"Bearer {inf_token}"})
        assert resp.status_code == 403

    async def test_funded_campaign_reflects_in_count_and_spend(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="dash-brand-1@example.com")
        create_resp = await _create_draft_campaign(client, token, ad_id, target_views=10_000, platforms=["tiktok"], slot_count=1)
        campaign_id = create_resp.json()["id"]
        funded = await fund_and_confirm_campaign(client, token, campaign_id)

        resp = await client.get("/api/v1/brands/me/dashboard-summary", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_campaigns"] == 1
        assert float(body["total_spent"]) == float(funded["total_brand_payment"])
        assert body["currency"] == funded["currency"]

    async def test_slot_claim_and_post_reflects_in_views_and_top_campaigns(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="dash-brand-2@example.com")
        create_resp = await _create_draft_campaign(client, token, ad_id, target_views=10_000, platforms=["tiktok"], slot_count=1)
        campaign_id = create_resp.json()["id"]
        funded = await fund_and_confirm_campaign(client, token, campaign_id)
        slot_id = funded["slots"][0]["id"]

        inf_token = await register_influencer_token(client, email="dash-inf-2@example.com", username="dashinf2")
        claim_resp = await client.post(f"/api/v1/slots/{slot_id}/claim", headers={"Authorization": f"Bearer {inf_token}"})
        assert claim_resp.status_code == 200

        connect_resp = await client.get(
            "/api/v1/social-accounts/connect/tiktok", headers={"Authorization": f"Bearer {inf_token}"}
        )
        query = parse_qs(urlparse(connect_resp.json()["authorization_url"]).query)
        code, state = query["code"][0], query["state"][0]
        account_resp = await client.post(
            "/api/v1/social-accounts/callback/tiktok",
            json={"code": code, "state": state},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        account_id = account_resp.json()["id"]

        post_resp = await client.post(
            f"/api/v1/slots/{slot_id}/post",
            json={"social_account_id": account_id, "caption": "dashboard test"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert post_resp.status_code == 201

        await client.get(f"/api/v1/slots/{slot_id}/post/metrics", headers={"Authorization": f"Bearer {inf_token}"})

        resp = await client.get("/api/v1/brands/me/dashboard-summary", headers={"Authorization": f"Bearer {token}"})
        body = resp.json()
        assert body["total_views"] > 0
        assert "tiktok" in body["views_by_platform"]
        assert len(body["top_campaigns"]) == 1
        assert body["top_campaigns"][0]["campaign_id"] == campaign_id
        assert body["top_campaigns"][0]["total_views"] == body["total_views"]

        # Both the slot-claim and the post-published lifecycle events should
        # have notified the brand — driving the Recent Activity feed.
        notif_resp = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"})
        types = {n["type"] for n in notif_resp.json()}
        assert "slot_claimed" in types
        assert "payment_confirmed" in types


class TestLifecycleNotifications:
    async def test_slot_claim_notifies_brand(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="notif-claim-brand@example.com")
        create_resp = await _create_draft_campaign(client, token, ad_id, target_views=10_000, platforms=["tiktok"], slot_count=1)
        campaign_id = create_resp.json()["id"]
        funded = await fund_and_confirm_campaign(client, token, campaign_id)
        slot_id = funded["slots"][0]["id"]

        inf_token = await register_influencer_token(client, email="notif-claim-inf@example.com", username="notifclaiminf")
        await client.post(f"/api/v1/slots/{slot_id}/claim", headers={"Authorization": f"Bearer {inf_token}"})

        resp = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"})
        notif = next(n for n in resp.json() if n["type"] == "slot_claimed")
        assert notif["data"]["slot_id"] == slot_id
        assert notif["link"] == f"/brand/campaigns/{campaign_id}"

    async def test_payment_confirmation_notifies_brand(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="notif-pay-brand@example.com")
        create_resp = await _create_draft_campaign(client, token, ad_id, target_views=10_000, platforms=["tiktok"], slot_count=1)
        campaign_id = create_resp.json()["id"]
        await fund_and_confirm_campaign(client, token, campaign_id)

        resp = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"})
        notif = next(n for n in resp.json() if n["type"] == "payment_confirmed")
        assert notif["data"]["campaign_id"] == campaign_id
