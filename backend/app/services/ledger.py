import uuid
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionType, WalletOwnerType
from app.models.transaction import Transaction
from app.models.wallet import Wallet


class InsufficientBalanceError(Exception):
    pass


async def get_wallet(
    db: AsyncSession, *, owner_type: WalletOwnerType, owner_id: uuid.UUID | None, currency: str = "RWF"
) -> Wallet:
    result = await db.execute(
        select(Wallet).where(Wallet.owner_type == owner_type, Wallet.owner_id == owner_id, Wallet.currency == currency)
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise RuntimeError(f"No {owner_type.value} wallet found for owner_id={owner_id} currency={currency}")
    return wallet


async def get_or_create_wallet(
    db: AsyncSession, *, owner_type: WalletOwnerType, owner_id: uuid.UUID | None, currency: str = "RWF"
) -> Wallet:
    """Used for escrow wallets, which come into existence lazily the first time
    a campaign is funded rather than being pre-seeded like brand/influencer/
    platform wallets are at account-creation time.
    """
    result = await db.execute(
        select(Wallet).where(Wallet.owner_type == owner_type, Wallet.owner_id == owner_id, Wallet.currency == currency)
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        wallet = Wallet(owner_type=owner_type, owner_id=owner_id, currency=currency, balance=0)
        db.add(wallet)
        await db.flush()
    return wallet


async def record_transaction(
    db: AsyncSession,
    *,
    debit_wallet_id: uuid.UUID,
    credit_wallet_id: uuid.UUID,
    amount: Decimal,
    currency: str,
    type: TransactionType,
    reference: str,
    description: str | None = None,
    enforce_sufficient_balance: bool = True,
) -> Transaction:
    """Writes one immutable ledger row and atomically moves `amount` from
    debit_wallet's cached balance to credit_wallet's. The debit's balance check
    and update happen in a single conditional UPDATE (the same portable pattern
    as services/slot_claim.py's atomic claim) so two concurrent transactions
    against the same wallet can't both succeed past its available balance —
    `enforce_sufficient_balance=False` is only for crediting/debiting the
    EXTERNAL clearing wallet, which is allowed to go negative since it represents
    the boundary with real-world MoMo cash, not money actually held by CLOUT.
    """
    if amount <= 0:
        raise ValueError("Transaction amount must be positive")

    debit_stmt = update(Wallet).where(Wallet.id == debit_wallet_id)
    if enforce_sufficient_balance:
        debit_stmt = debit_stmt.where(Wallet.balance >= amount)
    debit_stmt = debit_stmt.values(balance=Wallet.balance - amount)

    result = await db.execute(debit_stmt)
    if result.rowcount == 0:
        raise InsufficientBalanceError(f"Wallet {debit_wallet_id} has insufficient balance for {amount}")

    await db.execute(update(Wallet).where(Wallet.id == credit_wallet_id).values(balance=Wallet.balance + amount))

    transaction = Transaction(
        debit_wallet_id=debit_wallet_id,
        credit_wallet_id=credit_wallet_id,
        amount=amount,
        currency=currency,
        type=type,
        reference=reference,
        description=description,
    )
    db.add(transaction)
    await db.flush()
    return transaction
