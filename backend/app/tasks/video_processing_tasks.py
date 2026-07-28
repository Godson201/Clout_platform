import logging
import os
import uuid

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.db_sync import SyncSessionLocal
from app.core.platform_specs import PLATFORM_VIDEO_SPECS
from app.models.advertisement_asset import AdvertisementAsset
from app.models.advertisement_rendition import AdvertisementRendition
from app.models.enums import AssetStatus, RenditionStatus
from app.services.storage import generate_rendition_key, get_storage_backend
from app.services.video_processing import VideoProcessingError, probe_video, transcode_for_platform

logger = logging.getLogger("clout.tasks")


@celery_app.task(name="process_advertisement_asset")
def process_advertisement_asset(asset_id: str) -> None:
    """Probes the uploaded source video, then transcodes one rendition per
    platform row already created (status=PENDING) for this asset. Every
    partial failure is recorded on its own rendition rather than aborting the
    whole batch — one bad platform spec shouldn't block the others.
    """
    storage = get_storage_backend()

    with SyncSessionLocal() as db:
        asset = db.get(AdvertisementAsset, uuid.UUID(asset_id))
        if asset is None:
            logger.error("process_advertisement_asset: asset %s not found", asset_id)
            return

        try:
            probe = probe_video(storage.local_path(asset.storage_key))
        except VideoProcessingError as exc:
            asset.status = AssetStatus.FAILED
            asset.error_message = str(exc)
            db.commit()
            return

        asset.duration_seconds = probe.duration_seconds
        asset.width = probe.width
        asset.height = probe.height
        asset.status = AssetStatus.PROCESSING
        db.commit()

        renditions = (
            db.execute(select(AdvertisementRendition).where(AdvertisementRendition.asset_id == asset.id))
            .scalars()
            .all()
        )

        any_ready = False
        for rendition in renditions:
            spec = PLATFORM_VIDEO_SPECS[rendition.platform]
            output_key = generate_rendition_key(asset.id, rendition.platform.value)
            output_path = storage.local_path(output_key)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            try:
                result = transcode_for_platform(storage.local_path(asset.storage_key), output_path, spec)
                rendition.storage_key = output_key
                rendition.width = result.width
                rendition.height = result.height
                rendition.duration_seconds = result.duration_seconds
                rendition.status = RenditionStatus.READY
                any_ready = True
            except VideoProcessingError as exc:
                rendition.status = RenditionStatus.FAILED
                rendition.error_message = str(exc)
                logger.error("Rendition failed for asset %s / %s: %s", asset_id, rendition.platform, exc)

            db.commit()

        asset.status = AssetStatus.READY if any_ready else AssetStatus.FAILED
        db.commit()
