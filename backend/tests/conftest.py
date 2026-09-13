import os

os.environ.setdefault("STAFF_PASSWORD", "test-password")
os.environ.setdefault("SESSION_SECRET", "test-secret-not-used-anywhere-real")
os.environ.setdefault("DATABASE_URL", "sqlite://")

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Database, create_tables, get_db
from app.main import create_app
from app.models import Base

STAFF_PASSWORD = "test-password"


@pytest.fixture(scope="session", autouse=True)
def configured_database_has_a_schema() -> None:
    """The app checks its own database at boot.

    Tests inject a private session per test and never touch this one, but it
    has to exist for the app to start, exactly as in production.
    """
    create_tables()


@pytest.fixture
def engine() -> Iterator[Engine]:
    """A private in-memory database per test.

    StaticPool keeps every connection pointed at the same in-memory database,
    which would otherwise vanish the moment a connection is returned.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Database]:
    """The repository the test itself seeds through.

    The app is given this same session, so a record seeded in a test is
    visible to the request that follows without a commit in between.
    """
    session = session_factory()
    try:
        yield Database(session)
    finally:
        session.close()


@pytest.fixture
def client(db: Database) -> Iterator[TestClient]:
    app = create_app()

    def override_get_db() -> Iterator[Database]:
        try:
            yield db
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def host(client: TestClient) -> TestClient:
    """A client carrying a valid staff session."""
    response = client.post("/api/auth/login", json={"password": STAFF_PASSWORD})
    assert response.status_code == 204
    return client
