"""add campaign creatives

Revision ID: f2c7b8e9a1d3
Revises: e1f39c74d502
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2c7b8e9a1d3"
down_revision: Union[str, None] = "e1f39c74d502"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_creatives",
        sa.Column("campaign_slot_id", sa.Uuid(), nullable=False),
        sa.Column("influencer_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("native_post_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_slot_id"], ["campaign_slots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["influencer_id"], ["influencers.id"]),
        sa.ForeignKeyConstraint(["native_post_id"], ["native_posts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_slot_id", name="uq_campaign_creative_slot"),
        sa.UniqueConstraint("storage_key"),
        sa.UniqueConstraint("native_post_id"),
    )
    op.create_index(op.f("ix_campaign_creatives_campaign_slot_id"), "campaign_creatives", ["campaign_slot_id"])
    op.create_index(op.f("ix_campaign_creatives_influencer_id"), "campaign_creatives", ["influencer_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_creatives_influencer_id"), table_name="campaign_creatives")
    op.drop_index(op.f("ix_campaign_creatives_campaign_slot_id"), table_name="campaign_creatives")
    op.drop_table("campaign_creatives")
