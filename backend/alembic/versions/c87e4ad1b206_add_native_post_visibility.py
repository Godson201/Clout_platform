"""add native post visibility

Revision ID: c87e4ad1b206
Revises: a6c1e09d2b77
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c87e4ad1b206"
down_revision: Union[str, None] = "a6c1e09d2b77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    visibility = sa.Enum("public", "followers", "brands_only", "private", name="native_post_visibility")
    visibility.create(op.get_bind(), checkfirst=True)
    op.add_column("native_posts", sa.Column("visibility", visibility, nullable=False, server_default="public"))
    op.create_index(op.f("ix_native_posts_visibility"), "native_posts", ["visibility"])

def downgrade() -> None:
    op.drop_index(op.f("ix_native_posts_visibility"), table_name="native_posts")
    op.drop_column("native_posts", "visibility")
    sa.Enum(name="native_post_visibility").drop(op.get_bind(), checkfirst=True)
