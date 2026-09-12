"""Domain records.

Plain Python for now. Stage 4 replaces these with SQLAlchemy models of the
same shape; nothing above this module should notice the change.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


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
    """The single row of operational settings (spec 5.3)."""

    restaurant_name: str = "The Blue Fig"
    history_window: int = 20
    smoothing_constant: int = 5
    buckets: dict[SizeBucket, BucketSettings] = field(default_factory=default_buckets)


@dataclass
class PartyRecord:
    """The single core entity (spec 5.1)."""

    token: str
    name: str
    size: int
    quoted_wait_minutes: int
    joined_at: datetime
    id: int = 0
    phone: str | None = None
    note: str | None = None
    status: PartyStatus = PartyStatus.WAITING
    notified_at: datetime | None = None
    seated_at: datetime | None = None
    closed_at: datetime | None = None
