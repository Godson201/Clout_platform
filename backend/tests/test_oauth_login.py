import base64
import json

from tests.test_auth_flow import _register_brand, _register_influencer


def _mock_code(email: str, name: str | None = None) -> str:
    payload = {"email": email, "name": name}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


async def _authorize(client, *, provider="google", user_type: str | None = None) -> dict:
    params = {"user_type": user_type} if user_type else {}
    resp = await client.get(f"/api/v1/auth/oauth/{provider}/authorize", params=params)
    assert resp.status_code == 200
    return resp.json()


def _extract_state(authorization_url: str) -> str:
    # Mock mode's authorization_url is our own mock-consent page with
    # ?state=...&redirect_uri=... — real Google's would need the same
    # extraction if this test suite ever ran against real credentials.
    query = authorization_url.split("?", 1)[1]
    params = dict(p.split("=", 1) for p in query.split("&"))
    from urllib.parse import unquote

    return unquote(params["state"])


class TestOAuthLoginRegistersNewAccount:
    async def test_new_brand_via_google(self, client):
        auth = await _authorize(client, user_type="brand")
        state = _extract_state(auth["authorization_url"])

        resp = await client.post(
            "/api/v1/auth/oauth/google/callback",
            json={"code": _mock_code("newbrand@example.com", "New Brand Co"), "state": state},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["created"] is True
        assert body["user"]["user_type"] == "brand"
        assert body["user"]["email"] == "newbrand@example.com"
        assert body["user"]["is_verified"] is True
        assert "clout_refresh_token" in resp.cookies

        me = await client.get(
            "/api/v1/brands/me", headers={"Authorization": f"Bearer {body['access_token']}"}
        )
        assert me.status_code == 200
        assert me.json()["business_name"] == "New Brand Co"

    async def test_new_influencer_via_google_generates_username(self, client):
        auth = await _authorize(client, user_type="influencer")
        state = _extract_state(auth["authorization_url"])

        resp = await client.post(
            "/api/v1/auth/oauth/google/callback",
            json={"code": _mock_code("cool.creator@example.com", "Cool Creator"), "state": state},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["created"] is True
        assert body["user"]["user_type"] == "influencer"

        me = await client.get(
            "/api/v1/influencers/me", headers={"Authorization": f"Bearer {body['access_token']}"}
        )
        assert me.status_code == 200
        assert me.json()["username"] == "cool.creator" or me.json()["username"].startswith("cool")
        assert me.json()["display_name"] == "Cool Creator"

    async def test_username_collision_gets_suffixed(self, client):
        await _register_influencer(client, email="taken@example.com", username="popularname")

        auth = await _authorize(client, user_type="influencer")
        state = _extract_state(auth["authorization_url"])
        resp = await client.post(
            "/api/v1/auth/oauth/google/callback",
            json={"code": _mock_code("popularname@example.com", "Popular Name"), "state": state},
        )
        assert resp.status_code == 200
        me = await client.get(
            "/api/v1/influencers/me", headers={"Authorization": f"Bearer {resp.json()['access_token']}"}
        )
        assert me.json()["username"] != "popularname"
        assert me.json()["username"].startswith("popularname")

    async def test_no_account_and_no_user_type_returns_404(self, client):
        auth = await _authorize(client)  # no user_type — simulates the login page
        state = _extract_state(auth["authorization_url"])

        resp = await client.post(
            "/api/v1/auth/oauth/google/callback",
            json={"code": _mock_code("nobody-yet@example.com"), "state": state},
        )
        assert resp.status_code == 404


class TestOAuthLoginExistingAccount:
    async def test_returning_oauth_user_logs_in_without_user_type(self, client):
        auth = await _authorize(client, user_type="brand")
        state = _extract_state(auth["authorization_url"])
        first = await client.post(
            "/api/v1/auth/oauth/google/callback",
            json={"code": _mock_code("returning@example.com", "Returning Brand"), "state": state},
        )
        first_user_id = first.json()["user"]["id"]

        auth2 = await _authorize(client)  # login page, no user_type this time
        state2 = _extract_state(auth2["authorization_url"])
        second = await client.post(
            "/api/v1/auth/oauth/google/callback",
            json={"code": _mock_code("returning@example.com", "Returning Brand"), "state": state2},
        )
        assert second.status_code == 200
        assert second.json()["created"] is False
        assert second.json()["user"]["id"] == first_user_id

    async def test_password_account_with_verified_email_auto_links(self, client):
        register_resp = await _register_brand(client, email="already-password@example.com")
        existing_id = register_resp.json()["user"]["id"]

        auth = await _authorize(client, user_type="brand")
        state = _extract_state(auth["authorization_url"])
        resp = await client.post(
            "/api/v1/auth/oauth/google/callback",
            json={"code": _mock_code("already-password@example.com", "Whatever Name"), "state": state},
        )
        assert resp.status_code == 200
        assert resp.json()["created"] is False
        assert resp.json()["user"]["id"] == existing_id


class TestOAuthStateSecurity:
    async def test_reused_state_is_rejected(self, client):
        auth = await _authorize(client, user_type="brand")
        state = _extract_state(auth["authorization_url"])
        code = _mock_code("replay@example.com", "Replay")

        first = await client.post("/api/v1/auth/oauth/google/callback", json={"code": code, "state": state})
        assert first.status_code == 200

        second = await client.post("/api/v1/auth/oauth/google/callback", json={"code": code, "state": state})
        assert second.status_code == 400

    async def test_unknown_state_is_rejected(self, client):
        resp = await client.post(
            "/api/v1/auth/oauth/google/callback", json={"code": _mock_code("x@example.com"), "state": "not-a-real-state"}
        )
        assert resp.status_code == 400

    async def test_unsupported_provider_rejected(self, client):
        resp = await client.get("/api/v1/auth/oauth/microsoft/authorize")
        assert resp.status_code == 400
