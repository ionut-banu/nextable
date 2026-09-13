"""Load a realistic evening so the adaptive estimator can be seen working.

Without history every quote is the configured prior, which makes the whole
point of section 6 invisible. This writes a service already in progress:
sixteen seated parties to learn from, a few that left, and six still waiting.

    uv run python scripts/seed.py [--force]
"""
import argparse
import pathlib
import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import get_session_factory  # noqa: E402
from app.models import PartyRecord, PartyStatus  # noqa: E402
from app.services.waitlist import new_token  # noqa: E402

# name, size, minutes ago they joined, minutes until seated, what we quoted
SEATED = [
    ("Marsh", 2, 205, 22, 25), ("Ferreira", 4, 198, 44, 40),
    ("Nakamura", 2, 190, 26, 25), ("Oyelaran", 5, 182, 58, 55),
    ("Baptiste", 3, 176, 38, 40), ("Kowalczyk", 2, 168, 19, 25),
    ("Ainsley", 4, 160, 51, 40), ("Rasmussen", 7, 150, 78, 75),
    ("Delacroix", 2, 141, 24, 25), ("Haddad", 6, 132, 61, 55),
    ("Strand", 4, 120, 35, 40), ("Iqbal", 2, 108, 31, 25),
    ("Bellweather", 3, 96, 42, 40), ("Sorrentino", 2, 84, 23, 25),
    ("Achebe", 5, 70, 54, 55), ("Mendelsohn", 4, 58, 46, 40),
]

# name, size, joined, called (None if never), quoted, note, phone
WAITING = [
    ("Dana Whitcomb", 4, 34, None, 40, "Highchair", None),
    ("Okonjo", 2, 27, 4, 25, None, "555 0147"),
    ("Vasquez", 6, 22, None, 55, "Patio if one opens", None),
    ("Lindqvist", 2, 15, None, 25, None, None),
    ("Behrouzi", 8, 11, None, 75, "Birthday, no candles", None),
    ("Dupont", 3, 5, None, 40, None, "555 0192"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="seed even if parties exist")
    args = parser.parse_args()

    now = datetime.now(UTC)
    ago = lambda minutes: now - timedelta(minutes=minutes)  # noqa: E731

    with get_session_factory()() as session:
        existing = session.query(PartyRecord).count()
        if existing and not args.force:
            print(f"{existing} parties already here. Use --force to add anyway.")
            return

        for name, size, joined, turnaround, quoted in SEATED:
            seated_at = ago(joined - turnaround)
            session.add(PartyRecord(
                token=new_token(), name=name, size=size, quoted_wait_minutes=quoted,
                joined_at=ago(joined), status=PartyStatus.SEATED,
                notified_at=ago(joined - turnaround + 4),
                seated_at=seated_at, closed_at=seated_at,
            ))

        session.add(PartyRecord(
            token=new_token(), name="Trelawny", size=2, quoted_wait_minutes=25,
            joined_at=ago(92), status=PartyStatus.NO_SHOW,
            notified_at=ago(68), closed_at=ago(60),
        ))
        session.add(PartyRecord(
            token=new_token(), name="Kaur", size=4, quoted_wait_minutes=40,
            joined_at=ago(78), status=PartyStatus.CANCELLED,
            note="Went next door", closed_at=ago(70),
        ))

        for name, size, joined, called, quoted, note, phone in WAITING:
            session.add(PartyRecord(
                token=new_token(), name=name, size=size, quoted_wait_minutes=quoted,
                joined_at=ago(joined), note=note, phone=phone,
                status=PartyStatus.NOTIFIED if called else PartyStatus.WAITING,
                notified_at=ago(called) if called else None,
            ))

        session.commit()

    print(f"Seeded {len(SEATED)} seated parties, 2 that left, and {len(WAITING)} on the list.")


if __name__ == "__main__":
    main()
