"""Tests for GET /api/v1/comic catalog."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.comic_page import ComicPage
from app.models.enums import ContentStatus, SimulationType
from app.models.island import Island
from app.models.simulation import Simulation
from tests.conftest import SessionLocal, signup_user, verify_user


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_parent_and_child(client, email: str) -> tuple[str, str]:
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
    assert child.status_code == 201
    child_id = child.json()["child"]["id"]

    login = client.post(
        "/api/v1/auth/child/login",
        json={"childId": child_id, "pin": "6756"},
    )
    assert login.status_code == 200
    child_token = login.json()["token"]
    return parent_token, child_token


def _create_island(
    *,
    island_name: str | None = None,
    comic_number: int | None = None,
    images_per_page: int = 1,
    active: bool = True,
) -> Island:
    db = SessionLocal()
    try:
        island = Island(
            island_name=island_name or f"Island-{uuid.uuid4().hex[:8]}",
            status=ContentStatus.ACTIVE if active else ContentStatus.INACTIVE,
            display_order=0,
            images_per_page=images_per_page,
        )
        if comic_number is not None:
            island.comic_number = comic_number
        db.add(island)
        db.flush()

        simulation = Simulation(
            island_id=island.id,
            simulation_name=f"Sim-{uuid.uuid4().hex[:8]}",
            simulation_type=SimulationType.SCRIPT,
            status=ContentStatus.ACTIVE,
            display_order=1,
        )
        db.add(simulation)
        db.commit()
        db.refresh(island)
        return island
    finally:
        db.close()


def _add_comic_page(
    *,
    island_id: uuid.UUID,
    image_url: str,
    order: int,
    status: ContentStatus,
) -> None:
    db = SessionLocal()
    try:
        page = ComicPage(
            island_id=island_id,
            image_url=image_url,
            display_order=order,
            status=status,
        )
        db.add(page)
        db.commit()
    finally:
        db.close()


def _next_free_comic_number() -> int:
    db = SessionLocal()
    try:
        max_number = db.scalar(select(Island.comic_number).order_by(Island.comic_number.desc()))
        return 0 if max_number is None else int(max_number) + 1
    finally:
        db.close()


def test_get_comic_requires_auth(client) -> None:
    response = client.get("/api/v1/comic")
    assert response.status_code == 401


def test_get_comic_forbidden_for_parent(client, tracked_email) -> None:
    parent_token, _ = _create_parent_and_child(client, tracked_email)

    response = client.get("/api/v1/comic", headers=_auth_headers(parent_token))
    assert response.status_code == 403
    assert response.json()["message"] == "Forbidden"


def test_get_comic_empty_catalog(client, tracked_email) -> None:
    _, child_token = _create_parent_and_child(client, tracked_email)
    # Island without active pages must not appear
    island = _create_island(comic_number=_next_free_comic_number())
    _add_comic_page(
        island_id=island.id,
        image_url="https://cdn.example.com/comics/inactive.png",
        order=1,
        status=ContentStatus.INACTIVE,
    )

    response = client.get("/api/v1/comic", headers=_auth_headers(child_token))
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["islands"], list)
    assert all(item["islandId"] != island.comic_number for item in body["islands"])


def test_get_comic_returns_all_islands_nested_contract(client, tracked_email) -> None:
    _, child_token = _create_parent_and_child(client, tracked_email)
    first_number = _next_free_comic_number()
    second_number = first_number + 1

    whirlpool = _create_island(
        island_name=f"Whirlpool-{uuid.uuid4().hex[:6]}",
        comic_number=first_number,
        images_per_page=2,
    )
    other = _create_island(island_name=f"Lagoon-{uuid.uuid4().hex[:6]}", comic_number=second_number)

    _add_comic_page(
        island_id=whirlpool.id,
        image_url="https://cdn.example.com/comics/w-2.png",
        order=2,
        status=ContentStatus.ACTIVE,
    )
    _add_comic_page(
        island_id=whirlpool.id,
        image_url="https://cdn.example.com/comics/w-inactive.png",
        order=3,
        status=ContentStatus.INACTIVE,
    )
    _add_comic_page(
        island_id=whirlpool.id,
        image_url="https://cdn.example.com/comics/w-1.png",
        order=1,
        status=ContentStatus.ACTIVE,
    )
    _add_comic_page(
        island_id=other.id,
        image_url="https://cdn.example.com/comics/l-1.png",
        order=1,
        status=ContentStatus.ACTIVE,
    )

    response = client.get("/api/v1/comic", headers=_auth_headers(child_token))
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    by_id = {island["islandId"]: island for island in body["islands"]}
    assert first_number in by_id
    assert second_number in by_id

    first = by_id[first_number]
    second = by_id[second_number]
    assert first["islandName"] == whirlpool.island_name
    assert first["totalPages"] == 2
    assert first["imagesPerPage"] == 2
    assert second["imagesPerPage"] == 1
    assert [page["order"] for page in first["pages"]] == [1, 2]
    assert first["pages"][0]["imageUrl"].endswith("w-1.png")
    assert set(first["pages"][0].keys()) == {"id", "imageUrl", "order"}

    assert second["totalPages"] == 1
    assert second["pages"][0]["imageUrl"].endswith("l-1.png")

    # Catalog is ordered by comic_number ascending
    our_islands = [i for i in body["islands"] if i["islandId"] in {first_number, second_number}]
    assert [i["islandId"] for i in our_islands] == [first_number, second_number]


def test_get_comic_filters_by_island_id(client, tracked_email) -> None:
    _, child_token = _create_parent_and_child(client, tracked_email)
    first_number = _next_free_comic_number()
    second_number = first_number + 1

    first = _create_island(island_name=f"Alpha-{uuid.uuid4().hex[:6]}", comic_number=first_number)
    second = _create_island(island_name=f"Beta-{uuid.uuid4().hex[:6]}", comic_number=second_number)
    _add_comic_page(
        island_id=first.id,
        image_url="https://cdn.example.com/comics/a.png",
        order=1,
        status=ContentStatus.ACTIVE,
    )
    _add_comic_page(
        island_id=second.id,
        image_url="https://cdn.example.com/comics/b.png",
        order=1,
        status=ContentStatus.ACTIVE,
    )

    response = client.get(
        f"/api/v1/comic?islandId={second_number}",
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["islands"]) == 1
    assert body["islands"][0]["islandId"] == second_number
    assert body["islands"][0]["pages"][0]["imageUrl"].endswith("b.png")


def test_get_comic_island_id_zero_supported(client, tracked_email) -> None:
    _, child_token = _create_parent_and_child(client, tracked_email)

    db = SessionLocal()
    try:
        existing_zero = db.scalar(select(Island).where(Island.comic_number == 0))
        if existing_zero is None:
            island = Island(
                island_name=f"Whirlpool-{uuid.uuid4().hex[:6]}",
                status=ContentStatus.ACTIVE,
                display_order=0,
                comic_number=0,
            )
            db.add(island)
            db.flush()
            db.add(
                Simulation(
                    island_id=island.id,
                    simulation_name=f"Sim-{uuid.uuid4().hex[:8]}",
                    simulation_type=SimulationType.SCRIPT,
                    status=ContentStatus.ACTIVE,
                    display_order=1,
                )
            )
            db.commit()
            db.refresh(island)
            island_id = island.id
            next_order = 1
        else:
            island_id = existing_zero.id
            if existing_zero.status != ContentStatus.ACTIVE:
                existing_zero.status = ContentStatus.ACTIVE
                db.commit()
            max_order = db.scalar(
                select(ComicPage.display_order)
                .where(ComicPage.island_id == island_id)
                .order_by(ComicPage.display_order.desc())
            )
            next_order = 1 if max_order is None else int(max_order) + 1
    finally:
        db.close()

    unique_url = f"https://cdn.example.com/comics/zero-{uuid.uuid4().hex[:8]}.png"
    _add_comic_page(
        island_id=island_id,
        image_url=unique_url,
        order=next_order,
        status=ContentStatus.ACTIVE,
    )

    response = client.get("/api/v1/comic?islandId=0", headers=_auth_headers(child_token))
    assert response.status_code == 200
    body = response.json()
    assert len(body["islands"]) == 1
    assert body["islands"][0]["islandId"] == 0
    assert any(page["imageUrl"] == unique_url for page in body["islands"][0]["pages"])


def test_get_comic_not_found_for_unknown_island(client, tracked_email) -> None:
    _, child_token = _create_parent_and_child(client, tracked_email)
    unknown = _next_free_comic_number() + 1000

    response = client.get(
        f"/api/v1/comic?islandId={unknown}",
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Island not found"


def test_get_comic_not_found_when_island_has_no_active_pages(client, tracked_email) -> None:
    _, child_token = _create_parent_and_child(client, tracked_email)
    comic_number = _next_free_comic_number()
    island = _create_island(comic_number=comic_number)
    _add_comic_page(
        island_id=island.id,
        image_url="https://cdn.example.com/comics/inactive-only.png",
        order=1,
        status=ContentStatus.INACTIVE,
    )

    response = client.get(
        f"/api/v1/comic?islandId={comic_number}",
        headers=_auth_headers(child_token),
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Comic not found"


def test_get_comic_invalid_negative_island_id(client, tracked_email) -> None:
    _, child_token = _create_parent_and_child(client, tracked_email)

    response = client.get("/api/v1/comic?islandId=-1", headers=_auth_headers(child_token))
    assert response.status_code == 400
    assert response.json()["message"] == "Invalid island id"


def test_get_comic_reflects_reordered_pages(client, tracked_email) -> None:
    _, child_token = _create_parent_and_child(client, tracked_email)
    comic_number = _next_free_comic_number()
    island = _create_island(comic_number=comic_number)
    page_one_url = "https://cdn.example.com/comics/page-a.png"
    page_two_url = "https://cdn.example.com/comics/page-b.png"
    _add_comic_page(
        island_id=island.id,
        image_url=page_one_url,
        order=1,
        status=ContentStatus.ACTIVE,
    )
    _add_comic_page(
        island_id=island.id,
        image_url=page_two_url,
        order=2,
        status=ContentStatus.ACTIVE,
    )

    first_response = client.get(
        f"/api/v1/comic?islandId={comic_number}",
        headers=_auth_headers(child_token),
    )
    assert first_response.status_code == 200
    assert [page["imageUrl"] for page in first_response.json()["islands"][0]["pages"]] == [
        page_one_url,
        page_two_url,
    ]

    db = SessionLocal()
    try:
        page_a = db.scalar(
            select(ComicPage).where(
                ComicPage.island_id == island.id,
                ComicPage.display_order == 1,
            )
        )
        page_b = db.scalar(
            select(ComicPage).where(
                ComicPage.island_id == island.id,
                ComicPage.display_order == 2,
            )
        )
        assert page_a is not None
        assert page_b is not None
        page_a.display_order = 99
        db.flush()
        page_b.display_order = 1
        db.flush()
        page_a.display_order = 2
        db.commit()
    finally:
        db.close()

    second_response = client.get(
        f"/api/v1/comic?islandId={comic_number}",
        headers=_auth_headers(child_token),
    )
    assert second_response.status_code == 200
    assert [page["imageUrl"] for page in second_response.json()["islands"][0]["pages"]] == [
        page_two_url,
        page_one_url,
    ]
    assert second_response.json()["islands"][0]["totalPages"] == 2
