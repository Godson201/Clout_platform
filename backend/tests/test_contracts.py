from tests.factories import connected_brand_and_influencer, register_brand_with_ready_ad, register_influencer_token
from tests.test_admin_flow import _make_admin_token


class TestContracts:
    async def test_unconnected_pair_cannot_propose_contract(self, client, tiny_video_bytes):
        brand_token, _ = await register_brand_with_ready_ad(client, tiny_video_bytes, email="nc-brand@example.com")
        inf_token = await register_influencer_token(client, email="nc-inf@example.com", username="ncinf")
        inf_me = await client.get("/api/v1/influencers/me", headers={"Authorization": f"Bearer {inf_token}"})

        resp = await client.post(
            "/api/v1/contracts",
            json={"counterpart_id": inf_me.json()["id"], "title": "Deal", "terms_text": "Some terms here for the deal."},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert resp.status_code == 403

    async def test_propose_and_accept_flow(self, client, tiny_video_bytes):
        brand_token, brand_id, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="contract-brand@example.com", influencer_email="contract-inf@example.com", influencer_username="contractinf",
        )

        propose_resp = await client.post(
            "/api/v1/contracts",
            json={"counterpart_id": inf_id, "title": "Campaign collab", "terms_text": "3 posts over 2 weeks, paid on delivery."},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert propose_resp.status_code == 200
        contract = propose_resp.json()
        assert contract["status"] == "proposed"
        assert contract["brand_id"] == brand_id
        assert contract["influencer_id"] == inf_id

        # The proposer can't accept their own proposal.
        self_accept = await client.post(
            f"/api/v1/contracts/{contract['id']}/accept", headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert self_accept.status_code == 400

        accept_resp = await client.post(
            f"/api/v1/contracts/{contract['id']}/accept", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert accept_resp.status_code == 200
        assert accept_resp.json()["status"] == "accepted"
        assert accept_resp.json()["responded_by_user_id"] == inf_id

        # Already resolved — can't respond again.
        second_response = await client.post(
            f"/api/v1/contracts/{contract['id']}/decline", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert second_response.status_code == 400

    async def test_decline_flow(self, client, tiny_video_bytes):
        brand_token, _, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="decline-brand@example.com", influencer_email="decline-inf@example.com", influencer_username="declineinf",
        )
        propose_resp = await client.post(
            "/api/v1/contracts",
            json={"counterpart_id": inf_id, "title": "Campaign collab", "terms_text": "Terms that will be declined."},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        contract_id = propose_resp.json()["id"]

        decline_resp = await client.post(
            f"/api/v1/contracts/{contract_id}/decline", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert decline_resp.status_code == 200
        assert decline_resp.json()["status"] == "declined"

    async def test_proposer_can_cancel_while_pending(self, client, tiny_video_bytes):
        brand_token, _, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="cancel-brand@example.com", influencer_email="cancel-inf@example.com", influencer_username="cancelinf",
        )
        propose_resp = await client.post(
            "/api/v1/contracts",
            json={"counterpart_id": inf_id, "title": "Campaign collab", "terms_text": "Terms that will be cancelled."},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        contract_id = propose_resp.json()["id"]

        # The counterpart can't cancel — only the proposer can.
        counterpart_cancel = await client.post(
            f"/api/v1/contracts/{contract_id}/cancel", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert counterpart_cancel.status_code == 403

        cancel_resp = await client.post(
            f"/api/v1/contracts/{contract_id}/cancel", headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

    async def test_stranger_cannot_view_or_respond(self, client, tiny_video_bytes):
        brand_token, _, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="strangerc-brand@example.com", influencer_email="strangerc-inf@example.com", influencer_username="strangercinf",
        )
        propose_resp = await client.post(
            "/api/v1/contracts",
            json={"counterpart_id": inf_id, "title": "Campaign collab", "terms_text": "Private terms not for strangers."},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        contract_id = propose_resp.json()["id"]

        stranger_token, _ = await register_brand_with_ready_ad(client, tiny_video_bytes, email="strangerc2@example.com")
        resp = await client.get(f"/api/v1/contracts/{contract_id}", headers={"Authorization": f"Bearer {stranger_token}"})
        assert resp.status_code == 403

    async def test_list_contracts_for_each_party(self, client, tiny_video_bytes):
        brand_token, _, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="list-brand@example.com", influencer_email="list-inf@example.com", influencer_username="listinf",
        )
        await client.post(
            "/api/v1/contracts",
            json={"counterpart_id": inf_id, "title": "Deal one", "terms_text": "First set of contract terms here."},
            headers={"Authorization": f"Bearer {brand_token}"},
        )

        brand_list = await client.get("/api/v1/contracts", headers={"Authorization": f"Bearer {brand_token}"})
        inf_list = await client.get("/api/v1/contracts", headers={"Authorization": f"Bearer {inf_token}"})
        assert len(brand_list.json()) == 1
        assert len(inf_list.json()) == 1
        assert brand_list.json()[0]["id"] == inf_list.json()[0]["id"]


class TestAdminContractOversight:
    async def test_admin_can_view_all_contracts_read_only(self, client, tiny_video_bytes):
        brand_token, _, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="admin-oversight-brand@example.com", influencer_email="admin-oversight-inf@example.com",
            influencer_username="adminoversightinf",
        )
        propose_resp = await client.post(
            "/api/v1/contracts",
            json={"counterpart_id": inf_id, "title": "Oversight deal", "terms_text": "Terms visible to admin only."},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        contract_id = propose_resp.json()["id"]

        admin_token = await _make_admin_token(email="contract-oversight-admin@clout.local")
        resp = await client.get("/api/v1/admin/contracts", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        contract = next(c for c in resp.json() if c["id"] == contract_id)
        assert contract["title"] == "Oversight deal"
        assert contract["brand_name"]
        assert contract["influencer_username"] == "adminoversightinf"

    async def test_non_admin_cannot_view_admin_contracts_list(self, client, tiny_video_bytes):
        brand_token, _ = await register_brand_with_ready_ad(client, tiny_video_bytes, email="not-admin-c@example.com")
        resp = await client.get("/api/v1/admin/contracts", headers={"Authorization": f"Bearer {brand_token}"})
        assert resp.status_code == 403
