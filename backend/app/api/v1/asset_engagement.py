import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.asset_comment import AssetCommentRead, AssetLikeStatusRead, CreateAssetCommentRequest
from app.services.asset_engagement import add_comment, get_asset_with_access, get_like_status, list_comments, toggle_like

router = APIRouter(prefix="/assets", tags=["asset-engagement"])


@router.get("/{asset_id}/comments", response_model=list[AssetCommentRead])
async def list_asset_comments(
    asset_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[AssetCommentRead]:
    await get_asset_with_access(db, user=user, asset_id=asset_id)
    enriched = await list_comments(db, asset_id=asset_id)
    return [
        AssetCommentRead(
            id=c.id,
            asset_id=c.asset_id,
            author_user_id=c.author_user_id,
            author_name=name,
            author_is_admin=is_admin,
            body=c.body,
            created_at=c.created_at,
        )
        for c, name, is_admin in enriched
    ]


@router.post("/{asset_id}/comments", response_model=AssetCommentRead, status_code=201)
async def create_asset_comment(
    asset_id: uuid.UUID,
    payload: CreateAssetCommentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssetCommentRead:
    asset = await get_asset_with_access(db, user=user, asset_id=asset_id)
    comment, name, is_admin = await add_comment(db, asset=asset, author=user, body=payload.body)
    return AssetCommentRead(
        id=comment.id,
        asset_id=comment.asset_id,
        author_user_id=comment.author_user_id,
        author_name=name,
        author_is_admin=is_admin,
        body=comment.body,
        created_at=comment.created_at,
    )


@router.get("/{asset_id}/like", response_model=AssetLikeStatusRead)
async def get_asset_like_status(
    asset_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AssetLikeStatusRead:
    await get_asset_with_access(db, user=user, asset_id=asset_id)
    liked, count = await get_like_status(db, asset_id=asset_id, user_id=user.id)
    return AssetLikeStatusRead(liked=liked, like_count=count)


@router.post("/{asset_id}/like", response_model=AssetLikeStatusRead)
async def toggle_asset_like(
    asset_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AssetLikeStatusRead:
    await get_asset_with_access(db, user=user, asset_id=asset_id)
    liked, count = await toggle_like(db, asset_id=asset_id, user_id=user.id)
    return AssetLikeStatusRead(liked=liked, like_count=count)
