"""Domain errors.

Services raise these. The API layer maps them to status codes — no service
knows what an HTTP status is (AGENTS.md).
"""


class PartyNotFound(Exception):
    def __init__(self, party_id: int | None = None) -> None:
        self.party_id = party_id
        super().__init__("That party is not on the list.")


class IllegalTransition(Exception):
    """A transition the lifecycle in spec 5.2 does not allow."""

    def __init__(self, current: str, attempted: str) -> None:
        self.current = current
        self.attempted = attempted
        super().__init__(
            f"A party that is {current} cannot become {attempted}."
        )
