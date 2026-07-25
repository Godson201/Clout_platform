import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.advertisement_template import AdvertisementTemplate
from app.schemas.advertisement_template import AdvertisementTemplateRead

router = APIRouter(prefix="/templates", tags=["templates"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AdvertisementTemplateRead])
async def list_templates(db: AsyncSession = Depends(get_db)) -> list[AdvertisementTemplateRead]:
    result = await db.execute(
        select(AdvertisementTemplate).where(AdvertisementTemplate.is_active.is_(True)).order_by(AdvertisementTemplate.name)
    )
    templates = result.scalars().all()
    return [AdvertisementTemplateRead.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=AdvertisementTemplateRead)
async def get_template(template_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> AdvertisementTemplateRead:
    template = await db.get(AdvertisementTemplate, template_id)
    if template is None or not template.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return AdvertisementTemplateRead.model_validate(template)
