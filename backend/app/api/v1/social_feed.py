import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.enums import NativePostStatus, NotificationType
from app.models.social_feed import Follow, NativePost, NativePostComment, NativePostLike, NativePostMedia, NativePostSave
from app.models.user import User
from app.schemas.social_feed import CreateCommentRequest, CreatePostRequest, FollowStatusRead, SocialAuthor, SocialCommentRead, SocialMediaRead, SocialPostRead
from app.services.notifications import notify_user
from app.services.storage import get_storage_backend, read_with_limit
import os

router = APIRouter(prefix="/social", tags=["social"])


async def _author(db: AsyncSession, user: User) -> SocialAuthor:
    await db.refresh(user, attribute_names=["brand", "influencer"])
    if user.influencer:
        return SocialAuthor(id=user.id, name=user.influencer.display_name, username=user.influencer.username, picture_url=user.influencer.profile_picture_url)
    if user.brand:
        return SocialAuthor(id=user.id, name=user.brand.business_name, picture_url=user.brand.logo_url)
    return SocialAuthor(id=user.id, name=user.email)


async def _post_read(db: AsyncSession, post: NativePost, viewer_id: uuid.UUID) -> SocialPostRead:
    author = await db.get(User, post.author_id)
    likes = (await db.execute(select(func.count()).select_from(NativePostLike).where(NativePostLike.post_id == post.id))).scalar_one()
    comments = (await db.execute(select(func.count()).select_from(NativePostComment).where(NativePostComment.post_id == post.id))).scalar_one()
    liked = (await db.execute(select(NativePostLike).where(NativePostLike.post_id == post.id, NativePostLike.user_id == viewer_id))).scalar_one_or_none() is not None
    saved = (await db.execute(select(NativePostSave).where(NativePostSave.post_id == post.id, NativePostSave.user_id == viewer_id))).scalar_one_or_none() is not None
    media_rows = (await db.execute(select(NativePostMedia).where(NativePostMedia.post_id == post.id).order_by(NativePostMedia.created_at.asc()))).scalars().all()
    storage = get_storage_backend()
    return SocialPostRead(id=post.id, body=post.body, created_at=post.created_at, author=await _author(db, author), like_count=likes, comment_count=comments, liked_by_me=liked, saved_by_me=saved, media=[SocialMediaRead(id=m.id, media_type=m.media_type, mime_type=m.mime_type, url=storage.url_for(m.storage_key)) for m in media_rows])


@router.get("/feed", response_model=list[SocialPostRead])
async def feed(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50)):
    following = select(Follow.following_id).where(Follow.follower_id == user.id)
    result = await db.execute(select(NativePost).where(NativePost.status == NativePostStatus.PUBLISHED, NativePost.author_id.in_(following)).order_by(NativePost.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    return [await _post_read(db, post, user.id) for post in result.scalars()]


@router.post("/posts", response_model=SocialPostRead, status_code=status.HTTP_201_CREATED)
async def create_post(payload: CreatePostRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = NativePost(author_id=user.id, body=payload.body.strip())
    db.add(post); await db.commit(); await db.refresh(post)
    return await _post_read(db, post, user.id)


async def _post_or_404(db: AsyncSession, post_id: uuid.UUID) -> NativePost:
    post = await db.get(NativePost, post_id)
    if post is None or post.status != NativePostStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/posts/{post_id}/media", response_model=SocialMediaRead, status_code=status.HTTP_201_CREATED)
async def upload_post_media(post_id: uuid.UUID, file: UploadFile = File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = await _post_or_404(db, post_id)
    if post.author_id != user.id: raise HTTPException(status_code=404, detail="Post not found")
    content_type = file.content_type or ""
    media_type = next((kind for kind in ("image", "video", "audio") if content_type.startswith(f"{kind}/")), None)
    if media_type is None: raise HTTPException(status_code=400, detail="Only image, video, and audio uploads are supported")
    allowed = {"image": {".jpg", ".jpeg", ".png", ".webp"}, "video": {".mp4", ".mov", ".webm"}, "audio": {".mp3", ".wav", ".m4a", ".aac"}}[media_type]
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed: raise HTTPException(status_code=400, detail="Unsupported media file extension")
    limit = {"image": 10, "video": 200, "audio": 20}[media_type] * 1024 * 1024
    content = await read_with_limit(file, limit)
    key = f"social/{post.id}/{media_type}/{uuid.uuid4()}{ext}"
    storage = get_storage_backend(); storage.save(key, content)
    media = NativePostMedia(post_id=post.id, storage_key=key, mime_type=content_type, media_type=media_type)
    db.add(media); await db.commit(); await db.refresh(media)
    return SocialMediaRead(id=media.id, media_type=media.media_type, mime_type=media.mime_type, url=storage.url_for(media.storage_key))


@router.post("/posts/{post_id}/like", response_model=SocialPostRead)
async def toggle_like(post_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = await _post_or_404(db, post_id)
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
    post = await _post_or_404(db, post_id)
    saved = (await db.execute(select(NativePostSave).where(NativePostSave.post_id == post.id, NativePostSave.user_id == user.id))).scalar_one_or_none()
    if saved: await db.delete(saved)
    else: db.add(NativePostSave(post_id=post.id, user_id=user.id))
    await db.commit()
    return await _post_read(db, post, user.id)


@router.get("/posts/{post_id}/comments", response_model=list[SocialCommentRead])
async def list_post_comments(post_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await _post_or_404(db, post_id)
    result = await db.execute(select(NativePostComment).where(NativePostComment.post_id == post_id).order_by(NativePostComment.created_at.asc()))
    items = []
    for comment in result.scalars():
        author = await db.get(User, comment.author_id)
        items.append(SocialCommentRead(id=comment.id, body=comment.body, created_at=comment.created_at, author=await _author(db, author)))
    return items


@router.post("/posts/{post_id}/comments", response_model=SocialCommentRead, status_code=status.HTTP_201_CREATED)
async def add_post_comment(post_id: uuid.UUID, payload: CreateCommentRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    post = await _post_or_404(db, post_id)
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
