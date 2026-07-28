from tests.factories import connected_brand_and_influencer, register_influencer_token, wait_for_asset_ready
from tests.test_admin_flow import _make_admin_token
from tests.test_advertisements import _brand_token, _get_template_id


async def _create_ad(client, token: str, title: str = "Notify test ad") -> str:
    template_id = await _get_template_id(client, token)
    resp = await client.post(
        "/api/v1/advertisements",
        json={"template_id": template_id, "title": title},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


async def _upload_image(client, brand_token: str, ad_id: str, filename: str = "photo.jpg") -> str:
    resp = await client.post(
        f"/api/v1/advertisements/{ad_id}/assets",
        data={"asset_type": "image"},
        files={"file": (filename, b"fake image bytes", "image/jpeg")},
        headers={"Authorization": f"Bearer {brand_token}"},
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()["id"]


class TestAssetModerationGate:
    async def test_upload_is_pending_and_does_not_notify_until_approved(self, client):
        inf_token = await register_influencer_token(client, email="notify-inf-1@example.com", username="notifyinf1")
        brand_token = await _brand_token(client, email="notify-brand-1@example.com")
        ad_id = await _create_ad(client, brand_token)

        asset_id = await _upload_image(client, brand_token, ad_id)

        detail = await client.get(f"/api/v1/advertisements/{ad_id}", headers={"Authorization": f"Bearer {brand_token}"})
        asset = detail.json()["assets"][0]
        assert asset["status"] == "ready"
        assert asset["moderation_status"] == "pending"

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {inf_token}"})
        assert feed.json() == []

        admin_token = await _make_admin_token(email="moderation-admin-1@clout.local")
        queue = await client.get("/api/v1/admin/asset-moderation", headers={"Authorization": f"Bearer {admin_token}"})
        assert queue.status_code == 200
        assert any(item["id"] == asset_id for item in queue.json())

        approve_resp = await client.post(
            f"/api/v1/admin/asset-moderation/{asset_id}/approve", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["moderation_status"] == "approved"

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {inf_token}"})
        types = [n["type"] for n in feed.json()]
        assert "new_brand_media" in types

        unread = await client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {inf_token}"})
        assert unread.json()["unread_count"] == 1

    async def test_video_notifies_influencers_only_once_approved(self, client, tiny_video_bytes):
        inf_token = await register_influencer_token(client, email="notify-inf-2@example.com", username="notifyinf2")
        brand_token = await _brand_token(client, email="notify-brand-2@example.com")
        ad_id = await _create_ad(client, brand_token)

        upload_resp = await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "video"},
            files={"file": ("clip.mp4", tiny_video_bytes, "video/mp4")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        asset = await wait_for_asset_ready(client, ad_id, upload_resp.json()["id"], brand_token)
        assert asset["status"] == "ready"
        assert asset["moderation_status"] == "pending"

        admin_token = await _make_admin_token(email="moderation-admin-2@clout.local")
        await client.post(
            f"/api/v1/admin/asset-moderation/{asset['id']}/approve", headers={"Authorization": f"Bearer {admin_token}"}
        )

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {inf_token}"})
        notif = next(n for n in feed.json() if n["type"] == "new_brand_media")
        assert notif["data"]["asset_type"] == "video"
        assert notif["link"] == "/influencer/marketplace"

    async def test_rejected_asset_never_notifies_and_shows_reason_to_brand(self, client):
        inf_token = await register_influencer_token(client, email="notify-inf-3@example.com", username="notifyinf3")
        brand_token = await _brand_token(client, email="notify-brand-3@example.com")
        ad_id = await _create_ad(client, brand_token)
        asset_id = await _upload_image(client, brand_token, ad_id)

        admin_token = await _make_admin_token(email="moderation-admin-3@clout.local")
        reject_resp = await client.post(
            f"/api/v1/admin/asset-moderation/{asset_id}/reject",
            json={"reason": "Low resolution, please re-upload."},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["moderation_status"] == "rejected"

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {inf_token}"})
        assert feed.json() == []

        detail = await client.get(f"/api/v1/advertisements/{ad_id}", headers={"Authorization": f"Bearer {brand_token}"})
        asset = detail.json()["assets"][0]
        assert asset["moderation_status"] == "rejected"
        assert asset["moderation_note"] == "Low resolution, please re-upload."

        queue = await client.get("/api/v1/admin/asset-moderation", headers={"Authorization": f"Bearer {admin_token}"})
        assert queue.json() == []

    async def test_logo_upload_never_notifies_even_once_approved(self, client):
        inf_token = await register_influencer_token(client, email="notify-inf-4@example.com", username="notifyinf4")
        brand_token = await _brand_token(client, email="notify-brand-4@example.com")
        ad_id = await _create_ad(client, brand_token)

        upload_resp = await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "logo"},
            files={"file": ("logo.png", b"fake logo bytes", "image/png")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        asset_id = upload_resp.json()["id"]

        admin_token = await _make_admin_token(email="moderation-admin-4@clout.local")
        await client.post(
            f"/api/v1/admin/asset-moderation/{asset_id}/approve", headers={"Authorization": f"Bearer {admin_token}"}
        )

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {inf_token}"})
        assert feed.json() == []

    async def test_brand_does_not_receive_the_influencer_broadcast(self, client):
        await register_influencer_token(client, email="notify-inf-5@example.com", username="notifyinf5")
        brand_token = await _brand_token(client, email="notify-brand-5@example.com")
        ad_id = await _create_ad(client, brand_token)
        asset_id = await _upload_image(client, brand_token, ad_id)

        admin_token = await _make_admin_token(email="moderation-admin-5@clout.local")
        await client.post(
            f"/api/v1/admin/asset-moderation/{asset_id}/approve", headers={"Authorization": f"Bearer {admin_token}"}
        )

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {brand_token}"})
        assert feed.json() == []

    async def test_non_admin_cannot_access_moderation_queue(self, client):
        brand_token = await _brand_token(client, email="notify-brand-6@example.com")
        resp = await client.get("/api/v1/admin/asset-moderation", headers={"Authorization": f"Bearer {brand_token}"})
        assert resp.status_code == 403

    async def test_mark_read_and_mark_all_read(self, client):
        inf_token = await register_influencer_token(client, email="notify-inf-7@example.com", username="notifyinf7")
        brand_token = await _brand_token(client, email="notify-brand-7@example.com")
        admin_token = await _make_admin_token(email="moderation-admin-7@clout.local")
        ad_id = await _create_ad(client, brand_token)

        asset_id = await _upload_image(client, brand_token, ad_id, filename="photo1.jpg")
        await client.post(
            f"/api/v1/admin/asset-moderation/{asset_id}/approve", headers={"Authorization": f"Bearer {admin_token}"}
        )

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {inf_token}"})
        notif_id = feed.json()[0]["id"]

        read_resp = await client.post(
            f"/api/v1/notifications/{notif_id}/read", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert read_resp.status_code == 204

        unread = await client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {inf_token}"})
        assert unread.json()["unread_count"] == 0

        for filename in ("photo2.jpg", "photo3.jpg"):
            asset_id = await _upload_image(client, brand_token, ad_id, filename=filename)
            await client.post(
                f"/api/v1/admin/asset-moderation/{asset_id}/approve", headers={"Authorization": f"Bearer {admin_token}"}
            )

        unread = await client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {inf_token}"})
        assert unread.json()["unread_count"] == 2

        mark_all_resp = await client.post("/api/v1/notifications/read-all", headers={"Authorization": f"Bearer {inf_token}"})
        assert mark_all_resp.status_code == 204
        unread = await client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {inf_token}"})
        assert unread.json()["unread_count"] == 0


class TestInfluencerPublishNotifiesBrand:
    async def test_manual_publish_notifies_brand_with_influencer_location(self, client, tiny_video_bytes, monkeypatch):
        brand_token, _, influencer_token, _ = await connected_brand_and_influencer(
            client, tiny_video_bytes, brand_email="publish-notify-brand@example.com",
            influencer_email="publish-notify-inf@example.com", influencer_username="publishnotifyinf",
        )
        await client.patch(
            "/api/v1/influencers/me",
            json={"province": "Kigali City", "location": "Gasabo", "admin_sector": "Kimironko"},
            headers={"Authorization": f"Bearer {influencer_token}"},
        )

        slots_resp = await client.get("/api/v1/slots/mine", headers={"Authorization": f"Bearer {influencer_token}"})
        slot_id = slots_resp.json()[0]["id"]

        connect_resp = await client.get(
            "/api/v1/social-accounts/connect/tiktok", headers={"Authorization": f"Bearer {influencer_token}"}
        )
        from urllib.parse import parse_qs, urlparse

        query = parse_qs(urlparse(connect_resp.json()["authorization_url"]).query)
        code, state = query["code"][0], query["state"][0]
        account_resp = await client.post(
            "/api/v1/social-accounts/callback/tiktok",
            json={"code": code, "state": state},
            headers={"Authorization": f"Bearer {influencer_token}"},
        )
        account_id = account_resp.json()["id"]

        from app.core.platform_capabilities import PlatformCapabilities

        no_capability = PlatformCapabilities(
            can_auto_publish=False, can_schedule=False, can_fetch_metrics=False, can_fetch_comments=False
        )
        monkeypatch.setattr("app.services.social_posting.get_capabilities", lambda platform: no_capability)

        post_resp = await client.post(
            f"/api/v1/slots/{slot_id}/post",
            json={"social_account_id": account_id, "caption": "manual"},
            headers={"Authorization": f"Bearer {influencer_token}"},
        )
        assert post_resp.status_code == 201

        submit_resp = await client.patch(
            f"/api/v1/slots/{slot_id}/post/submit-url",
            json={"post_url": "https://www.tiktok.com/@publishnotifyinf/video/1"},
            headers={"Authorization": f"Bearer {influencer_token}"},
        )
        assert submit_resp.status_code == 200

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {brand_token}"})
        assert feed.status_code == 200
        notif = next(n for n in feed.json() if n["type"] == "influencer_post_published")
        assert "Kimironko" in notif["body"] or "Kimironko" in notif["data"]["location"]
        assert notif["data"]["platform"] == "tiktok"
        assert notif["link"].startswith("/brand/campaigns/")

    async def test_auto_publish_notifies_brand(self, client, tiny_video_bytes):
        brand_token, _, influencer_token, _ = await connected_brand_and_influencer(
            client, tiny_video_bytes, brand_email="autopub-notify-brand@example.com",
            influencer_email="autopub-notify-inf@example.com", influencer_username="autopubnotifyinf",
        )
        slots_resp = await client.get("/api/v1/slots/mine", headers={"Authorization": f"Bearer {influencer_token}"})
        slot_id = slots_resp.json()[0]["id"]

        connect_resp = await client.get(
            "/api/v1/social-accounts/connect/tiktok", headers={"Authorization": f"Bearer {influencer_token}"}
        )
        from urllib.parse import parse_qs, urlparse

        query = parse_qs(urlparse(connect_resp.json()["authorization_url"]).query)
        code, state = query["code"][0], query["state"][0]
        account_resp = await client.post(
            "/api/v1/social-accounts/callback/tiktok",
            json={"code": code, "state": state},
            headers={"Authorization": f"Bearer {influencer_token}"},
        )
        account_id = account_resp.json()["id"]

        post_resp = await client.post(
            f"/api/v1/slots/{slot_id}/post",
            json={"social_account_id": account_id, "caption": "auto"},
            headers={"Authorization": f"Bearer {influencer_token}"},
        )
        assert post_resp.status_code == 201
        assert post_resp.json()["status"] == "published"

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {brand_token}"})
        notif = next(n for n in feed.json() if n["type"] == "influencer_post_published")
        assert notif["data"]["platform"] == "tiktok"
