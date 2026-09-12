"""The public guest route, spec 8.3. Never authenticated.

The token is the guest's only credential, so this module returns the same
bare 404 for a token that is unknown and for one that is malformed — there is
nothing here to probe.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.db import Database, get_db
from app.schemas import WaitlistEntry
from app.services import waitlist
from app.services.errors import PartyNotFound

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])

NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@router.get("/{token}", response_model=WaitlistEntry)
def get_waitlist_entry(token: str, db: Database = Depends(get_db)) -> WaitlistEntry:
    try:
        party = waitlist.get_party_by_token(db, token)
    except PartyNotFound:
        raise NOT_FOUND from None

    active = party.status.is_active
    return WaitlistEntry(
        restaurant_name=db.config.restaurant_name,
        party_first_name=party.name.split()[0] if party.name.split() else party.name,
        size=party.size,
        status=party.status,
        position_in_line=waitlist.position_in_line(db, party) if active else 0,
        estimated_wait_minutes=waitlist.live_estimate(db, party) if active else 0,
        joined_at=party.joined_at,
    )
