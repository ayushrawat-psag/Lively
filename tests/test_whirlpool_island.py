"""Tests for Whirlpool Island APIs."""

from __future__ import annotations

import uuid

from tests.conftest import signup_user, verify_user

EXPECTED_ACTIVITY_COUNT = 19
ONE_MORE_SIGN = "one_more_sign"
STOP_STAR_FISH = "stop_star_fish"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_parent_and_child(client, email: str) -> tuple[str, str, str]:
    signup = signup_user(client, email)
    verify = verify_user(client, email, signup["verificationCode"])
    parent_token = verify["token"]

    child = client.post(
        "/api/v1/children",
        json={
            "name": "Alex",
            "dateOfBirth": "2015-06-20",
            "gender": "boy",
            "devices": ["this_device"],
            "pin": "6756",
        },
        headers=_auth_headers(parent_token),
    )
    assert child.status_code == 201, child.text
    child_id = child.json()["child"]["id"]

    login = client.post(
        "/api/v1/auth/child/login",
        json={"childId": child_id, "pin": "6756"},
    )
    assert login.status_code == 200, login.text
    child_token = login.json()["token"]
    return parent_token, child_token, child_id


def test_whirlpool_requires_auth(client) -> None:
    fake_id = str(uuid.uuid4())
    assert client.get(f"/api/v1/children/{fake_id}/whirlpool-island").status_code == 401
    assert (
        client.post(
            f"/api/v1/children/{fake_id}/whirlpool-island/activities/{ONE_MORE_SIGN}/complete",
            json={"completed": True},
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"/api/v1/children/{fake_id}/whirlpool-island/complete",
            json={"completed": True},
        ).status_code
        == 401
    )


def test_get_whirlpool_details_as_child(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)

    response = client.get(
        f"/api/v1/children/{child_id}/whirlpool-island",
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Whirlpool Island details fetched successfully"
    assert body["data"]["island"]["completed"] is False
    assert body["data"]["island"]["completedAt"] is None

    activities = body["data"]["activities"]
    assert len(activities) == EXPECTED_ACTIVITY_COUNT
    assert all(a["status"] == "available" for a in activities)

    by_id = {a["id"]: a for a in activities}
    assert ONE_MORE_SIGN in by_id
    script_activity = by_id[ONE_MORE_SIGN]
    assert script_activity["type"] == "script"
    assert script_activity["title"] == "Scenario: One more"
    assert script_activity["progress"] == {
        "completed": False,
        "attempts": 0,
        "completedAt": None,
    }
    assert "script" in script_activity
    assert script_activity["script"]["question"].startswith("Your parent asked")
    assert len(script_activity["script"]["answers"]) == 2
    assert script_activity["script"]["answers"][0]["id"] == "log-off-anyway"
    assert script_activity["script"]["answers"][0]["isCorrect"] is True

    habit_activity = by_id[STOP_STAR_FISH]
    assert habit_activity["type"] == "habit"
    assert habit_activity["title"] == "Screen-free sanctuary"
    assert "habit" in habit_activity
    assert "screen-free" in habit_activity["habit"]["description"].lower()
    assert habit_activity["habit"]["steps"][0]["id"] == "choose-room"
    assert habit_activity["habit"]["steps"][0]["options"][0]["id"] == "bedroom"


def test_get_whirlpool_details_as_parent(client, tracked_email) -> None:
    parent_token, _child_token, child_id = _create_parent_and_child(client, tracked_email)

    response = client.get(
        f"/api/v1/children/{child_id}/whirlpool-island",
        headers=_auth_headers(parent_token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True


def test_get_whirlpool_forbidden_for_other_child(client, tracked_email) -> None:
    _parent_token, child_token, _child_id = _create_parent_and_child(client, tracked_email)
    other_id = str(uuid.uuid4())

    response = client.get(
        f"/api/v1/children/{other_id}/whirlpool-island",
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 403
    assert response.json()["success"] is False


def test_complete_activity(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)

    response = client.post(
        f"/api/v1/children/{child_id}/whirlpool-island/activities/{ONE_MORE_SIGN}/complete",
        json={"completed": True, "attempts": 1},
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Activity completed successfully"
    data = body["data"]
    assert data["activityId"] == ONE_MORE_SIGN
    assert data["childId"] == child_id
    assert data["activityType"] == "script"
    assert data["isCorrect"] is True
    assert data["progress"]["completed"] is True
    assert data["progress"]["attempts"] == 1
    assert data["progress"]["completedAt"] is not None

    details = client.get(
        f"/api/v1/children/{child_id}/whirlpool-island",
        headers=_auth_headers(child_token),
    )
    assert details.status_code == 200
    activity = next(a for a in details.json()["data"]["activities"] if a["id"] == ONE_MORE_SIGN)
    assert activity["progress"]["completed"] is True
    assert activity["progress"]["attempts"] == 1


def test_complete_activity_is_correct_false(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)

    response = client.post(
        f"/api/v1/children/{child_id}/whirlpool-island/activities/{ONE_MORE_SIGN}/complete",
        json={"completed": False, "attempts": 2},
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["isCorrect"] is False
    assert data["progress"]["completed"] is False
    assert data["progress"]["attempts"] == 2
    assert data["progress"]["completedAt"] is None


def test_complete_activity_invalid_id(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)

    response = client.post(
        f"/api/v1/children/{child_id}/whirlpool-island/activities/not_a_real_activity/complete",
        json={"completed": True},
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_complete_island(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)

    response = client.post(
        f"/api/v1/children/{child_id}/whirlpool-island/complete",
        json={"completed": True},
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Whirlpool Island completed successfully"
    assert body["data"]["childId"] == child_id
    assert body["data"]["island"]["completed"] is True
    assert body["data"]["island"]["completedAt"] is not None

    details = client.get(
        f"/api/v1/children/{child_id}/whirlpool-island",
        headers=_auth_headers(child_token),
    )
    assert details.status_code == 200
    assert details.json()["data"]["island"]["completed"] is True
