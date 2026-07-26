import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import Brand
from app.models.enums import HighlightCategory, ProfileOwnerType
from app.models.influencer import Influencer
from app.models.profile_highlight import ProfileHighlight
from app.schemas.profile_highlight import ProfileHighlightRead
from app.schemas.public_profile import PublicBrandProfile, PublicInfluencerProfile


def _is_visible(visibility_settings: dict, section: str) -> bool:
    # Absent key means visible — see Brand/Influencer.visibility_settings.
    return visibility_settings.get(section, True)


async def _highlights_for(
    db: AsyncSession, *, owner_type: ProfileOwnerType, owner_id: uuid.UUID, category: HighlightCategory
) -> list[ProfileHighlightRead]:
    result = await db.execute(
        select(ProfileHighlight)
        .where(
            ProfileHighlight.owner_type == owner_type,
            ProfileHighlight.owner_id == owner_id,
            ProfileHighlight.category == category,
        )
        .order_by(ProfileHighlight.occurred_on.desc().nulls_last(), ProfileHighlight.created_at.desc())
    )
    return [ProfileHighlightRead.model_validate(h) for h in result.scalars().all()]


async def build_public_brand_profile(db: AsyncSession, brand: Brand) -> PublicBrandProfile:
    v = brand.visibility_settings or {}
    awards = (
        await _highlights_for(db, owner_type=ProfileOwnerType.BRAND, owner_id=brand.id, category=HighlightCategory.AWARD)
        if _is_visible(v, "awards")
        else []
    )
    events = (
        await _highlights_for(db, owner_type=ProfileOwnerType.BRAND, owner_id=brand.id, category=HighlightCategory.EVENT)
        if _is_visible(v, "events")
        else []
    )

    return PublicBrandProfile(
        id=brand.id,
        business_name=brand.business_name,
        sector=brand.sector,
        logo_url=brand.logo_url,
        verification_status=brand.verification_status,
        location=brand.location if _is_visible(v, "location") else None,
        province=brand.province if _is_visible(v, "location") else None,
        description=brand.description if _is_visible(v, "about") else None,
        legacy=brand.legacy if _is_visible(v, "legacy") else None,
        website=brand.website if _is_visible(v, "about") else None,
        contact_email=brand.contact_email if _is_visible(v, "contact") else None,
        contact_phone=brand.contact_phone if _is_visible(v, "contact") else None,
        awards=awards,
        events=events,
    )


async def build_public_influencer_profile(db: AsyncSession, influencer: Influencer) -> PublicInfluencerProfile:
    v = influencer.visibility_settings or {}
    awards = (
        await _highlights_for(
            db, owner_type=ProfileOwnerType.INFLUENCER, owner_id=influencer.id, category=HighlightCategory.AWARD
        )
        if _is_visible(v, "awards")
        else []
    )
    events = (
        await _highlights_for(
            db, owner_type=ProfileOwnerType.INFLUENCER, owner_id=influencer.id, category=HighlightCategory.EVENT
        )
        if _is_visible(v, "events")
        else []
    )

    return PublicInfluencerProfile(
        id=influencer.id,
        display_name=influencer.display_name,
        username=influencer.username,
        sector=influencer.sector,
        profile_picture_url=influencer.profile_picture_url,
        verification_status=influencer.verification_status,
        location=influencer.location if _is_visible(v, "location") else None,
        province=influencer.province if _is_visible(v, "location") else None,
        bio=influencer.bio if _is_visible(v, "about") else None,
        legacy=influencer.legacy if _is_visible(v, "legacy") else None,
        follower_tier=influencer.follower_tier if _is_visible(v, "follower_stats") else None,
        estimated_followers=influencer.estimated_followers if _is_visible(v, "follower_stats") else None,
        awards=awards,
        events=events,
    )
