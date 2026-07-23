from datetime import datetime, timedelta, timezone
import uuid

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

    def test_signup_duplicate_unverified_email_resends_code(
        self, client, tracked_email, signup_payload
    ) -> None:
        signup_payload["email"] = tracked_email
        first = client.post("/api/v1/auth/signup", json=signup_payload)
        assert first.status_code == 201
        first_code = first.json()["verificationCode"]

        signup_payload["name"] = "Jane Updated"
        signup_payload["password"] = "NewPass1"
        second = client.post("/api/v1/auth/signup", json=signup_payload)
        assert second.status_code == 201
        body = second.json()
        assert body["success"] is True
        assert body["emailExists"] is False
        assert body["emailVerificationRequired"] is True
        assert body["user"]["name"] == "Jane Updated"
        assert body["verificationCode"]
        assert body["verificationCode"] != first_code

        db = SessionLocal()
        try:
            users = db.scalars(select(User).where(User.email == tracked_email)).all()
            assert len(users) == 1
            assert users[0].email_verified is False
            assert users[0].full_name == "Jane Updated"
        finally:
            db.close()

        login = client.post(
            "/api/v1/auth/login",
            json={"email": tracked_email, "password": "NewPass1"},
        )
        assert login.status_code == 403

    def test_signup_duplicate_verified_email_conflict(
        self, client, tracked_email, signup_payload
    ) -> None:
        signup_payload["email"] = tracked_email
        first = client.post("/api/v1/auth/signup", json=signup_payload)
        assert first.status_code == 201
        code = first.json()["verificationCode"]
        client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": code},
        )

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

        verify = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": code},
        )
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
        assert body["user"]["inviteCode"]
        assert body["subscription"] is None
        assert body["children"] == []

    def test_login_includes_children(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        verify = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": signup["verificationCode"]},
        ).json()
        token = verify["token"]

        created = client.post(
            "/api/v1/children",
            json={
                "name": "Alex",
                "dateOfBirth": "2015-06-20",
                "gender": "boy",
                "devices": ["this_device"],
                "pin": "6756",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert created.status_code == 201
        child_id = created.json()["child"]["id"]

        response = client.post(
            "/api/v1/auth/login",
            json={"email": tracked_email, "password": signup_payload["password"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["children"]) == 1
        assert body["children"][0]["id"] == child_id
        assert body["children"][0]["name"] == "Alex"
        assert body["children"][0]["initial"] == "A"

    def test_login_invalid_password(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": signup["verificationCode"]},
        )

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

        response = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": code},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["code"] == code
        assert body["token"]
        assert body["user"]["emailVerified"] is True
        assert body["user"]["inviteCode"]
        assert len(body["user"]["inviteCode"]) == 6
        assert body["children"] == []

    def test_verify_invalid_code(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        client.post("/api/v1/auth/signup", json=signup_payload)
        response = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": "0000"},
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["message"].lower() or "expired" in response.json()["message"].lower()

    def test_verify_code_with_wrong_email_fails(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        code = signup["verificationCode"]

        response = client.post(
            "/api/v1/auth/email/verify",
            json={"email": "other.user@example.com", "code": code},
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["message"].lower() or "expired" in response.json()["message"].lower()

        db = SessionLocal()
        try:
            user = db.scalar(select(User).where(User.email == tracked_email))
            assert user is not None
            assert user.email_verified is False
        finally:
            db.close()

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

        response = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": code},
        )
        assert response.status_code == 400

    def test_verify_code_cannot_be_reused(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        code = signup["verificationCode"]

        first = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": code},
        )
        assert first.status_code == 200

        second = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": code},
        )
        assert second.status_code == 400

    def test_verify_missing_fields_returns_400(self, client) -> None:
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
        old = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": old_code},
        )
        assert old.status_code == 400

        # New code should work
        verify = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": body["verificationCode"]},
        )
        assert verify.status_code == 200

    def test_resend_already_verified(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": signup["verificationCode"]},
        )

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

        verify = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": code},
        )
        assert verify.status_code == 200
        verify_body = verify.json()
        assert verify_body["user"]["emailVerified"] is True
        assert verify_body["token"]
        assert verify_body["user"]["inviteCode"]

        login = client.post(
            "/api/v1/auth/login",
            json={"email": tracked_email, "password": "Demo@123"},
        )
        assert login.status_code == 200
        login_body = login.json()
        assert login_body["token"]
        assert login_body["user"]["emailVerified"] is True
        assert login_body["user"]["inviteCode"] == verify_body["user"]["inviteCode"]
        assert login_body["subscription"] is None

    def test_signup_resume_after_app_closed_then_verify_without_login(
        self, client, tracked_email, signup_payload
    ) -> None:
        signup_payload["email"] = tracked_email
        first = client.post("/api/v1/auth/signup", json=signup_payload)
        assert first.status_code == 201
        old_code = first.json()["verificationCode"]

        second = client.post("/api/v1/auth/signup", json=signup_payload)
        assert second.status_code == 201
        new_code = second.json()["verificationCode"]
        assert new_code != old_code

        verify = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": new_code},
        )
        assert verify.status_code == 200
        body = verify.json()
        assert body["token"]
        assert body["user"]["emailVerified"] is True


class TestInviteCode:
    def test_generate_invite_code_alphanumeric_format(self) -> None:
        from app.core.config import get_settings
        from app.core.invite_code import INVITE_CODE_ALPHABET, generate_invite_code

        get_settings.cache_clear()
        code = generate_invite_code(format="alphanumeric", length=6)
        assert len(code) == 6
        assert all(ch in INVITE_CODE_ALPHABET for ch in code)
        assert not any(ch in code for ch in "01IOL")

    def test_generate_invite_code_numeric_format(self, monkeypatch) -> None:
        from app.core.config import get_settings
        from app.core.invite_code import generate_invite_code

        monkeypatch.setenv("INVITE_CODE_FORMAT", "numeric")
        monkeypatch.setenv("INVITE_CODE_LENGTH", "6")
        get_settings.cache_clear()
        try:
            code = generate_invite_code()
            assert len(code) == 6
            assert code.isdigit()
        finally:
            get_settings.cache_clear()

    def test_regenerate_invite_code_requires_auth(self, client) -> None:
        response = client.post("/api/v1/auth/invite-code/regenerate")
        assert response.status_code == 401

    def test_regenerate_invite_code_success(self, client, tracked_email, signup_payload) -> None:
        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        verify = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": signup["verificationCode"]},
        ).json()
        old_code = verify["user"]["inviteCode"]
        token = verify["token"]

        response = client.post(
            "/api/v1/auth/invite-code/regenerate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["inviteCode"]
        assert body["inviteCode"] != old_code
        assert len(body["inviteCode"]) == 6

        login = client.post(
            "/api/v1/auth/login",
            json={"email": tracked_email, "password": signup_payload["password"]},
        ).json()
        assert login["user"]["inviteCode"] == body["inviteCode"]

    def test_verify_generates_numeric_when_env_numeric(
        self, client, tracked_email, signup_payload, monkeypatch
    ) -> None:
        from app.core.config import get_settings

        monkeypatch.setenv("INVITE_CODE_FORMAT", "numeric")
        get_settings.cache_clear()
        try:
            signup_payload["email"] = tracked_email
            signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
            verify = client.post(
                "/api/v1/auth/email/verify",
                json={"email": tracked_email, "code": signup["verificationCode"]},
            ).json()
            invite = verify["user"]["inviteCode"]
            assert invite is not None
            assert len(invite) == 6
            assert invite.isdigit()
        finally:
            get_settings.cache_clear()

    def test_regenerate_under_numeric_produces_digits(
        self, client, tracked_email, signup_payload, monkeypatch
    ) -> None:
        from app.core.config import get_settings

        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        verify = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": signup["verificationCode"]},
        ).json()
        token = verify["token"]
        old_code = verify["user"]["inviteCode"]

        monkeypatch.setenv("INVITE_CODE_FORMAT", "numeric")
        get_settings.cache_clear()
        try:
            response = client.post(
                "/api/v1/auth/invite-code/regenerate",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            new_code = response.json()["inviteCode"]
            assert new_code != old_code
            assert len(new_code) == 6
            assert new_code.isdigit()
        finally:
            get_settings.cache_clear()

    def test_grandfathered_alphanumeric_code_still_verifies_when_env_numeric(
        self, client, tracked_email, signup_payload, monkeypatch
    ) -> None:
        """Existing stored codes remain valid after switching ENV to numeric."""
        from app.core.config import get_settings
        from app.db.session import SessionLocal
        from app.models.user import User
        from sqlalchemy import select

        signup_payload["email"] = tracked_email
        signup = client.post("/api/v1/auth/signup", json=signup_payload).json()
        verify = client.post(
            "/api/v1/auth/email/verify",
            json={"email": tracked_email, "code": signup["verificationCode"]},
        ).json()
        # Force an alphanumeric-looking code into DB while ENV becomes numeric
        legacy_code = f"A3K{uuid.uuid4().hex[:3].upper()}"
        # Ensure exactly 6 chars from alphanumeric alphabet style
        legacy_code = (legacy_code + "XXX")[:6].upper()
        # Prefer characters from invite alphabet (replace 0/1/I/O/L if any)
        from app.core.invite_code import INVITE_CODE_ALPHABET

        legacy_code = "".join(
            ch if ch in INVITE_CODE_ALPHABET else "2" for ch in legacy_code
        )
        db = SessionLocal()
        try:
            user = db.scalar(select(User).where(User.email == tracked_email.lower()))
            assert user is not None
            user.invite_code = legacy_code
            db.commit()
        finally:
            db.close()

        monkeypatch.setenv("INVITE_CODE_FORMAT", "numeric")
        get_settings.cache_clear()
        try:
            response = client.post(
                "/api/v1/auth/child/verify-invite-code",
                json={"inviteCode": legacy_code},
            )
            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert body["user"]["inviteCode"] == legacy_code
        finally:
            get_settings.cache_clear()
