"""Idempotent bootstrap seed: RBAC roles/permissions + platform wallet + one admin user.

Run with:  python -m app.seeds.seed
Safe to re-run — every insert is guarded by a lookup first.

There is deliberately no public "register as admin" endpoint. Admin accounts are
created only through this script (or later, by an existing admin), reading
credentials from environment variables so they are never hardcoded.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.db import AsyncSessionLocal, engine
from app.core.db import Base
from app.core.security import hash_password
from app.models.advertisement_template import AdvertisementTemplate
from app.models.enums import SocialPlatform, UserType, WalletOwnerType
from app.models.fee_config import FeeConfig
from app.models.rbac import Permission, Role
from app.models.user import User
from app.models.view_rate import ViewRate
from app.services.wallet import create_wallet_for_owner

ROLES = ["brand", "influencer", "admin", "super_admin"]

PERMISSIONS = [
    "admin:manage_users",
    "admin:verify_brands",
    "admin:verify_influencers",
    "admin:manage_fees",
    "admin:manage_disputes",
]

# (code, name, category, default_duration_seconds) — matches the Brand Toolkit
# categories from the product spec (product/service/campaign/e-commerce/SaaS/
# brand visibility/song/movie trailer/concert/government/police/RBC/other).
ADVERTISEMENT_TEMPLATES = [
    ("product", "Product Launch", "commercial", 30),
    ("service", "Service Promotion", "commercial", 30),
    ("campaign", "Marketing Campaign", "commercial", 30),
    ("ecommerce", "E-commerce Sale", "commercial", 20),
    ("saas", "SaaS Product", "commercial", 30),
    ("brand_visibility", "Brand Visibility", "commercial", 20),
    ("song", "Song Promotion", "entertainment", 30),
    ("movie_trailer", "Movie Trailer", "entertainment", 30),
    ("concert", "Concert / Event", "entertainment", 30),
    ("government", "Government Announcement", "institutional", 30),
    ("police", "Police / Public Safety", "institutional", 30),
    ("rbc", "RBC Public Health", "institutional", 30),
    ("other", "Other", "general", 30),
]

# Placeholder RWF-per-view defaults — matches the RWF 5/view example in the
# product spec for TikTok; admin can adjust via PATCH /admin/view-rates.
DEFAULT_VIEW_RATES = {
    SocialPlatform.TIKTOK: "5.0000",
    SocialPlatform.INSTAGRAM: "6.0000",
    SocialPlatform.FACEBOOK: "4.0000",
    SocialPlatform.YOUTUBE: "7.0000",
}


async def seed_roles_and_permissions(db) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for name in ROLES:
        result = await db.execute(select(Role).where(Role.name == name))
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(name=name)
            db.add(role)
            await db.flush()
        roles[name] = role

    permissions: dict[str, Permission] = {}
    for code in PERMISSIONS:
        result = await db.execute(select(Permission).where(Permission.code == code))
        perm = result.scalar_one_or_none()
        if perm is None:
            perm = Permission(code=code)
            db.add(perm)
            await db.flush()
        permissions[code] = perm

    # Re-fetch the admin role with `permissions` eagerly loaded: under AsyncSession,
    # touching an unloaded relationship attribute triggers an implicit lazy SELECT,
    # which raises MissingGreenlet outside of a session.execute()/refresh() call.
    admin_role_result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).where(Role.name == "admin")
    )
    admin_role = admin_role_result.scalar_one()
    existing_codes = {p.code for p in admin_role.permissions}
    for code, perm in permissions.items():
        if code not in existing_codes:
            admin_role.permissions.append(perm)
    roles["admin"] = admin_role

    await db.commit()
    return roles


async def seed_advertisement_templates(db) -> None:
    for code, name, category, default_duration_seconds in ADVERTISEMENT_TEMPLATES:
        result = await db.execute(select(AdvertisementTemplate).where(AdvertisementTemplate.code == code))
        if result.scalar_one_or_none() is None:
            db.add(
                AdvertisementTemplate(
                    code=code, name=name, category=category, default_duration_seconds=default_duration_seconds
                )
            )
    await db.commit()


async def seed_view_rates(db) -> None:
    for platform, rate in DEFAULT_VIEW_RATES.items():
        result = await db.execute(select(ViewRate).where(ViewRate.platform == platform))
        if result.scalar_one_or_none() is None:
            db.add(ViewRate(platform=platform, rate_per_view=rate))
    await db.commit()


async def seed_fee_config(db) -> None:
    result = await db.execute(select(FeeConfig))
    if result.scalar_one_or_none() is None:
        # Confirmed business decision: CLOUT charges both sides (10% brand-side
        # on top of payment, 10% influencer-side deducted at payout).
        db.add(FeeConfig(brand_fee_pct="0.1000", influencer_fee_pct="0.1000"))
        await db.commit()


async def seed_platform_wallet(db) -> None:
    from app.models.wallet import Wallet

    existing = await db.execute(select(Wallet).where(Wallet.owner_type == WalletOwnerType.PLATFORM))
    if existing.scalar_one_or_none() is None:
        await create_wallet_for_owner(db, owner_type=WalletOwnerType.PLATFORM, owner_id=None)
        await db.commit()


async def seed_external_wallet(db) -> None:
    """The EXTERNAL wallet is the ledger's boundary with real-world MoMo cash
    (see WalletOwnerType.EXTERNAL) — a singleton like the platform wallet."""
    from app.models.wallet import Wallet

    existing = await db.execute(select(Wallet).where(Wallet.owner_type == WalletOwnerType.EXTERNAL))
    if existing.scalar_one_or_none() is None:
        await create_wallet_for_owner(db, owner_type=WalletOwnerType.EXTERNAL, owner_id=None)
        await db.commit()


async def seed_admin_user(db, roles: dict[str, Role]) -> None:
    """The seed admin is also the platform's one and only super_admin — the
    account that can promote other users to admin (see POST
    /admin/users/{id}/promote-to-admin). Idempotent for role assignment too,
    not just creation, so re-running this after adding the super_admin role
    to an already-seeded database still grants it to the existing account.
    """
    settings = get_settings()
    admin_email = settings.SEED_ADMIN_EMAIL
    admin_password = settings.SEED_ADMIN_PASSWORD

    if not admin_email or not admin_password:
        print("SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD not set — skipping admin user seed.")
        return

    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.email == admin_email.lower())
    )
    admin_user = result.scalar_one_or_none()

    if admin_user is None:
        admin_user = User(
            email=admin_email.lower(),
            hashed_password=hash_password(admin_password),
            user_type=UserType.ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(admin_user)
        await db.flush()
        print(f"Created admin user {admin_email}.")
    else:
        print(f"Admin user {admin_email} already exists — ensuring roles are up to date.")

    existing_role_names = {r.name for r in admin_user.roles}
    for role_name in ("admin", "super_admin"):
        if role_name not in existing_role_names:
            admin_user.roles.append(roles[role_name])

    await db.commit()


async def main() -> None:
    # Ensures Base.metadata has every table registered before create_all.
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        roles = await seed_roles_and_permissions(db)
        await seed_advertisement_templates(db)
        await seed_view_rates(db)
        await seed_fee_config(db)
        await seed_platform_wallet(db)
        await seed_external_wallet(db)
        await seed_admin_user(db, roles)

    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
