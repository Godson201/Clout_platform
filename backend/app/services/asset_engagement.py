import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.advertisement import Advertisement
from app.models.advertisement_asset import AdvertisementAsset
from app.models.asset_comment import AssetComment
from app.models.asset_like import AssetLike
from app.models.brand import Brand
from app.models.enums import NotificationType, UserType
from app.models.user import User
from app.services.notifications import notify_user


async def get_asset_with_access(db: AsyncSession, *, user: User, asset_id: uuid.UUID) -> AdvertisementAsset:
    """A draft ad asset's comments/likes are visible only to the brand that
    owns it and admins reviewing it — never to influencers, since the asset
    itself isn't broadcast-visible until AssetModerationStatus.APPROVED.
    """
    asset = await db.get(AdvertisementAsset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    if user.user_type == UserType.ADMIN:
        return asset

    advertisement = await db.get(Advertisement, asset.advertisement_id)
    if advertisement is None or advertisement.brand_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


async def _author_display(db: AsyncSession, user: User) -> tuple[str, bool]:
    if user.user_type == UserType.ADMIN:
        return "Admin", True
    if user.user_type == UserType.BRAND:
        brand = await db.get(Brand, user.id)
        return (brand.business_name if brand else user.email), False
    return user.email, False


async def list_comments(db: AsyncSession, *, asset_id: uuid.UUID) -> list[tuple[AssetComment, str, bool]]:
    result = await db.execute(
        select(AssetComment).where(AssetComment.asset_id == asset_id).order_by(AssetComment.created_at.asc())
    )
    comments = result.scalars().all()

    enriched: list[tuple[AssetComment, str, bool]] = []
    for comment in comments:
        author = await db.get(User, comment.author_user_id)
        name, is_admin = await _author_display(db, author) if author else ("Unknown", False)
        enriched.append((comment, name, is_admin))
    return enriched


async def add_comment(
    db: AsyncSession, *, asset: AdvertisementAsset, author: User, body: str
) -> tuple[AssetComment, str, bool]:
    comment = AssetComment(asset_id=asset.id, author_user_id=author.id, body=body.strip())
    db.add(comment)
    await db.commit()
    await db.refresh(comment)

    name, is_admin = await _author_display(db, author)

    if author.user_type == UserType.ADMIN:
        advertisement = await db.get(Advertisement, asset.advertisement_id)
        if advertisement is not None:
            await notify_user(
                db,
                user_id=advertisement.brand_id,
                type_=NotificationType.ASSET_COMMENT,
                title="Admin left feedback on your ad media",
                body=comment.body[:200],
                link=f"/brand/ads/{advertisement.id}",
                data={"advertisement_id": str(advertisement.id), "asset_id": str(asset.id), "comment_id": str(comment.id)},
            )

    return comment, name, is_admin


async def get_like_status(db: AsyncSession, *, asset_id: uuid.UUID, user_id: uuid.UUID) -> tuple[bool, int]:
    liked = (
        await db.execute(select(AssetLike).where(AssetLike.asset_id == asset_id, AssetLike.user_id == user_id))
    ).scalar_one_or_none() is not None
    count = (
        await db.execute(select(func.count()).select_from(AssetLike).where(AssetLike.asset_id == asset_id))
    ).scalar_one()
    return liked, count


async def toggle_like(db: AsyncSession, *, asset_id: uuid.UUID, user_id: uuid.UUID) -> tuple[bool, int]:
    existing = (
        await db.execute(select(AssetLike).where(AssetLike.asset_id == asset_id, AssetLike.user_id == user_id))
    ).scalar_one_or_none()

    if existing is not None:
        await db.delete(existing)
    else:
        db.add(AssetLike(asset_id=asset_id, user_id=user_id))
    await db.commit()

    return await get_like_status(db, asset_id=asset_id, user_id=user_id)
