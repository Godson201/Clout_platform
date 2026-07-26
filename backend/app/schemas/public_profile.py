import uuid

from pydantic import BaseModel

from app.models.enums import FollowerTier, VerificationStatus
from app.schemas.profile_highlight import ProfileHighlightRead

# Keys a profile owner can turn OFF via visibility_settings (see Brand/Influencer
# .visibility_settings — absent key means visible). Kept here, next to where
# they're consumed, as the one source of truth the settings UI's toggle list
# and the public-profile builder both read from.
VISIBILITY_SECTIONS = ["about", "legacy", "location", "awards", "events", "contact", "follower_stats"]


class PublicBrandProfile(BaseModel):
    id: uuid.UUID
    business_name: str
    sector: str | None
    logo_url: str | None
    verification_status: VerificationStatus
    location: str | None = None
    province: str | None = None
    description: str | None = None
    legacy: str | None = None
    website: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    awards: list[ProfileHighlightRead] = []
    events: list[ProfileHighlightRead] = []


class PublicInfluencerProfile(BaseModel):
    id: uuid.UUID
    display_name: str
    username: str
    sector: str | None
    profile_picture_url: str | None
    verification_status: VerificationStatus
    location: str | None = None
    province: str | None = None
    bio: str | None = None
    legacy: str | None = None
    follower_tier: FollowerTier | None = None
    estimated_followers: int | None = None
    awards: list[ProfileHighlightRead] = []
    events: list[ProfileHighlightRead] = []
