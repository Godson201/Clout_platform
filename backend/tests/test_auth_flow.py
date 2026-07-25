async def _register_brand(client, email="brand@example.com"):
    resp = await client.post(
        "/api/v1/auth/register/brand",
        json={
            "email": email,
            "password": "SuperSecret123",
            "business_name": "Acme Ads",
            "sector": "retail",
            "location": "Kigali",
        },
    )
    return resp


async def _register_influencer(client, email="influencer@example.com", username="thecreator"):
    resp = await client.post(
        "/api/v1/auth/register/influencer",
        json={
            "email": email,
            "password": "SuperSecret123",
            "display_name": "The Creator",
            "username": username,
            "location": "Kigali",
            "sector": "lifestyle",
        },
    )
    return resp


class TestRegistration:
    async def test_register_brand_creates_profile_and_wallet(self, client):
        resp = await _register_brand(client)
        assert resp.status_code == 201
        body = resp.json()
        assert body["user"]["user_type"] == "brand"
        assert body["user"]["roles"] == ["brand"]
        assert "access_token" in body
        assert "clout_refresh_token" in resp.cookies

    async def test_register_influencer_creates_profile(self, client):
        resp = await _register_influencer(client)
        assert resp.status_code == 201
        body = resp.json()
        assert body["user"]["user_type"] == "influencer"

    async def test_duplicate_email_rejected(self, client):
        await _register_brand(client, email="dupe@example.com")
        resp = await _register_brand(client, email="dupe@example.com")
        assert resp.status_code == 409

    async def test_duplicate_username_rejected(self, client):
        await _register_influencer(client, email="a@example.com", username="sameuser")
        resp = await _register_influencer(client, email="b@example.com", username="sameuser")
        assert resp.status_code == 409


class TestLoginAndMe:
    async def test_login_and_fetch_me(self, client):
        await _register_brand(client, email="login@example.com")
        resp = await client.post(
            "/api/v1/auth/login", json={"email": "login@example.com", "password": "SuperSecret123"}
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["email"] == "login@example.com"

    async def test_wrong_password_rejected(self, client):
        await _register_brand(client, email="wrongpw@example.com")
        resp = await client.post(
            "/api/v1/auth/login", json={"email": "wrongpw@example.com", "password": "not-the-password"}
        )
        assert resp.status_code == 401

    async def test_me_requires_token(self, client):
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401


class TestRefreshRotation:
    async def test_refresh_issues_new_access_token_and_rotates_cookie(self, client):
        register_resp = await _register_brand(client, email="refresh@example.com")
        old_refresh_cookie = register_resp.cookies["clout_refresh_token"]
        client.cookies.set("clout_refresh_token", old_refresh_cookie)

        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        new_refresh_cookie = resp.cookies["clout_refresh_token"]
        assert new_refresh_cookie != old_refresh_cookie

        # The old refresh token must be revoked once rotated (replay protection).
        client.cookies.set("clout_refresh_token", old_refresh_cookie)
        replay = await client.post("/api/v1/auth/refresh")
        assert replay.status_code == 401

    async def test_logout_revokes_refresh_token(self, client):
        register_resp = await _register_brand(client, email="logout@example.com")
        refresh_cookie = register_resp.cookies["clout_refresh_token"]
        client.cookies.set("clout_refresh_token", refresh_cookie)

        logout_resp = await client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 204

        reuse = await client.post("/api/v1/auth/refresh")
        assert reuse.status_code == 401


class TestRBAC:
    async def test_brand_cannot_access_influencer_profile(self, client):
        register_resp = await _register_brand(client, email="rbac-brand@example.com")
        token = register_resp.json()["access_token"]

        resp = await client.get("/api/v1/influencers/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    async def test_non_admin_cannot_list_users(self, client):
        register_resp = await _register_influencer(client, email="rbac-inf@example.com", username="rbacinf")
        token = register_resp.json()["access_token"]

        resp = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    async def test_brand_can_update_own_profile(self, client):
        register_resp = await _register_brand(client, email="update-brand@example.com")
        token = register_resp.json()["access_token"]

        resp = await client.patch(
            "/api/v1/brands/me",
            json={"business_name": "New Name", "location": "Musanze"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["business_name"] == "New Name"
        assert resp.json()["location"] == "Musanze"
