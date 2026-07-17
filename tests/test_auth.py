from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.email_verification import EmailVerificationCode
from app.models.user import User


class TestSignup:
    def test_signup_success(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        response = client.post("/api/v1/auth/signup", json=signup_payload)

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["emailExists"] is False
        assert body["emailVerificationRequired"] is True
        assert body["user"]["email"] == tracked_email
        assert body["user"]["name"] == "John Doe"
        assert body["user"]["guardian"] is True
        assert body["user"]["emailVerified"] is False
        assert body["verificationCode"]
        assert len(body["verificationCode"]) == 4

        db = SessionLocal()
        try:
            user = db.scalar(select(User).where(User.email == tracked_email))
            assert user is not None
            assert user.email_verified is False
            assert user.password_hash is not None
            assert user.password_hash != signup_payload["password"]
        finally:
            db.close()

    def test_signup_duplicate_email_conflict(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        first = client.post("/api/v1/auth/signup", json=signup_payload)
        assert first.status_code == 201

        second = client.post("/api/v1/auth/signup", json=signup_payload)
        assert second.status_code == 409
        body = second.json()
        assert body["success"] is False
        assert body["emailExists"] is True
        assert "already exists" in body["message"].lower()

    def test_signup_missing_email_returns_400(self, client, signup_payload) -> None:
        del signup_payload["email"]
        response = client.post("/api/v1/auth/signup", json=signup_payload)
        assert response.status_code == 400
        assert response.json()["success"] is False

    def test_signup_guardian_false_returns_400(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup_payload["guardian"] = False
        response = client.post("/api/v1/auth/signup", json=signup_payload)
        assert response.status_code == 400
        assert response.json()["success"] is False

    def test_signup_terms_false_returns_400(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup_payload["acceptedTerms"] = False
        response = client.post("/api/v1/auth/signup", json=signup_payload)
        assert response.status_code == 400
        assert response.json()["success"] is False


class TestLogin:
    def test_login_before_verify_forbidden(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        client.post("/api/v1/auth/signup", json=signup_payload)

        response = client.post(
            "/api/v1/auth/login",
            json={"email": tracked_email, "password": signup_payload["password"]},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert body["emailVerified"] is False

    def test_login_success_after_verify(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        code = signup["verificationCode"]

        verify = client.post("/api/v1/auth/email/verify", json={"code": code})
        assert verify.status_code == 200

        response = client.post(
            "/api/v1/auth/login",
            json={"email": tracked_email, "password": signup_payload["password"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["token"]
        assert body["user"]["email"] == tracked_email
        assert body["user"]["emailVerified"] is True
        assert body["children"] == []

    def test_login_invalid_password(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        client.post("/api/v1/auth/email/verify", json={"code": signup["verificationCode"]})

        response = client.post(
            "/api/v1/auth/login",
            json={"email": tracked_email, "password": "WrongPass1"},
        )
        assert response.status_code == 401
        assert response.json()["message"] == "Invalid credentials"

    def test_login_unknown_email(self, client) -> None:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing.user@example.com", "password": "Demo@123"},
        )
        assert response.status_code == 401
        assert response.json()["success"] is False

    def test_login_missing_password_returns_400(self, client) -> None:
        response = client.post("/api/v1/auth/login", json={"email": "a@example.com"})
        assert response.status_code == 400
        assert response.json()["success"] is False


class TestVerifyEmail:
    def test_verify_email_success(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        code = signup["verificationCode"]

        response = client.post("/api/v1/auth/email/verify", json={"code": code})
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["code"] == code
        assert body["user"]["emailVerified"] is True

    def test_verify_invalid_code(self, client) -> None:
        response = client.post("/api/v1/auth/email/verify", json={"code": "0000"})
        assert response.status_code == 400
        assert "invalid" in response.json()["message"].lower() or "expired" in response.json()["message"].lower()

    def test_verify_expired_code(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        code = signup["verificationCode"]

        db = SessionLocal()
        try:
            verification = db.scalar(
                select(EmailVerificationCode).where(EmailVerificationCode.code == code)
            )
            assert verification is not None
            verification.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()

        response = client.post("/api/v1/auth/email/verify", json={"code": code})
        assert response.status_code == 400

    def test_verify_code_cannot_be_reused(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        code = signup["verificationCode"]

        first = client.post("/api/v1/auth/email/verify", json={"code": code})
        assert first.status_code == 200

        second = client.post("/api/v1/auth/email/verify", json={"code": code})
        assert second.status_code == 400

    def test_verify_missing_code_returns_400(self, client) -> None:
        response = client.post("/api/v1/auth/email/verify", json={})
        assert response.status_code == 400
        assert response.json()["success"] is False


class TestResendVerification:
    def test_resend_success(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        old_code = signup["verificationCode"]

        response = client.post(
            "/api/v1/auth/email/resend",
            json={"email": tracked_email},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Verification email resent"
        assert body["verificationCode"]
        assert body["verificationCode"] != old_code

        # Old code should no longer work
        old = client.post("/api/v1/auth/email/verify", json={"code": old_code})
        assert old.status_code == 400

        # New code should work
        verify = client.post(
            "/api/v1/auth/email/verify",
            json={"code": body["verificationCode"]},
        )
        assert verify.status_code == 200

    def test_resend_already_verified(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        client.post("/api/v1/auth/email/verify", json={"code": signup["verificationCode"]})

        response = client.post(
            "/api/v1/auth/email/resend",
            json={"email": tracked_email},
        )
        assert response.status_code == 400
        assert "already verified" in response.json()["message"].lower()

    def test_resend_unknown_email_still_returns_success(self, client) -> None:
        # Avoid email enumeration
        response = client.post(
            "/api/v1/auth/email/resend",
            json={"email": "does.not.exist@example.com"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestFullAuthFlow:
    def test_signup_verify_login_happy_path(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email

        signup = client.post("/api/v1/auth/signup", json=signup_payload)
        assert signup.status_code == 201
        code = signup.json()["verificationCode"]

        verify = client.post("/api/v1/auth/email/verify", json={"code": code})
        assert verify.status_code == 200
        assert verify.json()["user"]["emailVerified"] is True

        login = client.post(
            "/api/v1/auth/login",
            json={"email": tracked_email, "password": "Demo@123"},
        )
        assert login.status_code == 200
        assert login.json()["token"]
        assert login.json()["user"]["emailVerified"] is True
