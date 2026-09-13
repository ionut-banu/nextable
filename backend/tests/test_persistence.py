"""What the real database adds: durability, constraints, and transactions.

These go through the repository rather than the API, because they are about
storage behaviour that no endpoint can show you.
"""
import threading
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Enum, create_engine, inspect
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import sessionmaker

from app.db import Database, build_engine, session_scope
from app.models import Base, PartyRecord, PartyStatus, UtcDateTime


def make_party(token="tok", size=2, joined_at=None, **extra) -> PartyRecord:
    return PartyRecord(
        token=token,
        name="Whitcomb",
        size=size,
        quoted_wait_minutes=25,
        joined_at=joined_at or datetime.now(UTC),
        **extra,
    )


# --- durability ------------------------------------------------------------


def test_a_party_outlives_the_session_that_wrote_it(session_factory):
    with session_scope(session_factory) as db:
        db.add_party(make_party(token="survivor"))

    with session_scope(session_factory) as db:
        assert db.party_by_token("survivor") is not None


def test_a_status_change_is_committed_not_just_held_in_memory(session_factory):
    with session_scope(session_factory) as db:
        party = db.add_party(make_party(token="moved"))
        party_id = party.id

    with session_scope(session_factory) as db:
        db.party_by_id(party_id).status = PartyStatus.SEATED

    with session_scope(session_factory) as db:
        assert db.party_by_id(party_id).status is PartyStatus.SEATED


def test_nothing_is_written_when_the_request_fails_partway(session_factory):
    with pytest.raises(RuntimeError):
        with session_scope(session_factory) as db:
            db.add_party(make_party(token="doomed"))
            raise RuntimeError("the request blew up after the write")

    with session_scope(session_factory) as db:
        assert db.party_by_token("doomed") is None
        assert db.parties() == []


# --- constraints -----------------------------------------------------------


def test_two_parties_cannot_share_a_token(session_factory):
    with session_scope(session_factory) as db:
        db.add_party(make_party(token="duplicate"))

    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as db:
            db.add_party(make_party(token="duplicate"))


def test_a_party_of_nobody_is_refused_by_the_database(session_factory):
    with pytest.raises(IntegrityError):
        with session_scope(session_factory) as db:
            db.add_party(make_party(token="empty", size=0))


def test_the_token_column_is_indexed_because_every_guest_read_uses_it(engine):
    indexed = {
        column
        for index in inspect(engine).get_indexes("parties")
        for column in index["column_names"]
    }

    assert "token" in indexed


# --- time ------------------------------------------------------------------


def test_a_naive_datetime_is_refused_rather_than_stored_ambiguously(session_factory):
    with pytest.raises(StatementError):
        with session_scope(session_factory) as db:
            db.add_party(make_party(token="naive", joined_at=datetime(2026, 9, 12, 18, 4)))


def test_times_come_back_aware_and_in_utc(session_factory):
    written = datetime.now(UTC) - timedelta(hours=3)

    with session_scope(session_factory) as db:
        party_id = db.add_party(make_party(token="timed", joined_at=written)).id

    with session_scope(session_factory) as db:
        read = db.party_by_id(party_id).joined_at

    assert read.tzinfo is not None
    assert read.utcoffset() == timedelta(0)
    assert abs((read - written).total_seconds()) < 1


# --- config ----------------------------------------------------------------


def test_the_cold_start_settings_are_written_on_first_read_and_then_kept(session_factory):
    with session_scope(session_factory) as db:
        assert db.config.buckets["SMALL"].table_count == 8
        db.save_config(_with_small_tables(db.config, 2))

    with session_scope(session_factory) as db:
        assert db.config.buckets["SMALL"].table_count == 2


def _with_small_tables(config, table_count):
    config.buckets["SMALL"].table_count = table_count
    return config


# --- staying database-agnostic ---------------------------------------------


def test_no_column_relies_on_a_native_enum_type():
    """Native enums are a schema migration on Postgres and absent on SQLite."""
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, Enum):
                assert column.type.native_enum is False, f"{table.name}.{column.name}"


def test_every_timestamp_uses_the_utc_column_type():
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.name.endswith("_at"):
                assert isinstance(column.type, UtcDateTime), f"{table.name}.{column.name}"


def test_the_url_decides_where_the_data_goes(tmp_path):
    location = tmp_path / "nextable.db"
    engine = build_engine(f"sqlite:///{location}")
    Base.metadata.create_all(engine)

    with sessionmaker(engine)() as session:
        Database(session).add_party(make_party(token="on-disk"))
        session.commit()
    engine.dispose()

    assert location.exists()

    reopened = create_engine(f"sqlite:///{location}")
    with sessionmaker(reopened)() as session:
        assert Database(session).party_by_token("on-disk") is not None
    reopened.dispose()


def test_an_in_memory_database_is_shared_across_threads():
    """SQLAlchemy pools in-memory SQLite per thread by default.

    The server reads it from more than one thread — the startup check runs on
    a worker thread — so each would otherwise open its own empty database.
    """
    engine = build_engine("sqlite://")
    Base.metadata.create_all(engine)

    with sessionmaker(engine)() as session:
        Database(session).add_party(make_party(token="in-memory"))
        session.commit()

    seen: list[bool] = []

    def look() -> None:
        with sessionmaker(engine)() as session:
            seen.append(Database(session).party_by_token("in-memory") is not None)

    thread = threading.Thread(target=look)
    thread.start()
    thread.join()
    engine.dispose()

    assert seen == [True]
