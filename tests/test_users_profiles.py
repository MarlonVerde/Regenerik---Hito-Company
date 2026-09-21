from uuid import uuid4


def test_create_user_and_duplicate_email(client):
    payload = {"email": f"new-{uuid4()}@example.com", "password": "password-123", "name": "New User"}
    first = client.post("/users", json=payload)
    assert first.status_code == 201
    assert first.json()["email"] == payload["email"]
    assert "hashed_password" not in first.json()

    duplicate = client.post("/users", json=payload)
    assert duplicate.status_code == 400


def test_user_detail_forbidden_for_other_user(client, auth_headers, user_factory):
    headers, _ = auth_headers
    other = user_factory(email="other@example.com")
    response = client.get(f"/users/{other['id']}", headers=headers)
    assert response.status_code == 403


def test_user_list_and_missing_user(client, auth_headers):
    headers, _ = auth_headers
    listed = client.get("/users", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    missing = client.get("/users/not-found", headers=headers)
    assert missing.status_code == 403 or missing.status_code == 404


def test_profile_update_creates_and_validates_profile(client, auth_headers):
    headers, _ = auth_headers
    updated = client.put("/profiles/me", headers=headers, json={"name": "Updated", "phone": "+57 300 1234567"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Updated"

    invalid = client.put("/profiles/me", headers=headers, json={"phone": "bad"})
    assert invalid.status_code == 422
