"""Tests for Fridge Inventory APIs."""

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


def test_fridge_inventory_requires_auth(client) -> None:
    fake_id = str(uuid.uuid4())
    assert client.get(f"/api/v1/children/{fake_id}/fridge-inventory").status_code == 401


def test_get_fridge_inventory_empty(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)

    response = client.get(
        f"/api/v1/children/{child_id}/fridge-inventory",
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["data"]["childId"] == child_id
    habits = {item["habitId"]: item["inventory"] for item in body["data"]["habits"]}
    assert "body_checkin" in habits
    assert habits["body_checkin"] == {"fries": 0, "mussels": 0, "sardini": 0}


def test_fridge_inventory_after_complete_and_consume(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)

    complete = client.post(
        f"/api/v1/children/{child_id}/habit-tracker/complete",
        json={
            "habitId": "body_checkin",
            "defaultActivityId": "heart_beat",
            "date": "2026-08-03",
        },
        headers=_auth_headers(child_token),
    )
    assert complete.status_code == 200, complete.text

    one = client.get(
        f"/api/v1/children/{child_id}/fridge-inventory/habits/body_checkin",
        headers=_auth_headers(child_token),
    )
    assert one.status_code == 200, one.text
    assert one.json()["data"]["inventory"]["fries"] == 9

    consume = client.patch(
        f"/api/v1/children/{child_id}/fridge-inventory/habits/body_checkin/consume",
        json={"rewardIcon": "fries", "quantity": 1},
        headers=_auth_headers(child_token),
    )
    assert consume.status_code == 200, consume.text
    assert consume.json()["data"]["inventory"]["fries"] == 8
    assert consume.json()["data"]["consumed"]["quantity"] == 1


def test_fridge_consume_insufficient(client, tracked_email) -> None:
    _parent_token, child_token, child_id = _create_parent_and_child(client, tracked_email)

    response = client.patch(
        f"/api/v1/children/{child_id}/fridge-inventory/habits/body_checkin/consume",
        json={"rewardIcon": "fries", "quantity": 2},
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INSUFFICIENT_INVENTORY"
