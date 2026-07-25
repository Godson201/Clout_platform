import os
import uuid
from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings

settings = get_settings()


class StorageBackend(ABC):
    """Every call site (upload handlers, FFmpeg service) talks to this interface only.
    Swapping `LocalStorageBackend` for an S3/MinIO-backed implementation later is a
    one-class change, not a rewrite — same contract the payments module uses for
    MoMo-vs-future-providers.
    """

    @abstractmethod
    def save(self, key: str, content: bytes) -> None: ...

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def local_path(self, key: str) -> str:
        """Absolute filesystem path FFmpeg can read/write. Only meaningful for
        backends that are actually local; an S3 backend would instead need to
        download to a temp path before invoking ffmpeg and upload the result after.
        """
        ...

    @abstractmethod
    def url_for(self, key: str) -> str: ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, media_root: str):
        self.media_root = os.path.abspath(media_root)

    def _resolve(self, key: str) -> str:
        # `key` is always server-generated (see generate_storage_key) — never
        # built from client input — so this is a defense-in-depth check, not the
        # primary guard against path traversal.
        full_path = os.path.abspath(os.path.join(self.media_root, key))
        if not full_path.startswith(self.media_root + os.sep):
            raise ValueError("Invalid storage key")
        return full_path

    def save(self, key: str, content: bytes) -> None:
        full_path = self._resolve(key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(content)

    def read(self, key: str) -> bytes:
        with open(self._resolve(key), "rb") as f:
            return f.read()

    def delete(self, key: str) -> None:
        full_path = self._resolve(key)
        if os.path.exists(full_path):
            os.remove(full_path)

    def local_path(self, key: str) -> str:
        return self._resolve(key)

    def url_for(self, key: str) -> str:
        return f"/media/{key}"


@lru_cache
def get_storage_backend() -> StorageBackend:
    return LocalStorageBackend(settings.MEDIA_ROOT)


_ASSET_TYPE_EXTENSIONS = {
    "video": {".mp4", ".mov", ".webm", ".mkv"},
    "image": {".jpg", ".jpeg", ".png", ".webp"},
    "logo": {".jpg", ".jpeg", ".png", ".webp", ".svg"},
    "audio": {".mp3", ".wav", ".m4a", ".aac"},
    "voiceover": {".mp3", ".wav", ".m4a", ".aac"},
}


def allowed_extensions(asset_type: str) -> set[str]:
    return _ASSET_TYPE_EXTENSIONS.get(asset_type, set())


def generate_storage_key(advertisement_id: uuid.UUID, asset_type: str, original_filename: str) -> str:
    ext = os.path.splitext(original_filename)[1].lower()
    return f"advertisements/{advertisement_id}/{asset_type}/{uuid.uuid4()}{ext}"


def generate_rendition_key(asset_id: uuid.UUID, platform: str) -> str:
    return f"renditions/{asset_id}/{platform}.mp4"
