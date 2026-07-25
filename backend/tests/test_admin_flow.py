from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.core.security import hash_password
from app.models.enums import UserType
from app.models.rbac import Role
from app.models.user import User
from app.services.auth import issue_access_token

from tests.test_auth_flow import _register_brand, _register_influencer


async def _make_admin_token(email="admin@clout.local") -> str:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Role).where(Role.name == "admin"))
        admin_role = result.scalar_one()

        admin = User(
            email=email,
            hashed_password=hash_password("AdminPass123"),
            user_type=UserType.ADMIN,
            is_active=True,
            is_verified=True,
        )
        admin.roles.append(admin_role)
        db.add(admin)
        await db.commit()
        await db.refresh(admin, attribute_names=["roles"])
        return issue_access_token(admin)


class TestAdminUserManagement:
    async def test_admin_can_list_users(self, client):
        await _register_brand(client, email="listed-brand@example.com")
        token = await _make_admin_token()

        resp = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert any(u["email"] == "listed-brand@example.com" for u in body["items"])

    async def test_admin_can_filter_by_user_type(self, client):
        await _register_brand(client, email="filter-brand@example.com")
        await _register_influencer(client, email="filter-inf@example.com", username="filterinf")
        token = await _make_admin_token(email="filter-admin@clout.local")

        resp = await client.get(
            "/api/v1/admin/users", params={"user_type": "influencer"}, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(u["user_type"] == "influencer" for u in body["items"])

    async def test_admin_can_suspend_user(self, client):
        register_resp = await _register_brand(client, email="suspend-me@example.com")
        user_id = register_resp.json()["user"]["id"]
        admin_token = await _make_admin_token(email="suspend-admin@clout.local")

        resp = await client.patch(
            f"/api/v1/admin/users/{user_id}/status",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        login_resp = await client.post(
            "/api/v1/auth/login", json={"email": "suspend-me@example.com", "password": "SuperSecret123"}
        )
        assert login_resp.status_code == 403


class TestAdminVerification:
    async def test_admin_can_verify_brand(self, client):
        register_resp = await _register_brand(client, email="verify-brand@example.com")
        user_id = register_resp.json()["user"]["id"]
        admin_token = await _make_admin_token(email="verify-admin@clout.local")

        resp = await client.patch(
            f"/api/v1/admin/brands/{user_id}/verify",
            json={"status": "approved", "reason": "KYC documents checked"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["verification_status"] == "approved"

    async def test_admin_can_verify_influencer(self, client):
        register_resp = await _register_influencer(client, email="verify-inf@example.com", username="verifyinf")
        user_id = register_resp.json()["user"]["id"]
        admin_token = await _make_admin_token(email="verify-inf-admin@clout.local")

        resp = await client.patch(
            f"/api/v1/admin/influencers/{user_id}/verify",
            json={"status": "rejected", "reason": "Could not confirm identity"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["verification_status"] == "rejected"
