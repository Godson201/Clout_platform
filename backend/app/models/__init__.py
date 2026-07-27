"""Import every mapped model so `Base.metadata` is fully populated for Alembic
autogenerate and for `create_all` in tests. Import order matters only in that
every module referenced by a string forward-ref (e.g. "User", "Brand") must be
imported somewhere before `configure_mappers()` runs.
"""

from app.models.advertisement import Advertisement  # noqa: F401
from app.models.advertisement_asset import AdvertisementAsset  # noqa: F401
from app.models.advertisement_rendition import AdvertisementRendition  # noqa: F401
from app.models.advertisement_template import AdvertisementTemplate  # noqa: F401
from app.models.announcement import Announcement  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.brand import Brand  # noqa: F401
from app.models.campaign import Campaign  # noqa: F401
from app.models.campaign_report import CampaignReport  # noqa: F401
from app.models.campaign_slot import CampaignSlot  # noqa: F401
from app.models.comment import Comment  # noqa: F401
from app.models.comment_analysis import CommentAnalysis  # noqa: F401
from app.models.contract import Contract  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.email_token import EmailToken  # noqa: F401
from app.models.fee_config import FeeConfig  # noqa: F401
from app.models.influencer import Influencer  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.payment import Payment  # noqa: F401
from app.models.payout import Payout  # noqa: F401
from app.models.post_metric_snapshot import PostMetricSnapshot  # noqa: F401
from app.models.profile_highlight import ProfileHighlight  # noqa: F401
from app.models.rbac import Permission, Role, role_permissions, user_roles  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.refund import Refund  # noqa: F401
from app.models.social_account import SocialAccount  # noqa: F401
from app.models.social_oauth_state import SocialOAuthState  # noqa: F401
from app.models.social_post import SocialPost  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.view_rate import ViewRate  # noqa: F401
from app.models.wallet import Wallet  # noqa: F401

__all__ = [
    "Advertisement",
    "AdvertisementAsset",
    "AdvertisementRendition",
    "AdvertisementTemplate",
    "Announcement",
    "AuditLog",
    "Brand",
    "Campaign",
    "CampaignReport",
    "CampaignSlot",
    "Comment",
    "CommentAnalysis",
    "Contract",
    "Conversation",
    "EmailToken",
    "FeeConfig",
    "Influencer",
    "Message",
    "Notification",
    "Payment",
    "Payout",
    "PostMetricSnapshot",
    "ProfileHighlight",
    "Permission",
    "Role",
    "role_permissions",
    "user_roles",
    "RefreshToken",
    "Refund",
    "SocialAccount",
    "SocialOAuthState",
    "SocialPost",
    "Transaction",
    "User",
    "ViewRate",
    "Wallet",
]
