"""
Full end-to-end integration tests for the auth MVP.

Covers: signup → email verification (DB + Campaign Monitor) → login → JWT,
plus error paths and API contract shapes.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.invite_code import INVITE_CODE_ALPHABET, INVITE_CODE_LENGTH
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.email_verification import EmailVerificationCode
from app.models.enums import UserType
from app.models.user import User
from app.models.user_activity import UserActivity
from tests.conftest import (
    get_active_codes_for_user,
    get_latest_code_from_db,
    get_user_from_db,
    login_user,
    signup_user,
    verify_user,
)


class TestFullE2EAuthFlow:
    """Complete user journey from signup through verified login."""

    def test_full_flow_with_db_and_jwt_assertions(self, client, tracked_email) -> None:
        # 1. Signup
        signup = signup_user(client, tracked_email)
        assert signup["success"] is True
        assert signup["emailVerificationRequired"] is True
        assert signup["user"]["emailVerified"] is False
        code = signup["verificationCode"]
        user_id = signup["user"]["id"]

        # 2. User persisted in DB (ORM)
        user = get_user_from_db(tracked_email)
        assert user is not None
        assert str(user.id) == user_id
        assert user.email_verified is False
        assert user.user_type == UserType.PARENT
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.accepted_terms is True
        assert user.password_hash is not None

        # 3. Verification code persisted in DB
        codes = get_active_codes_for_user(user.id)
        assert len(codes) == 1
        assert codes[0].code == code
        assert codes[0].email == tracked_email
        assert codes[0].is_used is False
        assert codes[0].expires_at > datetime.now(timezone.utc)

        # 4. Login blocked before verify
        blocked = client.post(
            "/api/v1/auth/login",
            json={"email": tracked_email, "password": "Demo@123"},
        )
        assert blocked.status_code == 403
        assert blocked.json()["emailVerified"] is False

        # 5. Verify email
        verify = verify_user(client, tracked_email, code)
        assert verify["success"] is True
        assert verify["user"]["emailVerified"] is True
        assert verify["code"] == code
        assert verify["token"]
        invite_code = verify["user"]["inviteCode"]
        assert invite_code is not None
        assert len(invite_code) == INVITE_CODE_LENGTH
        assert all(ch in INVITE_CODE_ALPHABET for ch in invite_code)

        user = get_user_from_db(tracked_email)
        assert user is not None
        assert user.email_verified is True
        assert user.invite_code == invite_code
        assert get_active_codes_for_user(user.id) == []

        # 6. Login succeeds with JWT
        login = login_user(client, tracked_email)
        assert login["success"] is True
        assert login["token"]
        assert login["user"]["emailVerified"] is True
        assert login["user"]["inviteCode"] == invite_code
        assert login["subscription"] is None
        assert login["children"] == []

        claims = decode_access_token(login["token"])
        assert claims is not None
        assert claims["sub"] == user_id
        assert claims["email"] == tracked_email
        assert claims["user_type"] == "PARENT"

        # 7. last_login_at updated in user_activity
        db = SessionLocal()
        try:
            user = db.scalar(select(User).where(User.email == tracked_email))
            assert user is not None
            activity = db.scalar(select(UserActivity).where(UserActivity.user_id == user.id))
            assert activity is not None
            assert activity.last_login_at is not None
        finally:
            db.close()

    def test_signup_resend_verify_login_flow(self, client, tracked_email) -> None:
        signup = signup_user(client, tracked_email)
        old_code = signup["verificationCode"]

        resend = client.post(
            "/api/v1/auth/email/resend",
            json={"email": tracked_email},
        )
        assert resend.status_code == 200
        new_code = resend.json()["verificationCode"]
        assert new_code != old_code

        # Old code invalidated
        old_verify = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": old_code},
        )
        assert old_verify.status_code == 400

        verify_user(client, tracked_email, new_code)
        login_user(client, tracked_email)


class TestEmailVerificationIntegration:
    """Email verification behaviour with DB and Campaign Monitor integration."""

    def test_signup_triggers_campaign_monitor_email_with_correct_code(
        self, campaign_monitor_client, tracked_email, email_capture
    ) -> None:
        signup = signup_user(campaign_monitor_client, tracked_email)
        code = signup["verificationCode"]

        assert len(email_capture.sent) == 1
        sent = email_capture.sent[0]
        assert sent.to_email == tracked_email
        assert sent.to_name == "John Doe"
        assert sent.code == code

        # Code in email matches DB
        assert get_latest_code_from_db(tracked_email) == code

    def test_resend_triggers_new_campaign_monitor_email(
        self, campaign_monitor_client, tracked_email, email_capture
    ) -> None:
        signup_user(campaign_monitor_client, tracked_email)
        assert len(email_capture.sent) == 1

        resend = campaign_monitor_client.post(
            "/api/v1/auth/email/resend",
            json={"email": tracked_email},
        )
        assert resend.status_code == 200
        assert len(email_capture.sent) == 2
        assert email_capture.sent[1].code == resend.json()["verificationCode"]

    def test_verify_without_api_code_uses_db_code(self, client, tracked_email, monkeypatch) -> None:
        """Simulates production: code not returned in API, user gets it from email."""
        monkeypatch.setenv("INCLUDE_VERIFICATION_CODE_IN_RESPONSE", "false")
        get_settings.cache_clear()

        response = client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Jane Smith",
                "email": tracked_email,
                "password": "Demo@123",
                "guardian": True,
                "acceptedTerms": True,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body.get("verificationCode") is None

        code_from_db = get_latest_code_from_db(tracked_email)
        verify = verify_user(client, tracked_email, code_from_db)
        assert verify["user"]["emailVerified"] is True

        get_settings.cache_clear()

    def test_signup_succeeds_when_campaign_monitor_fails(
        self, client, tracked_email, monkeypatch
    ) -> None:
        monkeypatch.setenv("CAMPAIGN_MONITOR_API_KEY", "cm-test-key")
        monkeypatch.setenv("CAMPAIGN_MONITOR_SENDER_EMAIL", "noreply@test.com")
        get_settings.cache_clear()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "server error"

        with patch("app.services.email_service.httpx.Client") as client_cls:
            http = client_cls.return_value.__enter__.return_value
            http.post.return_value = mock_response

            response = client.post(
                "/api/v1/auth/signup",
                json={
                    "name": "Fail User",
                    "email": tracked_email,
                    "password": "Demo@123",
                    "guardian": True,
                    "acceptedTerms": True,
                },
            )

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert "could not be sent" in body["message"].lower()
        assert body.get("verificationCode") is not None

        user = get_user_from_db(tracked_email)
        assert user is not None
        assert user.email_verified is False

        get_settings.cache_clear()

    def test_campaign_monitor_http_error_on_signup_still_succeeds(
        self, client, tracked_email, monkeypatch
    ) -> None:
        monkeypatch.setenv("CAMPAIGN_MONITOR_API_KEY", "cm-test-key")
        monkeypatch.setenv("CAMPAIGN_MONITOR_SENDER_EMAIL", "noreply@test.com")
        get_settings.cache_clear()

        with patch("app.services.email_service.httpx.Client") as client_cls:
            http = client_cls.return_value.__enter__.return_value
            http.post.side_effect = httpx.ConnectError("network down")

            response = client.post(
                "/api/v1/auth/signup",
                json={
                    "name": "Net Fail",
                    "email": tracked_email,
                    "password": "Demo@123",
                    "guardian": True,
                    "acceptedTerms": True,
                },
            )

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body.get("verificationCode") is not None
        get_settings.cache_clear()

    def test_resend_succeeds_when_campaign_monitor_fails(
        self, client, tracked_email, monkeypatch
    ) -> None:
        monkeypatch.setenv("CAMPAIGN_MONITOR_API_KEY", "cm-test-key")
        monkeypatch.setenv("CAMPAIGN_MONITOR_SENDER_EMAIL", "noreply@test.com")
        get_settings.cache_clear()

        signup_user(client, tracked_email)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"Code":102,"Message":"Invalid ClientID"}'

        with patch("app.services.email_service.httpx.Client") as client_cls:
            http = client_cls.return_value.__enter__.return_value
            http.post.return_value = mock_response

            response = client.post(
                "/api/v1/auth/email/resend",
                json={"email": tracked_email},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "could not be sent" in body["message"].lower()
        assert body.get("verificationCode") is not None

        get_settings.cache_clear()

    def test_verification_code_marked_used_after_verify(self, client, tracked_email) -> None:
        signup = signup_user(client, tracked_email)
        code = signup["verificationCode"]

        verify_user(client, tracked_email, code)

        db = SessionLocal()
        try:
            record = db.scalar(
                select(EmailVerificationCode).where(EmailVerificationCode.code == code)
            )
            assert record is not None
            assert record.is_used is True
            assert record.used_at is not None
        finally:
            db.close()


class TestAPIContractShapes:
    """Response payloads match Mobile BFF contract fields."""

    def test_signup_response_contract(self, client, tracked_email) -> None:
        body = signup_user(client, tracked_email)
        required = {
            "success",
            "message",
            "emailExists",
            "emailVerificationRequired",
            "user",
            "verificationCode",
        }
        assert required.issubset(body.keys())
        assert set(body["user"].keys()) >= {"id", "name", "email", "guardian", "emailVerified"}

    def test_login_response_contract(self, verified_user, client) -> None:
        login = login_user(client, verified_user["email"])
        required = {"success", "message", "token", "user", "children", "subscription"}
        assert required.issubset(login.keys())
        assert isinstance(login["children"], list)
        assert login["subscription"] is None
        assert "inviteCode" in login["user"]

    def test_verify_response_contract(self, client, tracked_email) -> None:
        signup = signup_user(client, tracked_email)
        body = verify_user(client, tracked_email, signup["verificationCode"])
        required = {"success", "message", "code", "token", "user", "children"}
        assert required.issubset(body.keys())
        assert isinstance(body["children"], list)
        assert "inviteCode" in body["user"]
        assert body["user"]["inviteCode"]

    def test_resend_response_contract(self, client, tracked_email) -> None:
        signup_user(client, tracked_email)
        response = client.post(
            "/api/v1/auth/email/resend",
            json={"email": tracked_email},
        )
        body = response.json()
        assert response.status_code == 200
        assert {"success", "message", "verificationCode"}.issubset(body.keys())

    def test_409_duplicate_signup_contract(self, client, tracked_email) -> None:
        signup = signup_user(client, tracked_email)
        verify_user(client, tracked_email, signup["verificationCode"])
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "name": "John Doe",
                "email": tracked_email,
                "password": "Demo@123",
                "guardian": True,
                "acceptedTerms": True,
            },
        )
        body = response.json()
        assert response.status_code == 409
        assert body["success"] is False
        assert body["emailExists"] is True

    def test_403_unverified_login_contract(self, client, tracked_email) -> None:
        signup_user(client, tracked_email)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": tracked_email, "password": "Demo@123"},
        )
        body = response.json()
        assert response.status_code == 403
        assert body["success"] is False
        assert body["emailVerified"] is False


class TestAcceptanceCriteria:
    """Jira LA-2 / LA-31 acceptance criteria."""

    def test_ac1_signup_creates_user_with_basic_details(self, client, tracked_email) -> None:
        """AC1: signup creates a new record with all basic details."""
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Parent User",
                "email": tracked_email,
                "password": "Demo@123",
                "guardian": True,
                "acceptedTerms": True,
            },
        )
        assert response.status_code == 201

        user = get_user_from_db(tracked_email)
        assert user is not None
        assert user.email == tracked_email
        assert user.full_name == "Parent User"
        assert user.is_guardian is True

    def test_ac2_verify_email_with_valid_code(self, client, tracked_email) -> None:
        """AC2: valid verification code marks email as verified."""
        signup = signup_user(client, tracked_email)
        verify = verify_user(client, tracked_email, signup["verificationCode"])

        assert verify["user"]["emailVerified"] is True
        user = get_user_from_db(tracked_email)
        assert user is not None
        assert user.email_verified is True

    def test_ac3_login_authenticates_valid_credentials(self, verified_user, client) -> None:
        """AC3: valid credentials authenticate and return token."""
        login = login_user(client, verified_user["email"], verified_user["password"])
        assert login["success"] is True
        assert login["token"]
        assert login["message"] == "Login successful"

    def test_ac3_login_rejects_unverified_user(self, client, tracked_email) -> None:
        signup_user(client, tracked_email)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": tracked_email, "password": "Demo@123"},
        )
        assert response.status_code == 403


class TestEdgeCases:
    def test_single_name_user_gets_first_and_last_name(self, client, tracked_email) -> None:
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Madonna",
                "email": tracked_email,
                "password": "Demo@123",
                "guardian": True,
                "acceptedTerms": True,
            },
        )
        assert response.status_code == 201
        user = get_user_from_db(tracked_email)
        assert user is not None
        assert user.first_name == "Madonna"
        assert user.last_name == "Madonna"

    def test_email_stored_lowercase(self, client, tracked_email) -> None:
        mixed = tracked_email.replace("test.", "Test.")
        response = client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Case Test",
                "email": mixed,
                "password": "Demo@123",
                "guardian": True,
                "acceptedTerms": True,
            },
        )
        assert response.status_code == 201
        user = get_user_from_db(mixed)
        assert user is not None
        assert user.email == mixed.lower()

    def test_only_one_active_code_after_resend(self, client, tracked_email) -> None:
        signup_user(client, tracked_email)
        user = get_user_from_db(tracked_email)
        assert user is not None

        client.post("/api/v1/auth/email/resend", json={"email": tracked_email})
        active = get_active_codes_for_user(user.id)
        assert len(active) == 1

    def test_expired_code_rejected(self, client, tracked_email) -> None:
        signup = signup_user(client, tracked_email)
        code = signup["verificationCode"]

        db = SessionLocal()
        try:
            record = db.scalar(
                select(EmailVerificationCode).where(EmailVerificationCode.code == code)
            )
            assert record is not None
            record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
            db.commit()
        finally:
            db.close()

        response = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": code},
        )
        assert response.status_code == 400

    def test_campaign_monitor_not_configured_still_signs_up(self, client, tracked_email) -> None:
        """Dev fallback: no Campaign Monitor creds, signup still works."""
        body = signup_user(client, tracked_email)
        assert body["verificationCode"]
        assert get_user_from_db(tracked_email) is not None


class TestInviteCodeRegenerate:
    def test_regenerate_changes_code_and_persists(self, client, tracked_email) -> None:
        signup = signup_user(client, tracked_email)
        verify = verify_user(client, tracked_email, signup["verificationCode"])
        old_code = verify["user"]["inviteCode"]
        token = verify["token"]

        response = client.post(
            "/api/v1/auth/invite-code/regenerate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["inviteCode"] != old_code

        user = get_user_from_db(tracked_email)
        assert user is not None
        assert user.invite_code == body["inviteCode"]

        login = login_user(client, tracked_email)
        assert login["user"]["inviteCode"] == body["inviteCode"]
        assert login["subscription"] is None

    def test_regenerate_without_token_returns_401(self, client) -> None:
        response = client.post("/api/v1/auth/invite-code/regenerate")
        assert response.status_code == 401
