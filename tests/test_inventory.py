from concurrent.futures import ThreadPoolExecutor
import os
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlmodel import select

from services.models import Ingredient
from services.routers.inventory import get_product

PRODUCT = {
    "name": "Carne de prueba",
    "sku": "MEAT-TEST-001",
    "unit": "kg",
    "category": "meat",
    "country": "CO",
}


def create_product(client, headers, sku=None):
    sku = sku or f"MEAT-TEST-{uuid4()}"
    payload = {**PRODUCT, "sku": sku}
    response = client.post("/inventory/products", headers=headers, json=payload)
    return response


def test_inventory_reads_require_valid_bearer_token(client, auth_headers):
    invalid_headers = {"Authorization": "Bearer invalid-token"}
    endpoints = [
        ("GET", "/inventory/products", None),
        ("GET", "/inventory/products/999999", None),
        ("GET", "/inventory/orders", None),
        ("POST", "/inventory/products", PRODUCT),
        (
            "POST",
            "/inventory/orders/inbound",
            {"ingredient_id": 1, "quantity": 1, "supplier_name": "Supplier", "location_id": 1},
        ),
        (
            "POST",
            "/inventory/orders/outbound",
            {"ingredient_id": 1, "quantity": 1, "reason": "consumption", "location_id": 1},
        ),
    ]

    for method, path, payload in endpoints:
        assert client.request(method, path, json=payload).status_code == 401
        assert client.request(method, path, headers=invalid_headers, json=payload).status_code == 401

    headers, _ = auth_headers
    assert client.get("/inventory/products", headers=headers).status_code == 200
    assert client.get("/inventory/orders", headers=headers).status_code == 200
    assert client.get("/inventory/products/999999", headers=headers).status_code == 404


def test_regular_user_and_admin_can_access_inventory(client, user_factory):
    user = user_factory(email="inventory-user@example.com")
    admin = user_factory(email="inventory-admin@example.com", role="admin")
    user_login = client.post("/auth/login", json={"email": user["email"], "password": "correct-password"})
    admin_login = client.post("/auth/login", json={"email": admin["email"], "password": "correct-password"})
    user_headers = {"Authorization": f"Bearer {user_login.json()['access_token']}"}
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    assert create_product(client, user_headers).status_code == 200
    assert client.get("/inventory/products", headers=admin_headers).status_code == 200


def test_product_creation_validation_duplicate_and_not_found(client, auth_headers):
    headers, _ = auth_headers
    sku = f"MEAT-DUP-{uuid4()}"
    created = create_product(client, headers, sku)
    assert created.status_code == 200
    product_id = created.json()["id"]

    duplicate = create_product(client, headers, sku)
    assert duplicate.status_code == 409
    assert client.get(f"/inventory/products/{product_id}", headers=headers).status_code == 200
    assert client.get("/inventory/products/999999", headers=headers).status_code == 404

    for field, value in (("name", "  "), ("sku", ""), ("unit", " "), ("country", "CA"), ("category", "unknown")):
        invalid = client.post("/inventory/products", headers=headers, json={**PRODUCT, field: value})
        assert invalid.status_code == 422, (field, invalid.text)


def test_orders_validate_fields_and_calculate_stock(client, auth_headers):
    headers, user = auth_headers
    product = create_product(client, headers)
    product_id = product.json()["id"]

    invalid_location = client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={"ingredient_id": product_id, "quantity": 10, "supplier_name": "Supplier", "location_id": 15},
    )
    assert invalid_location.status_code == 422

    inbound = client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={"ingredient_id": product_id, "quantity": 10, "supplier_name": "  Supplier  ", "location_id": 1},
    )
    assert inbound.status_code == 200
    assert inbound.json()["supplier_name"] == "Supplier"
    assert inbound.json()["user_uuid"] == user["id"]

    outbound = client.post(
        "/inventory/orders/outbound",
        headers=headers,
        json={"ingredient_id": product_id, "quantity": 4, "reason": "consumption", "location_id": 1},
    )
    assert outbound.status_code == 200
    products = client.get("/inventory/products", headers=headers).json()
    product_stock = next(item["current_stock"] for item in products if item["id"] == product_id)
    assert product_stock == 6

    overdraw = client.post(
        "/inventory/orders/outbound",
        headers=headers,
        json={"ingredient_id": product_id, "quantity": 7, "reason": "waste", "location_id": 1},
    )
    assert overdraw.status_code == 400

    history = client.get("/inventory/orders", headers=headers)
    assert history.status_code == 200
    product_history = [item for item in history.json() if item["ingredient"]["id"] == product_id]
    assert len(product_history) == 2
    assert {item["movement_type"] for item in product_history} == {"inbound", "outbound"}
    assert all(item["user_uuid"] == user["id"] for item in product_history)


def test_zero_stock_rejects_outbound_and_missing_product_returns_404(client, auth_headers):
    headers, _ = auth_headers
    product = create_product(client, headers)
    product_id = product.json()["id"]

    zero_stock = client.post(
        "/inventory/orders/outbound",
        headers=headers,
        json={"ingredient_id": product_id, "quantity": 1, "reason": "consumption", "location_id": 1},
    )
    missing_product = client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={"ingredient_id": 999999, "quantity": 1, "supplier_name": "Supplier", "location_id": 1},
    )

    assert zero_stock.status_code == 400
    assert missing_product.status_code == 404


def test_admin_locked_product_query_uses_postgresql_row_lock():
    captured = {}

    class Result:
        @staticmethod
        def first():
            return Ingredient(id=1, name="Test", sku="LOCK-1", unit="kg", category="meat", country="CO")

    class SessionStub:
        @staticmethod
        def exec(statement):
            captured["sql"] = str(statement.compile(dialect=postgresql.dialect()))
            return Result()

    assert get_product(SessionStub(), 1, lock=True).id == 1
    assert "FOR UPDATE" in captured["sql"]


@pytest.mark.skipif(
    not os.getenv("BRASALAND_TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="La concurrencia real de SELECT FOR UPDATE requiere PostgreSQL; configura BRASALAND_TEST_DATABASE_URL.",
)
def test_concurrent_outbound_orders_do_not_oversell_postgresql(client, auth_headers):
    headers, _ = auth_headers
    product = create_product(client, headers)
    product_id = product.json()["id"]
    inbound = client.post(
        "/inventory/orders/inbound",
        headers=headers,
        json={"ingredient_id": product_id, "quantity": 10, "supplier_name": "Supplier", "location_id": 1},
    )
    assert inbound.status_code == 200

    barrier = Barrier(2)

    def request_outbound():
        barrier.wait()
        return client.post(
            "/inventory/orders/outbound",
            headers=headers,
            json={"ingredient_id": product_id, "quantity": 7, "reason": "consumption", "location_id": 1},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: request_outbound(), range(2)))

    assert sorted(response.status_code for response in responses) == [200, 400]
    stock = client.get("/inventory/products", headers=headers).json()[0]["current_stock"]
    assert stock == 3
