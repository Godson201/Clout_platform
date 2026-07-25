import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_influencer
from app.models.influencer import Influencer
from app.models.payout import Payout
from app.models.user import User
from app.schemas.common import Page
from app.schemas.payout import PayoutRead, PayoutRequest
from app.services.payouts import request_payout, sync_payout_status

router = APIRouter(prefix="/influencers/me/payouts", tags=["payouts"], dependencies=[Depends(require_influencer)])


async def _get_own_influencer(db: AsyncSession, user: User) -> Influencer:
    result = await db.execute(select(Influencer).where(Influencer.id == user.id))
    influencer = result.scalar_one_or_none()
    if influencer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer profile not found")
    return influencer


@router.post("", response_model=PayoutRead, status_code=status.HTTP_201_CREATED)
async def create_payout(
    payload: PayoutRequest, user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)
) -> PayoutRead:
    influencer = await _get_own_influencer(db, user)
    payout = await request_payout(db, influencer=influencer, amount=payload.amount, phone_number=payload.phone_number)
    return PayoutRead.model_validate(payout)


@router.get("", response_model=Page[PayoutRead])
async def list_payouts(
    user: User = Depends(require_influencer),
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[PayoutRead]:
    stmt = select(Payout).where(Payout.influencer_id == user.id)
    count_stmt = select(func.count()).select_from(Payout).where(Payout.influencer_id == user.id)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(Payout.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(stmt)).scalars().all()

    return Page(items=[PayoutRead.model_validate(p) for p in items], total=total, page=page, page_size=page_size)


@router.get("/{payout_id}", response_model=PayoutRead)
async def get_payout(
    payout_id: uuid.UUID, user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)
) -> PayoutRead:
    result = await db.execute(select(Payout).where(Payout.id == payout_id, Payout.influencer_id == user.id))
    payout = result.scalar_one_or_none()
    if payout is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found")

    payout = await sync_payout_status(db, payout=payout)
    return PayoutRead.model_validate(payout)
