"""Shared test setup helpers for Phase 3 (campaigns/marketplace/slots), which all
need a brand with a *ready* advertisement and/or an influencer with a profile —
building that by hand in every test would bury the actual assertions.
"""

from tests.test_advertisements import _brand_token, _get_template_id
from tests.test_auth_flow import _register_influencer


async def register_brand_with_ready_ad(client, tiny_video_bytes: bytes, *, email: str, title: str = "Campaign ad") -> tuple[str, str]:
    """Returns (brand_access_token, advertisement_id) for an ad that has a
    processed (status=ready) video asset, i.e. one that's actually eligible to
    back a campaign.
    """
    token = await _brand_token(client, email=email)
    template_id = await _get_template_id(client, token)

    create_resp = await client.post(
        "/api/v1/advertisements",
        json={"template_id": template_id, "title": title},
        headers={"Authorization": f"Bearer {token}"},
    )
    ad_id = create_resp.json()["id"]

    upload_resp = await client.post(
        f"/api/v1/advertisements/{ad_id}/assets",
        data={"asset_type": "video"},
        files={"file": ("clip.mp4", tiny_video_bytes, "video/mp4")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_resp.json()["status"] == "ready", upload_resp.json()

    ready_resp = await client.patch(
        f"/api/v1/advertisements/{ad_id}",
        json={"status": "ready"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ready_resp.status_code == 200, ready_resp.json()

    return token, ad_id


async def fund_and_confirm_campaign(client, token: str, campaign_id: str, *, phone_number: str = "0788000001") -> dict:
    """Initiates MoMo funding (mock provider, PENDING) and immediately confirms
    it via the same webhook path a real MTN MoMo callback would hit, rather
    than calling the service layer directly — exercises the actual HTTP
    contract the same way the real provider integration will. Returns the
    campaign detail (with slots) once funding is confirmed.
    """
    fund_resp = await client.post(
        f"/api/v1/campaigns/{campaign_id}/fund",
        json={"phone_number": phone_number},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fund_resp.status_code == 200, fund_resp.json()
    provider_reference = fund_resp.json()["payment"]["provider_reference"]

    webhook_resp = await client.post(
        "/api/v1/webhooks/momo/collection", json={"referenceId": provider_reference, "status": "SUCCESSFUL"}
    )
    assert webhook_resp.status_code == 204, webhook_resp.text

    detail_resp = await client.get(f"/api/v1/campaigns/{campaign_id}", headers={"Authorization": f"Bearer {token}"})
    assert detail_resp.status_code == 200
    return detail_resp.json()


async def register_influencer_token(
    client, *, email: str, username: str, sector: str | None = None, location: str | None = None,
    follower_tier: str | None = None,
) -> str:
    resp = await _register_influencer(client, email=email, username=username)
    token = resp.json()["access_token"]

    profile_updates: dict = {}
    if sector is not None:
        profile_updates["sector"] = sector
    if location is not None:
        profile_updates["location"] = location
    if follower_tier is not None:
        profile_updates["follower_tier"] = follower_tier

    if profile_updates:
        patch_resp = await client.patch(
            "/api/v1/influencers/me", json=profile_updates, headers={"Authorization": f"Bearer {token}"}
        )
        assert patch_resp.status_code == 200, patch_resp.json()

    return token


async def connected_brand_and_influencer(
    client, tiny_video_bytes, *, brand_email: str, influencer_email: str, influencer_username: str
) -> tuple[str, str, str, str]:
    """Returns (brand_token, brand_id, influencer_token, influencer_id) for a
    pair that actually has a relationship — the influencer has claimed a slot on
    one of the brand's campaigns — satisfying the gate messaging/contracts/public
    profiles share (see app/services/relationships.py).
    """
    brand_token, ad_id = await register_brand_with_ready_ad(client, tiny_video_bytes, email=brand_email)
    create_resp = await client.post(
        "/api/v1/campaigns",
        json={
            "advertisement_id": ad_id,
            "platforms": ["tiktok"],
            "target_views": 10_000,
            "tier": "micro",
            "slot_count": 1,
        },
        headers={"Authorization": f"Bearer {brand_token}"},
    )
    campaign_id = create_resp.json()["id"]
    funded = await fund_and_confirm_campaign(client, brand_token, campaign_id)
    slot_id = funded["slots"][0]["id"]

    influencer_token = await register_influencer_token(client, email=influencer_email, username=influencer_username)
    claim_resp = await client.post(f"/api/v1/slots/{slot_id}/claim", headers={"Authorization": f"Bearer {influencer_token}"})
    assert claim_resp.status_code == 200, claim_resp.json()

    brand_me = await client.get("/api/v1/brands/me", headers={"Authorization": f"Bearer {brand_token}"})
    influencer_me = await client.get("/api/v1/influencers/me", headers={"Authorization": f"Bearer {influencer_token}"})

    return brand_token, brand_me.json()["id"], influencer_token, influencer_me.json()["id"]
