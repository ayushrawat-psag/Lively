"""Tests for Habit Tracker APIs."""

from __future__ import annotations

import uuid

from tests.conftest import signup_user, verify_user


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


def _first_habit_and_activity(habit_tracker_payload: dict) -> tuple[str, str]:
    habit_catalog = habit_tracker_payload["habitCatalog"]
    assert habit_catalog
    assert "body_checkin" in habit_catalog
    first_habit = habit_catalog["body_checkin"]
    habit_id = first_habit["habitId"]
    activities = first_habit["activities"]
    assert activities
    first_activity = next(iter(activities.values()))
    return habit_id, first_activity["activityId"]


def test_habit_tracker_requires_auth(client) -> None:
    fake_id = str(uuid.uuid4())
    assert client.get(f"/api/v1/children/{fake_id}/habit-tracker").status_code == 401
    assert (
        client.post(
            f"/api/v1/children/{fake_id}/habit-tracker/complete",
            json={
                "habitId": "body_checkin",
                "defaultActivityId": "heart_beat",
                "date": "2026-08-03",
            },
        ).status_code
        == 401
    )


def test_get_habit_tracker_as_child(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)

    response = client.get(
        f"/api/v1/children/{child_id}/habit-tracker",
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Habit tracker fetched successfully"

    tracker = body["data"]["habitTracker"]
    assert tracker["child"]["childId"] == child_id
    assert "body_checkin" in tracker["habitCatalog"]
    assert tracker["habitCatalog"]["body_checkin"]["defaultActivityId"] == "heart_beat"
    assert tracker["habitCatalog"]["body_checkin"]["cardColor"] == "#89C27D"
    assert "focus" in tracker["habitCatalog"]


def test_get_habit_tracker_as_parent(client, tracked_email) -> None:
    parent_token, _child_token, child_id = _create_parent_and_child(client, tracked_email)

    response = client.get(
        f"/api/v1/children/{child_id}/habit-tracker",
        headers=_auth_headers(parent_token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True


def test_get_habit_tracker_forbidden_for_other_child(client, tracked_email) -> None:
    _parent_token, child_token, _child_id = _create_parent_and_child(client, tracked_email)
    other_id = str(uuid.uuid4())

    response = client.get(
        f"/api/v1/children/{other_id}/habit-tracker",
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 403
    assert response.json()["success"] is False


def test_complete_habit_rewards_and_idempotent(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)
    details = client.get(
        f"/api/v1/children/{child_id}/habit-tracker",
        headers=_auth_headers(child_token),
    )
    assert details.status_code == 200, details.text
    habit_id, activity_id = _first_habit_and_activity(details.json()["data"]["habitTracker"])

    payload = {
        "habitId": habit_id,
        "defaultActivityId": activity_id,
        "date": "2026-08-03",
    }
    response_one = client.post(
        f"/api/v1/children/{child_id}/habit-tracker/complete",
        json=payload,
        headers=_auth_headers(child_token),
    )
    assert response_one.status_code == 200, response_one.text
    data_one = response_one.json()["data"]
    assert data_one["habitId"] == habit_id
    assert data_one["childId"] == child_id
    assert data_one["completion"]["completedDate"] == "2026-08-03"
    assert data_one["reward"]["icon"] == "fries"
    assert data_one["reward"]["attemptedQuantity"] == 9
    assert data_one["reward"]["addedQuantity"] == 9
    assert data_one["inventory"]["fries"] == 9

    response_two = client.post(
        f"/api/v1/children/{child_id}/habit-tracker/complete",
        json=payload,
        headers=_auth_headers(child_token),
    )
    assert response_two.status_code == 200, response_two.text
    data_two = response_two.json()["data"]
    assert data_two["inventory"]["fries"] == 9
    assert data_two["reward"]["addedQuantity"] == 0


def test_complete_habit_streak_continues(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)
    payload_base = {
        "habitId": "body_checkin",
        "defaultActivityId": "heart_beat",
    }
    first = client.post(
        f"/api/v1/children/{child_id}/habit-tracker/complete",
        json={**payload_base, "date": "2026-08-01"},
        headers=_auth_headers(child_token),
    )
    assert first.status_code == 200, first.text

    second = client.post(
        f"/api/v1/children/{child_id}/habit-tracker/complete",
        json={**payload_base, "date": "2026-08-02"},
        headers=_auth_headers(child_token),
    )
    assert second.status_code == 200, second.text
    data = second.json()["data"]
    assert data["completion"]["streakContinued"] is True
    assert data["completion"]["streakReset"] is False
    assert data["reward"]["icon"] == "fries"
    assert data["inventory"]["fries"] == 9


def test_complete_habit_with_invalid_activity(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)

    response = client.post(
        f"/api/v1/children/{child_id}/habit-tracker/complete",
        json={
            "habitId": "body_checkin",
            "defaultActivityId": "not_a_real_activity",
            "date": "2026-08-03",
        },
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 400
    assert response.json()["success"] is False
