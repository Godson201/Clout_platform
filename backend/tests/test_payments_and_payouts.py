import asyncio
from decimal import Decimal

from tests.factories import fund_and_confirm_campaign, register_brand_with_ready_ad, register_influencer_token
from tests.test_admin_flow import _make_admin_token
from tests.test_campaigns import _create_draft_campaign


async def _create_funded_campaign(client, tiny_video_bytes, *, brand_email: str, phone_number: str, **overrides):
    token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email=brand_email)
    create_resp = await _create_draft_campaign(client, token, ad_id, **overrides)
    campaign_id = create_resp.json()["id"]
    body = await fund_and_confirm_campaign(client, token, campaign_id, phone_number=phone_number)
    return token, campaign_id, body


class TestCampaignFundingFailureAndIdempotency:
    async def test_funding_failure_reverts_campaign_and_creates_no_escrow(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="fail-fund@example.com")
        create_resp = await _create_draft_campaign(client, token, ad_id)
        campaign_id = create_resp.json()["id"]

        fund_resp = await client.post(
            f"/api/v1/campaigns/{campaign_id}/fund",
            json={"phone_number": "0788000000"},  # ends in 0000 -> mock simulates provider failure
            headers={"Authorization": f"Bearer {token}"},
        )
        provider_reference = fund_resp.json()["payment"]["provider_reference"]

        webhook_resp = await client.post(
            "/api/v1/webhooks/momo/collection", json={"referenceId": provider_reference, "status": "FAILED"}
        )
        assert webhook_resp.status_code == 204

        detail = await client.get(f"/api/v1/campaigns/{campaign_id}", headers={"Authorization": f"Bearer {token}"})
        body = detail.json()
        assert body["status"] == "pending_funding"
        assert body["slots"] == []
        assert body["escrow_balance"] is None

        # Brand can retry funding after a failure.
        retry = await client.post(
            f"/api/v1/campaigns/{campaign_id}/fund",
            json={"phone_number": "0788111111"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert retry.status_code == 200

    async def test_duplicate_webhook_does_not_double_credit_escrow(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="dup-webhook@example.com")
        create_resp = await _create_draft_campaign(client, token, ad_id, target_views=10_000, platforms=["tiktok"])
        campaign_id = create_resp.json()["id"]

        fund_resp = await client.post(
            f"/api/v1/campaigns/{campaign_id}/fund",
            json={"phone_number": "0788222222"},
            headers={"Authorization": f"Bearer {token}"},
        )
        provider_reference = fund_resp.json()["payment"]["provider_reference"]

        for _ in range(3):
            resp = await client.post(
                "/api/v1/webhooks/momo/collection", json={"referenceId": provider_reference, "status": "SUCCESSFUL"}
            )
            assert resp.status_code == 204

        detail = await client.get(f"/api/v1/campaigns/{campaign_id}", headers={"Authorization": f"Bearer {token}"})
        body = detail.json()
        assert Decimal(str(body["escrow_balance"])) == Decimal(str(body["base_price"]))

    async def test_polling_payment_status_resolves_without_webhook(self, client, tiny_video_bytes):
        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="poll-fund@example.com")
        create_resp = await _create_draft_campaign(client, token, ad_id)
        campaign_id = create_resp.json()["id"]

        await client.post(
            f"/api/v1/campaigns/{campaign_id}/fund",
            json={"phone_number": "0788333333"},
            headers={"Authorization": f"Bearer {token}"},
        )
        # No webhook sent at all — GET .../payment triggers the same
        # sync_payment_status the reconciliation task runs on a schedule.
        payment_resp = await client.get(
            f"/api/v1/campaigns/{campaign_id}/payment", headers={"Authorization": f"Bearer {token}"}
        )
        assert payment_resp.json()["status"] == "successful"

        detail = await client.get(f"/api/v1/campaigns/{campaign_id}", headers={"Authorization": f"Bearer {token}"})
        assert detail.json()["status"] == "listed"


class TestCampaignCancelRefund:
    async def test_cancel_funded_unclaimed_campaign_refunds_escrow(self, client, tiny_video_bytes):
        token, campaign_id, body = await _create_funded_campaign(
            client, tiny_video_bytes, brand_email="cancel-funded@example.com", phone_number="0788444444"
        )
        assert Decimal(str(body["escrow_balance"])) > 0

        cancel_resp = await client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel",
            json={"phone_number": "0788444444"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"
        assert Decimal(str(cancel_resp.json()["escrow_balance"])) == Decimal("0")

    async def test_cancel_funded_campaign_without_phone_number_rejected(self, client, tiny_video_bytes):
        token, campaign_id, _ = await _create_funded_campaign(
            client, tiny_video_bytes, brand_email="cancel-no-phone@example.com", phone_number="0788555555"
        )
        resp = await client.post(
            f"/api/v1/campaigns/{campaign_id}/cancel", json={}, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 400


class TestAdminSettlement:
    async def _claimed_slot(self, client, tiny_video_bytes, *, suffix: str, target_views: int = 10_000):
        token, campaign_id, body = await _create_funded_campaign(
            client,
            tiny_video_bytes,
            brand_email=f"settle-brand-{suffix}@example.com",
            phone_number="0788600001",
            platforms=["tiktok"],
            slot_count=1,
            target_views=target_views,
        )
        slot = body["slots"][0]
        inf_token = await register_influencer_token(
            client, email=f"settle-inf-{suffix}@example.com", username=f"settleinf{suffix}"
        )
        claim_resp = await client.post(
            f"/api/v1/slots/{slot['id']}/claim", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert claim_resp.status_code == 200
        return inf_token, slot

    async def test_settle_100_percent_completes_slot_and_pays_influencer(self, client, tiny_video_bytes):
        inf_token, slot = await self._claimed_slot(client, tiny_video_bytes, suffix="100")
        admin_token = await _make_admin_token(email="settle-admin-100@clout-platform.com")

        settle_resp = await client.post(
            f"/api/v1/admin/slots/{slot['id']}/settle",
            json={"delivered_pct": "100"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert settle_resp.status_code == 200
        assert settle_resp.json()["status"] == "completed"

        wallet_resp = await client.get(
            "/api/v1/influencers/me/wallet", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert Decimal(str(wallet_resp.json()["balance"])) == Decimal(str(slot["budget_allocated"]))

        profile_resp = await client.get("/api/v1/influencers/me", headers={"Authorization": f"Bearer {inf_token}"})
        assert profile_resp.json()["completed_slots_count"] == 1

    async def test_settle_partial_delivers_proportional_amount(self, client, tiny_video_bytes):
        inf_token, slot = await self._claimed_slot(client, tiny_video_bytes, suffix="50")
        admin_token = await _make_admin_token(email="settle-admin-50@clout-platform.com")

        settle_resp = await client.post(
            f"/api/v1/admin/slots/{slot['id']}/settle",
            json={"delivered_pct": "50"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert settle_resp.json()["status"] == "partially_completed"

        wallet_resp = await client.get(
            "/api/v1/influencers/me/wallet", headers={"Authorization": f"Bearer {inf_token}"}
        )
        expected = Decimal(str(slot["budget_allocated"])) * Decimal("0.5")
        assert Decimal(str(wallet_resp.json()["balance"])) == expected

    async def test_settle_zero_marks_failed_with_no_payment(self, client, tiny_video_bytes):
        inf_token, slot = await self._claimed_slot(client, tiny_video_bytes, suffix="0")
        admin_token = await _make_admin_token(email="settle-admin-0@clout-platform.com")

        settle_resp = await client.post(
            f"/api/v1/admin/slots/{slot['id']}/settle",
            json={"delivered_pct": "0"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert settle_resp.json()["status"] == "failed"

        wallet_resp = await client.get(
            "/api/v1/influencers/me/wallet", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert Decimal(str(wallet_resp.json()["balance"])) == Decimal("0")

        profile_resp = await client.get("/api/v1/influencers/me", headers={"Authorization": f"Bearer {inf_token}"})
        assert profile_resp.json()["failed_slots_count"] == 1

    async def test_cannot_settle_unclaimed_slot(self, client, tiny_video_bytes):
        _, _, body = await _create_funded_campaign(
            client,
            tiny_video_bytes,
            brand_email="settle-open@example.com",
            phone_number="0788600002",
            platforms=["tiktok"],
            slot_count=1,
        )
        admin_token = await _make_admin_token(email="settle-admin-open@clout-platform.com")

        resp = await client.post(
            f"/api/v1/admin/slots/{body['slots'][0]['id']}/settle",
            json={"delivered_pct": "100"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400

    async def test_non_admin_cannot_settle(self, client, tiny_video_bytes):
        inf_token, slot = await self._claimed_slot(client, tiny_video_bytes, suffix="rbac")
        resp = await client.post(
            f"/api/v1/admin/slots/{slot['id']}/settle",
            json={"delivered_pct": "100"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert resp.status_code == 403


class TestPayouts:
    async def _settled_influencer(self, client, tiny_video_bytes, *, suffix: str) -> tuple[str, Decimal]:
        token, campaign_id, body = await _create_funded_campaign(
            client,
            tiny_video_bytes,
            brand_email=f"payout-brand-{suffix}@example.com",
            phone_number="0788700001",
            platforms=["tiktok"],
            slot_count=1,
            target_views=10_000,
        )
        slot = body["slots"][0]
        inf_token = await register_influencer_token(
            client, email=f"payout-inf-{suffix}@example.com", username=f"payoutinf{suffix}"
        )
        await client.post(f"/api/v1/slots/{slot['id']}/claim", headers={"Authorization": f"Bearer {inf_token}"})

        admin_token = await _make_admin_token(email=f"payout-admin-{suffix}@clout-platform.com")
        await client.post(
            f"/api/v1/admin/slots/{slot['id']}/settle",
            json={"delivered_pct": "100"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        wallet_resp = await client.get(
            "/api/v1/influencers/me/wallet", headers={"Authorization": f"Bearer {inf_token}"}
        )
        return inf_token, Decimal(str(wallet_resp.json()["balance"]))

    async def test_request_payout_debits_wallet_and_splits_fee(self, client, tiny_video_bytes):
        inf_token, balance = await self._settled_influencer(client, tiny_video_bytes, suffix="a")

        payout_resp = await client.post(
            "/api/v1/influencers/me/payouts",
            json={"amount": str(balance), "phone_number": "0788800001"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert payout_resp.status_code == 201
        body = payout_resp.json()
        assert body["status"] == "pending"
        assert Decimal(str(body["fee_pct"])) == Decimal("0.1000")
        assert Decimal(str(body["fee_amount"])) + Decimal(str(body["net_amount"])) == Decimal(str(body["amount"]))
        assert Decimal(str(body["fee_amount"])) == balance * Decimal("0.1000")

        wallet_resp = await client.get(
            "/api/v1/influencers/me/wallet", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert Decimal(str(wallet_resp.json()["balance"])) == Decimal("0")

    async def test_payout_exceeding_balance_rejected(self, client, tiny_video_bytes):
        inf_token, balance = await self._settled_influencer(client, tiny_video_bytes, suffix="b")

        resp = await client.post(
            "/api/v1/influencers/me/payouts",
            json={"amount": str(balance + Decimal("1")), "phone_number": "0788800002"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert resp.status_code == 400

        wallet_resp = await client.get(
            "/api/v1/influencers/me/wallet", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert Decimal(str(wallet_resp.json()["balance"])) == balance  # untouched

    async def test_payout_status_resolves_to_failed_and_reverses_hold(self, client, tiny_video_bytes):
        inf_token, balance = await self._settled_influencer(client, tiny_video_bytes, suffix="c")

        payout_resp = await client.post(
            "/api/v1/influencers/me/payouts",
            json={"amount": str(balance), "phone_number": "0788880000"},  # ends in 0000 -> simulated failure
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        payout_id = payout_resp.json()["id"]

        status_resp = await client.get(
            f"/api/v1/influencers/me/payouts/{payout_id}", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert status_resp.json()["status"] == "failed"

        wallet_resp = await client.get(
            "/api/v1/influencers/me/wallet", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert Decimal(str(wallet_resp.json()["balance"])) == balance  # fully reversed

    async def test_concurrent_payout_requests_cannot_overdraw_wallet(self, client, tiny_video_bytes):
        inf_token, balance = await self._settled_influencer(client, tiny_video_bytes, suffix="d")
        more_than_half = (balance / 2) + Decimal("1")

        results = await asyncio.gather(
            client.post(
                "/api/v1/influencers/me/payouts",
                json={"amount": str(more_than_half), "phone_number": "0788900001"},
                headers={"Authorization": f"Bearer {inf_token}"},
            ),
            client.post(
                "/api/v1/influencers/me/payouts",
                json={"amount": str(more_than_half), "phone_number": "0788900002"},
                headers={"Authorization": f"Bearer {inf_token}"},
            ),
        )
        status_codes = sorted(r.status_code for r in results)
        assert status_codes == [201, 400], "exactly one payout must win, the other must be rejected for insufficient balance"

    async def test_list_payouts(self, client, tiny_video_bytes):
        inf_token, balance = await self._settled_influencer(client, tiny_video_bytes, suffix="e")
        await client.post(
            "/api/v1/influencers/me/payouts",
            json={"amount": str(balance), "phone_number": "0788900003"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        list_resp = await client.get("/api/v1/influencers/me/payouts", headers={"Authorization": f"Bearer {inf_token}"})
        assert list_resp.json()["total"] == 1


class TestReconciliationTask:
    async def test_reconcile_pending_payments_resolves_via_provider_status(self, client, tiny_video_bytes):
        from app.tasks.payment_reconciliation_tasks import reconcile_pending_payments

        token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="reconcile-fund@example.com")
        create_resp = await _create_draft_campaign(client, token, ad_id)
        campaign_id = create_resp.json()["id"]
        await client.post(
            f"/api/v1/campaigns/{campaign_id}/fund",
            json={"phone_number": "0788999999"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resolved_count = await reconcile_pending_payments()
        assert resolved_count == 1

        detail = await client.get(f"/api/v1/campaigns/{campaign_id}", headers={"Authorization": f"Bearer {token}"})
        assert detail.json()["status"] == "listed"
