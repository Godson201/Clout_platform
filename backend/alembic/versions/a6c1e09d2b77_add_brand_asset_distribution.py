"""add brand asset distribution

Revision ID: a6c1e09d2b77
Revises: d40a4d817e71
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6c1e09d2b77"
down_revision: Union[str, None] = "d40a4d817e71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    distribution = sa.Enum(
        "campaign_eligible", "specific_influencers", "all_influencers", name="asset_distribution"
    )
    distribution.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "advertisement_assets",
        sa.Column("distribution", distribution, nullable=False, server_default="campaign_eligible"),
    )
    op.create_table(
        "asset_share_recipients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("influencer_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["advertisement_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["influencer_id"], ["influencers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "influencer_id", name="uq_asset_share_recipient"),
    )
    op.create_index(op.f("ix_asset_share_recipients_asset_id"), "asset_share_recipients", ["asset_id"])
    op.create_index(op.f("ix_asset_share_recipients_influencer_id"), "asset_share_recipients", ["influencer_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_asset_share_recipients_influencer_id"), table_name="asset_share_recipients")
    op.drop_index(op.f("ix_asset_share_recipients_asset_id"), table_name="asset_share_recipients")
    op.drop_table("asset_share_recipients")
    op.drop_column("advertisement_assets", "distribution")
    sa.Enum(name="asset_distribution").drop(op.get_bind(), checkfirst=True)
