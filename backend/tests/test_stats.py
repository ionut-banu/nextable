"""Today's summary, spec 8.2.

Turnarounds have to be minutes long to be worth averaging, so these tests
seed the mock database directly rather than waiting around.
"""
from datetime import UTC, datetime, timedelta

from app.models import PartyRecord, PartyStatus


def seed_seated(db, *, size=2, quoted=25, waited=30, days_ago=0):
    joined = datetime.now(UTC) - timedelta(days=days_ago, minutes=waited + 1)
    party = PartyRecord(
        token=f"seeded-{len(db.parties)}",
        name="Seated party",
        size=size,
        quoted_wait_minutes=quoted,
        joined_at=joined,
        status=PartyStatus.SEATED,
        seated_at=joined + timedelta(minutes=waited),
    )
    party.closed_at = party.seated_at
    return db.add_party(party)


def seed_closed(db, status, *, days_ago=0):
    joined = datetime.now(UTC) - timedelta(days=days_ago, minutes=20)
    party = PartyRecord(
        token=f"seeded-{len(db.parties)}",
        name="Gone",
        size=2,
        quoted_wait_minutes=25,
        joined_at=joined,
        status=status,
    )
    party.closed_at = joined + timedelta(minutes=10)
    return db.add_party(party)


def test_an_empty_day_counts_nothing_rather_than_dividing_by_zero(host):
    stats = host.get("/api/stats").json()

    assert stats["parties_seated"] == 0
    assert stats["guests_seated"] == 0
    assert stats["average_wait_minutes"] is None
    assert stats["median_wait_minutes"] is None
    assert stats["quote_accuracy_minutes"] is None


def test_seated_parties_and_the_guests_in_them_are_counted(host, db):
    seed_seated(db, size=2)
    seed_seated(db, size=4)
    seed_seated(db, size=7)

    stats = host.get("/api/stats").json()

    assert stats["parties_seated"] == 3
    assert stats["guests_seated"] == 13


def test_average_and_median_wait_come_from_real_turnarounds(host, db):
    seed_seated(db, waited=10)
    seed_seated(db, waited=20)
    seed_seated(db, waited=60)

    stats = host.get("/api/stats").json()

    assert stats["average_wait_minutes"] == 30
    assert stats["median_wait_minutes"] == 20


def test_quote_accuracy_is_the_average_miss_in_either_direction(host, db):
    seed_seated(db, quoted=25, waited=10)  # quoted 15 minutes too long
    seed_seated(db, quoted=45, waited=70)  # quoted 25 minutes too short

    stats = host.get("/api/stats").json()

    assert stats["quote_accuracy_minutes"] == 20


def test_no_shows_and_cancellations_are_counted_separately(host, db):
    seed_closed(db, PartyStatus.NO_SHOW)
    seed_closed(db, PartyStatus.CANCELLED)
    seed_closed(db, PartyStatus.CANCELLED)

    stats = host.get("/api/stats").json()

    assert stats["no_show_count"] == 1
    assert stats["cancelled_count"] == 2
    assert stats["parties_seated"] == 0


def test_yesterday_is_not_part_of_today(host, db):
    seed_seated(db, days_ago=1)

    assert host.get("/api/stats").json()["parties_seated"] == 0


def test_a_past_day_can_be_asked_for_by_date(host, db):
    seed_seated(db, days_ago=1)
    yesterday = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()

    stats = host.get("/api/stats", params={"date": yesterday}).json()

    assert stats["date"] == yesterday
    assert stats["parties_seated"] == 1


def test_stats_refuse_a_caller_without_a_session(client):
    assert client.get("/api/stats").status_code == 401
