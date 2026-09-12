import os

os.environ.setdefault("STAFF_PASSWORD", "test-password")
os.environ.setdefault("SESSION_SECRET", "test-secret-not-used-anywhere-real")

import pytest
from fastapi.testclient import TestClient

from app.db import Database, get_db
from app.main import create_app

STAFF_PASSWORD = "test-password"


@pytest.fixture
def db() -> Database:
    """A fresh mock database per test."""
    return Database()


@pytest.fixture
def client(db: Database) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def host(client: TestClient) -> TestClient:
    """A client carrying a valid staff session."""
    response = client.post("/api/auth/login", json={"password": STAFF_PASSWORD})
    assert response.status_code == 204
    return client
