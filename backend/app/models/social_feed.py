import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import NativePostStatus, NativePostVisibility, SocialPlatform, SocialPostStatus
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
    visibility: Mapped[NativePostVisibility] = mapped_column(
        Enum(NativePostVisibility, name="native_post_visibility", values_callable=lambda e: [m.value for m in e]),
        default=NativePostVisibility.PUBLIC,
        index=True,
    )
    repost_of_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("native_posts.id", ondelete="SET NULL"), default=None, index=True)


class Hashtag(UUIDPk, TimestampMixin, Base):
    __tablename__ = "hashtags"
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)


class NativePostHashtag(Base):
    __tablename__ = "native_post_hashtags"
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("native_posts.id", ondelete="CASCADE"), primary_key=True)
    hashtag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("hashtags.id", ondelete="CASCADE"), primary_key=True)


class NativePostMedia(UUIDPk, TimestampMixin, Base):
    __tablename__ = "native_post_media"

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("native_posts.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    mime_type: Mapped[str] = mapped_column(String(128))
    media_type: Mapped[str] = mapped_column(String(16))
    alt_text: Mapped[str | None] = mapped_column(String(255), default=None)
    processing_status: Mapped[str] = mapped_column(String(16), default="ready", index=True)
    processed_storage_key: Mapped[str | None] = mapped_column(String(512), default=None)
    thumbnail_storage_key: Mapped[str | None] = mapped_column(String(512), default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    retry_count: Mapped[int] = mapped_column(default=0)


class NativePostDistribution(UUIDPk, TimestampMixin, Base):
    """One owner-authorized delivery of a native post to a connected account."""
    __tablename__ = "native_post_distributions"
    __table_args__ = (UniqueConstraint("post_id", "social_account_id", name="uq_native_post_distribution_account"),)
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("native_posts.id", ondelete="CASCADE"), index=True)
    social_account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("social_accounts.id", ondelete="CASCADE"), index=True)
    platform: Mapped[SocialPlatform] = mapped_column(Enum(SocialPlatform, name="social_platform", values_callable=lambda e: [m.value for m in e]))
    status: Mapped[SocialPostStatus] = mapped_column(Enum(SocialPostStatus, name="social_post_status", values_callable=lambda e: [m.value for m in e]), default=SocialPostStatus.PENDING)
    external_post_id: Mapped[str | None] = mapped_column(String(128), default=None)
    post_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)


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


class UserBlock(TimestampMixin, Base):
    __tablename__ = "user_blocks"
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id", name="uq_user_block"),)
    blocker_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    blocked_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class NativePostReport(UUIDPk, TimestampMixin, Base):
    __tablename__ = "native_post_reports"
    __table_args__ = (UniqueConstraint("post_id", "reporter_id", name="uq_native_post_report"),)
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("native_posts.id", ondelete="CASCADE"), index=True)
    reporter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reason: Mapped[str] = mapped_column(String(64))
    details: Mapped[str | None] = mapped_column(Text, default=None)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
