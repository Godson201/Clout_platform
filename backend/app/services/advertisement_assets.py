import os
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.models.advertisement import Advertisement
from app.models.advertisement_asset import AdvertisementAsset
from app.models.advertisement_rendition import AdvertisementRendition
from app.models.brand import Brand
from app.models.enums import AssetStatus, AssetType, NotificationType, SocialPlatform
from app.services.notifications import notify_all_influencers
from app.services.storage import allowed_extensions, generate_storage_key, get_storage_backend, read_with_limit

settings = get_settings()

# LOGO is brand housekeeping, not campaign creative — excluded so influencers
# aren't notified about a brand simply uploading its logo.
_NOTIFIABLE_ASSET_TYPES = {AssetType.VIDEO, AssetType.IMAGE, AssetType.AUDIO, AssetType.VOICEOVER}

_MAX_MB_BY_TYPE = {
    AssetType.VIDEO: settings.MAX_VIDEO_UPLOAD_MB,
    AssetType.IMAGE: settings.MAX_IMAGE_UPLOAD_MB,
    AssetType.LOGO: settings.MAX_IMAGE_UPLOAD_MB,
    AssetType.AUDIO: settings.MAX_AUDIO_UPLOAD_MB,
    AssetType.VOICEOVER: settings.MAX_AUDIO_UPLOAD_MB,
}

_EXPECTED_CONTENT_TYPE_PREFIX = {
    AssetType.VIDEO: "video/",
    AssetType.IMAGE: "image/",
    AssetType.LOGO: "image/",
    AssetType.AUDIO: "audio/",
    AssetType.VOICEOVER: "audio/",
}


def _validate_upload(asset_type: AssetType, file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_extensions(asset_type.value):
        allowed = ", ".join(sorted(allowed_extensions(asset_type.value)))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext or '(none)'}' for {asset_type.value}. Allowed: {allowed}",
        )

    expected_prefix = _EXPECTED_CONTENT_TYPE_PREFIX[asset_type]
    if file.content_type and not file.content_type.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content-Type '{file.content_type}' doesn't match expected {asset_type.value} upload",
        )
    return ext


async def store_advertisement_asset(
    db: AsyncSession, *, advertisement_id: uuid.UUID, asset_type: AssetType, file: UploadFile
) -> AdvertisementAsset:
    _validate_upload(asset_type, file)

    max_bytes = _MAX_MB_BY_TYPE[asset_type] * 1024 * 1024
    content = await read_with_limit(file, max_bytes)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    storage = get_storage_backend()
    storage_key = generate_storage_key(advertisement_id, asset_type.value, file.filename or "upload")
    storage.save(storage_key, content)

    asset = AdvertisementAsset(
        advertisement_id=advertisement_id,
        asset_type=asset_type,
        storage_key=storage_key,
        original_filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(content),
    )
    db.add(asset)
    await db.flush()

    if asset_type == AssetType.VIDEO:
        for platform in SocialPlatform:
            db.add(AdvertisementRendition(asset_id=asset.id, platform=platform))
        await db.flush()
    else:
        # Non-video assets need no transcode pipeline — they're playable as
        # uploaded, so they're "ready" the moment the bytes are stored.
        asset.status = AssetStatus.READY

    await db.commit()
    await db.refresh(asset)

    if asset_type == AssetType.VIDEO:
        # Imported lazily to avoid pulling Celery/the sync DB engine into every
        # module that imports this file (e.g. plain profile-CRUD tests).
        from app.tasks.video_processing_tasks import process_advertisement_asset

        # run_in_threadpool matters even (especially) in CELERY_TASK_ALWAYS_EAGER
        # dev mode: eager mode runs the *entire* ffmpeg pipeline synchronously
        # wherever `.delay()` is called, which would otherwise block this
        # request's event loop — and every other concurrent request — for the
        # duration of the transcode.
        await run_in_threadpool(process_advertisement_asset.delay, str(asset.id))
    elif asset_type in _NOTIFIABLE_ASSET_TYPES:
        await _notify_influencers_of_new_media(db, advertisement_id=advertisement_id, asset=asset)

    return asset


async def _notify_influencers_of_new_media(
    db: AsyncSession, *, advertisement_id: uuid.UUID, asset: AdvertisementAsset
) -> None:
    advertisement = await db.get(Advertisement, advertisement_id)
    brand = await db.get(Brand, advertisement.brand_id) if advertisement else None
    brand_name = brand.business_name if brand else "A brand"
    await notify_all_influencers(
        db,
        type_=NotificationType.NEW_BRAND_MEDIA,
        title=f"{brand_name} shared new {asset.asset_type.value} content",
        body=f'New {asset.asset_type.value} added to "{advertisement.title if advertisement else "an advertisement"}" '
        f"— see what {brand_name} is looking for.",
        link="/influencer/marketplace",
        data={
            "advertisement_id": str(advertisement_id),
            "asset_id": str(asset.id),
            "asset_type": asset.asset_type.value,
            "brand_name": brand_name,
        },
    )


def delete_advertisement_asset(asset: AdvertisementAsset) -> None:
    storage = get_storage_backend()
    storage.delete(asset.storage_key)
    for rendition in asset.renditions:
        if rendition.storage_key:
            storage.delete(rendition.storage_key)
