import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import ReportGeneratorMode
from app.models.mixins import UUIDPk


class CampaignReport(UUIDPk, Base):
    """A generated brand-facing summary. `data_snapshot` is the exact
    CampaignAnalytics + comment-sentiment payload the narrative was generated
    from — kept verbatim so the report is reproducible/auditable and so
    validate_narrative_numbers can be re-run against it later if needed.
    Regenerating a report creates a new row rather than overwriting the old
    one, same append-only philosophy as the ledger and metric snapshots.
    """

    __tablename__ = "campaign_reports"

    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    narrative: Mapped[str] = mapped_column(Text)
    data_snapshot: Mapped[dict] = mapped_column(JSON)
    generator: Mapped[ReportGeneratorMode] = mapped_column(
        Enum(ReportGeneratorMode, name="report_generator_mode", values_callable=lambda e: [m.value for m in e])
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
