from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_admin
from app.models.fee_config import FeeConfig
from app.models.user import User
from app.models.view_rate import ViewRate
from app.schemas.admin_pricing import FeeConfigRead, FeeConfigUpdate, ViewRateRead, ViewRateUpsert
from app.services.audit import write_audit_log
from app.services.pricing import get_current_fee_config

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/view-rates", response_model=list[ViewRateRead])
async def list_view_rates(db: AsyncSession = Depends(get_db)) -> list[ViewRateRead]:
    result = await db.execute(select(ViewRate).order_by(ViewRate.platform))
    return [ViewRateRead.model_validate(r) for r in result.scalars().all()]


@router.put("/view-rates", response_model=ViewRateRead)
async def upsert_view_rate(
    payload: ViewRateUpsert, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
) -> ViewRateRead:
    result = await db.execute(select(ViewRate).where(ViewRate.platform == payload.platform))
    rate = result.scalar_one_or_none()

    before = ViewRateRead.model_validate(rate).model_dump(mode="json") if rate else None
    if rate is None:
        rate = ViewRate(platform=payload.platform, rate_per_view=payload.rate_per_view, currency=payload.currency)
        db.add(rate)
    else:
        rate.rate_per_view = payload.rate_per_view
        rate.currency = payload.currency

    await db.flush()
    # created_at/updated_at are server_default/onupdate — not populated on the
    # Python object until refreshed, so reading them (via model_validate) right
    # after flush() without a refresh() first triggers an implicit lazy load,
    # which raises MissingGreenlet under AsyncSession.
    await db.refresh(rate)
    await write_audit_log(
        db,
        actor_user_id=admin.id,
        action="admin.view_rate.upsert",
        entity_type="view_rate",
        entity_id=rate.id,
        before=before,
        after=ViewRateRead.model_validate(rate).model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(rate)
    return ViewRateRead.model_validate(rate)


@router.get("/fee-config", response_model=FeeConfigRead)
async def get_fee_config(db: AsyncSession = Depends(get_db)) -> FeeConfigRead:
    config = await get_current_fee_config(db)
    return FeeConfigRead.model_validate(config)


@router.patch("/fee-config", response_model=FeeConfigRead)
async def update_fee_config(
    payload: FeeConfigUpdate, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)
) -> FeeConfigRead:
    config = await get_current_fee_config(db)
    before = FeeConfigRead.model_validate(config).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    for field, value in updates.items():
        setattr(config, field, value)

    await write_audit_log(
        db,
        actor_user_id=admin.id,
        action="admin.fee_config.update",
        entity_type="fee_config",
        entity_id=config.id,
        before=before,
        after=FeeConfigRead.model_validate(config).model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(config)
    return FeeConfigRead.model_validate(config)
