from decimal import Decimal

from tests.factories import fund_and_confirm_campaign, register_brand_with_ready_ad
from tests.test_advertisements import _brand_token, _get_template_id


async def _create_draft_campaign(client, token: str, ad_id: str, **overrides) -> dict:
    payload = {
        "advertisement_id": ad_id,
        "platforms": ["tiktok"],
        "target_views": 10_000,
        "tier": "micro",
        "slot_count": 4,
        "performance_window_days": 3,
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/campaigns", json=payload, headers={"Authorization": f"Bearer {token}"})
    return resp


class TestCampaignCreation:
    async def test_create_campaign_computes_pricing(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="camp-brand@example.com")

        resp = await _create_draft_campaign(client, token, ad_id, target_views=10_000, platforms=["tiktok"])
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "pending_funding"
        # Decimal comparison, not float — binary floats can't represent 55000.0
        # exactly after a *1.1 multiplication, and the backend never does this
        # math in float in the first place (see services/pricing.py).
        assert Decimal(str(body["base_price"])) == Decimal("10000") * Decimal("5.0000")
        assert Decimal(str(body["total_brand_payment"])) == Decimal("10000") * Decimal("5.0000") * Decimal("1.1000")
        assert body["rate_snapshot"] == {"tiktok": "5.0000"}

    async def test_cannot_create_campaign_from_draft_advertisement(self, client):
        token = await _brand_token(client, email="draft-ad-brand@example.com")
        template_id = await _get_template_id(client, token)
        ad_resp = await client.post(
            "/api/v1/advertisements",
            json={"template_id": template_id, "title": "Still a draft"},
            headers={"Authorization": f"Bearer {token}"},
        )
        ad_id = ad_resp.json()["id"]

        resp = await _create_draft_campaign(client, token, ad_id)
        assert resp.status_code == 400

    async def test_cannot_use_another_brands_advertisement(self, client, tiny_video_bytes):
        token_a, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="owner-ad@example.com")
        token_b = await _brand_token(client, email="thief-brand@example.com")

        resp = await _create_draft_campaign(client, token_b, ad_id)
        assert resp.status_code == 404


class TestCampaignFundingAndSlots:
    async def test_funding_creates_slots_and_lists_campaign(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="fund-brand@example.com")
        create_resp = await _create_draft_campaign(
            client, token, ad_id, platforms=["tiktok", "instagram"], slot_count=3, target_views=9000
        )
        campaign_id = create_resp.json()["id"]

        body = await fund_and_confirm_campaign(client, token, campaign_id)
        assert body["status"] == "listed"
        assert len(body["slots"]) == 6  # 3 slots x 2 platforms
        assert all(s["status"] == "open" for s in body["slots"])
        assert all(s["target_views"] == 3000 for s in body["slots"])  # 9000 / 3 slots per platform
        # base_price (performance-contingent) landed in escrow; the brand fee
        # portion of total_brand_payment was carved off to platform revenue.
        assert Decimal(str(body["escrow_balance"])) == Decimal(str(body["base_price"]))

    async def test_cannot_fund_twice(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="fund-twice@example.com")
        create_resp = await _create_draft_campaign(client, token, ad_id)
        campaign_id = create_resp.json()["id"]

        await fund_and_confirm_campaign(client, token, campaign_id)
        second = await client.post(
            f"/api/v1/campaigns/{campaign_id}/fund",
            json={"phone_number": "0788000001"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert second.status_code == 400

    async def test_cancel_before_funding(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="cancel-brand@example.com")
        create_resp = await _create_draft_campaign(client, token, ad_id)
        campaign_id = create_resp.json()["id"]

        resp = await client.post(f"/api/v1/campaigns/{campaign_id}/cancel", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    async def test_list_and_filter_campaigns(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="list-camp@example.com")
        await _create_draft_campaign(client, token, ad_id)

        list_resp = await client.get("/api/v1/campaigns", headers={"Authorization": f"Bearer {token}"})
        assert list_resp.json()["total"] == 1

        filtered = await client.get(
            "/api/v1/campaigns", params={"status": "listed"}, headers={"Authorization": f"Bearer {token}"}
        )
        assert filtered.json()["total"] == 0
