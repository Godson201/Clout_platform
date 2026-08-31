from tests.factories import register_influencer_token
from tests.test_admin_flow import _make_admin_token
from tests.test_advertisements import _brand_token, _get_template_id


async def _create_and_approve_image_asset(client, *, brand_email: str, admin_email: str, title: str) -> tuple[str, str]:
    brand_token = await _brand_token(client, email=brand_email)
    template_id = await _get_template_id(client, brand_token)
    ad_resp = await client.post(
        "/api/v1/advertisements",
        json={"template_id": template_id, "title": title},
        headers={"Authorization": f"Bearer {brand_token}"},
    )
    ad_id = ad_resp.json()["id"]

    upload_resp = await client.post(
        f"/api/v1/advertisements/{ad_id}/assets",
        data={"asset_type": "image"},
        files={"file": ("photo.jpg", b"fake image bytes", "image/jpeg")},
        headers={"Authorization": f"Bearer {brand_token}"},
    )
    asset_id = upload_resp.json()["id"]

    admin_token = await _make_admin_token(email=admin_email)
    await client.post(
        f"/api/v1/admin/asset-moderation/{asset_id}/approve", headers={"Authorization": f"Bearer {admin_token}"}
    )
    return brand_token, asset_id


class TestMarketplaceMedia:
    async def test_influencer_cannot_see_unassigned_brand_media(self, client):
        inf_token = await register_influencer_token(client, email="media-browser@example.com", username="mediabrowser")

        _, approved_id = await _create_and_approve_image_asset(
            client, brand_email="media-brand-1@example.com", admin_email="media-admin-1@clout.local", title="Approved ad"
        )

        # A second, never-approved asset must not show up.
        brand_token = await _brand_token(client, email="media-brand-2@example.com")
        template_id = await _get_template_id(client, brand_token)
        ad_resp = await client.post(
            "/api/v1/advertisements",
            json={"template_id": template_id, "title": "Pending ad"},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        await client.post(
            f"/api/v1/advertisements/{ad_resp.json()['id']}/assets",
            data={"asset_type": "image"},
            files={"file": ("photo2.jpg", b"fake image bytes 2", "image/jpeg")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )

        resp = await client.get("/api/v1/marketplace/media", headers={"Authorization": f"Bearer {inf_token}"})
        assert resp.status_code == 200
        body = resp.json()
        ids = [item["id"] for item in body]
        # Approval alone is never a distribution grant. This influencer has no
        # assigned slot and does not meet a live campaign's eligibility rules.
        assert approved_id not in ids
        assert ids == []

    async def test_brand_and_admin_cannot_use_influencer_only_route(self, client):
        brand_token = await _brand_token(client, email="media-brand-3@example.com")
        resp = await client.get("/api/v1/marketplace/media", headers={"Authorization": f"Bearer {brand_token}"})
        assert resp.status_code == 403
