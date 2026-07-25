from urllib.parse import parse_qs, urlparse

from app.core.platform_capabilities import PlatformCapabilities
from tests.factories import fund_and_confirm_campaign, register_brand_with_ready_ad, register_influencer_token
from tests.test_campaigns import _create_draft_campaign


def _extract_code_and_state(authorization_url: str) -> tuple[str, str]:
    query = parse_qs(urlparse(authorization_url).query)
    return query["code"][0], query["state"][0]


async def _connect_account(client, token: str, platform: str = "tiktok") -> dict:
    connect_resp = await client.get(f"/api/v1/social-accounts/connect/{platform}", headers={"Authorization": f"Bearer {token}"})
    assert connect_resp.status_code == 200, connect_resp.json()
    code, state = _extract_code_and_state(connect_resp.json()["authorization_url"])

    callback_resp = await client.post(
        f"/api/v1/social-accounts/callback/{platform}",
        json={"code": code, "state": state},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert callback_resp.status_code == 201, callback_resp.json()
    return callback_resp.json()


async def _claimed_slot(client, tiny_video_bytes, *, brand_email: str, inf_email: str, inf_username: str, platform: str = "tiktok"):
    brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email=brand_email)
    create_resp = await _create_draft_campaign(client, brand_token, ad_id, platforms=[platform], slot_count=1)
    campaign_id = create_resp.json()["id"]
    body = await fund_and_confirm_campaign(client, brand_token, campaign_id, phone_number="0788123123")
    slot = body["slots"][0]

    inf_token = await register_influencer_token(client, email=inf_email, username=inf_username)
    claim_resp = await client.post(f"/api/v1/slots/{slot['id']}/claim", headers={"Authorization": f"Bearer {inf_token}"})
    assert claim_resp.status_code == 200
    return inf_token, slot


class TestSocialAccountConnection:
    async def test_connect_and_callback_creates_account(self, client, tiny_video_bytes):
        inf_token = await register_influencer_token(client, email="connect-inf@example.com", username="connectinf")
        account = await _connect_account(client, inf_token, platform="tiktok")

        assert account["platform"] == "tiktok"
        assert account["status"] == "active"
        assert account["handle"] == "mockuser-tiktok"

        list_resp = await client.get("/api/v1/social-accounts/me", headers={"Authorization": f"Bearer {inf_token}"})
        assert len(list_resp.json()) == 1

    async def test_brand_can_also_connect_an_account(self, client, tiny_video_bytes):
        brand_token, _ = await register_brand_with_ready_ad(client, tiny_video_bytes, email="connect-brand@example.com")
        account = await _connect_account(client, brand_token, platform="instagram")
        assert account["platform"] == "instagram"

    async def test_reconnecting_same_platform_updates_existing_account(self, client, tiny_video_bytes):
        inf_token = await register_influencer_token(client, email="reconnect-inf@example.com", username="reconnectinf")
        first = await _connect_account(client, inf_token, platform="tiktok")
        second = await _connect_account(client, inf_token, platform="tiktok")

        assert first["id"] == second["id"]
        list_resp = await client.get("/api/v1/social-accounts/me", headers={"Authorization": f"Bearer {inf_token}"})
        assert len(list_resp.json()) == 1

    async def test_invalid_state_rejected(self, client, tiny_video_bytes):
        inf_token = await register_influencer_token(client, email="badstate-inf@example.com", username="badstateinf")
        resp = await client.post(
            "/api/v1/social-accounts/callback/tiktok",
            json={"code": "mock-code-bogus", "state": "bogus-state-never-issued"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert resp.status_code == 400

    async def test_state_cannot_be_replayed(self, client, tiny_video_bytes):
        inf_token = await register_influencer_token(client, email="replay-inf@example.com", username="replayinf")
        connect_resp = await client.get(
            "/api/v1/social-accounts/connect/tiktok", headers={"Authorization": f"Bearer {inf_token}"}
        )
        code, state = _extract_code_and_state(connect_resp.json()["authorization_url"])

        first = await client.post(
            "/api/v1/social-accounts/callback/tiktok",
            json={"code": code, "state": state},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert first.status_code == 201

        replay = await client.post(
            "/api/v1/social-accounts/callback/tiktok",
            json={"code": code, "state": state},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert replay.status_code == 400

    async def test_disconnect_account(self, client, tiny_video_bytes):
        inf_token = await register_influencer_token(client, email="disconnect-inf@example.com", username="disconnectinf")
        account = await _connect_account(client, inf_token, platform="tiktok")

        del_resp = await client.delete(
            f"/api/v1/social-accounts/{account['id']}", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert del_resp.status_code == 204

        list_resp = await client.get("/api/v1/social-accounts/me", headers={"Authorization": f"Bearer {inf_token}"})
        assert list_resp.json()[0]["status"] == "disconnected"


class TestAutoPublishFlow:
    """Exercises the AUTO publish + metrics path via the mock adapter's claimed
    full capability — proves the code that will run once a platform's real
    capability flips on actually works, even though production runs manual
    mode today (see TestManualPublishFlow)."""

    async def test_creating_post_auto_publishes_and_updates_slot(self, client, tiny_video_bytes):
        inf_token, slot = await _claimed_slot(
            client, tiny_video_bytes, brand_email="autopub-brand@example.com",
            inf_email="autopub-inf@example.com", inf_username="autopubinf",
        )
        account = await _connect_account(client, inf_token, platform="tiktok")

        post_resp = await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": account["id"], "caption": "Check this out!"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert post_resp.status_code == 201, post_resp.json()
        body = post_resp.json()
        assert body["publish_mode"] == "auto"
        assert body["status"] == "published"
        assert body["external_post_id"]
        assert body["post_url"]

        slot_resp = await client.get("/api/v1/slots/mine", headers={"Authorization": f"Bearer {inf_token}"})
        assert slot_resp.json()[0]["status"] == "published"

    async def test_platform_mismatch_rejected(self, client, tiny_video_bytes):
        inf_token, slot = await _claimed_slot(
            client, tiny_video_bytes, brand_email="mismatch-brand@example.com",
            inf_email="mismatch-inf@example.com", inf_username="mismatchinf", platform="tiktok",
        )
        account = await _connect_account(client, inf_token, platform="instagram")

        resp = await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": account["id"], "caption": "wrong platform"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert resp.status_code == 400

    async def test_cannot_post_twice_to_same_slot(self, client, tiny_video_bytes):
        inf_token, slot = await _claimed_slot(
            client, tiny_video_bytes, brand_email="doublepost-brand@example.com",
            inf_email="doublepost-inf@example.com", inf_username="doublepostinf",
        )
        account = await _connect_account(client, inf_token, platform="tiktok")

        first = await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": account["id"], "caption": "first"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert first.status_code == 201

        second = await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": account["id"], "caption": "second"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert second.status_code == 400

    async def test_non_owner_cannot_post_to_slot(self, client, tiny_video_bytes):
        _, slot = await _claimed_slot(
            client, tiny_video_bytes, brand_email="owned-brand@example.com",
            inf_email="owner-inf@example.com", inf_username="ownerinf",
        )
        other_inf_token = await register_influencer_token(client, email="intruder@example.com", username="intruder")
        account = await _connect_account(client, other_inf_token, platform="tiktok")

        resp = await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": account["id"], "caption": "not mine"},
            headers={"Authorization": f"Bearer {other_inf_token}"},
        )
        assert resp.status_code == 404


class TestMetricsPolling:
    async def test_polling_metrics_appends_growing_snapshots_and_tracks_slot(self, client, tiny_video_bytes):
        inf_token, slot = await _claimed_slot(
            client, tiny_video_bytes, brand_email="metrics-brand@example.com",
            inf_email="metrics-inf@example.com", inf_username="metricsinf",
        )
        account = await _connect_account(client, inf_token, platform="tiktok")
        await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": account["id"], "caption": "metrics test"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )

        first_poll = await client.get(
            f"/api/v1/slots/{slot['id']}/post/metrics", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert first_poll.status_code == 200
        assert len(first_poll.json()) == 1
        first_views = first_poll.json()[0]["views"]

        second_poll = await client.get(
            f"/api/v1/slots/{slot['id']}/post/metrics", headers={"Authorization": f"Bearer {inf_token}"}
        )
        snapshots = second_poll.json()
        assert len(snapshots) == 2
        assert snapshots[1]["views"] > first_views, "later snapshot should show growth, not a flat/duplicate reading"

        slot_resp = await client.get("/api/v1/slots/mine", headers={"Authorization": f"Bearer {inf_token}"})
        assert slot_resp.json()[0]["status"] == "tracking"

    async def test_reconciliation_task_polls_all_published_posts(self, client, tiny_video_bytes):
        from app.tasks.social_metrics_tasks import poll_all_active_post_metrics

        inf_token, slot = await _claimed_slot(
            client, tiny_video_bytes, brand_email="reconcile-social-brand@example.com",
            inf_email="reconcile-social-inf@example.com", inf_username="reconcilesocialinf",
        )
        account = await _connect_account(client, inf_token, platform="tiktok")
        await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": account["id"], "caption": "task test"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )

        polled_count = await poll_all_active_post_metrics()
        assert polled_count == 1


class TestManualPublishFlow:
    """Forces every platform's capability to today's honest, all-False reality
    (see app.core.platform_capabilities) even though the test suite otherwise
    runs against the mock adapter's claimed full capability — proving the
    manual/assisted flow that actually ships works too, not just the aspirational
    auto path."""

    async def test_manual_mode_requires_url_submission_before_publishing(self, client, tiny_video_bytes, monkeypatch):
        no_capability = PlatformCapabilities(
            can_auto_publish=False, can_schedule=False, can_fetch_metrics=False, can_fetch_comments=False
        )
        monkeypatch.setattr("app.services.social_posting.get_capabilities", lambda platform: no_capability)

        inf_token, slot = await _claimed_slot(
            client, tiny_video_bytes, brand_email="manual-brand@example.com",
            inf_email="manual-inf@example.com", inf_username="manualinf",
        )
        account = await _connect_account(client, inf_token, platform="tiktok")

        post_resp = await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": account["id"], "caption": "manual post"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert post_resp.status_code == 201
        body = post_resp.json()
        assert body["publish_mode"] == "manual"
        assert body["status"] == "pending"
        assert body["external_post_id"] is None

        slot_resp = await client.get("/api/v1/slots/mine", headers={"Authorization": f"Bearer {inf_token}"})
        assert slot_resp.json()[0]["status"] == "claimed"  # unchanged until URL submitted

        submit_resp = await client.patch(
            f"/api/v1/slots/{slot['id']}/post/submit-url",
            json={"post_url": "https://www.tiktok.com/@manualinf/video/1234567890"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "published"

        slot_resp = await client.get("/api/v1/slots/mine", headers={"Authorization": f"Bearer {inf_token}"})
        assert slot_resp.json()[0]["status"] == "published"

        # No external_post_id was ever assigned, so metrics polling is a no-op —
        # exactly the "can't fetch metrics for a manually-posted video" reality.
        metrics_resp = await client.get(
            f"/api/v1/slots/{slot['id']}/post/metrics", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert metrics_resp.json() == []

    async def test_cannot_submit_url_twice(self, client, tiny_video_bytes, monkeypatch):
        no_capability = PlatformCapabilities(
            can_auto_publish=False, can_schedule=False, can_fetch_metrics=False, can_fetch_comments=False
        )
        monkeypatch.setattr("app.services.social_posting.get_capabilities", lambda platform: no_capability)

        inf_token, slot = await _claimed_slot(
            client, tiny_video_bytes, brand_email="resubmit-brand@example.com",
            inf_email="resubmit-inf@example.com", inf_username="resubmitinf",
        )
        account = await _connect_account(client, inf_token, platform="tiktok")
        await client.post(
            f"/api/v1/slots/{slot['id']}/post",
            json={"social_account_id": account["id"], "caption": "manual post"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        await client.patch(
            f"/api/v1/slots/{slot['id']}/post/submit-url",
            json={"post_url": "https://www.tiktok.com/@resubmitinf/video/1"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )

        second = await client.patch(
            f"/api/v1/slots/{slot['id']}/post/submit-url",
            json={"post_url": "https://www.tiktok.com/@resubmitinf/video/2"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert second.status_code == 400
