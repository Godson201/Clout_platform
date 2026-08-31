import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import NativePostStatus
from app.models.mixins import TimestampMixin, UUIDPk


class Follow(TimestampMixin, Base):
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_id", "following_id", name="uq_follow_pair"),)

    follower_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    following_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class NativePost(UUIDPk, TimestampMixin, Base):
    __tablename__ = "native_posts"
    __table_args__ = (Index("ix_native_posts_author_created", "author_id", "created_at"),)

    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[NativePostStatus] = mapped_column(
        Enum(NativePostStatus, name="native_post_status", values_callable=lambda e: [m.value for m in e]),
        default=NativePostStatus.PUBLISHED,
    )


class NativePostMedia(UUIDPk, TimestampMixin, Base):
    __tablename__ = "native_post_media"

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("native_posts.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    mime_type: Mapped[str] = mapped_column(String(128))
    media_type: Mapped[str] = mapped_column(String(16))
    alt_text: Mapped[str | None] = mapped_column(String(255), default=None)


class NativePostLike(TimestampMixin, Base):
    __tablename__ = "native_post_likes"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_native_post_like"),)

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("native_posts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class NativePostComment(UUIDPk, TimestampMixin, Base):
    __tablename__ = "native_post_comments"
    __table_args__ = (Index("ix_native_post_comments_post_created", "post_id", "created_at"),)

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("native_posts.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)


class NativePostSave(TimestampMixin, Base):
    __tablename__ = "native_post_saves"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_native_post_save"),)

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("native_posts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
