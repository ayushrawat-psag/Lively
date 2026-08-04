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
    first_habit = next(iter(habit_catalog.values()))
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
                "habitId": str(uuid.uuid4()),
                "defaultActivityId": str(uuid.uuid4()),
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
    assert isinstance(tracker["habitCatalog"], dict)
    assert len(tracker["habitCatalog"]) >= 1
    assert isinstance(tracker["child"]["habits"], list)


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


def test_complete_habit_and_avoid_duplicate_dates(client, tracked_email) -> None:
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
    assert data_one["defaultActivityId"] == activity_id
    assert data_one["completedDates"].count("2026-08-03") == 1

    response_two = client.post(
        f"/api/v1/children/{child_id}/habit-tracker/complete",
        json=payload,
        headers=_auth_headers(child_token),
    )
    assert response_two.status_code == 200, response_two.text
    data_two = response_two.json()["data"]
    assert data_two["completedDates"].count("2026-08-03") == 1


def test_complete_habit_with_invalid_activity(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)
    details = client.get(
        f"/api/v1/children/{child_id}/habit-tracker",
        headers=_auth_headers(child_token),
    )
    assert details.status_code == 200, details.text
    habit_id, _activity_id = _first_habit_and_activity(details.json()["data"]["habitTracker"])

    response = client.post(
        f"/api/v1/children/{child_id}/habit-tracker/complete",
        json={
            "habitId": habit_id,
            "defaultActivityId": str(uuid.uuid4()),
            "date": "2026-08-03",
        },
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 400
    assert response.json()["success"] is False
