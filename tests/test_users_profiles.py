import pytest
from uuid import uuid4

from stores import profile_store, user_store


def test_create_user_and_duplicate_email(client):
    payload = {"email": f"new-{uuid4()}@example.com", "password": "password-123", "name": "New User"}
    first = client.post("/users", json=payload)
    assert first.status_code == 201
    assert first.json()["email"] == payload["email"]
    assert first.json()["role"] == "user"
    assert "hashed_password" not in first.json()

    duplicate = client.post("/users", json=payload)
    assert duplicate.status_code == 400


def test_public_registration_cannot_assign_admin_role(client):
    response = client.post(
        "/users",
        json={"email": f"role-{uuid4()}@example.com", "password": "password-123", "role": "admin"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "user"


def test_user_list_requires_authentication_and_only_returns_self(client, auth_headers):
    headers, user = auth_headers

    anonymous = client.get("/users")
    listed = client.get("/users", headers=headers)

    assert anonymous.status_code == 401
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == user["id"]


def test_admin_can_list_users_and_manage_roles(client, user_factory):
    regular_user = user_factory(email="regular-list@example.com")
    admin = user_factory(email="admin-list@example.com", role="admin")
    login = client.post("/auth/login", json={"email": admin["email"], "password": "correct-password"})
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    listed = client.get("/users", headers=admin_headers)
    updated = client.put(f"/users/{regular_user['id']}", headers=admin_headers, json={"role": "manager"})

    assert listed.status_code == 200
    listed_ids = {user["id"] for user in listed.json()["items"]}
    assert regular_user["id"] in listed_ids
    assert admin["id"] in listed_ids
    assert listed.json()["total"] >= 2
    assert updated.status_code == 200
    assert updated.json()["role"] == "manager"


def test_development_admin_bootstrap_requires_explicit_environment(monkeypatch):
    from seed_admin import main

    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "bootstrap@example.com")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "a-local-development-password")

    with pytest.raises(SystemExit):
        main()


def test_development_admin_bootstrap_creates_only_local_configured_admin(monkeypatch):
    from seed_admin import main

    email = f"bootstrap-{uuid4()}@example.com"
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", email)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "a-local-development-password")

    main()
    created = user_store.get_by_email(email)

    assert created is not None
    assert created["role"] == "admin"
    profile_store.delete_by_user_id(created["id"])
    user_store.delete(created["id"])


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
