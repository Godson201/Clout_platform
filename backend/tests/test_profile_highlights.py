from tests.test_auth_flow import _register_brand, _register_influencer


class TestProfileHighlights:
    async def test_influencer_can_add_award_and_event(self, client):
        resp = await _register_influencer(client, email="highlights-inf@example.com", username="highlightsinf")
        token = resp.json()["access_token"]

        award_resp = await client.post(
            "/api/v1/profile-highlights",
            json={"category": "award", "title": "Creator of the Year", "subtitle": "Rwanda Digital Awards", "occurred_on": "2025-11-01"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert award_resp.status_code == 201
        assert award_resp.json()["category"] == "award"

        event_resp = await client.post(
            "/api/v1/profile-highlights",
            json={"category": "event", "title": "Kigali Creator Summit", "subtitle": "Kigali Convention Centre"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert event_resp.status_code == 201

        list_resp = await client.get("/api/v1/profile-highlights/me", headers={"Authorization": f"Bearer {token}"})
        assert len(list_resp.json()) == 2

    async def test_brand_can_add_highlights_too(self, client):
        resp = await _register_brand(client, email="highlights-brand@example.com")
        token = resp.json()["access_token"]

        create_resp = await client.post(
            "/api/v1/profile-highlights",
            json={"category": "award", "title": "Best New Brand"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert create_resp.status_code == 201

    async def test_can_delete_own_highlight(self, client):
        resp = await _register_influencer(client, email="delete-highlight-inf@example.com", username="deletehlinf")
        token = resp.json()["access_token"]

        create_resp = await client.post(
            "/api/v1/profile-highlights",
            json={"category": "award", "title": "To be deleted"},
            headers={"Authorization": f"Bearer {token}"},
        )
        highlight_id = create_resp.json()["id"]

        delete_resp = await client.delete(
            f"/api/v1/profile-highlights/{highlight_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert delete_resp.status_code == 204

        list_resp = await client.get("/api/v1/profile-highlights/me", headers={"Authorization": f"Bearer {token}"})
        assert list_resp.json() == []

    async def test_cannot_delete_someone_elses_highlight(self, client):
        owner_resp = await _register_influencer(client, email="owner-hl@example.com", username="ownerhl")
        owner_token = owner_resp.json()["access_token"]
        create_resp = await client.post(
            "/api/v1/profile-highlights",
            json={"category": "award", "title": "Owner's award"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        highlight_id = create_resp.json()["id"]

        other_resp = await _register_influencer(client, email="other-hl@example.com", username="otherhl")
        other_token = other_resp.json()["access_token"]

        delete_resp = await client.delete(
            f"/api/v1/profile-highlights/{highlight_id}", headers={"Authorization": f"Bearer {other_token}"}
        )
        assert delete_resp.status_code == 404
