"""Tests for POST /api/v1/promo-code/validate."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.promo_code import PromoCode, PromoCodeRedemption
from tests.conftest import signup_user, verify_user


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_promo(
    *,
    code: str,
    discount_percent: int = 15,
    is_active: bool = True,
    starts_at: datetime | None = None,
    expires_at: datetime | None = None,
    max_redemptions: int | None = None,
    max_redemptions_per_user: int | None = 1,
) -> PromoCode:
    db = SessionLocal()
    try:
        promo = PromoCode(
            code=code.upper(),
            discount_percent=discount_percent,
            is_active=is_active,
            starts_at=starts_at,
            expires_at=expires_at,
            max_redemptions=max_redemptions,
            max_redemptions_per_user=max_redemptions_per_user,
        )
        db.add(promo)
        db.commit()
        db.refresh(promo)
        # Detach for use outside session
        db.expunge(promo)
        return promo
    finally:
        db.close()


def _delete_promo(code: str) -> None:
    db = SessionLocal()
    try:
        promo = db.scalar(select(PromoCode).where(PromoCode.code == code.upper()))
        if promo:
            db.execute(
                delete(PromoCodeRedemption).where(PromoCodeRedemption.promo_code_id == promo.id)
            )
            db.delete(promo)
            db.commit()
    finally:
        db.close()


def _add_redemption(promo_id, user_id) -> None:
    db = SessionLocal()
    try:
        db.add(
            PromoCodeRedemption(
                promo_code_id=promo_id if isinstance(promo_id, uuid.UUID) else uuid.UUID(str(promo_id)),
                user_id=user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id)),
                redeemed_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    finally:
        db.close()


def _verified_token(client, email: str) -> tuple[str, str]:
    signup = signup_user(client, email)
    verify = verify_user(client, email, signup["verificationCode"])
    return verify["token"], signup["user"]["id"]


def test_validate_requires_auth(client) -> None:
    response = client.post("/api/v1/promo-code/validate", json={"code": "LIVELY20"})
    assert response.status_code == 401


def test_validate_seeded_lively20_success(client, tracked_email) -> None:
    token, _ = _verified_token(client, tracked_email)
    response = client.post(
        "/api/v1/promo-code/validate",
        json={"code": "LIVELY20"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["valid"] is True
    assert body["code"] == "LIVELY20"
    assert body["discountPercent"] == 20
    assert body["message"] == "Promo code applied"


def test_validate_case_insensitive(client, tracked_email) -> None:
    token, _ = _verified_token(client, tracked_email)
    response = client.post(
        "/api/v1/promo-code/validate",
        json={"code": "lively20"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["code"] == "LIVELY20"
    assert body["discountPercent"] == 20


def test_validate_unknown_code(client, tracked_email) -> None:
    token, _ = _verified_token(client, tracked_email)
    response = client.post(
        "/api/v1/promo-code/validate",
        json={"code": "DOESNOTEXIST"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["valid"] is False
    assert body["discountPercent"] is None
    assert body["message"] == "Invalid or expired promo code"


def test_validate_inactive_code(client, tracked_email) -> None:
    code = f"INACTIVE{uuid.uuid4().hex[:6].upper()}"
    _create_promo(code=code, is_active=False)
    try:
        token, _ = _verified_token(client, tracked_email)
        response = client.post(
            "/api/v1/promo-code/validate",
            json={"code": code},
            headers=_auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["valid"] is False
    finally:
        _delete_promo(code)


def test_validate_expired_code(client, tracked_email) -> None:
    code = f"EXPIRED{uuid.uuid4().hex[:6].upper()}"
    _create_promo(
        code=code,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    try:
        token, _ = _verified_token(client, tracked_email)
        response = client.post(
            "/api/v1/promo-code/validate",
            json={"code": code},
            headers=_auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["valid"] is False
    finally:
        _delete_promo(code)


def test_validate_not_yet_started(client, tracked_email) -> None:
    code = f"FUTURE{uuid.uuid4().hex[:6].upper()}"
    _create_promo(
        code=code,
        starts_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    try:
        token, _ = _verified_token(client, tracked_email)
        response = client.post(
            "/api/v1/promo-code/validate",
            json={"code": code},
            headers=_auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["valid"] is False
    finally:
        _delete_promo(code)


def test_validate_global_redemption_limit(client, tracked_email) -> None:
    code = f"GLOBAL{uuid.uuid4().hex[:6].upper()}"
    promo = _create_promo(code=code, max_redemptions=1, max_redemptions_per_user=None)
    try:
        token, user_id = _verified_token(client, tracked_email)
        _add_redemption(promo.id, user_id)

        response = client.post(
            "/api/v1/promo-code/validate",
            json={"code": code},
            headers=_auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["valid"] is False
    finally:
        _delete_promo(code)


def test_validate_per_user_redemption_limit(client, tracked_email) -> None:
    code = f"PERUSER{uuid.uuid4().hex[:6].upper()}"
    promo = _create_promo(code=code, max_redemptions_per_user=1)
    try:
        token, user_id = _verified_token(client, tracked_email)
        _add_redemption(promo.id, user_id)

        response = client.post(
            "/api/v1/promo-code/validate",
            json={"code": code},
            headers=_auth_headers(token),
        )
        assert response.status_code == 200
        assert response.json()["valid"] is False
    finally:
        _delete_promo(code)
