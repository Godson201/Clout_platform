from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import decrypt_token
from app.core.platform_capabilities import get_capabilities
from app.models.advertisement_asset import AdvertisementAsset
from app.models.advertisement_rendition import AdvertisementRendition
from app.models.campaign import Campaign
from app.models.campaign_slot import CampaignSlot
from app.models.enums import (
    AssetStatus,
    AssetType,
    NotificationType,
    PublishMode,
    RenditionStatus,
    SlotStatus,
    SocialAccountStatus,
    SocialPostStatus,
)
from app.models.influencer import Influencer
from app.models.social_account import SocialAccount
from app.models.social_post import SocialPost
from app.services.notifications import notify_user
from app.services.social import get_adapter
from app.services.storage import get_storage_backend

settings = get_settings()


def _format_location(influencer: Influencer) -> str:
    parts = [influencer.admin_village, influencer.admin_cell, influencer.admin_sector, influencer.location, influencer.province]
    formatted = ", ".join(p for p in parts if p)
    return formatted or "Location not shared"


async def _notify_brand_of_publish(db: AsyncSession, *, campaign: Campaign, slot: CampaignSlot, post: SocialPost) -> None:
    influencer = await db.get(Influencer, slot.influencer_id)
    influencer_name = influencer.display_name if influencer else "An influencer"
    location = _format_location(influencer) if influencer else "Location not shared"
    await notify_user(
        db,
        user_id=campaign.brand_id,
        type_=NotificationType.INFLUENCER_POST_PUBLISHED,
        title=f"{influencer_name} published your ad on {slot.platform.value}",
        body=f"{influencer_name} just posted your ad on {slot.platform.value}. Location: {location}.",
        link=f"/brand/campaigns/{campaign.id}",
        data={
            "campaign_id": str(campaign.id),
            "slot_id": str(slot.id),
            "influencer_id": str(slot.influencer_id) if slot.influencer_id else None,
            "influencer_name": influencer_name,
            "location": location,
            "post_url": post.post_url,
            "platform": slot.platform.value,
        },
    )


async def _get_ready_rendition_url(db: AsyncSession, *, campaign: Campaign, slot: CampaignSlot) -> str:
    asset_result = await db.execute(
        select(AdvertisementAsset).where(
            AdvertisementAsset.advertisement_id == campaign.advertisement_id,
            AdvertisementAsset.asset_type == AssetType.VIDEO,
            AdvertisementAsset.status == AssetStatus.READY,
        )
    )
    asset = asset_result.scalars().first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Advertisement has no ready video asset")

    rendition_result = await db.execute(
        select(AdvertisementRendition).where(
            AdvertisementRendition.asset_id == asset.id,
            AdvertisementRendition.platform == slot.platform,
            AdvertisementRendition.status == RenditionStatus.READY,
        )
    )
    rendition = rendition_result.scalar_one_or_none()
    if rendition is None or rendition.storage_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No ready {slot.platform.value} rendition for this advertisement yet",
        )

    storage = get_storage_backend()
    return f"{settings.PUBLIC_BASE_URL}{storage.url_for(rendition.storage_key)}"


async def create_post_for_slot(
    db: AsyncSession, *, slot: CampaignSlot, social_account: SocialAccount, caption: str
) -> SocialPost:
    """Decides AUTO vs MANUAL from the platform's current capability (see
    app.core.platform_capabilities) — never from user input. AUTO calls the
    adapter immediately; MANUAL just records the post as PENDING and waits for
    the influencer to submit the live post's URL via submit_manual_post_url.
    """
    if slot.status != SlotStatus.CLAIMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Slot must be claimed to post, is '{slot.status.value}'"
        )
    if social_account.platform != slot.platform:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Connected account's platform doesn't match this slot"
        )
    if social_account.status != SocialAccountStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reconnect this social account first")

    existing = await db.execute(select(SocialPost).where(SocialPost.campaign_slot_id == slot.id))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This slot already has a post")

    campaign_result = await db.execute(select(Campaign).where(Campaign.id == slot.campaign_id))
    campaign = campaign_result.scalar_one()

    capabilities = get_capabilities(slot.platform)
    publish_mode = PublishMode.AUTO if capabilities.can_auto_publish else PublishMode.MANUAL

    post = SocialPost(
        campaign_slot_id=slot.id,
        social_account_id=social_account.id,
        platform=slot.platform,
        publish_mode=publish_mode,
        caption=caption,
        status=SocialPostStatus.PENDING,
    )
    db.add(post)

    if publish_mode == PublishMode.AUTO:
        video_url = await _get_ready_rendition_url(db, campaign=campaign, slot=slot)
        adapter = get_adapter(slot.platform)
        access_token = decrypt_token(social_account.access_token_encrypted)

        try:
            result = await adapter.publish_post(access_token=access_token, video_url=video_url, caption=caption)
        except Exception:
            post.status = SocialPostStatus.FAILED
            await db.commit()
            await db.refresh(post)
            return post

        post.external_post_id = result.external_post_id
        post.post_url = result.post_url
        post.status = SocialPostStatus.PUBLISHED
        post.published_at = datetime.now(timezone.utc)
        slot.status = SlotStatus.PUBLISHED

    await db.commit()
    await db.refresh(post)

    if post.status == SocialPostStatus.PUBLISHED:
        await _notify_brand_of_publish(db, campaign=campaign, slot=slot, post=post)

    return post


async def submit_manual_post_url(
    db: AsyncSession, *, post: SocialPost, slot: CampaignSlot, post_url: str
) -> SocialPost:
    if post.publish_mode != PublishMode.MANUAL:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This post isn't in manual publish mode")
    if post.status == SocialPostStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This post has already been submitted")

    post.post_url = post_url
    post.status = SocialPostStatus.PUBLISHED
    post.published_at = datetime.now(timezone.utc)
    slot.status = SlotStatus.PUBLISHED

    await db.commit()
    await db.refresh(post)

    campaign_result = await db.execute(select(Campaign).where(Campaign.id == slot.campaign_id))
    campaign = campaign_result.scalar_one()
    await _notify_brand_of_publish(db, campaign=campaign, slot=slot, post=post)

    return post
