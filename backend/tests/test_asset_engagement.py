from tests.test_admin_flow import _make_admin_token
from tests.test_advertisements import _brand_token, _get_template_id


async def _create_ad_with_image(client, token: str, title: str = "Engagement test ad") -> str:
    template_id = await _get_template_id(client, token)
    ad_resp = await client.post(
        "/api/v1/advertisements",
        json={"template_id": template_id, "title": title},
        headers={"Authorization": f"Bearer {token}"},
    )
    ad_id = ad_resp.json()["id"]
    upload_resp = await client.post(
        f"/api/v1/advertisements/{ad_id}/assets",
        data={"asset_type": "image"},
        files={"file": ("photo.jpg", b"fake image bytes", "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    return upload_resp.json()["id"]


class TestAssetComments:
    async def test_brand_and_admin_can_comment_on_asset(self, client):
        brand_token = await _brand_token(client, email="engage-brand-1@example.com")
        asset_id = await _create_ad_with_image(client, brand_token)

        brand_comment = await client.post(
            f"/api/v1/assets/{asset_id}/comments",
            json={"body": "Here's the first draft."},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert brand_comment.status_code == 201
        assert brand_comment.json()["author_is_admin"] is False

        admin_token = await _make_admin_token(email="engage-admin-1@clout.local")
        admin_comment = await client.post(
            f"/api/v1/assets/{asset_id}/comments",
            json={"body": "Please increase the resolution."},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_comment.status_code == 201
        assert admin_comment.json()["author_is_admin"] is True

        listing = await client.get(f"/api/v1/assets/{asset_id}/comments", headers={"Authorization": f"Bearer {brand_token}"})
        assert listing.status_code == 200
        bodies = [c["body"] for c in listing.json()]
        assert bodies == ["Here's the first draft.", "Please increase the resolution."]

    async def test_admin_comment_notifies_brand(self, client):
        brand_token = await _brand_token(client, email="engage-brand-2@example.com")
        asset_id = await _create_ad_with_image(client, brand_token)

        admin_token = await _make_admin_token(email="engage-admin-2@clout.local")
        await client.post(
            f"/api/v1/assets/{asset_id}/comments",
            json={"body": "Looks great, approving soon."},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {brand_token}"})
        notif = next(n for n in feed.json() if n["type"] == "asset_comment")
        assert notif["data"]["asset_id"] == asset_id

    async def test_brand_comment_does_not_self_notify(self, client):
        brand_token = await _brand_token(client, email="engage-brand-3@example.com")
        asset_id = await _create_ad_with_image(client, brand_token)

        await client.post(
            f"/api/v1/assets/{asset_id}/comments",
            json={"body": "Note to self."},
            headers={"Authorization": f"Bearer {brand_token}"},
        )

        feed = await client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {brand_token}"})
        assert feed.json() == []

    async def test_other_brand_cannot_see_or_comment(self, client):
        brand_token = await _brand_token(client, email="engage-brand-4@example.com")
        asset_id = await _create_ad_with_image(client, brand_token)

        other_brand_token = await _brand_token(client, email="engage-brand-5@example.com")
        list_resp = await client.get(
            f"/api/v1/assets/{asset_id}/comments", headers={"Authorization": f"Bearer {other_brand_token}"}
        )
        assert list_resp.status_code == 404

        comment_resp = await client.post(
            f"/api/v1/assets/{asset_id}/comments",
            json={"body": "Not my asset"},
            headers={"Authorization": f"Bearer {other_brand_token}"},
        )
        assert comment_resp.status_code == 404

    async def test_empty_body_rejected(self, client):
        brand_token = await _brand_token(client, email="engage-brand-6@example.com")
        asset_id = await _create_ad_with_image(client, brand_token)

        resp = await client.post(
            f"/api/v1/assets/{asset_id}/comments",
            json={"body": ""},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert resp.status_code == 422


class TestAssetLikes:
    async def test_toggle_like_and_count(self, client):
        brand_token = await _brand_token(client, email="engage-brand-7@example.com")
        asset_id = await _create_ad_with_image(client, brand_token)

        status_resp = await client.get(f"/api/v1/assets/{asset_id}/like", headers={"Authorization": f"Bearer {brand_token}"})
        assert status_resp.json() == {"liked": False, "like_count": 0}

        like_resp = await client.post(f"/api/v1/assets/{asset_id}/like", headers={"Authorization": f"Bearer {brand_token}"})
        assert like_resp.json() == {"liked": True, "like_count": 1}

        admin_token = await _make_admin_token(email="engage-admin-7@clout.local")
        admin_like_resp = await client.post(f"/api/v1/assets/{asset_id}/like", headers={"Authorization": f"Bearer {admin_token}"})
        assert admin_like_resp.json() == {"liked": True, "like_count": 2}

        unlike_resp = await client.post(f"/api/v1/assets/{asset_id}/like", headers={"Authorization": f"Bearer {brand_token}"})
        assert unlike_resp.json() == {"liked": False, "like_count": 1}

    async def test_other_brand_cannot_like(self, client):
        brand_token = await _brand_token(client, email="engage-brand-8@example.com")
        asset_id = await _create_ad_with_image(client, brand_token)

        other_brand_token = await _brand_token(client, email="engage-brand-9@example.com")
        resp = await client.post(f"/api/v1/assets/{asset_id}/like", headers={"Authorization": f"Bearer {other_brand_token}"})
        assert resp.status_code == 404
