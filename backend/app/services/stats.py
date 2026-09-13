"""The single-day operational summary behind /api/stats (spec 8.2)."""
from dataclasses import dataclass
from datetime import date
from statistics import mean, median

from app.db import Database
from app.models import PartyStatus
from app.services.waitlist import turnaround_minutes


@dataclass
class DailyStats:
    date: date
    parties_seated: int
    guests_seated: int
    average_wait_minutes: int | None
    median_wait_minutes: int | None
    no_show_count: int
    cancelled_count: int
    quote_accuracy_minutes: int | None


def summarise(db: Database, day: date) -> DailyStats:
    on_the_day = db.parties(day=day)
    seated = [p for p in on_the_day if p.status is PartyStatus.SEATED and p.seated_at]

    waits = [turnaround_minutes(party) for party in seated]
    # How far each quote was out, in either direction (spec 8.2).
    misses = [
        abs(party.quoted_wait_minutes - wait) for party, wait in zip(seated, waits, strict=True)
    ]

    return DailyStats(
        date=day,
        parties_seated=len(seated),
        guests_seated=sum(party.size for party in seated),
        average_wait_minutes=round(mean(waits)) if waits else None,
        median_wait_minutes=round(median(waits)) if waits else None,
        no_show_count=sum(1 for p in on_the_day if p.status is PartyStatus.NO_SHOW),
        cancelled_count=sum(1 for p in on_the_day if p.status is PartyStatus.CANCELLED),
        quote_accuracy_minutes=round(mean(misses)) if misses else None,
    )
