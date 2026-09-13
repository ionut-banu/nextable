"""The database: engine, session, and the repository the services talk to.

`Database` is the only place that knows SQLAlchemy. Its methods are the same
ones the in-memory store offered, so services and routers above it never
learned there was a swap.

Nothing here is dialect-specific. `DATABASE_URL` chooses the backend; SQLite
gets the one connect argument it needs and everything else is standard.
"""
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import (
    Base,
    BucketSettingRow,
    BucketSettings,
    ConfigRecord,
    ConfigRow,
    PartyRecord,
    PartyStatus,
    default_buckets,
)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def build_engine(url: str) -> Engine:
    """Two SQLite quirks to absorb; everything else is standard.

    SQLite objects to a connection being used from another thread, and an
    in-memory database belongs to its connection — with a normal pool every
    connection would open its own empty database. StaticPool keeps them all on
    one connection so an in-memory URL behaves like a database.
    """
    if not url.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True)

    connect_args = {"check_same_thread": False}
    if _is_in_memory(url):
        return create_engine(url, connect_args=connect_args, poolclass=StaticPool)
    return create_engine(url, connect_args=connect_args)


def _is_in_memory(url: str) -> bool:
    path = url.partition("sqlite")[2].lstrip(":").lstrip("/")
    return path in ("", ":memory:") or path.startswith(":memory:")


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = build_engine(get_settings().database_url)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        # expire_on_commit=False: a response is built from records that were
        # just committed, and refetching them would be pointless work.
        _session_factory = sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


def create_tables() -> None:
    """For tests and first runs. Real schema changes go through Alembic."""
    Base.metadata.create_all(get_engine())


class Database:
    """A repository over one session. One instance per request."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # --- parties -----------------------------------------------------------

    def add_party(self, party: PartyRecord) -> PartyRecord:
        self.session.add(party)
        # Flush rather than commit: the id is needed to build the response,
        # but the request is not finished and may still fail.
        self.session.flush()
        return party

    def party_by_id(self, party_id: int) -> PartyRecord | None:
        return self.session.get(PartyRecord, party_id)

    def party_by_token(self, token: str) -> PartyRecord | None:
        return self.session.scalar(select(PartyRecord).where(PartyRecord.token == token))

    def parties(
        self, *, active_only: bool = False, day: date | None = None
    ) -> list[PartyRecord]:
        query = select(PartyRecord)

        if active_only:
            query = query.where(
                PartyRecord.status.in_([PartyStatus.WAITING, PartyStatus.NOTIFIED])
            )

        if day is not None:
            # A half-open range rather than a date function, because date
            # extraction is spelled differently on every backend.
            start = datetime.combine(day, time.min, tzinfo=UTC)
            query = query.where(
                PartyRecord.joined_at >= start,
                PartyRecord.joined_at < start + timedelta(days=1),
            )

        query = query.order_by(PartyRecord.joined_at, PartyRecord.id)
        return list(self.session.scalars(query))

    def active_parties(self) -> list[PartyRecord]:
        """The queue: waiting and notified parties, oldest first."""
        return self.parties(active_only=True)

    def all_parties(self) -> list[PartyRecord]:
        return self.parties()

    def seated_parties(self) -> list[PartyRecord]:
        """What the estimator learns from, oldest seating first."""
        query = (
            select(PartyRecord)
            .where(PartyRecord.status == PartyStatus.SEATED)
            .where(PartyRecord.seated_at.is_not(None))
            .order_by(PartyRecord.seated_at)
        )
        return list(self.session.scalars(query))

    # --- config ------------------------------------------------------------

    @property
    def config(self) -> ConfigRecord:
        row = self.session.get(ConfigRow, 1)
        if row is None:
            row = self._install_defaults()

        buckets = {
            setting.bucket: BucketSettings(
                default_turn_minutes=setting.default_turn_minutes,
                table_count=setting.table_count,
            )
            for setting in self.session.scalars(select(BucketSettingRow))
        }
        return ConfigRecord(
            restaurant_name=row.restaurant_name,
            history_window=row.history_window,
            smoothing_constant=row.smoothing_constant,
            buckets=buckets or default_buckets(),
        )

    def save_config(self, record: ConfigRecord) -> ConfigRecord:
        row = self.session.get(ConfigRow, 1) or self._install_defaults()
        row.restaurant_name = record.restaurant_name
        row.history_window = record.history_window
        row.smoothing_constant = record.smoothing_constant

        for bucket, settings in record.buckets.items():
            setting = self.session.get(BucketSettingRow, bucket)
            if setting is None:
                setting = BucketSettingRow(bucket=bucket)
                self.session.add(setting)
            setting.default_turn_minutes = settings.default_turn_minutes
            setting.table_count = settings.table_count

        self.session.flush()
        return self.config

    def _install_defaults(self) -> ConfigRow:
        """First run: write the cold-start numbers from spec 6.1."""
        row = ConfigRow(id=1)
        self.session.add(row)
        for bucket, settings in default_buckets().items():
            self.session.add(
                BucketSettingRow(
                    bucket=bucket,
                    default_turn_minutes=settings.default_turn_minutes,
                    table_count=settings.table_count,
                )
            )
        self.session.flush()
        return row


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Database]:
    """One transaction per request: commit on success, roll back on anything else."""
    session = factory()
    try:
        yield Database(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Database]:
    """FastAPI dependency. Tests override it with a session of their own."""
    with session_scope(get_session_factory()) as database:
        yield database


__all__ = ["Database", "build_engine", "create_tables", "get_db", "get_engine", "session_scope"]

