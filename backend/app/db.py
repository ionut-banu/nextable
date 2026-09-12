"""The mock database.

An in-memory stand-in with the shape a SQLAlchemy session will have later:
routers and services ask it for records, never for rows. Stage 4 swaps the
body of this module for a real engine and session.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.models import ConfigRecord, PartyRecord, PartyStatus


@dataclass
class Database:
    parties: list[PartyRecord] = field(default_factory=list)
    config: ConfigRecord = field(default_factory=ConfigRecord)
    _next_id: int = 1

    def add_party(self, party: PartyRecord) -> PartyRecord:
        party.id = self._next_id
        self._next_id += 1
        self.parties.append(party)
        return party

    def party_by_id(self, party_id: int) -> PartyRecord | None:
        return next((p for p in self.parties if p.id == party_id), None)

    def party_by_token(self, token: str) -> PartyRecord | None:
        return next((p for p in self.parties if p.token == token), None)

    def active_parties(self) -> list[PartyRecord]:
        """The queue: waiting and notified parties, oldest first."""
        active = [p for p in self.parties if p.status.is_active]
        return sorted(active, key=lambda p: (p.joined_at, p.id))

    def all_parties(self) -> list[PartyRecord]:
        return sorted(self.parties, key=lambda p: (p.joined_at, p.id))

    def seated_parties(self) -> list[PartyRecord]:
        seated = [p for p in self.parties if p.status is PartyStatus.SEATED and p.seated_at]
        return sorted(seated, key=lambda p: p.seated_at or datetime.min.replace(tzinfo=UTC))


_database = Database()


def get_db() -> Database:
    """FastAPI dependency. Tests override this with a fresh Database."""
    return _database
