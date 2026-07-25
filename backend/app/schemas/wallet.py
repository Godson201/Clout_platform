import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import WalletOwnerType


class WalletRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_type: WalletOwnerType
    owner_id: uuid.UUID | None
    currency: str
    balance: Decimal
