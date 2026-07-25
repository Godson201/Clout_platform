from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPk


class AdvertisementTemplate(UUIDPk, TimestampMixin, Base):
    """Platform-defined starting points for the Brand Toolkit (Product, Service,
    Campaign, E-commerce, SaaS, Brand Visibility, Song, Movie Trailer, Concert,
    Government, Police, RBC, Other). Seeded by app.seeds.seed; admins can add or
    retire templates via /admin/templates, which is the Phase 2 stand-in for the
    "template approval" responsibility called out in the platform's admin scope.
    """

    __tablename__ = "advertisement_templates"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    default_duration_seconds: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
