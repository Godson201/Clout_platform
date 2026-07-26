from tests.test_admin_flow import _make_admin_token
from tests.test_auth_flow import _register_brand, _register_influencer


class TestAdminAnnouncements:
    async def test_admin_can_create_and_list_all_announcements(self, client):
        admin_token = await _make_admin_token(email="ann-admin@clout.local")

        resp = await client.post(
            "/api/v1/admin/announcements",
            json={"title": "Platform maintenance", "body": "Brief downtime Sunday.", "audience": "all"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["is_active"] is True

        list_resp = await client.get("/api/v1/admin/announcements", headers={"Authorization": f"Bearer {admin_token}"})
        assert len(list_resp.json()) == 1

    async def test_non_admin_cannot_create_announcement(self, client):
        brand_resp = await _register_brand(client, email="ann-brand@example.com")
        token = brand_resp.json()["access_token"]

        resp = await client.post(
            "/api/v1/admin/announcements",
            json={"title": "Hack attempt", "body": "...", "audience": "all"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_admin_can_deactivate_announcement(self, client):
        admin_token = await _make_admin_token(email="deact-admin@clout.local")
        create_resp = await client.post(
            "/api/v1/admin/announcements",
            json={"title": "Temp notice", "body": "Will be retracted.", "audience": "all"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        announcement_id = create_resp.json()["id"]

        deactivate_resp = await client.patch(
            f"/api/v1/admin/announcements/{announcement_id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert deactivate_resp.status_code == 200
        assert deactivate_resp.json()["is_active"] is False


class TestAnnouncementAudience:
    async def test_audience_filtering_by_user_type(self, client):
        admin_token = await _make_admin_token(email="audience-admin@clout.local")
        await client.post(
            "/api/v1/admin/announcements",
            json={"title": "For everyone", "body": "...", "audience": "all"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        await client.post(
            "/api/v1/admin/announcements",
            json={"title": "For brands only", "body": "...", "audience": "brands"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        await client.post(
            "/api/v1/admin/announcements",
            json={"title": "For influencers only", "body": "...", "audience": "influencers"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        brand_resp = await _register_brand(client, email="audience-brand@example.com")
        brand_token = brand_resp.json()["access_token"]
        inf_resp = await _register_influencer(client, email="audience-inf@example.com", username="audienceinf")
        inf_token = inf_resp.json()["access_token"]

        brand_feed = await client.get("/api/v1/announcements", headers={"Authorization": f"Bearer {brand_token}"})
        inf_feed = await client.get("/api/v1/announcements", headers={"Authorization": f"Bearer {inf_token}"})

        brand_titles = {a["title"] for a in brand_feed.json()}
        inf_titles = {a["title"] for a in inf_feed.json()}

        assert brand_titles == {"For everyone", "For brands only"}
        assert inf_titles == {"For everyone", "For influencers only"}

    async def test_inactive_announcement_hidden_from_feed(self, client):
        admin_token = await _make_admin_token(email="inactive-admin@clout.local")
        create_resp = await client.post(
            "/api/v1/admin/announcements",
            json={"title": "Retracted notice", "body": "...", "audience": "all"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        announcement_id = create_resp.json()["id"]
        await client.patch(
            f"/api/v1/admin/announcements/{announcement_id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        brand_resp = await _register_brand(client, email="inactive-brand@example.com")
        brand_token = brand_resp.json()["access_token"]
        feed = await client.get("/api/v1/announcements", headers={"Authorization": f"Bearer {brand_token}"})
        assert "Retracted notice" not in {a["title"] for a in feed.json()}
