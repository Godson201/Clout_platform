from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models.email_token import EmailToken
from app.services.email.console import SENT_EMAILS


async def _register_brand(client, email="pw-brand@example.com", **extra):
    payload = {
        "email": email,
        "password": "SuperSecret123",
        "business_name": "Acme Ads",
        "sector": "retail",
        "location": "Kigali",
        **extra,
    }
    resp = await client.post("/api/v1/auth/register/brand", json=payload)
    return resp


async def _latest_token_for(email: str) -> str | None:
    """Test-only helper: pulls the raw token back out of the email body captured
    in the mock outbox, since only the hash is ever persisted server-side."""
    for sent in reversed(SENT_EMAILS):
        if sent.to == email:
            for line in sent.text_body.splitlines():
                if "token=" in line:
                    return line.split("token=")[-1].strip()
    return None


class TestRegistrationVerificationEmail:
    async def test_register_sends_a_verification_email(self, client):
        resp = await _register_brand(client, email="verify-me@example.com")
        assert resp.status_code == 201

        sent = [e for e in SENT_EMAILS if e.to == "verify-me@example.com"]
        assert len(sent) == 1
        assert "Confirm" in sent[0].subject

    async def test_verify_email_marks_account_verified(self, client):
        await _register_brand(client, email="verify-flow@example.com")
        token = await _latest_token_for("verify-flow@example.com")
        assert token

        resp = await client.post("/api/v1/auth/verify-email", json={"token": token})
        assert resp.status_code == 200

        login = await client.post(
            "/api/v1/auth/login", json={"email": "verify-flow@example.com", "password": "SuperSecret123"}
        )
        me = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
        assert me.json()["is_verified"] is True

    async def test_verify_email_token_is_single_use(self, client):
        await _register_brand(client, email="verify-once@example.com")
        token = await _latest_token_for("verify-once@example.com")

        first = await client.post("/api/v1/auth/verify-email", json={"token": token})
        assert first.status_code == 200
        second = await client.post("/api/v1/auth/verify-email", json={"token": token})
        assert second.status_code == 400

    async def test_invalid_token_rejected(self, client):
        resp = await client.post("/api/v1/auth/verify-email", json={"token": "not-a-real-token"})
        assert resp.status_code == 400


class TestForgotPassword:
    async def test_unknown_email_still_returns_200(self, client):
        resp = await client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
        assert resp.status_code == 200
        assert not [e for e in SENT_EMAILS if e.to == "nobody@example.com"]

    async def test_known_email_gets_a_reset_email(self, client):
        await _register_brand(client, email="forgot-me@example.com")
        SENT_EMAILS.clear()

        resp = await client.post("/api/v1/auth/forgot-password", json={"email": "forgot-me@example.com"})
        assert resp.status_code == 200

        sent = [e for e in SENT_EMAILS if e.to == "forgot-me@example.com"]
        assert len(sent) == 1
        assert "Reset" in sent[0].subject


class TestResetPassword:
    async def test_prompt_returns_security_question_when_set(self, client):
        await _register_brand(
            client,
            email="secure-reset@example.com",
            security_question="What is your favorite color?",
            security_answer="Violet",
        )
        SENT_EMAILS.clear()
        await client.post("/api/v1/auth/forgot-password", json={"email": "secure-reset@example.com"})
        token = await _latest_token_for("secure-reset@example.com")

        resp = await client.get(f"/api/v1/auth/reset-password/{token}")
        assert resp.status_code == 200
        assert resp.json()["security_question"] == "What is your favorite color?"

    async def test_prompt_is_null_when_no_security_question_set(self, client):
        await _register_brand(client, email="no-question@example.com")
        SENT_EMAILS.clear()
        await client.post("/api/v1/auth/forgot-password", json={"email": "no-question@example.com"})
        token = await _latest_token_for("no-question@example.com")

        resp = await client.get(f"/api/v1/auth/reset-password/{token}")
        assert resp.json()["security_question"] is None

    async def test_wrong_security_answer_rejected(self, client):
        await _register_brand(
            client,
            email="wrong-answer@example.com",
            security_question="What is your favorite color?",
            security_answer="Violet",
        )
        SENT_EMAILS.clear()
        await client.post("/api/v1/auth/forgot-password", json={"email": "wrong-answer@example.com"})
        token = await _latest_token_for("wrong-answer@example.com")

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "BrandNewPass123", "security_answer": "Chartreuse"},
        )
        assert resp.status_code == 400

        # Original password must still work — the reset must not have gone through.
        login = await client.post(
            "/api/v1/auth/login", json={"email": "wrong-answer@example.com", "password": "SuperSecret123"}
        )
        assert login.status_code == 200

    async def test_correct_security_answer_resets_password_case_insensitively(self, client):
        await _register_brand(
            client,
            email="right-answer@example.com",
            security_question="What is your favorite color?",
            security_answer="Violet",
        )
        SENT_EMAILS.clear()
        await client.post("/api/v1/auth/forgot-password", json={"email": "right-answer@example.com"})
        token = await _latest_token_for("right-answer@example.com")

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "BrandNewPass123", "security_answer": "  VIOLET  "},
        )
        assert resp.status_code == 200

        old_login = await client.post(
            "/api/v1/auth/login", json={"email": "right-answer@example.com", "password": "SuperSecret123"}
        )
        assert old_login.status_code == 401

        new_login = await client.post(
            "/api/v1/auth/login", json={"email": "right-answer@example.com", "password": "BrandNewPass123"}
        )
        assert new_login.status_code == 200

    async def test_reset_without_security_question_needs_no_answer(self, client):
        await _register_brand(client, email="no-secq-reset@example.com")
        SENT_EMAILS.clear()
        await client.post("/api/v1/auth/forgot-password", json={"email": "no-secq-reset@example.com"})
        token = await _latest_token_for("no-secq-reset@example.com")

        resp = await client.post(
            "/api/v1/auth/reset-password", json={"token": token, "new_password": "BrandNewPass123"}
        )
        assert resp.status_code == 200

    async def test_reset_sends_confirmation_email(self, client):
        await _register_brand(client, email="confirm-reset@example.com")
        SENT_EMAILS.clear()
        await client.post("/api/v1/auth/forgot-password", json={"email": "confirm-reset@example.com"})
        token = await _latest_token_for("confirm-reset@example.com")

        await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "BrandNewPass123"})

        confirmations = [
            e for e in SENT_EMAILS if e.to == "confirm-reset@example.com" and "changed" in e.subject.lower()
        ]
        assert len(confirmations) == 1

    async def test_reset_revokes_existing_refresh_tokens(self, client):
        register_resp = await _register_brand(client, email="revoke-on-reset@example.com")
        old_refresh_cookie = register_resp.cookies["clout_refresh_token"]

        SENT_EMAILS.clear()
        await client.post("/api/v1/auth/forgot-password", json={"email": "revoke-on-reset@example.com"})
        token = await _latest_token_for("revoke-on-reset@example.com")
        await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "BrandNewPass123"})

        client.cookies.set("clout_refresh_token", old_refresh_cookie)
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401

    async def test_reused_reset_token_rejected(self, client):
        await _register_brand(client, email="reuse-reset@example.com")
        SENT_EMAILS.clear()
        await client.post("/api/v1/auth/forgot-password", json={"email": "reuse-reset@example.com"})
        token = await _latest_token_for("reuse-reset@example.com")

        first = await client.post(
            "/api/v1/auth/reset-password", json={"token": token, "new_password": "BrandNewPass123"}
        )
        assert first.status_code == 200

        second = await client.post(
            "/api/v1/auth/reset-password", json={"token": token, "new_password": "AnotherPass456"}
        )
        assert second.status_code == 400

    async def test_expired_reset_token_rejected(self, client):
        await _register_brand(client, email="expired-reset@example.com")
        SENT_EMAILS.clear()
        await client.post("/api/v1/auth/forgot-password", json={"email": "expired-reset@example.com"})
        token = await _latest_token_for("expired-reset@example.com")

        async with AsyncSessionLocal() as db:
            from app.core.security import hash_secure_token

            result = await db.execute(
                select(EmailToken).where(EmailToken.token_hash == hash_secure_token(token))
            )
            row = result.scalar_one()
            row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            await db.commit()

        resp = await client.post(
            "/api/v1/auth/reset-password", json={"token": token, "new_password": "BrandNewPass123"}
        )
        assert resp.status_code == 400


class TestResendVerification:
    async def test_unverified_user_can_request_resend(self, client):
        register_resp = await _register_brand(client, email="resend-me@example.com")
        token = register_resp.json()["access_token"]
        SENT_EMAILS.clear()

        resp = await client.post("/api/v1/auth/resend-verification", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert [e for e in SENT_EMAILS if e.to == "resend-me@example.com"]

    async def test_requires_authentication(self, client):
        resp = await client.post("/api/v1/auth/resend-verification")
        assert resp.status_code == 401
