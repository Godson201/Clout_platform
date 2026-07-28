from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_admin
from app.models.brand import Brand
from app.models.contract import Contract
from app.models.influencer import Influencer
from app.schemas.contract import AdminContractRead, ContractRead

router = APIRouter(prefix="/admin/contracts", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[AdminContractRead])
async def list_all_contracts(db: AsyncSession = Depends(get_db)) -> list[AdminContractRead]:
    """Read-only oversight view — an admin can open/review any contract's
    terms between a brand and influencer (e.g. for dispute resolution), but
    accepting/declining/cancelling stays exclusive to the two parties
    themselves (see app/api/v1/contracts.py)."""
    result = await db.execute(select(Contract).order_by(Contract.created_at.desc()))
    contracts = result.scalars().all()

    items: list[AdminContractRead] = []
    for contract in contracts:
        brand = await db.get(Brand, contract.brand_id)
        influencer = await db.get(Influencer, contract.influencer_id)
        items.append(
            AdminContractRead(
                **ContractRead.model_validate(contract).model_dump(),
                brand_name=brand.business_name if brand else "Unknown",
                influencer_username=influencer.username if influencer else "unknown",
            )
        )
    return items
