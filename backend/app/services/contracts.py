import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract
from app.models.enums import ContractStatus, UserType
from app.models.user import User
from app.services.relationships import brand_and_influencer_are_connected


async def propose_contract(
    db: AsyncSession,
    *,
    user: User,
    counterpart_id: uuid.UUID,
    title: str,
    terms_text: str,
    campaign_id: uuid.UUID | None = None,
) -> Contract:
    if user.user_type == UserType.BRAND:
        brand_id, influencer_id = user.id, counterpart_id
    elif user.user_type == UserType.INFLUENCER:
        brand_id, influencer_id = counterpart_id, user.id
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only brands and influencers can propose contracts")

    if not await brand_and_influencer_are_connected(db, brand_id=brand_id, influencer_id=influencer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only propose a contract to someone you have an active campaign relationship with",
        )

    contract = Contract(
        brand_id=brand_id,
        influencer_id=influencer_id,
        campaign_id=campaign_id,
        title=title,
        terms_text=terms_text,
        status=ContractStatus.PROPOSED,
        proposed_by_user_id=user.id,
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


async def get_contract_for_user(db: AsyncSession, *, contract_id: uuid.UUID, user: User) -> Contract:
    contract = await db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    if contract.brand_id != user.id and contract.influencer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a party to this contract")
    return contract


async def list_contracts_for_user(db: AsyncSession, user: User) -> list[Contract]:
    result = await db.execute(
        select(Contract)
        .where(or_(Contract.brand_id == user.id, Contract.influencer_id == user.id))
        .order_by(Contract.created_at.desc())
    )
    return list(result.scalars().all())


async def respond_to_contract(db: AsyncSession, *, contract: Contract, user: User, accept: bool) -> Contract:
    if contract.status != ContractStatus.PROPOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This contract is no longer pending")
    if contract.proposed_by_user_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You proposed this contract — the other party must respond")

    contract.status = ContractStatus.ACCEPTED if accept else ContractStatus.DECLINED
    contract.responded_by_user_id = user.id
    contract.responded_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(contract)
    return contract


async def cancel_contract(db: AsyncSession, *, contract: Contract, user: User) -> Contract:
    if contract.status != ContractStatus.PROPOSED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This contract is no longer pending")
    if contract.proposed_by_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the proposer can cancel this contract")

    contract.status = ContractStatus.CANCELLED
    await db.commit()
    await db.refresh(contract)
    return contract
