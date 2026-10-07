from datetime import timedelta

import pytest
from jose import jwt

import auth


def test_password_hash_and_verification():
    password_hash = auth.hash_password("secret-password")
    assert password_hash != "secret-password"
    assert auth.verify_password("secret-password", password_hash)
    assert not auth.verify_password("wrong-password", password_hash)


def test_access_token_contains_subject_and_expires():
    token, expires_in = auth.create_access_token("user-1", timedelta(minutes=5))
    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert payload["sub"] == "user-1"
    assert expires_in == 300
    assert payload["exp"] > 0


def test_expired_access_token_is_rejected(user_factory):
    user = user_factory()
    token, _ = auth.create_access_token(user["id"], timedelta(seconds=-1))
    with pytest.raises(Exception) as error:
        auth.get_current_user(token, users=auth.user_store)
    assert getattr(error.value, "status_code", None) == 401


def test_login_happy_path_and_wrong_password(client, user_factory):
    user = user_factory(email="login@example.com")
    response = client.post("/auth/login", json={"email": user["email"], "password": "correct-password"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"

    invalid = client.post("/auth/login", json={"email": user["email"], "password": "wrong-password"})
    assert invalid.status_code == 401


def test_login_rejects_empty_password_and_unknown_user(client):
    empty = client.post("/auth/login", json={"email": "user@example.com", "password": ""})
    assert empty.status_code == 422
    unknown = client.post("/auth/login", json={"email": "missing@example.com", "password": "password"})
    assert unknown.status_code == 401


def test_me_requires_token_and_returns_profile(client, auth_headers):
    headers, user = auth_headers
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert response.json()["profile"]["name"] == "Test User"

    unauthorized = client.get("/auth/me")
    assert unauthorized.status_code == 401


def test_password_reset_token_is_single_use(client, user_factory, monkeypatch):
    user = user_factory(email="reset@example.com")
    monkeypatch.setattr("routes.auth.send_password_reset_email", lambda **kwargs: None)
    response = client.post("/auth/forgot-password", json={"email": user["email"]})
    assert response.status_code == 200

    token, _ = auth.create_password_reset_token(user["id"], user["hashed_password"])
    reset = client.post("/auth/reset-password", json={"token": token, "new_password": "new-password"})
    assert reset.status_code == 200
    reused = client.post("/auth/reset-password", json={"token": token, "new_password": "another-password"})
    assert reused.status_code == 400


def test_forgot_password_does_not_reveal_unknown_email(client, monkeypatch):
    monkeypatch.setattr("routes.auth.send_password_reset_email", lambda **kwargs: (_ for _ in ()).throw(AssertionError()))
    response = client.post("/auth/forgot-password", json={"email": "unknown@example.com"})
    assert response.status_code == 200
    assert "email" not in response.json()


def test_email_fallback_never_logs_recovery_link(monkeypatch, caplog):
    from email_service import send_password_reset_email

    recovery_link = "https://example.test/reset?token=unique-sensitive-token"
    monkeypatch.setenv("EMAIL_PROVIDER", "")

    with caplog.at_level("WARNING", logger="email_service"):
        result = send_password_reset_email("person@example.test", recovery_link, 15)

    assert result is False
    assert recovery_link not in caplog.text
    assert "unique-sensitive-token" not in caplog.text


def test_change_password_rejects_wrong_current_and_accepts_valid(client, auth_headers):
    headers, _ = auth_headers
    wrong = client.post("/auth/change-password", headers=headers, json={"current_password": "wrong", "new_password": "new-password"})
    assert wrong.status_code == 400
    valid = client.post("/auth/change-password", headers=headers, json={"current_password": "correct-password", "new_password": "new-password"})
    assert valid.status_code == 200
