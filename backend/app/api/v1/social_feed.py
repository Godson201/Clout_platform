import uuid
import re

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.enums import NativePostStatus, NativePostVisibility, NotificationType, SocialAccountStatus, UserType
from app.models.social_feed import Follow, Hashtag, NativePost, NativePostComment, NativePostDistribution, NativePostHashtag, NativePostLike, NativePostMedia, NativePostReport, NativePostSave, UserBlock
from app.models.social_account import SocialAccount
from app.models.user import User
from app.schemas.social_feed import CreateCommentRequest, CreatePostRequest, CrossPostRead, CrossPostRequest, FollowStatusRead, ReportPostRequest, SocialAuthor, SocialCommentRead, SocialMediaRead, SocialPostRead, SocialProfileListRead, SocialProfileRead
from app.services.notifications import notify_user
from app.services.storage import get_storage_backend, read_with_limit, validate_media_signature
from app.services.malware_scanning import scan_upload
from app.core.crypto import decrypt_token
from app.core.platform_capabilities import get_capabilities
from app.services.social import get_adapter
from app.services.social_feed_ranking import ranked_posts_for_user
import os

router = APIRouter(prefix="/social", tags=["social"])


async def _author(db: AsyncSession, user: User) -> SocialAuthor:
    await db.refresh(user, attribute_names=["brand", "influencer"])
    if user.influencer:
        return SocialAuthor(id=user.id, name=user.influencer.display_name, username=user.influencer.username, picture_url=user.influencer.profile_picture_url)
    if user.brand:
        return SocialAuthor(id=user.id, name=user.brand.business_name, picture_url=user.brand.logo_url)
    return SocialAuthor(id=user.id, name=user.email)


async def _post_read(db: AsyncSession, post: NativePost, viewer_id: uuid.UUID | None) -> SocialPostRead:
    author = await db.get(User, post.author_id)
    likes = (await db.execute(select(func.count()).select_from(NativePostLike).where(NativePostLike.post_id == post.id))).scalar_one()
    comments = (await db.execute(select(func.count()).select_from(NativePostComment).where(NativePostComment.post_id == post.id))).scalar_one()
    liked = viewer_id is not None and (await db.execute(select(NativePostLike).where(NativePostLike.post_id == post.id, NativePostLike.user_id == viewer_id))).scalar_one_or_none() is not None
    saved = viewer_id is not None and (await db.execute(select(NativePostSave).where(NativePostSave.post_id == post.id, NativePostSave.user_id == viewer_id))).scalar_one_or_none() is not None
    media_rows = (await db.execute(select(NativePostMedia).where(NativePostMedia.post_id == post.id).order_by(NativePostMedia.created_at.asc()))).scalars().all()
    storage = get_storage_backend()
    tags = (await db.execute(select(Hashtag.name).join(NativePostHashtag).where(NativePostHashtag.post_id == post.id))).scalars().all()
    # A validated source video is safe to play immediately.  While FFmpeg is
    # preparing the platform rendition, expose that source with its processing
    # state instead of hiding the post's media until the worker completes.
    visible_media = [m for m in media_rows if m.processing_status != "failed"]
    return SocialPostRead(id=post.id, body=post.body, created_at=post.created_at, author=await _author(db, author), like_count=likes, comment_count=comments, liked_by_me=liked, saved_by_me=saved, media=[SocialMediaRead(id=m.id, media_type=m.media_type, mime_type=m.mime_type, url=storage.url_for(m.processed_storage_key or m.storage_key), processing_status=m.processing_status, thumbnail_url=storage.url_for(m.thumbnail_storage_key) if m.thumbnail_storage_key else None) for m in visible_media], hashtags=tags, repost_of_id=post.repost_of_id, visibility=post.visibility)


async def _can_view_post(db: AsyncSession, post: NativePost, viewer: User | None) -> bool:
    if post.visibility == NativePostVisibility.PUBLIC:
        return True
    if viewer is None:
        return False
    if post.author_id == viewer.id:
        return True
    if post.visibility == NativePostVisibility.BRANDS_ONLY:
        return viewer.user_type == UserType.BRAND
    if post.visibility == NativePostVisibility.FOLLOWERS:
        return (await db.execute(select(Follow).where(Follow.follower_id == viewer.id, Follow.following_id == post.author_id))).scalar_one_or_none() is not None
    return False


@router.get("/feed", response_model=list[SocialPostRead])
async def feed(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50)):
    following = select(Follow.following_id).where(Follow.follower_id == user.id)
    blocked = select(UserBlock.blocked_id).where(UserBlock.blocker_id == user.id)
    result = await db.execute(select(NativePost).where(NativePost.status == NativePostStatus.PUBLISHED, NativePost.author_id.in_(following), ~NativePost.author_id.in_(blocked)).order_by(NativePost.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    return [await _post_read(db, post, user.id) for post in result.scalars() if await _can_view_post(db, post, user)]


@router.get("/for-you", response_model=list[SocialPostRead])
async def for_you_feed(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), page_size: int = Query(20, ge=1, le=50)
) -> list[SocialPostRead]:
    posts = await ranked_posts_for_user(db, user=user, limit=page_size)
    return [await _post_read(db, post, user.id) for post in posts]


@router.get("/discover", response_model=list[SocialPostRead])
async def discover(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), page_size: int = Query(20, ge=1, le=50)):
    blocked = select(UserBlock.blocked_id).where(UserBlock.blocker_id == user.id)
    result = await db.execute(select(NativePost).where(NativePost.status == NativePostStatus.PUBLISHED, ~NativePost.author_id.in_(blocked)).order_by(NativePost.created_at.desc()).limit(page_size))
    return [await _post_read(db, post, user.id) for post in result.scalars() if await _can_view_post(db, post, user)]


@router.get("/trending", response_model=list[SocialPostRead])
async def trending(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), page_size: int = Query(20, ge=1, le=50)):
    result = await db.execute(select(NativePost).outerjoin(NativePostLike, NativePostLike.post_id == NativePost.id).where(NativePost.status == NativePostStatus.PUBLISHED).group_by(NativePost.id).order_by(func.count(NativePostLike.user_id).desc(), NativePost.created_at.desc()).limit(page_size))
    return [await _post_read(db, post, user.id) for post in result.scalars() if await _can_view_post(db, post, user)]


@router.get("/public/discover", response_model=list[SocialPostRead])
async def public_discover(db: AsyncSession = Depends(get_db), page_size: int = Query(20, ge=1, le=50)):
    """Unauthenticated, read-only discovery for public audiences."""
    posts = (await db.execute(select(NativePost).where(NativePost.status == NativePostStatus.PUBLISHED, NativePost.visibility == NativePostVisibility.PUBLIC).order_by(NativePost.created_at.desc()).limit(page_size))).scalars().all()
    return [await _post_read(db, post, None) for post in posts]


@router.get("/profiles/{target_id}", response_model=SocialProfileRead)
async def social_profile(target_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    target = await db.get(User, target_id)
    if target is None: raise HTTPException(status_code=404, detail="User not found")
    followers = (await db.execute(select(func.count()).select_from(Follow).where(Follow.following_id == target_id))).scalar_one()
    following = (await db.execute(select(func.count()).select_from(Follow).where(Follow.follower_id == target_id))).scalar_one()
    is_following = (await db.execute(select(Follow).where(Follow.follower_id == user.id, Follow.following_id == target_id))).scalar_one_or_none() is not None
    posts = (await db.execute(select(NativePost).where(NativePost.author_id == target_id, NativePost.status == NativePostStatus.PUBLISHED).order_by(NativePost.created_at.desc()).limit(50))).scalars().all()
    return SocialProfileRead(author=await _author(db, target), follower_count=followers, following_count=following, following_by_me=is_following, posts=[await _post_read(db, post, user.id) for post in posts if await _can_view_post(db, post, user)])


async def _profile_list(db: AsyncSession, ids: list[uuid.UUID]) -> list[SocialAuthor]:
    users = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
    lookup = {item.id: item for item in users}
    return [await _author(db, lookup[item]) for item in ids if item in lookup]


@router.get("/profiles/{target_id}/followers", response_model=SocialProfileListRead)
async def followers(target_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50)):
    stmt = select(Follow.follower_id).where(Follow.following_id == target_id).order_by(Follow.created_at.desc())
    ids = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    total = (await db.execute(select(func.count()).select_from(Follow).where(Follow.following_id == target_id))).scalar_one()
    return SocialProfileListRead(items=await _profile_list(db, ids), total=total)


@router.get("/profiles/{target_id}/following", response_model=SocialProfileListRead)
async def following_list(target_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50)):
    stmt = select(Follow.following_id).where(Follow.follower_id == target_id).order_by(Follow.created_at.desc())
    ids = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    total = (await db.execute(select(func.count()).select_from(Follow).where(Follow.follower_id == target_id))).scalar_one()
    return SocialProfileListRead(items=await _profile_list(db, ids), total=total)


@router.get("/search", response_model=list[SocialAuthor])
async def search_profiles(q: str = Query(min_length=2, max_length=64), sector: str | None = None, location: str | None = None, tier: str | None = None, platform: str | None = None, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import or_
    from app.models.influencer import Influencer
    from app.models.brand import Brand
    from app.models.social_account import SocialAccount
    stmt = select(User).outerjoin(Influencer, Influencer.id == User.id).outerjoin(Brand, Brand.id == User.id).where(or_(Influencer.username.ilike(f"%{q}%"), Influencer.display_name.ilike(f"%{q}%"), Brand.business_name.ilike(f"%{q}%")))
    if sector: stmt = stmt.where(Influencer.sector.ilike(f"%{sector}%"))
    if location: stmt = stmt.where(Influencer.location.ilike(f"%{location}%"))
    if tier: stmt = stmt.where(Influencer.follower_tier == tier)
    if platform: stmt = stmt.join(SocialAccount, SocialAccount.owner_user_id == User.id).where(SocialAccount.platform == platform)
    rows = await db.execute(stmt.limit(20))
    return [await _author(db, candidate) for candidate in rows.scalars()]


@router.post("/posts", response_model=SocialPostRead, status_code=status.HTTP_201_CREATED)
async def create_post(payload: CreatePostRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = NativePost(author_id=user.id, body=payload.body.strip(), visibility=payload.visibility)
    db.add(post); await db.flush()
    for name in set(tag.lower() for tag in re.findall(r"(?<!\w)#([\w]{1,80})", post.body)):
        tag = (await db.execute(select(Hashtag).where(Hashtag.name == name))).scalar_one_or_none()
        if tag is None: tag = Hashtag(name=name); db.add(tag); await db.flush()
        db.add(NativePostHashtag(post_id=post.id, hashtag_id=tag.id))
    await db.commit(); await db.refresh(post)
    return await _post_read(db, post, user.id)


@router.post("/posts/{post_id}/repost", response_model=SocialPostRead, status_code=status.HTTP_201_CREATED)
async def repost(post_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    original = await _post_or_404(db, post_id, viewer=user)
    existing = (await db.execute(select(NativePost).where(NativePost.author_id == user.id, NativePost.repost_of_id == original.id, NativePost.status == NativePostStatus.PUBLISHED))).scalar_one_or_none()
    if existing: return await _post_read(db, existing, user.id)
    post = NativePost(author_id=user.id, body=original.body, repost_of_id=original.id)
    db.add(post); await db.commit(); await db.refresh(post)
    return await _post_read(db, post, user.id)


@router.get("/hashtags/{name}", response_model=list[SocialPostRead])
async def hashtag_posts(name: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NativePost).join(NativePostHashtag).join(Hashtag).where(Hashtag.name == name.lower(), NativePost.status == NativePostStatus.PUBLISHED).order_by(NativePost.created_at.desc()).limit(50))
    return [await _post_read(db, post, user.id) for post in result.scalars()]


async def _post_or_404(db: AsyncSession, post_id: uuid.UUID, *, viewer: User | None = None) -> NativePost:
    post = await db.get(NativePost, post_id)
    if post is None or post.status != NativePostStatus.PUBLISHED or not await _can_view_post(db, post, viewer):
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/posts/{post_id}/report", status_code=status.HTTP_204_NO_CONTENT)
async def report_post(post_id: uuid.UUID, payload: ReportPostRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _post_or_404(db, post_id, viewer=user)
    existing = (await db.execute(select(NativePostReport).where(NativePostReport.post_id == post_id, NativePostReport.reporter_id == user.id))).scalar_one_or_none()
    if existing: raise HTTPException(status_code=409, detail="Post already reported")
    db.add(NativePostReport(post_id=post_id, reporter_id=user.id, reason=payload.reason, details=payload.details))
    await db.commit()


@router.post("/users/{target_id}/block", status_code=status.HTTP_204_NO_CONTENT)
async def block_user(target_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if target_id == user.id or await db.get(User, target_id) is None: raise HTTPException(status_code=404, detail="User not found")
    existing = (await db.execute(select(UserBlock).where(UserBlock.blocker_id == user.id, UserBlock.blocked_id == target_id))).scalar_one_or_none()
    if existing: return
    db.add(UserBlock(blocker_id=user.id, blocked_id=target_id)); await db.commit()


@router.post("/posts/{post_id}/media", response_model=SocialMediaRead, status_code=status.HTTP_201_CREATED)
async def upload_post_media(post_id: uuid.UUID, file: UploadFile = File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = await _post_or_404(db, post_id, viewer=user)
    if post.author_id != user.id: raise HTTPException(status_code=404, detail="Post not found")
    content_type = file.content_type or ""
    media_type = next((kind for kind in ("image", "video", "audio") if content_type.startswith(f"{kind}/")), None)
    if media_type is None: raise HTTPException(status_code=400, detail="Only image, video, and audio uploads are supported")
    allowed = {"image": {".jpg", ".jpeg", ".png", ".webp"}, "video": {".mp4", ".mov", ".webm"}, "audio": {".mp3", ".wav", ".m4a", ".aac"}}[media_type]
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed: raise HTTPException(status_code=400, detail="Unsupported media file extension")
    limit = {"image": 10, "video": 200, "audio": 20}[media_type] * 1024 * 1024
    content = await read_with_limit(file, limit)
    validate_media_signature(media_type=media_type, content=content)
    scan_upload(content)
    key = f"social/{post.id}/{media_type}/{uuid.uuid4()}{ext}"
    storage = get_storage_backend(); storage.save(key, content)
    media = NativePostMedia(post_id=post.id, storage_key=key, mime_type=content_type, media_type=media_type, processing_status="pending" if media_type == "video" else "ready")
    db.add(media); await db.commit(); await db.refresh(media)
    if media_type == "video":
        from app.tasks.video_processing_tasks import process_native_post_video
        process_native_post_video.delay(str(media.id))
    return SocialMediaRead(id=media.id, media_type=media.media_type, mime_type=media.mime_type, url=storage.url_for(media.storage_key), processing_status=media.processing_status)


@router.post("/posts/{post_id}/cross-post", response_model=list[CrossPostRead], status_code=status.HTTP_201_CREATED)
async def cross_post(post_id: uuid.UUID, payload: CrossPostRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Publish a post only to accounts the post owner explicitly selected."""
    post = await _post_or_404(db, post_id, viewer=user)
    if post.author_id != user.id:
        raise HTTPException(status_code=404, detail="Post not found")
    media = (await db.execute(select(NativePostMedia).where(NativePostMedia.post_id == post.id, NativePostMedia.media_type == "video", NativePostMedia.processing_status == "ready"))).scalars().first()
    if media is None:
        raise HTTPException(status_code=400, detail="Cross-posting currently requires one ready video")
    accounts = (await db.execute(select(SocialAccount).where(SocialAccount.id.in_(set(payload.social_account_ids)), SocialAccount.owner_user_id == user.id))).scalars().all()
    if len(accounts) != len(set(payload.social_account_ids)):
        raise HTTPException(status_code=422, detail="Select only your active connected accounts")
    storage = get_storage_backend(); deliveries = []
    for account in accounts:
        if account.status != SocialAccountStatus.ACTIVE:
            raise HTTPException(status_code=422, detail=f"Reconnect @{account.handle} before delivery")
        existing = (await db.execute(select(NativePostDistribution).where(NativePostDistribution.post_id == post.id, NativePostDistribution.social_account_id == account.id))).scalar_one_or_none()
        if existing is not None:
            deliveries.append(existing)
            continue
        delivery = NativePostDistribution(post_id=post.id, social_account_id=account.id, platform=account.platform)
        db.add(delivery); await db.flush()
        if not get_capabilities(account.platform).can_auto_publish:
            delivery.status = "failed"; delivery.error_message = "Automatic publishing is not enabled for this platform yet"
        else:
            try:
                result = await get_adapter(account.platform).publish_post(access_token=decrypt_token(account.access_token_encrypted), video_url=storage.url_for(media.processed_storage_key or media.storage_key), caption=post.body)
                delivery.status = "published"; delivery.external_post_id = result.external_post_id; delivery.post_url = result.post_url
            except Exception as exc:
                delivery.status = "failed"; delivery.error_message = str(exc)[:1000]
        deliveries.append(delivery)
    await db.commit()
    return [CrossPostRead(id=item.id, social_account_id=item.social_account_id, platform=item.platform, status=item.status, post_url=item.post_url, error_message=item.error_message) for item in deliveries]


@router.get("/posts/{post_id}/cross-posts", response_model=list[CrossPostRead])
async def list_cross_posts(post_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = await _post_or_404(db, post_id, viewer=user)
    if post.author_id != user.id:
        return []
    deliveries = (await db.execute(select(NativePostDistribution).where(NativePostDistribution.post_id == post.id).order_by(NativePostDistribution.created_at.desc()))).scalars().all()
    return [CrossPostRead(id=item.id, social_account_id=item.social_account_id, platform=item.platform, status=item.status, post_url=item.post_url, error_message=item.error_message) for item in deliveries]


@router.post("/posts/{post_id}/cross-posts/{distribution_id}/retry", response_model=CrossPostRead)
async def retry_cross_post(post_id: uuid.UUID, distribution_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = await _post_or_404(db, post_id, viewer=user)
    delivery = await db.get(NativePostDistribution, distribution_id)
    if post.author_id != user.id or delivery is None or delivery.post_id != post.id:
        raise HTTPException(status_code=404, detail="Cross-post delivery not found")
    if delivery.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed deliveries can be retried")
    account = await db.get(SocialAccount, delivery.social_account_id)
    media = (await db.execute(select(NativePostMedia).where(NativePostMedia.post_id == post.id, NativePostMedia.media_type == "video", NativePostMedia.processing_status == "ready"))).scalars().first()
    if account is None or account.owner_user_id != user.id or media is None:
        raise HTTPException(status_code=400, detail="Connected account or ready video is unavailable")
    try:
        if not get_capabilities(account.platform).can_auto_publish:
            raise RuntimeError("Automatic publishing is not enabled for this platform yet")
        result = await get_adapter(account.platform).publish_post(access_token=decrypt_token(account.access_token_encrypted), video_url=get_storage_backend().url_for(media.processed_storage_key or media.storage_key), caption=post.body)
        delivery.status = "published"; delivery.external_post_id = result.external_post_id; delivery.post_url = result.post_url; delivery.error_message = None
    except Exception as exc:
        delivery.error_message = str(exc)[:1000]
    await db.commit()
    return CrossPostRead(id=delivery.id, social_account_id=delivery.social_account_id, platform=delivery.platform, status=delivery.status, post_url=delivery.post_url, error_message=delivery.error_message)


@router.post("/posts/{post_id}/like", response_model=SocialPostRead)
async def toggle_like(post_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = await _post_or_404(db, post_id, viewer=user)
    like = (await db.execute(select(NativePostLike).where(NativePostLike.post_id == post.id, NativePostLike.user_id == user.id))).scalar_one_or_none()
    if like:
        await db.delete(like)
        await db.commit()
    else:
        db.add(NativePostLike(post_id=post.id, user_id=user.id))
        await db.commit()
        if post.author_id != user.id:
            await notify_user(db, user_id=post.author_id, type_=NotificationType.SOCIAL_LIKE, title="New like", body=f"{(await _author(db, user)).name} liked your post.", link="/social", data={"post_id": str(post.id)})
    return await _post_read(db, post, user.id)


@router.post("/posts/{post_id}/save", response_model=SocialPostRead)
async def toggle_save(post_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = await _post_or_404(db, post_id, viewer=user)
    saved = (await db.execute(select(NativePostSave).where(NativePostSave.post_id == post.id, NativePostSave.user_id == user.id))).scalar_one_or_none()
    if saved: await db.delete(saved)
    else: db.add(NativePostSave(post_id=post.id, user_id=user.id))
    await db.commit()
    return await _post_read(db, post, user.id)


@router.get("/posts/{post_id}/comments", response_model=list[SocialCommentRead])
async def list_post_comments(post_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _post_or_404(db, post_id, viewer=user)
    result = await db.execute(select(NativePostComment).where(NativePostComment.post_id == post_id).order_by(NativePostComment.created_at.asc()))
    items = []
    for comment in result.scalars():
        author = await db.get(User, comment.author_id)
        items.append(SocialCommentRead(id=comment.id, body=comment.body, created_at=comment.created_at, author=await _author(db, author)))
    return items


@router.post("/posts/{post_id}/comments", response_model=SocialCommentRead, status_code=status.HTTP_201_CREATED)
async def add_post_comment(post_id: uuid.UUID, payload: CreateCommentRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = await _post_or_404(db, post_id, viewer=user)
    comment = NativePostComment(post_id=post.id, author_id=user.id, body=payload.body.strip())
    db.add(comment); await db.commit(); await db.refresh(comment)
    if post.author_id != user.id:
        await notify_user(db, user_id=post.author_id, type_=NotificationType.SOCIAL_COMMENT, title="New comment", body=f"{(await _author(db, user)).name} commented on your post.", link="/social", data={"post_id": str(post.id)})
    return SocialCommentRead(id=comment.id, body=comment.body, created_at=comment.created_at, author=await _author(db, user))


@router.post("/users/{target_id}/follow", response_model=FollowStatusRead)
async def toggle_follow(target_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if target_id == user.id or await db.get(User, target_id) is None: raise HTTPException(404, "User not found")
    relation = (await db.execute(select(Follow).where(Follow.follower_id == user.id, Follow.following_id == target_id))).scalar_one_or_none()
    if relation: await db.delete(relation); following = False
    else:
        db.add(Follow(follower_id=user.id, following_id=target_id)); following = True
        await notify_user(db, user_id=target_id, type_=NotificationType.SOCIAL_FOLLOW, title="New follower", body=f"{(await _author(db, user)).name} started following you.", link=None, data={"user_id": str(user.id)})
    await db.commit()
    followers = (await db.execute(select(func.count()).select_from(Follow).where(Follow.following_id == target_id))).scalar_one()
    following_count = (await db.execute(select(func.count()).select_from(Follow).where(Follow.follower_id == target_id))).scalar_one()
    return FollowStatusRead(following=following, follower_count=followers, following_count=following_count)
