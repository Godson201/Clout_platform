import base64
import time
import uuid
from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.models.enums import PaymentStatus
from app.services.payments.base import InitiationResult, StatusResult

settings = get_settings()

_MOMO_STATUS_MAP = {
    "PENDING": PaymentStatus.PENDING,
    "SUCCESSFUL": PaymentStatus.SUCCESSFUL,
    "FAILED": PaymentStatus.FAILED,
}


class MoMoConfigurationError(RuntimeError):
    pass


class _TokenCache:
    """MoMo access tokens are short-lived (~1h); avoid round-tripping the token
    endpoint on every single request while still never hardcoding a token."""

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0

    def get(self) -> str | None:
        return self._token if time.monotonic() < self._expires_at else None

    def set(self, token: str, expires_in_seconds: int) -> None:
        self._token = token
        self._expires_at = time.monotonic() + max(expires_in_seconds - 30, 0)


_collections_token_cache = _TokenCache()
_disbursements_token_cache = _TokenCache()


class MoMoPaymentClient:
    """Real MTN MoMo Collections + Disbursements REST client. Never exercised in
    this codebase's test suite — there's no sandbox credential available in this
    environment — but implements the actual MTN MoMo API shape so switching
    PAYMENT_PROVIDER_MODE from "mock" to "momo" (plus setting the MOMO_* env vars)
    is the entire migration; no call-site changes in campaign_funding.py /
    payouts.py / refunds.py.
    """

    def __init__(self) -> None:
        self._base_url = settings.MOMO_BASE_URL
        self._target_env = settings.MOMO_TARGET_ENVIRONMENT

    def _require(self, value: str | None, name: str) -> str:
        if not value:
            raise MoMoConfigurationError(f"{name} is not configured — set it in the environment to use MoMo live")
        return value

    async def _get_token(self, *, product: str, cache: _TokenCache) -> str:
        cached = cache.get()
        if cached is not None:
            return cached

        if product == "collection":
            api_user = self._require(settings.MOMO_COLLECTIONS_API_USER, "MOMO_COLLECTIONS_API_USER")
            api_key = self._require(settings.MOMO_COLLECTIONS_API_KEY, "MOMO_COLLECTIONS_API_KEY")
            subscription_key = self._require(
                settings.MOMO_COLLECTIONS_SUBSCRIPTION_KEY, "MOMO_COLLECTIONS_SUBSCRIPTION_KEY"
            )
        else:
            api_user = self._require(settings.MOMO_DISBURSEMENTS_API_USER, "MOMO_DISBURSEMENTS_API_USER")
            api_key = self._require(settings.MOMO_DISBURSEMENTS_API_KEY, "MOMO_DISBURSEMENTS_API_KEY")
            subscription_key = self._require(
                settings.MOMO_DISBURSEMENTS_SUBSCRIPTION_KEY, "MOMO_DISBURSEMENTS_SUBSCRIPTION_KEY"
            )

        basic = base64.b64encode(f"{api_user}:{api_key}".encode()).decode()
        async with httpx.AsyncClient(base_url=self._base_url, timeout=15.0) as client:
            resp = await client.post(
                f"/{product}/token/",
                headers={"Authorization": f"Basic {basic}", "Ocp-Apim-Subscription-Key": subscription_key},
            )
            resp.raise_for_status()
            body = resp.json()

        cache.set(body["access_token"], int(body.get("expires_in", 3600)))
        return body["access_token"]

    async def initiate_collection(
        self, *, phone_number: str, amount: Decimal, currency: str, external_id: str, payer_message: str
    ) -> InitiationResult:
        token = await self._get_token(product="collection", cache=_collections_token_cache)
        subscription_key = self._require(
            settings.MOMO_COLLECTIONS_SUBSCRIPTION_KEY, "MOMO_COLLECTIONS_SUBSCRIPTION_KEY"
        )
        reference_id = str(uuid.uuid4())

        async with httpx.AsyncClient(base_url=self._base_url, timeout=15.0) as client:
            resp = await client.post(
                "/collection/v1_0/requesttopay",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Reference-Id": reference_id,
                    "X-Target-Environment": self._target_env,
                    "Ocp-Apim-Subscription-Key": subscription_key,
                    "Content-Type": "application/json",
                },
                json={
                    "amount": str(amount),
                    "currency": currency,
                    "externalId": external_id,
                    "payer": {"partyIdType": "MSISDN", "partyId": phone_number},
                    "payerMessage": payer_message,
                    "payeeNote": payer_message,
                },
            )
            resp.raise_for_status()

        return InitiationResult(provider_reference=reference_id, status=PaymentStatus.PENDING)

    async def get_collection_status(self, provider_reference: str) -> StatusResult:
        token = await self._get_token(product="collection", cache=_collections_token_cache)
        subscription_key = self._require(
            settings.MOMO_COLLECTIONS_SUBSCRIPTION_KEY, "MOMO_COLLECTIONS_SUBSCRIPTION_KEY"
        )

        async with httpx.AsyncClient(base_url=self._base_url, timeout=15.0) as client:
            resp = await client.get(
                f"/collection/v1_0/requesttopay/{provider_reference}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Target-Environment": self._target_env,
                    "Ocp-Apim-Subscription-Key": subscription_key,
                },
            )
            resp.raise_for_status()
            body = resp.json()

        status = _MOMO_STATUS_MAP.get(body.get("status", ""), PaymentStatus.PENDING)
        return StatusResult(status=status, raw_payload=body, failure_reason=body.get("reason"))

    async def initiate_disbursement(
        self, *, phone_number: str, amount: Decimal, currency: str, external_id: str, payee_message: str
    ) -> InitiationResult:
        token = await self._get_token(product="disbursement", cache=_disbursements_token_cache)
        subscription_key = self._require(
            settings.MOMO_DISBURSEMENTS_SUBSCRIPTION_KEY, "MOMO_DISBURSEMENTS_SUBSCRIPTION_KEY"
        )
        reference_id = str(uuid.uuid4())

        async with httpx.AsyncClient(base_url=self._base_url, timeout=15.0) as client:
            resp = await client.post(
                "/disbursement/v1_0/transfer",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Reference-Id": reference_id,
                    "X-Target-Environment": self._target_env,
                    "Ocp-Apim-Subscription-Key": subscription_key,
                    "Content-Type": "application/json",
                },
                json={
                    "amount": str(amount),
                    "currency": currency,
                    "externalId": external_id,
                    "payee": {"partyIdType": "MSISDN", "partyId": phone_number},
                    "payerMessage": payee_message,
                    "payeeNote": payee_message,
                },
            )
            resp.raise_for_status()

        return InitiationResult(provider_reference=reference_id, status=PaymentStatus.PENDING)

    async def get_disbursement_status(self, provider_reference: str) -> StatusResult:
        token = await self._get_token(product="disbursement", cache=_disbursements_token_cache)
        subscription_key = self._require(
            settings.MOMO_DISBURSEMENTS_SUBSCRIPTION_KEY, "MOMO_DISBURSEMENTS_SUBSCRIPTION_KEY"
        )

        async with httpx.AsyncClient(base_url=self._base_url, timeout=15.0) as client:
            resp = await client.get(
                f"/disbursement/v1_0/transfer/{provider_reference}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Target-Environment": self._target_env,
                    "Ocp-Apim-Subscription-Key": subscription_key,
                },
            )
            resp.raise_for_status()
            body = resp.json()

        status = _MOMO_STATUS_MAP.get(body.get("status", ""), PaymentStatus.PENDING)
        return StatusResult(status=status, raw_payload=body, failure_reason=body.get("reason"))
