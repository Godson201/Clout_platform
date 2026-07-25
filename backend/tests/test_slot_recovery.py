import uuid
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models.campaign_slot import CampaignSlot
from app.models.enums import FollowerTier, SocialPlatform
from app.models.refund import Refund
from app.services.matching import NEUTRAL_RELIABILITY, get_reliability_score
from app.services.recommendations import MAX_BOOST, MIN_BOOST, get_historical_performance_boost
from tests.factories import fund_and_confirm_campaign, register_brand_with_ready_ad, register_influencer_token
from tests.test_admin_flow import _make_admin_token
from tests.test_campaigns import _create_draft_campaign


class TestSlotRecoveryChain:
    async def test_recovery_chain_recycles_twice_then_refunds_and_completes_campaign(
        self, client, tiny_video_bytes
    ):
        brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="recovery-brand@example.com")
        create_resp = await _create_draft_campaign(
            client, brand_token, ad_id, platforms=["tiktok"], slot_count=1, target_views=1000
        )
        campaign_id = create_resp.json()["id"]
        body = await fund_and_confirm_campaign(client, brand_token, campaign_id, phone_number="0788700700")
        original_slot = body["slots"][0]
        assert Decimal(str(original_slot["budget_allocated"])) == Decimal("5000")  # 1000 views x 5.0000/view

        admin_token = await _make_admin_token(email="recovery-admin@clout-platform.com")

        async def _claim_and_settle(slot_id: str, *, email: str, username: str, delivered_pct: str):
            inf_token = await register_influencer_token(client, email=email, username=username)
            claim_resp = await client.post(f"/api/v1/slots/{slot_id}/claim", headers={"Authorization": f"Bearer {inf_token}"})
            assert claim_resp.status_code == 200
            settle_resp = await client.post(
                f"/api/v1/admin/slots/{slot_id}/settle",
                json={"delivered_pct": delivered_pct},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert settle_resp.status_code == 200
            return settle_resp.json()

        # Generation 0 -> 1: original slot settles at 50%, leaving a 500-view /
        # 2500-budget shortfall recycled into a new generation-1 slot.
        settled = await _claim_and_settle(original_slot["id"], email="recovery-inf-a@example.com", username="recoveryinfa", delivered_pct="50")
        assert settled["status"] == "partially_completed"
        assert Decimal(str(settled["delivered_pct"])) == Decimal("50.00")

        detail = await client.get(f"/api/v1/campaigns/{campaign_id}", headers={"Authorization": f"Bearer {brand_token}"})
        slots = detail.json()["slots"]
        assert len(slots) == 2, "the shortfall should have been recycled into a new slot"
        gen1_slot = next(s for s in slots if s["recovery_generation"] == 1)
        assert gen1_slot["recovered_from_slot_id"] == original_slot["id"]
        assert gen1_slot["target_views"] == 500
        assert Decimal(str(gen1_slot["budget_allocated"])) == Decimal("2500.0000")
        assert gen1_slot["status"] == "open"
        assert gen1_slot["platform"] == original_slot["platform"]
        assert gen1_slot["tier"] == original_slot["tier"]

        # Generation 1 -> 2: same story, one level deeper.
        await _claim_and_settle(gen1_slot["id"], email="recovery-inf-b@example.com", username="recoveryinfb", delivered_pct="50")

        detail = await client.get(f"/api/v1/campaigns/{campaign_id}", headers={"Authorization": f"Bearer {brand_token}"})
        slots = detail.json()["slots"]
        assert len(slots) == 3
        gen2_slot = next(s for s in slots if s["recovery_generation"] == 2)
        assert gen2_slot["recovered_from_slot_id"] == gen1_slot["id"]
        assert gen2_slot["target_views"] == 250

        escrow_before = Decimal(str(detail.json()["escrow_balance"]))

        # Generation 2 is at MAX_RECOVERY_GENERATIONS: this shortfall must be
        # refunded, not recycled into a generation-3 slot.
        await _claim_and_settle(gen2_slot["id"], email="recovery-inf-c@example.com", username="recoveryinfc", delivered_pct="50")

        detail = await client.get(f"/api/v1/campaigns/{campaign_id}", headers={"Authorization": f"Bearer {brand_token}"})
        final_body = detail.json()
        slots = final_body["slots"]
        assert len(slots) == 3, "no generation-3 slot should have been created — the chain is capped"
        assert all(s["recovery_generation"] <= 2 for s in slots)

        # Every slot is now terminal, so the campaign itself must be complete.
        assert final_body["status"] == "completed"

        escrow_after = Decimal(str(final_body["escrow_balance"]))
        assert escrow_after < escrow_before, "the generation-2 shortfall should have left escrow via a refund"

        async with AsyncSessionLocal() as db:
            refund_result = await db.execute(select(Refund).where(Refund.campaign_id == uuid.UUID(campaign_id)))
            refunds = refund_result.scalars().all()
        assert len(refunds) == 1
        assert Decimal(str(refunds[0].amount)) == Decimal("625.0000")  # 250 views x 5.0000/view x 50% shortfall
        assert refunds[0].phone_number == "0788700700"  # reused the original funding number


class TestCancelWithClaimedSlots:
    async def test_can_cancel_campaign_with_claimed_but_unpublished_slot(self, client, tiny_video_bytes):
        brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="cancel-claimed-brand@example.com")
        create_resp = await _create_draft_campaign(client, brand_token, ad_id, platforms=["tiktok"], slot_count=1)
        campaign_id = create_resp.json()["id"]
        body = await fund_and_confirm_campaign(client, brand_token, campaign_id, phone_number="0788800800")
        slot = body["slots"][0]

        inf_token = await register_influencer_token(client, email="cancel-claimed-inf@example.com", username="cancelclaimedinf")
        await client.post(f"/api/v1/slots/{slot['id']}/claim", headers={"Authorization": f"Bearer {inf_token}"})

        resp = await client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel",
            json={"phone_number": "0788800800"},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"
        assert resp.json()["slots"][0]["status"] == "cancelled"

    async def test_cannot_cancel_campaign_with_published_slot(self, client, tiny_video_bytes):
        brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="cancel-published-brand@example.com")
        create_resp = await _create_draft_campaign(client, brand_token, ad_id, platforms=["tiktok"], slot_count=1)
        campaign_id = create_resp.json()["id"]
        body = await fund_and_confirm_campaign(client, brand_token, campaign_id, phone_number="0788900900")
        slot = body["slots"][0]

        inf_token = await register_influencer_token(client, email="cancel-published-inf@example.com", username="cancelpublishedinf")
        await client.post(f"/api/v1/slots/{slot['id']}/claim", headers={"Authorization": f"Bearer {inf_token}"})

        connect_resp = await client.get("/api/v1/social-accounts/connect/tiktok", headers={"Authorization": f"Bearer {inf_token}"})
        query = parse_qs(urlparse(connect_resp.json()["authorization_url"]).query)
        callback = await client.post(
            "/api/v1/social-accounts/callback/tiktok",
            json={"code": query["code"][0], "state": query["state"][0]},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": callback.json()["id"], "caption": "already live"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )

        resp = await client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel",
            json={"phone_number": "0788900900"},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert resp.status_code == 400


class TestReliabilityScore:
    async def test_no_settlement_history_is_neutral(self, client, tiny_video_bytes):
        inf_token = await register_influencer_token(client, email="reliability-new@example.com", username="reliabilitynew")
        me_resp = await client.get("/api/v1/influencers/me", headers={"Authorization": f"Bearer {inf_token}"})
        influencer_id = uuid.UUID(me_resp.json()["id"])

        async with AsyncSessionLocal() as db:
            score = await get_reliability_score(db, influencer_id)
        assert score == NEUTRAL_RELIABILITY

    async def test_reliability_is_the_average_delivered_pct_not_binary(self, client, tiny_video_bytes):
        brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="reliability-brand@example.com")
        create_resp = await _create_draft_campaign(client, brand_token, ad_id, platforms=["tiktok"], slot_count=3, target_views=300)
        campaign_id = create_resp.json()["id"]
        body = await fund_and_confirm_campaign(client, brand_token, campaign_id, phone_number="0788110110")
        slots = body["slots"]

        inf_token = await register_influencer_token(client, email="reliability-inf@example.com", username="reliabilityinf")
        me_resp = await client.get("/api/v1/influencers/me", headers={"Authorization": f"Bearer {inf_token}"})
        influencer_id = uuid.UUID(me_resp.json()["id"])

        # Directly stamp settlement outcomes (90%, 90%, 0%) rather than driving
        # three full claim/settle/recover cycles — this test is about the
        # averaging math, not the settlement pipeline (covered elsewhere).
        async with AsyncSessionLocal() as db:
            for slot, pct in zip(slots, [90.0, 90.0, 0.0]):
                result = await db.execute(select(CampaignSlot).where(CampaignSlot.id == uuid.UUID(slot["id"])))
                row = result.scalar_one()
                row.influencer_id = influencer_id
                row.delivered_pct = pct
            await db.commit()

            score = await get_reliability_score(db, influencer_id)
        # (90 + 90 + 0) / 3 / 100 = 0.6 — deliberately chosen to differ from
        # what a binary completed/failed count (2/3 = 0.667) would have given,
        # proving this reads the graded delivered_pct, not a pass/fail tally.
        assert score == 0.6


class TestHistoricalPerformanceBoost:
    async def test_insufficient_sample_size_is_neutral(self, client, tiny_video_bytes):
        async with AsyncSessionLocal() as db:
            result = await get_historical_performance_boost(
                db, sector="a-sector-nobody-used", platform=SocialPlatform.TIKTOK, tier=FollowerTier.MICRO
            )
        assert result.sample_size == 0
        assert result.boost == 1.0

    async def test_strong_and_weak_segments_get_opposite_boosts(self, client, tiny_video_bytes):
        strong_brand, strong_ad = await register_brand_with_ready_ad(client, tiny_video_bytes, email="hist-strong-brand@example.com")
        strong_create = await _create_draft_campaign(
            client, strong_brand, strong_ad, platforms=["tiktok"], slot_count=5, tier="micro", target_sector="beauty-hist",
        )
        strong_campaign_id = strong_create.json()["id"]
        strong_body = await fund_and_confirm_campaign(client, strong_brand, strong_campaign_id, phone_number="0788220220")

        weak_brand, weak_ad = await register_brand_with_ready_ad(client, tiny_video_bytes, email="hist-weak-brand@example.com")
        weak_create = await _create_draft_campaign(
            client, weak_brand, weak_ad, platforms=["tiktok"], slot_count=5, tier="micro", target_sector="tech-hist",
        )
        weak_campaign_id = weak_create.json()["id"]
        weak_body = await fund_and_confirm_campaign(client, weak_brand, weak_campaign_id, phone_number="0788330330")

        async with AsyncSessionLocal() as db:
            for slot in strong_body["slots"]:
                result = await db.execute(select(CampaignSlot).where(CampaignSlot.id == uuid.UUID(slot["id"])))
                result.scalar_one().delivered_pct = 95.0
            for slot in weak_body["slots"]:
                result = await db.execute(select(CampaignSlot).where(CampaignSlot.id == uuid.UUID(slot["id"])))
                result.scalar_one().delivered_pct = 20.0
            await db.commit()

            strong = await get_historical_performance_boost(
                db, sector="beauty-hist", platform=SocialPlatform.TIKTOK, tier=FollowerTier.MICRO
            )
            weak = await get_historical_performance_boost(
                db, sector="tech-hist", platform=SocialPlatform.TIKTOK, tier=FollowerTier.MICRO
            )

        assert strong.sample_size == 5
        assert strong.boost == MAX_BOOST
        assert weak.sample_size == 5
        assert weak.boost == MIN_BOOST
        assert strong.boost > weak.boost
