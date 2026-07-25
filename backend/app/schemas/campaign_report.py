import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ReportGeneratorMode


class CampaignReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    campaign_id: uuid.UUID
    narrative: str
    data_snapshot: dict
    generator: ReportGeneratorMode
    created_at: datetime
