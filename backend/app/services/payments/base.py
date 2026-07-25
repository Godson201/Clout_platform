from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.models.enums import PaymentStatus


@dataclass(frozen=True)
class InitiationResult:
    provider_reference: str
    status: PaymentStatus
    raw_payload: dict | None = None


@dataclass(frozen=True)
class StatusResult:
    status: PaymentStatus
    raw_payload: dict | None = None
    failure_reason: str | None = None


class PaymentClient(Protocol):
    """Abstraction over an external mobile-money provider's Collections
    (charging a payer) and Disbursements (paying out a payee) APIs. MTN MoMo is
    the only real implementation (see momo.py); MockPaymentClient stands in for
    it everywhere there's no sandbox credentials (all of local dev + the test
    suite). Business logic in services/campaign_funding.py, payouts.py, and
    refunds.py is written entirely against this interface, so adding a second
    provider (e.g. Airtel Money) later means a new adapter, not call-site changes.
    """

    async def initiate_collection(
        self, *, phone_number: str, amount: Decimal, currency: str, external_id: str, payer_message: str
    ) -> InitiationResult: ...

    async def get_collection_status(self, provider_reference: str) -> StatusResult: ...

    async def initiate_disbursement(
        self, *, phone_number: str, amount: Decimal, currency: str, external_id: str, payee_message: str
    ) -> InitiationResult: ...

    async def get_disbursement_status(self, provider_reference: str) -> StatusResult: ...
