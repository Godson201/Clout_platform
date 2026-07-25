from tests.test_admin_flow import _make_admin_token
from tests.test_auth_flow import _register_brand


async def _brand_token(client, email="ad-brand@example.com") -> str:
    resp = await _register_brand(client, email=email)
    return resp.json()["access_token"]


async def _get_template_id(client, token: str, code: str = "product") -> str:
    resp = await client.get("/api/v1/templates", headers={"Authorization": f"Bearer {token}"})
    template = next(t for t in resp.json() if t["code"] == code)
    return template["id"]


class TestTemplates:
    async def test_seeded_templates_are_listed(self, client):
        token = await _brand_token(client)
        resp = await client.get("/api/v1/templates", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        codes = {t["code"] for t in resp.json()}
        assert {"product", "service", "song", "movie_trailer", "government", "police", "rbc"}.issubset(codes)

    async def test_templates_require_auth(self, client):
        resp = await client.get("/api/v1/templates")
        assert resp.status_code == 401

    async def test_admin_can_create_and_update_template(self, client):
        admin_token = await _make_admin_token(email="template-admin@clout-platform.com")

        create_resp = await client.post(
            "/api/v1/admin/templates",
            json={"code": "custom_test", "name": "Custom Test", "category": "general"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_resp.status_code == 201
        template_id = create_resp.json()["id"]

        dup_resp = await client.post(
            "/api/v1/admin/templates",
            json={"code": "custom_test", "name": "Dup", "category": "general"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert dup_resp.status_code == 409

        update_resp = await client.patch(
            f"/api/v1/admin/templates/{template_id}",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["is_active"] is False

    async def test_brand_cannot_manage_templates(self, client):
        token = await _brand_token(client, email="not-admin@example.com")
        resp = await client.post(
            "/api/v1/admin/templates",
            json={"code": "x", "name": "X", "category": "general"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


class TestAdvertisementCRUD:
    async def test_create_advertisement(self, client):
        token = await _brand_token(client, email="create-ad@example.com")
        template_id = await _get_template_id(client, token)

        resp = await client.post(
            "/api/v1/advertisements",
            json={"template_id": template_id, "title": "Summer Sale", "hashtags": ["#sale", "#summer"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Summer Sale"
        assert body["status"] == "draft"
        assert body["duration_seconds"] == 30  # "product" template's default_duration_seconds

    async def test_create_advertisement_with_invalid_template_rejected(self, client):
        token = await _brand_token(client, email="bad-template@example.com")
        resp = await client.post(
            "/api/v1/advertisements",
            json={"template_id": "00000000-0000-0000-0000-000000000000", "title": "Nope"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_list_advertisements_scoped_to_owner(self, client):
        token_a = await _brand_token(client, email="brand-a@example.com")
        token_b = await _brand_token(client, email="brand-b@example.com")
        template_id = await _get_template_id(client, token_a)

        await client.post(
            "/api/v1/advertisements",
            json={"template_id": template_id, "title": "A's ad"},
            headers={"Authorization": f"Bearer {token_a}"},
        )

        list_a = await client.get("/api/v1/advertisements", headers={"Authorization": f"Bearer {token_a}"})
        list_b = await client.get("/api/v1/advertisements", headers={"Authorization": f"Bearer {token_b}"})

        assert list_a.json()["total"] == 1
        assert list_b.json()["total"] == 0

    async def test_cannot_access_another_brands_advertisement(self, client):
        token_a = await _brand_token(client, email="owner@example.com")
        token_b = await _brand_token(client, email="intruder@example.com")
        template_id = await _get_template_id(client, token_a)

        create_resp = await client.post(
            "/api/v1/advertisements",
            json={"template_id": template_id, "title": "Private ad"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        ad_id = create_resp.json()["id"]

        resp = await client.get(f"/api/v1/advertisements/{ad_id}", headers={"Authorization": f"Bearer {token_b}"})
        assert resp.status_code == 404

    async def test_update_advertisement_fields(self, client):
        token = await _brand_token(client, email="update-ad@example.com")
        template_id = await _get_template_id(client, token)
        create_resp = await client.post(
            "/api/v1/advertisements",
            json={"template_id": template_id, "title": "Original"},
            headers={"Authorization": f"Bearer {token}"},
        )
        ad_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/advertisements/{ad_id}",
            json={"title": "Updated title", "cta_text": "Shop now"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated title"
        assert resp.json()["cta_text"] == "Shop now"

    async def test_cannot_mark_ready_without_processed_video(self, client):
        token = await _brand_token(client, email="ready-guard@example.com")
        template_id = await _get_template_id(client, token)
        create_resp = await client.post(
            "/api/v1/advertisements",
            json={"template_id": template_id, "title": "No video yet"},
            headers={"Authorization": f"Bearer {token}"},
        )
        ad_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/advertisements/{ad_id}",
            json={"status": "ready"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_archived_advertisement_is_read_only(self, client):
        token = await _brand_token(client, email="archive-me@example.com")
        template_id = await _get_template_id(client, token)
        create_resp = await client.post(
            "/api/v1/advertisements",
            json={"template_id": template_id, "title": "To archive"},
            headers={"Authorization": f"Bearer {token}"},
        )
        ad_id = create_resp.json()["id"]

        archive_resp = await client.patch(
            f"/api/v1/advertisements/{ad_id}",
            json={"status": "archived"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert archive_resp.status_code == 200

        edit_resp = await client.patch(
            f"/api/v1/advertisements/{ad_id}",
            json={"title": "Should fail"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert edit_resp.status_code == 400
