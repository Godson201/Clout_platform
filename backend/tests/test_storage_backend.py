import os
import sys
from types import SimpleNamespace

from app.services import storage


class _FakeS3Client:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_object(self, *, Bucket, Key, Body, **kwargs):
        self.objects[Key] = Body

    def get_object(self, *, Bucket, Key):
        return {"Body": SimpleNamespace(read=lambda: self.objects[Key])}

    def delete_object(self, *, Bucket, Key):
        self.objects.pop(Key, None)

    def download_file(self, bucket, key, path):
        if key not in self.objects:
            raise FileNotFoundError(key)
        with open(path, "wb") as file:
            file.write(self.objects[key])

    def upload_file(self, path, bucket, key, ExtraArgs=None):
        with open(path, "rb") as file:
            self.objects[key] = file.read()

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        return f"https://signed.example.com/{Params['Key']}?expires={ExpiresIn}"


def test_s3_backend_persists_uploads_and_worker_outputs(monkeypatch):
    client = _FakeS3Client()
    fake_boto3 = SimpleNamespace(client=lambda *args, **kwargs: client)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setattr(
        storage,
        "settings",
        SimpleNamespace(
            S3_BUCKET="clout-media",
            S3_ACCESS_KEY_ID="key",
            S3_SECRET_ACCESS_KEY="secret",
            S3_REGION="auto",
            S3_ENDPOINT_URL="https://example.r2.cloudflarestorage.com",
            MEDIA_URL_EXPIRE_SECONDS=3600,
        ),
    )
    backend = storage.S3StorageBackend()
    try:
        backend.save("social/source.mp4", b"original")
        assert backend.read("social/source.mp4") == b"original"
        assert backend.url_for("social/source.mp4") == "https://signed.example.com/social/source.mp4?expires=3600"

        output_path = backend.local_path("social/processed/output.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as file:
            file.write(b"transcoded")
        backend.commit_local("social/processed/output.mp4")
        assert client.objects["social/processed/output.mp4"] == b"transcoded"
    finally:
        backend.clear_cache()
