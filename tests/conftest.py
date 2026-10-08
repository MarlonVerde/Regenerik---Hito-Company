import os
import secrets
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

API_DIR = Path(__file__).resolve().parents[1]
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

TEST_RUNTIME_DIR = Path(tempfile.mkdtemp(prefix="brasaland-tests-"))
os.environ["BRASALAND_DATA_DIR"] = str(TEST_RUNTIME_DIR / "tinydb")
os.environ["DATABASE_URL"] = os.getenv(
    "BRASALAND_TEST_DATABASE_URL",
    f"sqlite:///{TEST_RUNTIME_DIR / 'inventory.sqlite'}",
)
os.environ["AUTH_SECRET_KEY"] = secrets.token_urlsafe(32)
os.environ["EMAIL_PROVIDER"] = ""

from auth import hash_password  # noqa: E402
import services.models  # noqa: E402,F401
from init_db import initialize_database  # noqa: E402
from main import app  # noqa: E402
from stores import profile_store, user_store  # noqa: E402

initialize_database()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_factory():
    created_ids = []

    def create(email="test@example.com", password="correct-password", role="user"):
        from models import ProfileCreate, UserCreate, UserRole

        payload = UserCreate(email=email, password=password, role=UserRole(role))
        record = user_store.create(payload, hash_password(password))
        profile_store.create(ProfileCreate(user_id=record["id"], name="Test User"))
        created_ids.append(record["id"])
        return record

    yield create

    for user_id in created_ids:
        profile_store.delete_by_user_id(user_id)
        user_store.delete(user_id)


@pytest.fixture
def auth_headers(client, user_factory):
    user = user_factory()
    response = client.post("/auth/login", json={"email": user["email"], "password": "correct-password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, user
