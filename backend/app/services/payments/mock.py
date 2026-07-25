import uuid
from decimal import Decimal

from app.models.enums import PaymentStatus
from app.services.payments.base import InitiationResult, StatusResult

# Module-level so state survives across separate get_payment_client() calls
# within the same process (mirrors a sandbox provider remembering its own
# requests) — this is a test/dev stand-in, never used when PAYMENT_PROVIDER_MODE
# is "momo", so it's fine for it to not survive a process restart.
_requests: dict[str, str] = {}  # provider_reference -> phone_number


def _simulated_status(phone_number: str) -> PaymentStatus:
    """Deterministic test hook: a phone number ending in "0000" simulates a
    provider-side failure (insufficient funds, wrong PIN, etc.) so failure/reversal
    code paths can be exercised without a real provider — the same convention
    test card numbers serve for card-payment sandboxes.
    """
    return PaymentStatus.FAILED if phone_number.endswith("0000") else PaymentStatus.SUCCESSFUL


class MockPaymentClient:
    async def initiate_collection(
        self, *, phone_number: str, amount: Decimal, currency: str, external_id: str, payer_message: str
    ) -> InitiationResult:
        reference = str(uuid.uuid4())
        _requests[reference] = phone_number
        return InitiationResult(provider_reference=reference, status=PaymentStatus.PENDING)

    async def get_collection_status(self, provider_reference: str) -> StatusResult:
        phone_number = _requests.get(provider_reference)
        if phone_number is None:
            return StatusResult(status=PaymentStatus.FAILED, failure_reason="Unknown reference")
        status = _simulated_status(phone_number)
        reason = "Simulated failure (mock phone number ends in 0000)" if status == PaymentStatus.FAILED else None
        return StatusResult(status=status, failure_reason=reason)

    async def initiate_disbursement(
        self, *, phone_number: str, amount: Decimal, currency: str, external_id: str, payee_message: str
    ) -> InitiationResult:
        reference = str(uuid.uuid4())
        _requests[reference] = phone_number
        return InitiationResult(provider_reference=reference, status=PaymentStatus.PENDING)

    async def get_disbursement_status(self, provider_reference: str) -> StatusResult:
        return await self.get_collection_status(provider_reference)
