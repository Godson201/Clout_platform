from tests.test_admin_flow import _make_admin_token
from tests.test_advertisements import _brand_token


class TestAdminViewRates:
    async def test_admin_can_list_and_update_view_rates(self, client):
        admin_token = await _make_admin_token(email="rates-admin@clout-platform.com")

        list_resp = await client.get("/api/v1/admin/view-rates", headers={"Authorization": f"Bearer {admin_token}"})
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 4  # tiktok/instagram/facebook/youtube seeded

        update_resp = await client.put(
            "/api/v1/admin/view-rates",
            json={"platform": "tiktok", "rate_per_view": "9.5000", "currency": "RWF"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["rate_per_view"] == "9.5000"

    async def test_brand_cannot_manage_view_rates(self, client):
        token = await _brand_token(client, email="rates-brand@example.com")
        resp = await client.get("/api/v1/admin/view-rates", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


class TestAdminFeeConfig:
    async def test_admin_can_read_and_update_fee_config(self, client):
        admin_token = await _make_admin_token(email="fee-admin@clout-platform.com")

        get_resp = await client.get("/api/v1/admin/fee-config", headers={"Authorization": f"Bearer {admin_token}"})
        assert get_resp.status_code == 200
        assert get_resp.json()["brand_fee_pct"] == "0.1000"

        update_resp = await client.patch(
            "/api/v1/admin/fee-config",
            json={"brand_fee_pct": "0.1200"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["brand_fee_pct"] == "0.1200"
        assert update_resp.json()["influencer_fee_pct"] == "0.1000"  # untouched
