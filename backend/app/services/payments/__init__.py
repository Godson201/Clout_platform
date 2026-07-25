from app.core.config import get_settings
from app.models.enums import PaymentProvider
from app.services.payments.base import InitiationResult, PaymentClient, StatusResult
from app.services.payments.mock import MockPaymentClient
from app.services.payments.momo import MoMoPaymentClient

__all__ = ["InitiationResult", "PaymentClient", "StatusResult", "get_payment_client", "get_active_provider"]

_mock_client = MockPaymentClient()
_momo_client = MoMoPaymentClient()


def get_payment_client() -> PaymentClient:
    settings = get_settings()
    if settings.PAYMENT_PROVIDER_MODE == "momo":
        return _momo_client
    return _mock_client


def get_active_provider() -> PaymentProvider:
    settings = get_settings()
    return PaymentProvider.MOMO if settings.PAYMENT_PROVIDER_MODE == "momo" else PaymentProvider.MOCK
