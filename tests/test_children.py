"""Tests for /api/v1/children CRUD."""

from __future__ import annotations

import uuid

from tests.conftest import signup_user, verify_user


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _verified_token(client, email: str) -> str:
    signup = signup_user(client, email)
    verify = verify_user(client, email, signup["verificationCode"])
    return verify["token"]


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


def test_children_require_auth(client) -> None:
    assert client.get("/api/v1/children").status_code == 401
    assert client.post("/api/v1/children", json=_child_payload()).status_code == 401
    fake_id = str(uuid.uuid4())
    assert client.get(f"/api/v1/children/{fake_id}").status_code == 401
    assert client.patch(f"/api/v1/children/{fake_id}", json={"name": "Sam"}).status_code == 401
    assert (
        client.patch(f"/api/v1/children/{fake_id}/app-state", json={"onBoarding": True}).status_code
        == 401
    )
    assert client.delete(f"/api/v1/children/{fake_id}").status_code == 401


def test_list_empty(client, tracked_email) -> None:
    token = _verified_token(client, tracked_email)
    response = client.get("/api/v1/children", headers=_auth_headers(token))
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "No children found"
    assert body["children"] == []


def test_create_child_success(client, tracked_email) -> None:
    token = _verified_token(client, tracked_email)
    response = client.post(
        "/api/v1/children",
        json=_child_payload(),
        headers=_auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Child created successfully"
    child = body["child"]
    assert child["name"] == "Alex"
    assert child["dateOfBirth"] == "2015-06-20"
    assert child["gender"] == "boy"
    assert child["devices"] == ["this_device", "shared_device"]
    assert child["pin"] == "6756"
    assert child["onBoarding"] is False
    assert child["childAppTour"] is False
    assert "progress" not in child
    uuid.UUID(child["id"])


def test_list_and_get_child(client, tracked_email) -> None:
    token = _verified_token(client, tracked_email)
    created = client.post(
        "/api/v1/children",
        json=_child_payload(),
        headers=_auth_headers(token),
    ).json()["child"]

    listed = client.get("/api/v1/children", headers=_auth_headers(token))
    assert listed.status_code == 200
    list_body = listed.json()
    assert list_body["message"] == "Children fetched successfully"
    assert len(list_body["children"]) == 1
    assert list_body["children"][0]["id"] == created["id"]
    assert "pin" not in list_body["children"][0]

    detail = client.get(
        f"/api/v1/children/{created['id']}",
        headers=_auth_headers(token),
    )
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["message"] == "Child fetched successfully"
    assert detail_body["child"]["progress"] == {
        "completedActivities": 0,
        "currentLevel": None,
    }
    assert "pin" not in detail_body["child"]


def test_patch_child(client, tracked_email) -> None:
    token = _verified_token(client, tracked_email)
    created = client.post(
        "/api/v1/children",
        json=_child_payload(),
        headers=_auth_headers(token),
    ).json()["child"]

    response = client.patch(
        f"/api/v1/children/{created['id']}",
        json={"name": "Alexander"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Child updated successfully"
    assert body["child"]["name"] == "Alexander"
    assert body["child"]["gender"] == "boy"
    assert "pin" not in body["child"]


def test_delete_child_soft(client, tracked_email) -> None:
    token = _verified_token(client, tracked_email)
    created = client.post(
        "/api/v1/children",
        json=_child_payload(),
        headers=_auth_headers(token),
    ).json()["child"]

    deleted = client.delete(
        f"/api/v1/children/{created['id']}",
        headers=_auth_headers(token),
    )
    assert deleted.status_code == 200
    body = deleted.json()
    assert body["success"] is True
    assert body["message"] == "Child removed successfully"
    assert body["childId"] == created["id"]

    missing = client.get(
        f"/api/v1/children/{created['id']}",
        headers=_auth_headers(token),
    )
    assert missing.status_code == 404
    assert missing.json()["message"] == "Child not found"


def test_child_not_found_for_other_parent(client, tracked_email) -> None:
    token_a = _verified_token(client, tracked_email)
    created = client.post(
        "/api/v1/children",
        json=_child_payload(),
        headers=_auth_headers(token_a),
    ).json()["child"]

    other_email = f"other.{uuid.uuid4().hex[:10]}@example.com"
    try:
        token_b = _verified_token(client, other_email)
        response = client.get(
            f"/api/v1/children/{created['id']}",
            headers=_auth_headers(token_b),
        )
        assert response.status_code == 404
    finally:
        from tests.conftest import cleanup_user_by_email

        cleanup_user_by_email(other_email)


def test_invalid_child_id(client, tracked_email) -> None:
    token = _verified_token(client, tracked_email)
    response = client.get("/api/v1/children/not-a-uuid", headers=_auth_headers(token))
    assert response.status_code == 400
    assert response.json()["message"] == "Invalid child id"


def test_max_children_limit(client, tracked_email) -> None:
    token = _verified_token(client, tracked_email)
    headers = _auth_headers(token)
    for i in range(6):
        response = client.post(
            "/api/v1/children",
            json=_child_payload(name=f"Kid{i}", pin=f"{1000 + i}"),
            headers=headers,
        )
        assert response.status_code == 201, response.text

    blocked = client.post(
        "/api/v1/children",
        json=_child_payload(name="Extra", pin="9999"),
        headers=headers,
    )
    assert blocked.status_code == 400
    assert "Maximum" in blocked.json()["message"]


def _create_child(client, parent_token: str, **overrides) -> dict:
    response = client.post(
        "/api/v1/children",
        json=_child_payload(**overrides),
        headers=_auth_headers(parent_token),
    )
    assert response.status_code == 201
    return response.json()["child"]


def _child_login_token(client, child_id: str, pin: str = "6756") -> str:
    response = client.post(
        "/api/v1/auth/child/login",
        json={"childId": child_id, "pin": pin},
    )
    assert response.status_code == 200
    return response.json()["token"]


def test_parent_updates_child_app_state(client, tracked_email) -> None:
    token = _verified_token(client, tracked_email)
    child = _create_child(client, token)

    response = client.patch(
        f"/api/v1/children/{child['id']}/app-state",
        json={"onBoarding": True, "childAppTour": True},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Child app state updated successfully"
    assert body["child"]["onBoarding"] is True
    assert body["child"]["childAppTour"] is True


def test_child_updates_own_app_state(client, tracked_email) -> None:
    parent_token = _verified_token(client, tracked_email)
    child = _create_child(client, parent_token)
    child_token = _child_login_token(client, child["id"])

    response = client.patch(
        f"/api/v1/children/{child['id']}/app-state",
        json={"childAppTour": True},
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["child"]["childAppTour"] is True
    assert body["child"]["onBoarding"] is False


def test_child_cannot_update_other_child_app_state(client, tracked_email) -> None:
    parent_token = _verified_token(client, tracked_email)
    child_a = _create_child(client, parent_token, name="Alex", pin="6756")
    child_b = _create_child(client, parent_token, name="Sam", pin="1234")
    child_token = _child_login_token(client, child_a["id"])

    response = client.patch(
        f"/api/v1/children/{child_b['id']}/app-state",
        json={"onBoarding": True},
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 403
    assert response.json()["message"] == "Forbidden"


def test_update_child_app_state_requires_field(client, tracked_email) -> None:
    token = _verified_token(client, tracked_email)
    child = _create_child(client, token)

    response = client.patch(
        f"/api/v1/children/{child['id']}/app-state",
        json={},
        headers=_auth_headers(token),
    )
    assert response.status_code == 400
