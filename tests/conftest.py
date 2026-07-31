import uuid
from collections.abc import Generator
from dataclasses import dataclass, field
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.child_island_progress import ChildIslandProgress
from app.models.child_simulation_progress import ChildSimulationProgress
from app.models.email_verification import EmailVerificationCode
from app.models.family import Family
from app.models.user import User
from app.models.user_activity import UserActivity
from app.models.voucher import VoucherRedemption


@dataclass
class SentEmail:
    to_email: str
    to_name: str
    code: str


@dataclass
class EmailCapture:
    sent: list[SentEmail] = field(default_factory=list)

    def record(self, *, to_email: str, to_name: str, code: str) -> None:
        self.sent.append(SentEmail(to_email=to_email, to_name=to_name, code=code))


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Default test env: no real Campaign Monitor sends; return codes in API responses."""
    monkeypatch.setenv("CAMPAIGN_MONITOR_API_KEY", "")
    monkeypatch.setenv("CAMPAIGN_MONITOR_SENDER_EMAIL", "")
    monkeypatch.setenv("INCLUDE_VERIFICATION_CODE_IN_RESPONSE", "true")
    monkeypatch.setenv("INVITE_CODE_FORMAT", "alphanumeric")
    monkeypatch.setenv("INVITE_CODE_LENGTH", "6")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def unique_email() -> str:
    return f"test.{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture
def signup_payload(unique_email: str) -> dict:
    return {
        "name": "John Doe",
        "email": unique_email,
        "password": "Demo@123",
        "guardian": True,
        "acceptedTerms": True,
    }


def cleanup_user_by_email(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user:
            db.execute(delete(VoucherRedemption).where(VoucherRedemption.user_id == user.id))
            db.execute(
                delete(EmailVerificationCode).where(EmailVerificationCode.user_id == user.id)
            )
            db.execute(delete(UserActivity).where(UserActivity.user_id == user.id))

            family_ids = [
                family.id
                for family in db.scalars(
                    select(Family).where(
                        (Family.primary_parent_user_id == user.id)
                        | (Family.secondary_parent_user_id == user.id)
                    )
                ).all()
            ]
            for family_id in family_ids:
                child_ids = [
                    child_id
                    for (child_id,) in db.execute(
                        select(User.id).where(User.family_id == family_id, User.id != user.id)
                    ).all()
                ]
                if child_ids:
                    db.execute(delete(VoucherRedemption).where(VoucherRedemption.user_id.in_(child_ids)))
                    db.execute(delete(UserActivity).where(UserActivity.user_id.in_(child_ids)))
                    db.execute(
                        delete(ChildSimulationProgress).where(
                            ChildSimulationProgress.child_user_id.in_(child_ids)
                        )
                    )
                    db.execute(
                        delete(ChildIslandProgress).where(
                            ChildIslandProgress.child_user_id.in_(child_ids)
                        )
                    )
                    db.execute(delete(User).where(User.id.in_(child_ids)))

                db.execute(update(User).where(User.family_id == family_id).values(family_id=None))
                db.execute(delete(Family).where(Family.id == family_id))

            db.execute(delete(User).where(User.id == user.id))
            db.commit()
    finally:
        db.close()


@pytest.fixture
def tracked_email(unique_email: str) -> Generator[str, None, None]:
    yield unique_email
    cleanup_user_by_email(unique_email)


def get_user_from_db(email: str) -> User | None:
    db = SessionLocal()
    try:
        return db.scalar(select(User).where(User.email == email.lower()))
    finally:
        db.close()


def get_active_codes_for_user(user_id) -> list[EmailVerificationCode]:
    db = SessionLocal()
    try:
        return list(
            db.scalars(
                select(EmailVerificationCode)
                .where(
                    EmailVerificationCode.user_id == user_id,
                    EmailVerificationCode.is_used.is_(False),
                )
                .order_by(EmailVerificationCode.created_at.desc())
            ).all()
        )
    finally:
        db.close()


def get_latest_code_from_db(email: str) -> str:
    user = get_user_from_db(email)
    assert user is not None, f"No user found for {email}"
    codes = get_active_codes_for_user(user.id)
    assert codes, f"No active verification codes for {email}"
    return codes[0].code


@pytest.fixture
def email_capture() -> EmailCapture:
    return EmailCapture()


@pytest.fixture
def campaign_monitor_client(client, email_capture, monkeypatch) -> Generator[TestClient, None, None]:
    """Client with Campaign Monitor configured; emails are captured instead of sent."""
    monkeypatch.setenv("CAMPAIGN_MONITOR_API_KEY", "cm-test-key")
    monkeypatch.setenv("CAMPAIGN_MONITOR_SENDER_EMAIL", "noreply@lively.test")
    monkeypatch.setenv("CAMPAIGN_MONITOR_SENDER_NAME", "Lively Test")
    get_settings.cache_clear()

    def _capture_send(self, *, to_email: str, to_name: str, code: str) -> None:
        email_capture.record(to_email=to_email, to_name=to_name, code=code)

    with patch(
        "app.services.email_service.EmailService.send_verification_email",
        autospec=True,
        side_effect=_capture_send,
    ):
        yield client

    get_settings.cache_clear()


def signup_user(client: TestClient, email: str, password: str = "Demo@123") -> dict:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "John Doe",
            "email": email,
            "password": password,
            "guardian": True,
            "acceptedTerms": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def verify_user(client: TestClient, email: str, code: str) -> dict:
    response = client.post(
        "/api/v1/auth/email/verify",
        json={"email": email, "code": code},
    )
    assert response.status_code == 200, response.text
    return response.json()


def login_user(client: TestClient, email: str, password: str = "Demo@123") -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def verified_user(client, tracked_email) -> Generator[dict, None, None]:
    """Signup + verify; returns dict with email, password, signup, verify, login-ready user."""
    signup = signup_user(client, tracked_email)
    verify = verify_user(client, tracked_email, signup["verificationCode"])
    yield {
        "email": tracked_email,
        "password": "Demo@123",
        "signup": signup,
        "verify": verify,
        "user_id": signup["user"]["id"],
    }
