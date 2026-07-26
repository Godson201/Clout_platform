from tests.test_auth_flow import _register_brand


class TestChangePassword:
    async def test_change_password_with_correct_current_password(self, client):
        resp = await _register_brand(client, email="changepw@example.com")
        token = resp.json()["access_token"]

        change_resp = await client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "SuperSecret123", "new_password": "BrandNewPass456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert change_resp.status_code == 200

        old_login = await client.post(
            "/api/v1/auth/login", json={"email": "changepw@example.com", "password": "SuperSecret123"}
        )
        assert old_login.status_code == 401

        new_login = await client.post(
            "/api/v1/auth/login", json={"email": "changepw@example.com", "password": "BrandNewPass456"}
        )
        assert new_login.status_code == 200

    async def test_wrong_current_password_rejected(self, client):
        resp = await _register_brand(client, email="wrongcurrentpw@example.com")
        token = resp.json()["access_token"]

        change_resp = await client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "NotMyPassword", "new_password": "BrandNewPass456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert change_resp.status_code == 400

    async def test_requires_authentication(self, client):
        resp = await client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "x", "new_password": "BrandNewPass456"},
        )
        assert resp.status_code == 401

    async def test_change_password_revokes_existing_refresh_token(self, client):
        register_resp = await _register_brand(client, email="revoke-changepw@example.com")
        token = register_resp.json()["access_token"]
        old_refresh_cookie = register_resp.cookies["clout_refresh_token"]

        await client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "SuperSecret123", "new_password": "BrandNewPass456"},
            headers={"Authorization": f"Bearer {token}"},
        )

        client.cookies.set("clout_refresh_token", old_refresh_cookie)
        refresh_resp = await client.post("/api/v1/auth/refresh")
        assert refresh_resp.status_code == 401
