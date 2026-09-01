import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.core.deps import require_admin
from app.models.enums import NativePostStatus
from app.models.social_feed import NativePost, NativePostReport
from app.models.user import User
from app.schemas.social_moderation import ArchivedSocialPost, ModerationDecision, SocialReportQueueItem
from app.services.audit import write_audit_log

router = APIRouter(prefix="/admin/social-moderation", tags=["admin"], dependencies=[Depends(require_admin)])

@router.get("/reports", response_model=list[SocialReportQueueItem])
async def reports(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(NativePostReport, NativePost).join(NativePost).where(NativePostReport.resolved.is_(False)).order_by(NativePostReport.created_at.asc()))).all()
    return [SocialReportQueueItem(report_id=r.id, post_id=p.id, author_id=p.author_id, body=p.body, reason=r.reason, details=r.details, created_at=r.created_at) for r, p in rows]


@router.get("/posts/archived", response_model=list[ArchivedSocialPost])
async def archived_posts(db: AsyncSession = Depends(get_db)):
    posts = (await db.execute(select(NativePost).where(NativePost.status == NativePostStatus.ARCHIVED).order_by(NativePost.updated_at.desc()))).scalars().all()
    return [ArchivedSocialPost(post_id=post.id, author_id=post.author_id, body=post.body, updated_at=post.updated_at) for post in posts]

@router.post("/reports/{report_id}/resolve", status_code=204)
async def resolve(report_id: uuid.UUID, payload: ModerationDecision, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    report = await db.get(NativePostReport, report_id)
    if report is None: raise HTTPException(404, "Report not found")
    post = await db.get(NativePost, report.post_id)
    before = {"resolved": report.resolved, "status": post.status.value if post else None}
    report.resolved = True
    if payload.archive_post and post: post.status = NativePostStatus.ARCHIVED
    await write_audit_log(db, actor_user_id=admin.id, action="admin.social_report.resolve", entity_type="native_post_report", entity_id=report.id, before=before, after={"resolved": True, "archived": payload.archive_post, "note": payload.note})
    await db.commit()

@router.post("/posts/{post_id}/restore", status_code=204)
async def restore(post_id: uuid.UUID, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    post = await db.get(NativePost, post_id)
    if post is None: raise HTTPException(404, "Post not found")
    post.status = NativePostStatus.PUBLISHED
    await write_audit_log(db, actor_user_id=admin.id, action="admin.social_post.restore", entity_type="native_post", entity_id=post.id, after={"status": "published"})
    await db.commit()
