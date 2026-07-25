import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_admin
from app.models.campaign_slot import CampaignSlot
from app.models.user import User
from app.schemas.campaign_slot import CampaignSlotRead
from app.schemas.settlement import AwaitingSettlementItemRead, SlotSettlementRequest
from app.services.auto_settlement import get_awaiting_settlement_queue
from app.services.slot_recovery import settle_and_recover

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/slots/awaiting-settlement", response_model=list[AwaitingSettlementItemRead])
async def list_slots_awaiting_settlement(db: AsyncSession = Depends(get_db)) -> list[AwaitingSettlementItemRead]:
    """Slots whose performance window has closed on a platform CLOUT can't
    verify metrics for automatically — the actionable admin worklist. Slots
    that *can* be auto-settled (mock mode today) never appear here; the
    scheduled task (app/tasks/settlement_tasks.py) clears those on its own.
    """
    queue = await get_awaiting_settlement_queue(db)
    return [
        AwaitingSettlementItemRead(
            slot_id=slot.id,
            campaign_id=campaign.id,
            platform=slot.platform,
            tier=slot.tier,
            status=slot.status,
            target_views=slot.target_views,
            budget_allocated=slot.budget_allocated,
            brand_name=brand.business_name,
            influencer_username=influencer.username,
            post_url=post.post_url,
            published_at=post.published_at,
            window_closed_at=window_closed_at,
        )
        for slot, campaign, post, brand, influencer, window_closed_at in queue
    ]


@router.post("/slots/{slot_id}/settle", response_model=CampaignSlotRead)
async def settle_slot_endpoint(
    slot_id: uuid.UUID,
    payload: SlotSettlementRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CampaignSlotRead:
    """Manual settlement bridge — see services/settlement.py docstring. Still
    the only path for platforms CLOUT can't verify metrics on (every real
    platform in production today); Phase 6's automatic settlement
    (services/auto_settlement.py) only covers platforms with real metrics
    capability, which right now is mock mode only. Any shortfall is recycled
    into a fresh slot (or refunded once its chain is exhausted) by
    settle_and_recover — see services/slot_recovery.py."""
    result = await db.execute(select(CampaignSlot).where(CampaignSlot.id == slot_id))
    slot = result.scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

    slot = await settle_and_recover(db, slot=slot, delivered_pct=payload.delivered_pct, actor_user_id=admin.id)
    return CampaignSlotRead.model_validate(slot)
