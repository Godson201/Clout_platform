import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.enums import WalletOwnerType
from app.models.wallet import Wallet

settings = get_settings()


async def create_wallet_for_owner(
    db: AsyncSession, *, owner_type: WalletOwnerType, owner_id: uuid.UUID | None
) -> Wallet:
    """Every brand/influencer gets an empty wallet at account-creation time so the
    ledger schema is never retrofitted once Phase 4 (payments/escrow) starts writing
    to it. No money moves here — balance starts at zero.
    """
    wallet = Wallet(owner_type=owner_type, owner_id=owner_id, currency=settings.DEFAULT_CURRENCY, balance=0)
    db.add(wallet)
    return wallet
