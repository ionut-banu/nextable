"""SQLAlchemy models and the enums they use.

Everything here is written to be portable: no dialect-specific column types,
no native enums, no server-side defaults. SQLite today, Postgres later, with
`DATABASE_URL` the only thing that changes.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UtcDateTime(TypeDecorator):
    """A datetime that is always stored and returned in UTC.

    SQLite has no timezone type and hands back naive datetimes, so a column
    written as aware would come back naive and compare wrongly. This makes the
    behaviour identical on every backend, which is the whole point of keeping
    the app database-agnostic.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Refusing to store a naive datetime; all times are UTC.")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo else value.replace(tzinfo=UTC)


class SizeBucket(StrEnum):
    """Party sizes map to four buckets — the unit of capacity and of learning."""

    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"
    XLARGE = "XLARGE"


class PartyStatus(StrEnum):
    WAITING = "WAITING"
    NOTIFIED = "NOTIFIED"
    SEATED = "SEATED"
    NO_SHOW = "NO_SHOW"
    CANCELLED = "CANCELLED"

    @property
    def is_active(self) -> bool:
        """Waiting and notified parties are the queue."""
        return self in (PartyStatus.WAITING, PartyStatus.NOTIFIED)

    @property
    def is_terminal(self) -> bool:
        return not self.is_active


#: Stored as VARCHAR with a CHECK constraint rather than a native enum type,
#: so adding a status later is a migration and not a dialect problem.
_status_column = Enum(PartyStatus, native_enum=False, length=16, validate_strings=True)
_bucket_column = Enum(SizeBucket, native_enum=False, length=16, validate_strings=True)


class PartyRecord(Base):
    """The single core entity (spec 5.1)."""

    __tablename__ = "parties"
    __table_args__ = (CheckConstraint("size >= 1", name="party_size_at_least_one"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # The guest's only credential, so it is unique and indexed for lookup.
    token: Mapped[str] = mapped_column(String(43), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    size: Mapped[int]
    phone: Mapped[str | None] = mapped_column(String(40), default=None)
    note: Mapped[str | None] = mapped_column(String(200), default=None)
    status: Mapped[PartyStatus] = mapped_column(
        _status_column, default=PartyStatus.WAITING, index=True
    )
    quoted_wait_minutes: Mapped[int] = mapped_column(default=0)
    joined_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    notified_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)
    seated_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)


class ConfigRow(Base):
    """The single row of operational settings (spec 5.3)."""

    __tablename__ = "config"
    __table_args__ = (CheckConstraint("id = 1", name="config_is_a_single_row"),)

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    restaurant_name: Mapped[str] = mapped_column(String(80), default="The Blue Fig")
    history_window: Mapped[int] = mapped_column(default=20)
    smoothing_constant: Mapped[int] = mapped_column(default=5)


class BucketSettingRow(Base):
    """Per-bucket capacity and prior, one row each."""

    __tablename__ = "bucket_settings"

    bucket: Mapped[SizeBucket] = mapped_column(_bucket_column, primary_key=True)
    config_id: Mapped[int] = mapped_column(ForeignKey("config.id"), default=1)
    default_turn_minutes: Mapped[int] = mapped_column(default=30)
    table_count: Mapped[int] = mapped_column(default=1)


# --- the value objects the services work with ------------------------------


@dataclass
class BucketSettings:
    default_turn_minutes: int
    table_count: int


def default_buckets() -> dict[SizeBucket, BucketSettings]:
    """The cold-start numbers from spec 6.1."""
    return {
        SizeBucket.SMALL: BucketSettings(default_turn_minutes=25, table_count=8),
        SizeBucket.MEDIUM: BucketSettings(default_turn_minutes=40, table_count=6),
        SizeBucket.LARGE: BucketSettings(default_turn_minutes=55, table_count=3),
        SizeBucket.XLARGE: BucketSettings(default_turn_minutes=75, table_count=1),
    }


@dataclass
class ConfigRecord:
    """Settings as the services read them, assembled from the two tables."""

    restaurant_name: str = "The Blue Fig"
    history_window: int = 20
    smoothing_constant: int = 5
    buckets: dict[SizeBucket, BucketSettings] = field(default_factory=default_buckets)
