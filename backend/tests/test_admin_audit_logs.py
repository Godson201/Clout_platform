from tests.test_admin_flow import _make_admin_token
from tests.test_auth_flow import _register_brand


class TestAdminAuditLogs:
    async def test_lists_logged_actions_newest_first(self, client):
        register_resp = await _register_brand(client, email="audited-brand@example.com")
        user_id = register_resp.json()["user"]["id"]
        admin_token = await _make_admin_token(email="audit-admin-1@clout.local")

        # Generates one admin.user.status_update audit row.
        await client.patch(
            f"/api/v1/admin/users/{user_id}/status",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = await client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        entry = next(item for item in body["items"] if item["action"] == "admin.user.status_update")
        assert entry["entity_type"] == "user"
        assert entry["entity_id"] == user_id
        assert entry["actor_email"] == "audit-admin-1@clout.local"
        assert entry["after"]["is_active"] is False

    async def test_filters_by_action(self, client):
        admin_token = await _make_admin_token(email="audit-admin-2@clout.local")
        register_resp = await _register_brand(client, email="filtered-audit-brand@example.com")
        user_id = register_resp.json()["user"]["id"]
        await client.patch(
            f"/api/v1/admin/users/{user_id}/status",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        resp = await client.get(
            "/api/v1/admin/audit-logs",
            params={"action": "admin.user.status_update"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert all(item["action"] == "admin.user.status_update" for item in body["items"])

    async def test_non_admin_forbidden(self, client):
        actor = await _register_brand(client, email="non-admin-audit@example.com")
        token = actor.json()["access_token"]

        resp = await client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
