import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_admin
from app.models.advertisement_template import AdvertisementTemplate
from app.models.user import User
from app.schemas.advertisement_template import (
    AdvertisementTemplateCreate,
    AdvertisementTemplateRead,
    AdvertisementTemplateUpdate,
)
from app.services.audit import write_audit_log

router = APIRouter(prefix="/admin/templates", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[AdvertisementTemplateRead])
async def list_all_templates(db: AsyncSession = Depends(get_db)) -> list[AdvertisementTemplateRead]:
    result = await db.execute(select(AdvertisementTemplate).order_by(AdvertisementTemplate.name))
    return [AdvertisementTemplateRead.model_validate(t) for t in result.scalars().all()]


@router.post("", response_model=AdvertisementTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: AdvertisementTemplateCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AdvertisementTemplateRead:
    template = AdvertisementTemplate(**payload.model_dump())
    db.add(template)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Template code already exists")

    await write_audit_log(
        db, actor_user_id=admin.id, action="admin.template.create", entity_type="advertisement_template",
        entity_id=template.id, after=AdvertisementTemplateRead.model_validate(template).model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(template)
    return AdvertisementTemplateRead.model_validate(template)


@router.patch("/{template_id}", response_model=AdvertisementTemplateRead)
async def update_template(
    template_id: uuid.UUID,
    payload: AdvertisementTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AdvertisementTemplateRead:
    template = await db.get(AdvertisementTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    before = AdvertisementTemplateRead.model_validate(template).model_dump(mode="json")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    await write_audit_log(
        db, actor_user_id=admin.id, action="admin.template.update", entity_type="advertisement_template",
        entity_id=template.id, before=before,
        after=AdvertisementTemplateRead.model_validate(template).model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(template)
    return AdvertisementTemplateRead.model_validate(template)
