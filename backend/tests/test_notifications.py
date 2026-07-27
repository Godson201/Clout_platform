from tests.factories import connected_brand_and_influencer, register_influencer_token
from tests.test_advertisements import _brand_token, _get_template_id


async def _create_ad(client, token: str, title: str = "Notify test ad") -> str:
    template_id = await _get_template_id(client, token)
    resp = await client.post(
        "/api/v1/advertisements",
        json={"template_id": template_id, "title": title},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


class TestNewBrandMediaNotifications:
    async def test_image_upload_notifies_existing_influencers(self, client):
        inf_token = await register_influencer_token(client, email="notify-inf-1@example.com", username="notifyinf1")
        brand_token = await _brand_token(client, email="notify-brand-1@example.com")
        ad_id = await _create_ad(client, brand_token)

        upload_resp = await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "image"},
            files={"file": ("photo.jpg", b"fake image bytes", "image/jpeg")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert upload_resp.status_code == 201
        assert upload_resp.json()["status"] == "ready"

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {inf_token}"})
        assert feed.status_code == 200
        types = [n["type"] for n in feed.json()]
        assert "new_brand_media" in types

        unread = await client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {inf_token}"})
        assert unread.json()["unread_count"] == 1

    async def test_video_upload_notifies_influencers_once_ready(self, client, tiny_video_bytes):
        inf_token = await register_influencer_token(client, email="notify-inf-2@example.com", username="notifyinf2")
        brand_token = await _brand_token(client, email="notify-brand-2@example.com")
        ad_id = await _create_ad(client, brand_token)

        upload_resp = await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "video"},
            files={"file": ("clip.mp4", tiny_video_bytes, "video/mp4")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert upload_resp.json()["status"] == "ready"

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {inf_token}"})
        notif = next(n for n in feed.json() if n["type"] == "new_brand_media")
        assert notif["data"]["asset_type"] == "video"
        assert notif["link"] == "/influencer/marketplace"

    async def test_logo_upload_does_not_notify(self, client):
        inf_token = await register_influencer_token(client, email="notify-inf-3@example.com", username="notifyinf3")
        brand_token = await _brand_token(client, email="notify-brand-3@example.com")
        ad_id = await _create_ad(client, brand_token)

        await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "logo"},
            files={"file": ("logo.png", b"fake logo bytes", "image/png")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {inf_token}"})
        assert feed.json() == []

    async def test_brand_does_not_receive_the_influencer_broadcast(self, client):
        await register_influencer_token(client, email="notify-inf-4@example.com", username="notifyinf4")
        brand_token = await _brand_token(client, email="notify-brand-4@example.com")
        ad_id = await _create_ad(client, brand_token)

        await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "image"},
            files={"file": ("photo.jpg", b"fake image bytes", "image/jpeg")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {brand_token}"})
        assert feed.json() == []

    async def test_mark_read_and_mark_all_read(self, client):
        inf_token = await register_influencer_token(client, email="notify-inf-5@example.com", username="notifyinf5")
        brand_token = await _brand_token(client, email="notify-brand-5@example.com")
        ad_id = await _create_ad(client, brand_token)
        await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "image"},
            files={"file": ("photo.jpg", b"fake image bytes", "image/jpeg")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {inf_token}"})
        notif_id = feed.json()[0]["id"]

        read_resp = await client.post(
            f"/api/v1/notifications/{notif_id}/read", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert read_resp.status_code == 204

        unread = await client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {inf_token}"})
        assert unread.json()["unread_count"] == 0

        await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "image"},
            files={"file": ("photo2.jpg", b"more fake bytes", "image/jpeg")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "image"},
            files={"file": ("photo3.jpg", b"even more fake bytes", "image/jpeg")},
            headers={"Authorization": f"Bearer {brand_token}"},
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
