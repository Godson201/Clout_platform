from tests.test_advertisements import _brand_token, _get_template_id


async def _create_ad(client, token: str, title: str = "Asset test ad") -> str:
    template_id = await _get_template_id(client, token)
    resp = await client.post(
        "/api/v1/advertisements",
        json={"template_id": template_id, "title": title},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


class TestAssetUploadValidation:
    async def test_rejects_unsupported_extension(self, client):
        token = await _brand_token(client, email="ext-reject@example.com")
        ad_id = await _create_ad(client, token)

        resp = await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "image"},
            files={"file": ("malware.exe", b"not an image", "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_rejects_content_type_mismatch(self, client):
        token = await _brand_token(client, email="mime-reject@example.com")
        ad_id = await _create_ad(client, token)

        resp = await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "image"},
            files={"file": ("photo.jpg", b"fake bytes", "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_rejects_oversized_file(self, client):
        token = await _brand_token(client, email="size-reject@example.com")
        ad_id = await _create_ad(client, token)

        oversized = b"0" * (11 * 1024 * 1024)  # over the 10MB image cap
        resp = await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "image"},
            files={"file": ("big.jpg", oversized, "image/jpeg")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 413

    async def test_upload_on_archived_advertisement_rejected(self, client):
        token = await _brand_token(client, email="archived-upload@example.com")
        ad_id = await _create_ad(client, token)
        await client.patch(
            f"/api/v1/advertisements/{ad_id}",
            json={"status": "archived"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "image"},
            files={"file": ("photo.jpg", b"fake bytes", "image/jpeg")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400


class TestVideoProcessingPipeline:
    async def test_real_video_upload_transcodes_all_platform_renditions(self, client, tiny_video_bytes):
        token = await _brand_token(client, email="video-pipeline@example.com")
        ad_id = await _create_ad(client, token)

        resp = await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "video"},
            files={"file": ("clip.mp4", tiny_video_bytes, "video/mp4")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        asset = resp.json()

        # CELERY_TASK_ALWAYS_EAGER=true means the transcode already ran
        # synchronously (via run_in_threadpool) by the time this response
        # came back — no polling needed in the test.
        assert asset["status"] == "ready"
        assert asset["duration_seconds"] is not None
        assert 1.0 < asset["duration_seconds"] < 3.0

        renditions = {r["platform"]: r for r in asset["renditions"]}
        assert set(renditions) == {"tiktok", "instagram", "facebook", "youtube"}
        for platform, rendition in renditions.items():
            assert rendition["status"] == "ready", f"{platform} rendition failed: {rendition['error_message']}"
            assert rendition["width"] == 1080
            assert rendition["height"] == 1920
            assert rendition["url"] is not None

        # Marking the ad ready should now succeed since a video asset is ready.
        ready_resp = await client.patch(
            f"/api/v1/advertisements/{ad_id}",
            json={"status": "ready"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert ready_resp.status_code == 200
        assert ready_resp.json()["status"] == "ready"

    async def test_delete_asset_removes_it_from_advertisement(self, client):
        token = await _brand_token(client, email="delete-asset@example.com")
        ad_id = await _create_ad(client, token)

        upload_resp = await client.post(
            f"/api/v1/advertisements/{ad_id}/assets",
            data={"asset_type": "image"},
            files={"file": ("logo.png", b"\x89PNG fake bytes", "image/png")},
            headers={"Authorization": f"Bearer {token}"},
        )
        asset_id = upload_resp.json()["id"]

        delete_resp = await client.delete(
            f"/api/v1/advertisements/{ad_id}/assets/{asset_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert delete_resp.status_code == 204

        detail_resp = await client.get(
            f"/api/v1/advertisements/{ad_id}", headers={"Authorization": f"Bearer {token}"}
        )
        assert detail_resp.json()["assets"] == []
