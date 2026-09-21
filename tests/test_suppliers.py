def test_list_suppliers_filters_and_returns_items(client, auth_headers):
    headers, _ = auth_headers
    response = client.get("/suppliers", headers=headers, params={"country": "USA", "status": "active"})
    assert response.status_code == 200
    assert response.json()["total"] > 0
    assert all(item["country"] == "USA" and item["status"] == "active" for item in response.json()["items"])


def test_supplier_filter_rejects_unknown_country(client, auth_headers):
    headers, _ = auth_headers
    response = client.get("/suppliers", headers=headers, params={"country": "Mars"})
    assert response.status_code == 400


def test_supplier_lifecycle(client, auth_headers):
    headers, _ = auth_headers
    payload = {"name": "Test Supplier", "country": "USA", "categories": ["carne"], "rate_per_unit": 9.5, "currency": "USD", "contact_email": "sales@test.com"}
    created = client.post("/suppliers", headers=headers, json=payload)
    assert created.status_code == 201
    supplier_id = created.json()["id"]

    rate = client.patch(f"/suppliers/{supplier_id}/rate", headers=headers, json={"rate_per_unit": 10})
    assert rate.status_code == 200
    assert rate.json()["rate_per_unit"] == 10
    status = client.patch(f"/suppliers/{supplier_id}/status", headers=headers, json={"status": "suspended"})
    assert status.status_code == 200
    assert status.json()["status"] == "suspended"

    deleted = client.delete(f"/suppliers/{supplier_id}", headers=headers)
    assert deleted.status_code == 200
    missing = client.get(f"/suppliers/{supplier_id}", headers=headers)
    assert missing.status_code == 404


def test_supplier_creation_rejects_inconsistent_currency(client, auth_headers):
    headers, _ = auth_headers
    response = client.post("/suppliers", headers=headers, json={"name": "Invalid", "country": "USA", "categories": ["carne"], "rate_per_unit": 1, "currency": "COP"})
    assert response.status_code == 422
