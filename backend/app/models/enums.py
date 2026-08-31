import enum


class UserType(str, enum.Enum):
    BRAND = "brand"
    INFLUENCER = "influencer"
    ADMIN = "admin"


class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "unverified"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WalletOwnerType(str, enum.Enum):
    BRAND = "brand"
    INFLUENCER = "influencer"
    PLATFORM = "platform"
    # One per campaign (owner_id = campaign.id) — holds brand funds that are
    # earned-but-contingent on performance, until Phase 6 settlement releases them.
    ESCROW = "escrow"
    # Singleton, owner_id=None. Represents the boundary where real MoMo cash
    # crosses in (brand funding) or out (payouts/refunds) of the ledger — every
    # debit needs a matching credit even when the "other side" is the real world.
    EXTERNAL = "external"


class TransactionType(str, enum.Enum):
    FUNDING = "funding"
    ESCROW_HOLD = "escrow_hold"
    ESCROW_RELEASE = "escrow_release"
    PAYOUT = "payout"
    REFUND = "refund"
    FEE = "fee"
    ADJUSTMENT = "adjustment"


class PaymentProvider(str, enum.Enum):
    MOMO = "momo"
    MOCK = "mock"


class PaymentStatus(str, enum.Enum):
    """Shared shape for Payment (collections), Payout, and Refund (disbursements)
    — all three are "we asked an external provider to move money, and are
    waiting to hear back" state machines.
    """

    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"


class SocialPlatform(str, enum.Enum):
    """Shared across Brand Toolkit exports (Phase 2) and social account/posting
    integrations (Phase 5+) so both layers speak the same platform identifiers."""

    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"


class AdvertisementStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"


class AssetType(str, enum.Enum):
    VIDEO = "video"
    IMAGE = "image"
    LOGO = "logo"
    AUDIO = "audio"
    VOICEOVER = "voiceover"


class AssetStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class RenditionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class FollowerTier(str, enum.Enum):
    """Self-reported until Phase 5 connects real social accounts and can verify
    actual follower counts. Thresholds are a placeholder business decision, not
    yet admin-configurable.
    """

    NANO = "nano"  # <5,000
    MICRO = "micro"  # 5,000-20,000
    MID = "mid"  # 20,000-100,000
    MACRO = "macro"  # 100,000+


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_FUNDING = "pending_funding"
    # FUNDED/LISTED are collapsed into one step in Phase 3 since there's no real
    # escrow yet (see services/campaign_funding.py) — both values are kept
    # distinct in the enum so Phase 4 can insert real gating between them
    # without a migration.
    FUNDED = "funded"
    LISTED = "listed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SlotStatus(str, enum.Enum):
    """OPEN/CLAIMED/CANCELLED shipped in Phase 3; COMPLETED/PARTIALLY_COMPLETED/
    FAILED are driven by Phase 4's manual admin settlement bridge; PUBLISHED/
    TRACKING are driven by Phase 5's posting + metrics-polling flow. RECOVERED
    is deliberately left unused: Phase 8's recovery engine (see
    services/slot_recovery.py) never overwrites a slot's own delivery-outcome
    status with something recovery-related, since that status also drives
    influencer reliability history — recovery is instead tracked via each
    slot's recovered_from_slot_id/recovery_generation chain, on the *new* slot,
    not by relabeling the original.
    """

    OPEN = "open"
    CLAIMED = "claimed"
    PUBLISHED = "published"
    TRACKING = "tracking"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    RECOVERED = "recovered"
    CANCELLED = "cancelled"


# Slot states in which an influencer is still "using" one of their 5 concurrent
# slot allowance — referenced by both the atomic claim query and the matching
# service's active-slot-count factor.
ACTIVE_SLOT_STATUSES = (SlotStatus.CLAIMED, SlotStatus.PUBLISHED, SlotStatus.TRACKING)

# Slot states settlement (manual admin bridge or Phase 6's automatic window-
# expiry settlement) can act on — anything from "claimed but not yet posted"
# through "posted and being tracked".
SETTLEABLE_SLOT_STATUSES = (SlotStatus.CLAIMED, SlotStatus.PUBLISHED, SlotStatus.TRACKING)

# A campaign is COMPLETED once every one of its slots has reached one of these
# — nothing left that could still change the campaign's outcome.
TERMINAL_SLOT_STATUSES = (
    SlotStatus.COMPLETED,
    SlotStatus.PARTIALLY_COMPLETED,
    SlotStatus.FAILED,
    SlotStatus.CANCELLED,
    SlotStatus.RECOVERED,
)


class SocialAccountStatus(str, enum.Enum):
    ACTIVE = "active"
    # Access token past its expiry with no valid refresh token to renew it —
    # distinct from REVOKED so the UI can say "reconnect" instead of "removed".
    EXPIRED = "expired"
    REVOKED = "revoked"
    DISCONNECTED = "disconnected"


class PublishMode(str, enum.Enum):
    """Which workflow a SocialPost follows, decided per-platform by its adapter's
    capabilities (see app/services/social/base.py), never chosen by the user.
    """

    AUTO = "auto"
    MANUAL = "manual"


class SocialPostStatus(str, enum.Enum):
    PENDING = "pending"  # created; manual mode is waiting on the influencer's URL, auto mode is queued
    PUBLISHED = "published"
    FAILED = "failed"
    DELETED = "deleted"  # found missing on a later metrics poll — Scenario E from the payment/escrow analysis


class CommentCategory(str, enum.Enum):
    """Matches the product spec's category list directly — note it already
    blends intent (QUESTION/SUGGESTION/COMPLAINT) with sentiment-flavored
    buckets (POSITIVE/NEGATIVE/NEUTRAL); `CommentAnalysis.sentiment_score` is
    the separate continuous companion measure the spec also asks for, used for
    averaging/trending rather than bucketing.
    """

    QUESTION = "question"
    SUGGESTION = "suggestion"
    COMPLAINT = "complaint"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    OTHER = "other"


class SentimentLabel(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class ReportGeneratorMode(str, enum.Enum):
    TEMPLATE = "template"
    ANTHROPIC = "anthropic"


class EmailTokenPurpose(str, enum.Enum):
    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"


class ProfileOwnerType(str, enum.Enum):
    BRAND = "brand"
    INFLUENCER = "influencer"


class HighlightCategory(str, enum.Enum):
    AWARD = "award"
    EVENT = "event"


class AnnouncementAudience(str, enum.Enum):
    ALL = "all"
    BRANDS = "brands"
    INFLUENCERS = "influencers"


class MessageType(str, enum.Enum):
    TEXT = "text"
    AUDIO = "audio"
    VIDEO = "video"
    VOICE_NOTE = "voice_note"
    DOCUMENT = "document"


class ContractStatus(str, enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class AssetModerationStatus(str, enum.Enum):
    """Gates NotificationType.NEW_BRAND_MEDIA: an asset reaching AssetStatus.READY
    only means it's processed and playable, not that it's been broadcast to
    influencers — that only happens once an admin reviews and approves it here.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AssetDistribution(str, enum.Enum):
    """Who can receive an approved brand toolkit asset."""

    CAMPAIGN_ELIGIBLE = "campaign_eligible"
    SPECIFIC_INFLUENCERS = "specific_influencers"
    ALL_INFLUENCERS = "all_influencers"


class NotificationType(str, enum.Enum):
    # Fired to every influencer once a brand's advertisement asset finishes
    # processing and is playable — lets influencers browse fresh brand creative
    # without polling the marketplace themselves.
    NEW_BRAND_MEDIA = "new_brand_media"
    # Fired to a campaign's brand the moment an influencer's SocialPost for one
    # of its slots is confirmed published (auto or manual submit-url).
    INFLUENCER_POST_PUBLISHED = "influencer_post_published"
    # Fired to a campaign's brand the moment an influencer claims one of its slots.
    SLOT_CLAIMED = "slot_claimed"
    # Fired to a campaign's brand once its MoMo funding payment is confirmed.
    PAYMENT_CONFIRMED = "payment_confirmed"
    # Fired to a brand when an admin leaves feedback on one of their draft ad
    # assets (see AssetComment) — not fired for the brand's own comments.
    ASSET_COMMENT = "asset_comment"
    SOCIAL_FOLLOW = "social_follow"
    SOCIAL_LIKE = "social_like"
    SOCIAL_COMMENT = "social_comment"


class NativePostStatus(str, enum.Enum):
    PUBLISHED = "published"
    ARCHIVED = "archived"


class NativePostVisibility(str, enum.Enum):
    PUBLIC = "public"
    FOLLOWERS = "followers"
    BRANDS_ONLY = "brands_only"
    PRIVATE = "private"
