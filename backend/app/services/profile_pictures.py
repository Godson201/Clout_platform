import os
import uuid

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings
from app.services.storage import allowed_extensions, get_storage_backend, read_with_limit

settings = get_settings()

_ALLOWED_IMAGE_EXTENSIONS = allowed_extensions("image")


def _validate_image(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(sorted(_ALLOWED_IMAGE_EXTENSIONS))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext or '(none)'}' for a profile picture. Allowed: {allowed}",
        )
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content-Type '{file.content_type}' doesn't look like an image upload",
        )
    return ext


async def store_profile_picture(*, owner_kind: str, owner_id: uuid.UUID, file: UploadFile) -> str:
    """Saves a brand logo or influencer profile picture and returns the public URL.

    `owner_kind` is just a storage-key namespace ("brands" | "influencers") — kept
    generic rather than two near-identical functions since the validation, size
    limit, and storage call are otherwise identical.
    """
    ext = _validate_image(file)

    max_bytes = settings.MAX_IMAGE_UPLOAD_MB * 1024 * 1024
    content = await read_with_limit(file, max_bytes)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    storage = get_storage_backend()
    storage_key = f"profile-pictures/{owner_kind}/{owner_id}/{uuid.uuid4()}{ext}"
    storage.save(storage_key, content)

    return storage.url_for(storage_key)
