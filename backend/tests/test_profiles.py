async def _register_brand(client, email="loc-brand@example.com"):
    resp = await client.post(
        "/api/v1/auth/register/brand",
        json={
            "email": email,
            "password": "SuperSecret123",
            "business_name": "Rwanda Retail Co",
            "sector": "retail",
            "province": "Kigali city",
            "location": "Nyarugenge",
            "admin_sector": "Gitega",
            "admin_cell": "Akabahizi",
            "admin_village": "Iterambere",
            "address_detail": "KN 4 Ave, opposite the market",
        },
    )
    return resp.json()["access_token"]


async def _register_influencer(client, email="loc-inf@example.com", username="locinf"):
    resp = await client.post(
        "/api/v1/auth/register/influencer",
        json={
            "email": email,
            "password": "SuperSecret123",
            "display_name": "Loc Influencer",
            "username": username,
            "province": "Southern",
            "location": "Huye",
            "admin_sector": "Ngoma",
            "sector": "lifestyle",
        },
    )
    return resp.json()["access_token"]


class TestBrandLocationFields:
    async def test_register_stores_full_rwanda_location(self, client):
        token = await _register_brand(client)
        resp = await client.get("/api/v1/brands/me", headers={"Authorization": f"Bearer {token}"})
        body = resp.json()
        assert body["province"] == "Kigali city"
        assert body["location"] == "Nyarugenge"
        assert body["admin_sector"] == "Gitega"
        assert body["admin_cell"] == "Akabahizi"
        assert body["admin_village"] == "Iterambere"
        assert body["address_detail"] == "KN 4 Ave, opposite the market"

    async def test_update_location_fields(self, client):
        token = await _register_brand(client, email="update-loc-brand@example.com")
        resp = await client.patch(
            "/api/v1/brands/me",
            json={"province": "Western", "location": "Rubavu", "admin_sector": "Gisenyi"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["province"] == "Western"
        assert resp.json()["location"] == "Rubavu"
        assert resp.json()["admin_sector"] == "Gisenyi"


class TestInfluencerLocationFields:
    async def test_register_stores_full_rwanda_location(self, client):
        token = await _register_influencer(client)
        resp = await client.get("/api/v1/influencers/me", headers={"Authorization": f"Bearer {token}"})
        body = resp.json()
        assert body["province"] == "Southern"
        assert body["location"] == "Huye"
        assert body["admin_sector"] == "Ngoma"


class TestBrandLogoUpload:
    async def test_upload_sets_logo_url(self, client):
        token = await _register_brand(client, email="logo-upload@example.com")
        resp = await client.post(
            "/api/v1/brands/me/logo",
            files={"file": ("logo.png", b"fake-png-bytes", "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["logo_url"] is not None
        assert resp.json()["logo_url"].startswith("/media/profile-pictures/brands/")

    async def test_rejects_unsupported_extension(self, client):
        token = await _register_brand(client, email="logo-bad-ext@example.com")
        resp = await client.post(
            "/api/v1/brands/me/logo",
            files={"file": ("logo.exe", b"not an image", "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_rejects_oversized_file(self, client):
        token = await _register_brand(client, email="logo-big@example.com")
        oversized = b"0" * (11 * 1024 * 1024)
        resp = await client.post(
            "/api/v1/brands/me/logo",
            files={"file": ("big.jpg", oversized, "image/jpeg")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 413


class TestInfluencerPictureUpload:
    async def test_upload_sets_profile_picture_url(self, client):
        token = await _register_influencer(client, email="pic-upload@example.com", username="picupload")
        resp = await client.post(
            "/api/v1/influencers/me/picture",
            files={"file": ("me.jpg", b"fake-jpeg-bytes", "image/jpeg")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["profile_picture_url"] is not None
        assert resp.json()["profile_picture_url"].startswith("/media/profile-pictures/influencers/")

    async def test_rejects_content_type_mismatch(self, client):
        token = await _register_influencer(client, email="pic-bad-mime@example.com", username="picbadmime")
        resp = await client.post(
            "/api/v1/influencers/me/picture",
            files={"file": ("me.jpg", b"fake bytes", "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
