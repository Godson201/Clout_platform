"""add native post distributions

Revision ID: e1f39c74d502
Revises: c87e4ad1b206
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e1f39c74d502"
down_revision: Union[str, None] = "c87e4ad1b206"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table("native_post_distributions",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False), sa.Column("social_account_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.Enum("tiktok", "instagram", "facebook", "youtube", name="social_platform"), nullable=False),
        sa.Column("status", sa.Enum("pending", "published", "failed", "deleted", name="social_post_status"), nullable=False),
        sa.Column("external_post_id", sa.String(length=128)), sa.Column("post_url", sa.String(length=1024)), sa.Column("error_message", sa.Text()),
        sa.ForeignKeyConstraint(["post_id"], ["native_posts.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["social_account_id"], ["social_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("post_id", "social_account_id", name="uq_native_post_distribution_account"))
    op.create_index(op.f("ix_native_post_distributions_post_id"), "native_post_distributions", ["post_id"])
    op.create_index(op.f("ix_native_post_distributions_social_account_id"), "native_post_distributions", ["social_account_id"])

def downgrade() -> None:
    op.drop_index(op.f("ix_native_post_distributions_social_account_id"), table_name="native_post_distributions")
    op.drop_index(op.f("ix_native_post_distributions_post_id"), table_name="native_post_distributions")
    op.drop_table("native_post_distributions")
