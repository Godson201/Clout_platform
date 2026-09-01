from tests.factories import fund_and_confirm_campaign, register_brand_with_ready_ad, register_influencer_token
from tests.test_admin_flow import _make_admin_token
from tests.test_campaigns import _create_draft_campaign


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_public_post(client, token: str, body: str) -> dict:
    response = await client.post("/api/v1/social/posts", json={"body": body, "visibility": "public"}, headers=_headers(token))
    assert response.status_code == 201, response.json()
    return response.json()


class TestCampaignCreativePublishing:
    async def test_saved_creative_publishes_once_to_public_clout_feed(self, client, tiny_video_bytes):
        brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email="creative-publish-brand@example.com")
        campaign = await _create_draft_campaign(client, brand_token, ad_id, platforms=["tiktok"], slot_count=1)
        funded = await fund_and_confirm_campaign(client, brand_token, campaign.json()["id"])
        slot_id = funded["slots"][0]["id"]
        influencer_token = await register_influencer_token(client, email="creative-publish-inf@example.com", username="creativepublish")
        claim = await client.post(f"/api/v1/slots/{slot_id}/claim", headers=_headers(influencer_token))
        assert claim.status_code == 200, claim.json()

        saved = await client.post(
            f"/api/v1/slots/{slot_id}/creative",
            files={"file": ("finished.mp4", tiny_video_bytes, "video/mp4")},
            headers=_headers(influencer_token),
        )
        assert saved.status_code == 201, saved.json()
        assert 0 < saved.json()["duration_seconds"] <= 30

        published = await client.post(
            f"/api/v1/slots/{slot_id}/creative/publish",
            json={"caption": "My finished campaign ad #launch"},
            headers=_headers(influencer_token),
        )
        assert published.status_code == 201, published.json()
        post_id = published.json()["native_post_id"]
        duplicate = await client.post(
            f"/api/v1/slots/{slot_id}/creative/publish",
            json={"caption": "A changed caption must not duplicate the post"},
            headers=_headers(influencer_token),
        )
        assert duplicate.status_code == 201
        assert duplicate.json()["native_post_id"] == post_id

        public = await client.get("/api/v1/social/public/discover")
        assert public.status_code == 200
        post = next(item for item in public.json() if item["id"] == post_id)
        assert post["body"] == "My finished campaign ad #launch"
        assert post["media"][0]["media_type"] == "video"


class TestNativeSocialSafetyAndRanking:
    async def test_for_you_rewards_followed_creator_and_block_hides_creator(self, client):
        followed_token = await register_influencer_token(client, email="followed-feed@example.com", username="followedfeed")
        other_token = await register_influencer_token(client, email="other-feed@example.com", username="otherfeed")
        viewer_token = await register_influencer_token(client, email="viewer-feed@example.com", username="viewerfeed")
        followed_post = await _create_public_post(client, followed_token, "Followed creator #beauty")
        await _create_public_post(client, other_token, "Other creator #travel")

        followed_me = await client.get("/api/v1/users/me", headers=_headers(followed_token))
        assert followed_me.status_code == 200
        follow = await client.post(f"/api/v1/social/users/{followed_me.json()['id']}/follow", headers=_headers(viewer_token))
        assert follow.status_code == 200

        ranked = await client.get("/api/v1/social/for-you", headers=_headers(viewer_token))
        assert ranked.status_code == 200
        assert ranked.json()[0]["id"] == followed_post["id"]
        tags = await client.get("/api/v1/social/hashtags/beauty", headers=_headers(viewer_token))
        assert [post["id"] for post in tags.json()] == [followed_post["id"]]

        blocked = await client.post(f"/api/v1/social/users/{followed_me.json()['id']}/block", headers=_headers(viewer_token))
        assert blocked.status_code == 204
        after_block = await client.get("/api/v1/social/for-you", headers=_headers(viewer_token))
        assert followed_post["id"] not in [post["id"] for post in after_block.json()]

    async def test_admin_can_archive_and_restore_reported_post(self, client):
        author_token = await register_influencer_token(client, email="moderated-author@example.com", username="moderatedauthor")
        reporter_token = await register_influencer_token(client, email="moderated-reporter@example.com", username="moderatedreporter")
        post = await _create_public_post(client, author_token, "Reported content")
        report = await client.post(
            f"/api/v1/social/posts/{post['id']}/report",
            json={"reason": "spam", "details": "Repeated unsolicited promotion"},
            headers=_headers(reporter_token),
        )
        assert report.status_code == 204

        admin_token = await _make_admin_token(email="social-moderator@example.com")
        queue = await client.get("/api/v1/admin/social-moderation/reports", headers=_headers(admin_token))
        assert queue.status_code == 200
        report_id = next(item["report_id"] for item in queue.json() if item["post_id"] == post["id"])
        resolved = await client.post(
            f"/api/v1/admin/social-moderation/reports/{report_id}/resolve",
            json={"archive_post": True, "note": "Archived after spam review"},
            headers=_headers(admin_token),
        )
        assert resolved.status_code == 204

        archived = await client.get("/api/v1/admin/social-moderation/posts/archived", headers=_headers(admin_token))
        assert post["id"] in [item["post_id"] for item in archived.json()]
        public = await client.get("/api/v1/social/public/discover")
        assert post["id"] not in [item["id"] for item in public.json()]

        restored = await client.post(f"/api/v1/admin/social-moderation/posts/{post['id']}/restore", headers=_headers(admin_token))
        assert restored.status_code == 204
        public_after_restore = await client.get("/api/v1/social/public/discover")
        assert post["id"] in [item["id"] for item in public_after_restore.json()]
