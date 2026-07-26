from tests.factories import connected_brand_and_influencer, register_brand_with_ready_ad, register_influencer_token


class TestMessaging:
    async def test_unconnected_pair_cannot_start_conversation(self, client, tiny_video_bytes):
        brand_token, _ = await register_brand_with_ready_ad(client, tiny_video_bytes, email="lonely-brand@example.com")
        inf_token = await register_influencer_token(client, email="lonely-inf@example.com", username="lonelyinf")

        inf_me = await client.get("/api/v1/influencers/me", headers={"Authorization": f"Bearer {inf_token}"})
        resp = await client.post(
            "/api/v1/conversations",
            json={"counterpart_id": inf_me.json()["id"]},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert resp.status_code == 403

    async def test_connected_pair_can_start_conversation_and_exchange_text(self, client, tiny_video_bytes):
        brand_token, brand_id, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="chat-brand@example.com", influencer_email="chat-inf@example.com", influencer_username="chatinf",
        )

        start_resp = await client.post(
            "/api/v1/conversations", json={"counterpart_id": inf_id}, headers={"Authorization": f"Bearer {brand_token}"}
        )
        assert start_resp.status_code == 200
        conversation_id = start_resp.json()["id"]
        assert start_resp.json()["counterpart"]["user_id"] == inf_id

        # Starting from the influencer's side with the brand's id resolves to the same conversation.
        start_resp_2 = await client.post(
            "/api/v1/conversations", json={"counterpart_id": brand_id}, headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert start_resp_2.json()["id"] == conversation_id

        send_resp = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"text": "Hi! Excited to work together."},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert send_resp.status_code == 200
        assert send_resp.json()["message_type"] == "text"
        assert send_resp.json()["is_mine"] is True

        reply_resp = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"text": "Likewise!"},
            headers={"Authorization": f"Bearer {inf_token}"},
        )
        assert reply_resp.status_code == 200

        messages_resp = await client.get(
            f"/api/v1/conversations/{conversation_id}/messages", headers={"Authorization": f"Bearer {brand_token}"}
        )
        bodies = [m["text_body"] for m in messages_resp.json()]
        assert bodies == ["Hi! Excited to work together.", "Likewise!"]
        # From the brand's perspective, only their own message is "mine".
        mine_flags = [m["is_mine"] for m in messages_resp.json()]
        assert mine_flags == [True, False]

    async def test_empty_text_rejected(self, client, tiny_video_bytes):
        brand_token, _, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="empty-brand@example.com", influencer_email="empty-inf@example.com", influencer_username="emptyinf",
        )
        start_resp = await client.post(
            "/api/v1/conversations", json={"counterpart_id": inf_id}, headers={"Authorization": f"Bearer {brand_token}"}
        )
        conversation_id = start_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"text": "   "},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert resp.status_code == 400

    async def test_stranger_cannot_read_or_post_to_conversation(self, client, tiny_video_bytes):
        brand_token, _, _, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="private-brand@example.com", influencer_email="private-inf@example.com", influencer_username="privinf",
        )
        start_resp = await client.post(
            "/api/v1/conversations", json={"counterpart_id": inf_id}, headers={"Authorization": f"Bearer {brand_token}"}
        )
        conversation_id = start_resp.json()["id"]

        stranger_token, _ = await register_brand_with_ready_ad(client, tiny_video_bytes, email="stranger@example.com")

        read_resp = await client.get(
            f"/api/v1/conversations/{conversation_id}/messages", headers={"Authorization": f"Bearer {stranger_token}"}
        )
        assert read_resp.status_code == 403

        post_resp = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"text": "sneaking in"},
            headers={"Authorization": f"Bearer {stranger_token}"},
        )
        assert post_resp.status_code == 403

    async def test_unread_count_and_mark_read(self, client, tiny_video_bytes):
        brand_token, brand_id, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="unread-brand@example.com", influencer_email="unread-inf@example.com", influencer_username="unreadinf",
        )
        start_resp = await client.post(
            "/api/v1/conversations", json={"counterpart_id": inf_id}, headers={"Authorization": f"Bearer {brand_token}"}
        )
        conversation_id = start_resp.json()["id"]

        await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"text": "one"},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        await client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"text": "two"},
            headers={"Authorization": f"Bearer {brand_token}"},
        )

        list_resp = await client.get("/api/v1/conversations", headers={"Authorization": f"Bearer {inf_token}"})
        convo = next(c for c in list_resp.json() if c["id"] == conversation_id)
        assert convo["unread_count"] == 2
        assert convo["last_message"]["text_body"] == "two"

        mark_resp = await client.post(
            f"/api/v1/conversations/{conversation_id}/read", headers={"Authorization": f"Bearer {inf_token}"}
        )
        assert mark_resp.status_code == 204

        list_resp_2 = await client.get("/api/v1/conversations", headers={"Authorization": f"Bearer {inf_token}"})
        convo_2 = next(c for c in list_resp_2.json() if c["id"] == conversation_id)
        assert convo_2["unread_count"] == 0

    async def test_send_voice_note_attachment(self, client, tiny_video_bytes):
        brand_token, _, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="voice-brand@example.com", influencer_email="voice-inf@example.com", influencer_username="voiceinf",
        )
        start_resp = await client.post(
            "/api/v1/conversations", json={"counterpart_id": inf_id}, headers={"Authorization": f"Bearer {brand_token}"}
        )
        conversation_id = start_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages/attachment",
            data={"message_type": "voice_note"},
            files={"file": ("note.mp3", b"fake-audio-bytes", "audio/mpeg")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["message_type"] == "voice_note"
        assert body["attachment_url"] is not None
        assert body["attachment_original_filename"] == "note.mp3"

    async def test_send_document_attachment_with_caption(self, client, tiny_video_bytes):
        brand_token, _, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="doc-brand@example.com", influencer_email="doc-inf@example.com", influencer_username="docinf",
        )
        start_resp = await client.post(
            "/api/v1/conversations", json={"counterpart_id": inf_id}, headers={"Authorization": f"Bearer {brand_token}"}
        )
        conversation_id = start_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages/attachment",
            data={"message_type": "document", "caption": "Brief attached"},
            files={"file": ("brief.pdf", b"%PDF-fake", "application/pdf")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["text_body"] == "Brief attached"

    async def test_document_rejects_unsupported_extension(self, client, tiny_video_bytes):
        brand_token, _, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="badext-brand@example.com", influencer_email="badext-inf@example.com", influencer_username="badextinf",
        )
        start_resp = await client.post(
            "/api/v1/conversations", json={"counterpart_id": inf_id}, headers={"Authorization": f"Bearer {brand_token}"}
        )
        conversation_id = start_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages/attachment",
            data={"message_type": "document"},
            files={"file": ("virus.exe", b"not a document", "application/octet-stream")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert resp.status_code == 400

    async def test_video_attachment_oversized_rejected(self, client, tiny_video_bytes):
        brand_token, _, inf_token, inf_id = await connected_brand_and_influencer(
            client, tiny_video_bytes,
            brand_email="oversize-brand@example.com", influencer_email="oversize-inf@example.com", influencer_username="oversizeinf",
        )
        start_resp = await client.post(
            "/api/v1/conversations", json={"counterpart_id": inf_id}, headers={"Authorization": f"Bearer {brand_token}"}
        )
        conversation_id = start_resp.json()["id"]

        # Deliberately small cap check via the audio path (20MB default) since a
        # 200MB+ video fixture would be wasteful to generate just for this test.
        oversized = b"0" * (21 * 1024 * 1024)
        resp = await client.post(
            f"/api/v1/conversations/{conversation_id}/messages/attachment",
            data={"message_type": "audio"},
            files={"file": ("big.mp3", oversized, "audio/mpeg")},
            headers={"Authorization": f"Bearer {brand_token}"},
        )
        assert resp.status_code == 413
