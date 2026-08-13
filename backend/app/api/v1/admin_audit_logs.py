from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_admin
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page

router = APIRouter(prefix="/admin/audit-logs", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("", response_model=Page[AuditLogRead])
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    action: str | None = None,
    entity_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> Page[AuditLogRead]:
    """Read-only oversight of every audited action across the platform — role
    changes, verification decisions, financial mutations, moderation calls —
    for an admin (any admin, not just super_admin) to review. AuditLog rows
    are immutable and never expose write access here.
    """
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
        count_stmt = count_stmt.where(AuditLog.entity_type == entity_type)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    logs = (await db.execute(stmt)).scalars().all()

    actor_ids = {log.actor_user_id for log in logs if log.actor_user_id is not None}
    actor_emails: dict = {}
    if actor_ids:
        actors = (await db.execute(select(User.id, User.email).where(User.id.in_(actor_ids)))).all()
        actor_emails = {row.id: row.email for row in actors}

    items = [
        AuditLogRead(
            id=log.id,
            actor_user_id=log.actor_user_id,
            actor_email=actor_emails.get(log.actor_user_id) if log.actor_user_id else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            before=log.before,
            after=log.after,
            created_at=log.created_at,
        )
        for log in logs
    ]

    return Page(items=items, total=total, page=page, page_size=page_size)
