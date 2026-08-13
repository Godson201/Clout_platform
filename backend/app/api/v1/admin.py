import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import require_admin, require_super_admin
from app.models.brand import Brand
from app.models.enums import UserType
from app.models.influencer import Influencer
from app.models.rbac import Role
from app.models.user import User
from app.schemas.admin import UserStatusUpdate, VerificationDecision
from app.schemas.brand import BrandRead
from app.schemas.common import Page
from app.schemas.influencer import InfluencerRead
from app.schemas.user import UserRead
from app.services.audit import write_audit_log

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=Page[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    user_type: UserType | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[UserRead]:
    stmt = select(User).options(selectinload(User.roles))
    count_stmt = select(func.count()).select_from(User)

    if user_type is not None:
        stmt = stmt.where(User.user_type == user_type)
        count_stmt = count_stmt.where(User.user_type == user_type)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
        count_stmt = count_stmt.where(User.is_active == is_active)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    users = (await db.execute(stmt)).scalars().all()

    return Page(items=[UserRead.from_orm_user(u) for u in users], total=total, page=page, page_size=page_size)


@router.patch("/users/{user_id}/status", response_model=UserRead)
async def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> UserRead:
    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    before = {"is_active": user.is_active}
    user.is_active = payload.is_active

    await write_audit_log(
        db,
        actor_user_id=admin.id,
        action="admin.user.status_update",
        entity_type="user",
        entity_id=user.id,
        before=before,
        after={"is_active": user.is_active},
    )

    await db.commit()
    await db.refresh(user)
    return UserRead.from_orm_user(user)


@router.post("/users/{user_id}/promote-to-admin", response_model=UserRead)
async def promote_to_admin(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    super_admin: User = Depends(require_super_admin),
) -> UserRead:
    """Only a super_admin can do this — a flat "admin" role has no power to
    mint more admins, otherwise "super" would mean nothing. Promoting sets
    user_type=ADMIN outright (not just an extra RBAC role) since every
    admin-only frontend route gates on user_type, not roles — see
    RequireUserType. Any existing Brand/Influencer profile row is left in
    place but becomes inaccessible through their account once promoted.
    """
    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.user_type == UserType.ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already an admin")

    admin_role_result = await db.execute(select(Role).where(Role.name == "admin"))
    admin_role = admin_role_result.scalar_one()

    before = {"user_type": user.user_type.value, "roles": [r.name for r in user.roles]}
    user.user_type = UserType.ADMIN
    if admin_role not in user.roles:
        user.roles.append(admin_role)

    await write_audit_log(
        db,
        actor_user_id=super_admin.id,
        action="admin.user.promote_to_admin",
        entity_type="user",
        entity_id=user.id,
        before=before,
        after={"user_type": user.user_type.value, "roles": [r.name for r in user.roles]},
    )

    await db.commit()
    await db.refresh(user)
    return UserRead.from_orm_user(user)


@router.patch("/brands/{brand_id}/verify", response_model=BrandRead)
async def verify_brand(
    brand_id: uuid.UUID,
    payload: VerificationDecision,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> BrandRead:
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")

    before = {"verification_status": brand.verification_status.value}
    brand.verification_status = payload.status

    await write_audit_log(
        db,
        actor_user_id=admin.id,
        action="admin.brand.verify",
        entity_type="brand",
        entity_id=brand.id,
        before=before,
        after={"verification_status": brand.verification_status.value, "reason": payload.reason},
    )

    await db.commit()
    await db.refresh(brand)
    return BrandRead.model_validate(brand)


@router.patch("/influencers/{influencer_id}/verify", response_model=InfluencerRead)
async def verify_influencer(
    influencer_id: uuid.UUID,
    payload: VerificationDecision,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> InfluencerRead:
    result = await db.execute(select(Influencer).where(Influencer.id == influencer_id))
    influencer = result.scalar_one_or_none()
    if influencer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer not found")

    before = {"verification_status": influencer.verification_status.value}
    influencer.verification_status = payload.status

    await write_audit_log(
        db,
        actor_user_id=admin.id,
        action="admin.influencer.verify",
        entity_type="influencer",
        entity_id=influencer.id,
        before=before,
        after={"verification_status": influencer.verification_status.value, "reason": payload.reason},
    )

    await db.commit()
    await db.refresh(influencer)
    return InfluencerRead.model_validate(influencer)
