import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.contract import ContractRead, ProposeContractRequest
from app.services import contracts as contracts_service

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("", response_model=list[ContractRead])
async def list_contracts(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[ContractRead]:
    contracts = await contracts_service.list_contracts_for_user(db, user)
    return [ContractRead.model_validate(c) for c in contracts]


@router.post("", response_model=ContractRead)
async def propose_contract(
    payload: ProposeContractRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ContractRead:
    contract = await contracts_service.propose_contract(
        db,
        user=user,
        counterpart_id=payload.counterpart_id,
        title=payload.title,
        terms_text=payload.terms_text,
        campaign_id=payload.campaign_id,
    )
    return ContractRead.model_validate(contract)


@router.get("/{contract_id}", response_model=ContractRead)
async def get_contract(
    contract_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ContractRead:
    contract = await contracts_service.get_contract_for_user(db, contract_id=contract_id, user=user)
    return ContractRead.model_validate(contract)


@router.post("/{contract_id}/accept", response_model=ContractRead)
async def accept_contract(
    contract_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ContractRead:
    contract = await contracts_service.get_contract_for_user(db, contract_id=contract_id, user=user)
    contract = await contracts_service.respond_to_contract(db, contract=contract, user=user, accept=True)
    return ContractRead.model_validate(contract)


@router.post("/{contract_id}/decline", response_model=ContractRead)
async def decline_contract(
    contract_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ContractRead:
    contract = await contracts_service.get_contract_for_user(db, contract_id=contract_id, user=user)
    contract = await contracts_service.respond_to_contract(db, contract=contract, user=user, accept=False)
    return ContractRead.model_validate(contract)


@router.post("/{contract_id}/cancel", response_model=ContractRead)
async def cancel_contract(
    contract_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ContractRead:
    contract = await contracts_service.get_contract_for_user(db, contract_id=contract_id, user=user)
    contract = await contracts_service.cancel_contract(db, contract=contract, user=user)
    return ContractRead.model_validate(contract)
