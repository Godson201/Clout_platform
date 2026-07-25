import asyncio

from tests.factories import fund_and_confirm_campaign, register_brand_with_ready_ad, register_influencer_token
from tests.test_campaigns import _create_draft_campaign


async def _funded_campaign_slots(client, tiny_video_bytes, *, brand_email: str, **campaign_overrides) -> list[dict]:
    token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email=brand_email)
    create_resp = await _create_draft_campaign(client, token, ad_id, **campaign_overrides)
    campaign_id = create_resp.json()["id"]
    body = await fund_and_confirm_campaign(client, token, campaign_id)
    return body["slots"]


class TestMarketplaceBrowsing:
    async def test_browse_returns_open_slots_with_scores(self, client, tiny_video_bytes):
        await _funded_campaign_slots(
            client, tiny_video_bytes, brand_email="market-brand@example.com",
            platforms=["tiktok"], slot_count=2, target_sector="beauty", target_location="Kigali",
        )
        inf_token = await register_influencer_token(
            client, email="market-inf@example.com", username="marketinf",
            sector="beauty", location="Kigali", follower_tier="micro",
        )

        resp = await client.get("/api/v1/marketplace/slots", headers={"Authorization": f"Bearer {inf_token}"})
        assert resp.status_code == 200
        slots = resp.json()
        assert len(slots) >= 2
        assert all(s["status"] == "open" for s in slots)
        assert all("match_score" in s for s in slots)
        # Sorted by score descending.
        scores = [s["match_score"]["total"] for s in slots]
        assert scores == sorted(scores, reverse=True)

    async def test_browse_filters_by_platform_and_tier(self, client, tiny_video_bytes):
        await _funded_campaign_slots(
            client, tiny_video_bytes, brand_email="filter-brand@example.com",
            platforms=["tiktok", "youtube"], slot_count=1, tier="macro",
        )
        inf_token = await register_influencer_token(client, email="filter-inf@example.com", username="filterinf2")

        resp = await client.get(
            "/api/v1/marketplace/slots",
            params={"platform": "youtube", "tier": "macro"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert resp.status_code == 200
        assert all(s["platform"] == "youtube" and s["tier"] == "macro" for s in resp.json())

    async def test_non_influencer_cannot_browse_marketplace(self, client, tiny_video_bytes):
        token, _ = await register_brand_with_ready_ad(client, tiny_video_bytes, email="not-inf@example.com")
        resp = await client.get("/api/v1/marketplace/slots", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


class TestSlotClaiming:
    async def test_claim_slot_succeeds_and_appears_in_my_slots(self, client, tiny_video_bytes):
        slots = await _funded_campaign_slots(
            client, tiny_video_bytes, brand_email="claim-brand@example.com", platforms=["tiktok"], slot_count=1
        )
        slot_id = slots[0]["id"]
        inf_token = await register_influencer_token(client, email="claimer@example.com", username="claimer")

        claim_resp = await client.post(f"/api/v1/slots/{slot_id}/claim", headers={"Authorization": f"Bearer {inf_token}"})
        assert claim_resp.status_code == 200
        assert claim_resp.json()["status"] == "claimed"

        mine_resp = await client.get("/api/v1/slots/mine", headers={"Authorization": f"Bearer {inf_token}"})
        assert len(mine_resp.json()) == 1
        assert mine_resp.json()[0]["id"] == slot_id

    async def test_cannot_claim_already_claimed_slot(self, client, tiny_video_bytes):
        slots = await _funded_campaign_slots(
            client, tiny_video_bytes, brand_email="double-claim-brand@example.com", platforms=["tiktok"], slot_count=1
        )
        slot_id = slots[0]["id"]
        first_inf = await register_influencer_token(client, email="first-claimer@example.com", username="firstclaimer")
        second_inf = await register_influencer_token(client, email="second-claimer@example.com", username="secondclaimer")

        first = await client.post(f"/api/v1/slots/{slot_id}/claim", headers={"Authorization": f"Bearer {first_inf}"})
        assert first.status_code == 200

        second = await client.post(f"/api/v1/slots/{slot_id}/claim", headers={"Authorization": f"Bearer {second_inf}"})
        assert second.status_code == 409

    async def test_concurrent_claims_on_same_slot_only_one_wins(self, client, tiny_video_bytes):
        slots = await _funded_campaign_slots(
            client, tiny_video_bytes, brand_email="race-brand@example.com", platforms=["tiktok"], slot_count=1
        )
        slot_id = slots[0]["id"]
        inf_a = await register_influencer_token(client, email="race-a@example.com", username="racea")
        inf_b = await register_influencer_token(client, email="race-b@example.com", username="raceb")

        results = await asyncio.gather(
            client.post(f"/api/v1/slots/{slot_id}/claim", headers={"Authorization": f"Bearer {inf_a}"}),
            client.post(f"/api/v1/slots/{slot_id}/claim", headers={"Authorization": f"Bearer {inf_b}"}),
        )
        status_codes = sorted(r.status_code for r in results)
        assert status_codes == [200, 409], "exactly one claim must win the race, the other must be rejected"

    async def test_max_five_active_slots_per_influencer(self, client, tiny_video_bytes):
        slots = await _funded_campaign_slots(
            client, tiny_video_bytes, brand_email="five-slot-brand@example.com", platforms=["tiktok"], slot_count=6
        )
        assert len(slots) == 6
        inf_token = await register_influencer_token(client, email="grabby@example.com", username="grabby")

        for slot in slots[:5]:
            resp = await client.post(f"/api/v1/slots/{slot['id']}/claim", headers={"Authorization": f"Bearer {inf_token}"})
            assert resp.status_code == 200

        sixth = await client.post(f"/api/v1/slots/{slots[5]['id']}/claim", headers={"Authorization": f"Bearer {inf_token}"})
        assert sixth.status_code == 409
        assert "5 active slots" in sixth.json()["detail"]

    async def test_claim_nonexistent_slot_returns_404(self, client, tiny_video_bytes):
        inf_token = await register_influencer_token(client, email="ghost-claim@example.com", username="ghostclaim")
        resp = await client.post(
            "/api/v1/slots/00000000-0000-0000-0000-000000000000/claim",
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert resp.status_code == 404
