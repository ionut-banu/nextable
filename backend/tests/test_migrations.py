"""The migrations and the models must not drift apart."""
import os

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.autogenerate import compare_metadata

from app.config import get_settings
from app.db import build_engine
from app.models import Base


def run_migrations(url: str) -> None:
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


def test_migrating_a_fresh_database_gives_exactly_the_models_schema(tmp_path):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    run_migrations(url)

    engine = build_engine(url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"render_as_batch": True})
        differences = compare_metadata(context, Base.metadata)
    engine.dispose()

    assert differences == [], f"models and migrations disagree: {differences}"
