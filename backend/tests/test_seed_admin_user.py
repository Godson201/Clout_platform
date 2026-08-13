from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import AsyncSessionLocal
from app.models.rbac import Role
from app.models.user import User
from app.seeds.seed import seed_admin_user, seed_roles_and_permissions


class TestSeedAdminUser:
    """Regression test for a real production incident: seed_roles_and_permissions
    commits internally (default expire_on_commit=True expires every ORM object
    tied to that session), so the Role instances in its returned dict are stale
    by the time seed_admin_user tries to append them to a relationship —
    appending an expired instance triggers an implicit lazy-load, which raises
    MissingGreenlet under AsyncSession instead of just working.
    """

    async def test_creates_admin_with_admin_and_super_admin_roles(self, monkeypatch):
        settings_patches = {"SEED_ADMIN_EMAIL": "seed-test-admin@clout.local", "SEED_ADMIN_PASSWORD": "SeedTestPass123"}
        from app.core.config import get_settings

        settings = get_settings()
        for key, value in settings_patches.items():
            monkeypatch.setattr(settings, key, value)

        async with AsyncSessionLocal() as db:
            roles = await seed_roles_and_permissions(db)
            await seed_admin_user(db, roles)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).options(selectinload(User.roles)).where(User.email == "seed-test-admin@clout.local")
            )
            admin = result.scalar_one()
            role_names = {r.name for r in admin.roles}
            assert role_names == {"admin", "super_admin"}

    async def test_idempotent_rerun_grants_missing_role_to_existing_user(self, monkeypatch):
        """Simulates the exact production scenario: an admin user already
        exists with only the "admin" role (seeded before super_admin existed),
        and re-running the seed script must grant super_admin without crashing.
        """
        from app.core.config import get_settings
        from app.core.security import hash_password
        from app.models.enums import UserType

        settings = get_settings()
        monkeypatch.setattr(settings, "SEED_ADMIN_EMAIL", "preexisting-admin@clout.local")
        monkeypatch.setattr(settings, "SEED_ADMIN_PASSWORD", "SeedTestPass123")

        async with AsyncSessionLocal() as db:
            await seed_roles_and_permissions(db)
            admin_role_result = await db.execute(select(Role).where(Role.name == "admin"))
            admin = User(
                email="preexisting-admin@clout.local",
                hashed_password=hash_password("Whatever123"),
                user_type=UserType.ADMIN,
                is_active=True,
                is_verified=True,
            )
            admin.roles.append(admin_role_result.scalar_one())
            db.add(admin)
            await db.commit()

        async with AsyncSessionLocal() as db:
            roles = await seed_roles_and_permissions(db)
            await seed_admin_user(db, roles)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).options(selectinload(User.roles)).where(User.email == "preexisting-admin@clout.local")
            )
            refreshed = result.scalar_one()
            role_names = {r.name for r in refreshed.roles}
            assert role_names == {"admin", "super_admin"}
