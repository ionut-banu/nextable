"""Queue operations and status transitions.

This module owns every business rule. Routers call in; nothing here knows
about HTTP (AGENTS.md).
"""
import secrets
from datetime import UTC, date, datetime

from app.db import Database
from app.models import ConfigRecord, PartyRecord, PartyStatus, SizeBucket
from app.services.errors import IllegalTransition, PartyNotFound
from app.services.estimator import bucket_for_size, estimate_wait_minutes

#: The lifecycle of spec 5.2. A status missing from this map is terminal.
ALLOWED_TRANSITIONS: dict[PartyStatus, set[PartyStatus]] = {
    PartyStatus.WAITING: {PartyStatus.NOTIFIED, PartyStatus.SEATED, PartyStatus.CANCELLED},
    PartyStatus.NOTIFIED: {PartyStatus.SEATED, PartyStatus.NO_SHOW, PartyStatus.CANCELLED},
    PartyStatus.SEATED: set(),
    PartyStatus.NO_SHOW: set(),
    PartyStatus.CANCELLED: set(),
}


def new_token() -> str:
    """The guest's only credential: from secrets, never derived from the party."""
    return secrets.token_urlsafe(16)


def now_utc() -> datetime:
    return datetime.now(UTC)


# --- reading ---------------------------------------------------------------


def turnaround_minutes(party: PartyRecord) -> float:
    """What the estimator learns from: joining to sitting down."""
    if party.seated_at is None:
        raise ValueError("Only a seated party has a turnaround.")
    return (party.seated_at - party.joined_at).total_seconds() / 60


def samples_for_bucket(db: Database, bucket: SizeBucket) -> list[float]:
    """Turnarounds of seated parties in one bucket, oldest first."""
    return [
        turnaround_minutes(party)
        for party in db.seated_parties()
        if bucket_for_size(party.size) is bucket
    ]


def parties_ahead(db: Database, party: PartyRecord) -> int:
    """Active parties in the same bucket that joined strictly earlier (spec 6.3)."""
    bucket = bucket_for_size(party.size)
    return sum(
        1
        for other in db.active_parties()
        if bucket_for_size(other.size) is bucket
        and (other.joined_at, other.id) < (party.joined_at, party.id)
    )


def estimate_for(db: Database, bucket: SizeBucket, ahead: int) -> int:
    config: ConfigRecord = db.config
    bucket_settings = config.buckets[bucket]
    return estimate_wait_minutes(
        parties_ahead=ahead,
        samples=samples_for_bucket(db, bucket),
        default_turn_minutes=bucket_settings.default_turn_minutes,
        table_count=bucket_settings.table_count,
        history_window=config.history_window,
        smoothing_constant=config.smoothing_constant,
    )


def live_estimate(db: Database, party: PartyRecord) -> int:
    """Recomputed on every read, so positions and times fall (spec 6.4)."""
    return estimate_for(db, bucket_for_size(party.size), parties_ahead(db, party))


def position_in_line(db: Database, party: PartyRecord) -> int:
    return parties_ahead(db, party) + 1


def get_party(db: Database, party_id: int) -> PartyRecord:
    party = db.party_by_id(party_id)
    if party is None:
        raise PartyNotFound(party_id)
    return party


def get_party_by_token(db: Database, token: str) -> PartyRecord:
    party = db.party_by_token(token)
    if party is None:
        raise PartyNotFound()
    return party


def list_queue(
    db: Database, active_only: bool = True, day: date | None = None
) -> list[PartyRecord]:
    parties = db.active_parties() if active_only else db.all_parties()
    if day is None:
        return parties
    return [party for party in parties if party.joined_at.date() == day]


# --- writing ---------------------------------------------------------------


def add_party(
    db: Database,
    *,
    name: str,
    size: int,
    phone: str | None = None,
    note: str | None = None,
) -> PartyRecord:
    """Quote the party, then put it at the back of its bucket's line."""
    bucket = bucket_for_size(size)
    ahead = sum(
        1 for other in db.active_parties() if bucket_for_size(other.size) is bucket
    )

    party = PartyRecord(
        token=new_token(),
        name=name.strip(),
        size=size,
        phone=phone or None,
        note=note or None,
        # Frozen at join time, and never updated (spec 6.4).
        quoted_wait_minutes=estimate_for(db, bucket, ahead),
        joined_at=now_utc(),
    )
    return db.add_party(party)


def _transition(db: Database, party_id: int, to: PartyStatus) -> PartyRecord:
    party = get_party(db, party_id)

    if to not in ALLOWED_TRANSITIONS[party.status]:
        raise IllegalTransition(current=party.status.value, attempted=to.value)

    stamp = now_utc()
    party.status = to

    if to is PartyStatus.NOTIFIED:
        party.notified_at = stamp
    else:
        if to is PartyStatus.SEATED:
            party.seated_at = stamp
        party.closed_at = stamp

    return party


def notify(db: Database, party_id: int) -> PartyRecord:
    return _transition(db, party_id, PartyStatus.NOTIFIED)


def seat(db: Database, party_id: int) -> PartyRecord:
    return _transition(db, party_id, PartyStatus.SEATED)


def no_show(db: Database, party_id: int) -> PartyRecord:
    return _transition(db, party_id, PartyStatus.NO_SHOW)


def cancel(db: Database, party_id: int) -> PartyRecord:
    return _transition(db, party_id, PartyStatus.CANCELLED)
