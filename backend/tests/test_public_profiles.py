from tests.test_auth_flow import _register_brand, _register_influencer


class TestPublicInfluencerProfile:
    async def test_visible_by_default(self, client):
        resp = await _register_influencer(client, email="pub-inf@example.com", username="pubinf")
        token = resp.json()["access_token"]
        influencer_id = resp.json()["user"]["id"]

        await client.patch(
            "/api/v1/influencers/me",
            json={"bio": "I make cooking videos.", "legacy": "10 years in food content.", "location": "Kigali"},
            headers={"Authorization": f"Bearer {token}"},
        )

        viewer_resp = await _register_brand(client, email="pub-viewer@example.com")
        viewer_token = viewer_resp.json()["access_token"]

        public_resp = await client.get(
            f"/api/v1/influencers/{influencer_id}/public", headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert public_resp.status_code == 200
        body = public_resp.json()
        assert body["bio"] == "I make cooking videos."
        assert body["legacy"] == "10 years in food content."
        assert body["location"] == "Kigali"

    async def test_hidden_sections_are_null_to_other_viewers(self, client):
        resp = await _register_influencer(client, email="hidden-inf@example.com", username="hiddeninf")
        token = resp.json()["access_token"]
        influencer_id = resp.json()["user"]["id"]

        await client.patch(
            "/api/v1/influencers/me",
            json={
                "bio": "Secret bio",
                "legacy": "Secret legacy",
                "location": "Kigali",
                "visibility_settings": {"about": False, "legacy": False, "location": False},
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        viewer_resp = await _register_brand(client, email="hidden-viewer@example.com")
        viewer_token = viewer_resp.json()["access_token"]

        public_resp = await client.get(
            f"/api/v1/influencers/{influencer_id}/public", headers={"Authorization": f"Bearer {viewer_token}"}
        )
        body = public_resp.json()
        assert body["bio"] is None
        assert body["legacy"] is None
        assert body["location"] is None
        # Username/display name are never gated — always shown.
        assert body["username"] == "hiddeninf"

    async def test_owner_still_sees_full_profile_via_me_endpoint(self, client):
        resp = await _register_influencer(client, email="owner-view-inf@example.com", username="ownerviewinf")
        token = resp.json()["access_token"]

        await client.patch(
            "/api/v1/influencers/me",
            json={"bio": "My bio", "visibility_settings": {"about": False}},
            headers={"Authorization": f"Bearer {token}"},
        )

        me_resp = await client.get("/api/v1/influencers/me", headers={"Authorization": f"Bearer {token}"})
        assert me_resp.json()["bio"] == "My bio"

    async def test_awards_hidden_when_toggled_off(self, client):
        resp = await _register_influencer(client, email="awards-hidden-inf@example.com", username="awardshiddeninf")
        token = resp.json()["access_token"]
        influencer_id = resp.json()["user"]["id"]

        await client.post(
            "/api/v1/profile-highlights",
            json={"category": "award", "title": "Secret Award"},
            headers={"Authorization": f"Bearer {token}"},
        )
        await client.patch(
            "/api/v1/influencers/me",
            json={"visibility_settings": {"awards": False}},
            headers={"Authorization": f"Bearer {token}"},
        )

        viewer_resp = await _register_brand(client, email="awards-viewer@example.com")
        viewer_token = viewer_resp.json()["access_token"]
        public_resp = await client.get(
            f"/api/v1/influencers/{influencer_id}/public", headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert public_resp.json()["awards"] == []


class TestPublicBrandProfile:
    async def test_visible_by_default(self, client):
        resp = await _register_brand(client, email="pub-brand@example.com")
        token = resp.json()["access_token"]
        brand_id = resp.json()["user"]["id"]

        await client.patch(
            "/api/v1/brands/me",
            json={"description": "We sell great coffee.", "legacy": "Family business since 1990."},
            headers={"Authorization": f"Bearer {token}"},
        )

        viewer_resp = await _register_influencer(client, email="pub-brand-viewer@example.com", username="pubbrandviewer")
        viewer_token = viewer_resp.json()["access_token"]

        public_resp = await client.get(
            f"/api/v1/brands/{brand_id}/public", headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert public_resp.status_code == 200
        assert public_resp.json()["description"] == "We sell great coffee."
        assert public_resp.json()["legacy"] == "Family business since 1990."

    async def test_contact_info_hidden_when_toggled_off(self, client):
        resp = await _register_brand(client, email="contact-hidden-brand@example.com")
        token = resp.json()["access_token"]
        brand_id = resp.json()["user"]["id"]

        await client.patch(
            "/api/v1/brands/me",
            json={"contact_phone": "0788111222", "visibility_settings": {"contact": False}},
            headers={"Authorization": f"Bearer {token}"},
        )

        viewer_resp = await _register_influencer(client, email="contact-viewer@example.com", username="contactviewer")
        viewer_token = viewer_resp.json()["access_token"]
        public_resp = await client.get(
            f"/api/v1/brands/{brand_id}/public", headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert public_resp.json()["contact_phone"] is None
