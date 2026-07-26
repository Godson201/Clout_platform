import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, require_influencer
from app.models.enums import WalletOwnerType
from app.models.influencer import Influencer
from app.models.user import User
from app.schemas.influencer import InfluencerRead, InfluencerUpdate
from app.schemas.public_profile import PublicInfluencerProfile
from app.schemas.wallet import WalletRead
from app.services.audit import write_audit_log
from app.services.ledger import get_wallet
from app.services.profile_pictures import store_profile_picture
from app.services.public_profiles import build_public_influencer_profile

router = APIRouter(prefix="/influencers", tags=["influencers"])


async def _get_own_influencer(db: AsyncSession, user: User) -> Influencer:
    result = await db.execute(select(Influencer).where(Influencer.id == user.id))
    influencer = result.scalar_one_or_none()
    if influencer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer profile not found")
    return influencer


@router.get("/me", response_model=InfluencerRead)
async def get_my_influencer(
    user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)
) -> InfluencerRead:
    influencer = await _get_own_influencer(db, user)
    return InfluencerRead.model_validate(influencer)


@router.patch("/me", response_model=InfluencerRead)
async def update_my_influencer(
    payload: InfluencerUpdate, user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)
) -> InfluencerRead:
    influencer = await _get_own_influencer(db, user)
    before = InfluencerRead.model_validate(influencer).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(influencer, field, value)

    await write_audit_log(
        db,
        actor_user_id=user.id,
        action="influencer.update",
        entity_type="influencer",
        entity_id=influencer.id,
        before=before,
        after=InfluencerRead.model_validate(influencer).model_dump(mode="json"),
    )

    await db.commit()
    await db.refresh(influencer)
    return InfluencerRead.model_validate(influencer)


@router.post("/me/picture", response_model=InfluencerRead)
async def upload_my_picture(
    file: UploadFile, user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)
) -> InfluencerRead:
    influencer = await _get_own_influencer(db, user)
    influencer.profile_picture_url = await store_profile_picture(owner_kind="influencers", owner_id=user.id, file=file)
    await db.commit()
    await db.refresh(influencer)
    return InfluencerRead.model_validate(influencer)


@router.get("/me/wallet", response_model=WalletRead)
async def get_my_wallet(user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)) -> WalletRead:
    wallet = await get_wallet(db, owner_type=WalletOwnerType.INFLUENCER, owner_id=user.id)
    return WalletRead.model_validate(wallet)


@router.get("/{influencer_id}/public", response_model=PublicInfluencerProfile)
async def get_public_influencer_profile(
    influencer_id: uuid.UUID, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PublicInfluencerProfile:
    influencer = await db.get(Influencer, influencer_id)
    if influencer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer not found")
    return await build_public_influencer_profile(db, influencer)
