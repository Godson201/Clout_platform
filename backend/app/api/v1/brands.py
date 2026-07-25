from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_brand
from app.models.brand import Brand
from app.models.enums import WalletOwnerType
from app.models.user import User
from app.schemas.brand import BrandRead, BrandUpdate
from app.schemas.wallet import WalletRead
from app.services.audit import write_audit_log
from app.services.ledger import get_wallet

router = APIRouter(prefix="/brands", tags=["brands"])


async def _get_own_brand(db: AsyncSession, user: User) -> Brand:
    result = await db.execute(select(Brand).where(Brand.id == user.id))
    brand = result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand profile not found")
    return brand


@router.get("/me", response_model=BrandRead)
async def get_my_brand(user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)) -> BrandRead:
    brand = await _get_own_brand(db, user)
    return BrandRead.model_validate(brand)


@router.patch("/me", response_model=BrandRead)
async def update_my_brand(
    payload: BrandUpdate, user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> BrandRead:
    brand = await _get_own_brand(db, user)
    before = BrandRead.model_validate(brand).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(brand, field, value)

    await write_audit_log(
        db,
        actor_user_id=user.id,
        action="brand.update",
        entity_type="brand",
        entity_id=brand.id,
        before=before,
        after=BrandRead.model_validate(brand).model_dump(mode="json"),
    )

    await db.commit()
    await db.refresh(brand)
    return BrandRead.model_validate(brand)


@router.get("/me/wallet", response_model=WalletRead)
async def get_my_wallet(user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)) -> WalletRead:
    wallet = await get_wallet(db, owner_type=WalletOwnerType.BRAND, owner_id=user.id)
    return WalletRead.model_validate(wallet)
