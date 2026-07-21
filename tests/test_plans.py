def test_get_plans_success(client) -> None:
    response = client.get("/api/v1/plans")
    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert isinstance(body["plans"], list)
    assert len(body["plans"]) == 2


def test_get_plans_contract_values(client) -> None:
    response = client.get("/api/v1/plans")
    assert response.status_code == 200
    body = response.json()

    monthly = body["plans"][0]
    yearly = body["plans"][1]

    assert {
        "id",
        "name",
        "price",
        "billingInterval",
        "maxParents",
        "maxChildren",
    }.issubset(monthly.keys())
    assert {
        "id",
        "name",
        "price",
        "billingInterval",
        "maxParents",
        "maxChildren",
    }.issubset(yearly.keys())

    assert monthly == {
        "id": "monthly",
        "name": "Monthly",
        "price": 15.99,
        "billingInterval": "month",
        "maxParents": 1,
        "maxChildren": 6,
    }
    assert yearly == {
        "id": "yearly",
        "name": "Yearly",
        "price": 149.49,
        "billingInterval": "year",
        "maxParents": 1,
        "maxChildren": 6,
    }
