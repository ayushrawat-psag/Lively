"""Tests for child invite code verify and PIN login."""

from __future__ import annotations

import uuid

from tests.conftest import signup_user, verify_user


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _verified_parent(client, email: str) -> tuple[str, dict]:
    signup = signup_user(client, email)
    verify = verify_user(client, email, signup["verificationCode"])
    return verify["token"], verify


def _child_payload(**overrides) -> dict:
    payload = {
        "name": "Alex",
        "dateOfBirth": "2015-06-20",
        "gender": "boy",
        "devices": ["this_device", "shared_device"],
        "pin": "6756",
    }
    payload.update(overrides)
    return payload


def test_verify_invite_code_success(client, tracked_email) -> None:
    token, verify = _verified_parent(client, tracked_email)
    invite_code = verify["user"]["inviteCode"]

    created = client.post(
        "/api/v1/children",
        json=_child_payload(),
        headers=_auth_headers(token),
    )
    assert created.status_code == 201
    child_id = created.json()["child"]["id"]

    response = client.post(
        "/api/v1/auth/child/verify-invite-code",
        json={"inviteCode": invite_code},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Invite code verified"
    assert body["requiresPin"] is True
    assert body["user"]["email"] == tracked_email
    assert body["user"]["emailVerified"] is True
    assert body["subscription"] is None
    assert len(body["children"]) == 1
    assert body["children"][0]["id"] == child_id
    assert body["children"][0]["name"] == "Alex"
    assert "pin" not in body["children"][0]


def test_verify_invite_code_case_insensitive(client, tracked_email) -> None:
    _, verify = _verified_parent(client, tracked_email)
    invite_code = verify["user"]["inviteCode"]

    response = client.post(
        "/api/v1/auth/child/verify-invite-code",
        json={"inviteCode": invite_code.lower()},
    )
    assert response.status_code == 200
    assert response.json()["user"]["inviteCode"] == invite_code


def test_verify_invite_code_unknown(client) -> None:
    response = client.post(
        "/api/v1/auth/child/verify-invite-code",
        json={"inviteCode": "ZZZZZZ"},
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Invalid invite code"


def test_verify_invite_code_missing(client) -> None:
    response = client.post("/api/v1/auth/child/verify-invite-code", json={})
    assert response.status_code == 400


def test_child_login_success(client, tracked_email) -> None:
    token, verify = _verified_parent(client, tracked_email)
    created = client.post(
        "/api/v1/children",
        json=_child_payload(),
        headers=_auth_headers(token),
    ).json()["child"]
    child_id = created["id"]

    response = client.post(
        "/api/v1/auth/child/login",
        json={"childId": child_id, "pin": "6756"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Child login successful"
    assert body["token"]
    assert body["child"]["id"] == child_id
    assert body["child"]["name"] == "Alex"
    assert body["child"]["onBoarding"] is False
    assert body["child"]["childAppTour"] is False
    assert "pin" not in body["child"]

    from app.core.security import decode_access_token

    claims = decode_access_token(body["token"])
    assert claims is not None
    assert claims["sub"] == child_id
    assert claims["actor"] == "child"
    assert claims["user_type"] == "CHILD"


def test_child_login_wrong_pin(client, tracked_email) -> None:
    token, _ = _verified_parent(client, tracked_email)
    child_id = client.post(
        "/api/v1/children",
        json=_child_payload(),
        headers=_auth_headers(token),
    ).json()["child"]["id"]

    response = client.post(
        "/api/v1/auth/child/login",
        json={"childId": child_id, "pin": "0000"},
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Invalid PIN code"


def test_child_login_missing_pin(client, tracked_email) -> None:
    token, _ = _verified_parent(client, tracked_email)
    child_id = client.post(
        "/api/v1/children",
        json=_child_payload(),
        headers=_auth_headers(token),
    ).json()["child"]["id"]

    response = client.post(
        "/api/v1/auth/child/login",
        json={"childId": child_id, "pin": ""},
    )
    assert response.status_code == 400


def test_child_login_not_found(client) -> None:
    response = client.post(
        "/api/v1/auth/child/login",
        json={"childId": str(uuid.uuid4()), "pin": "6756"},
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Child not found"


def test_child_login_invalid_child_id(client) -> None:
    response = client.post(
        "/api/v1/auth/child/login",
        json={"childId": "not-a-uuid", "pin": "6756"},
    )
    assert response.status_code == 400
    assert response.json()["message"] == "Invalid child id"


def test_child_login_deleted_child(client, tracked_email) -> None:
    token, _ = _verified_parent(client, tracked_email)
    child_id = client.post(
        "/api/v1/children",
        json=_child_payload(),
        headers=_auth_headers(token),
    ).json()["child"]["id"]

    deleted = client.delete(
        f"/api/v1/children/{child_id}",
        headers=_auth_headers(token),
    )
    assert deleted.status_code == 200

    response = client.post(
        "/api/v1/auth/child/login",
        json={"childId": child_id, "pin": "6756"},
    )
    assert response.status_code == 404
