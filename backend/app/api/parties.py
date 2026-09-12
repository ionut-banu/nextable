"""The host's queue, spec 8.2. Routers validate and delegate."""
from typing import Literal

from fastapi import APIRouter, Depends, Query, status

from app.auth import require_session
from app.db import Database, get_db
from app.models import PartyRecord
from app.schemas import PartyCreate, PartyResponse
from app.services import waitlist
from app.services.estimator import bucket_for_size

router = APIRouter(
    prefix="/api/parties",
    tags=["parties"],
    dependencies=[Depends(require_session)],
)


def to_response(db: Database, party: PartyRecord) -> PartyResponse:
    """Add the derived fields a queue row needs (spec 8.2)."""
    active = party.status.is_active
    return PartyResponse(
        id=party.id,
        token=party.token,
        name=party.name,
        size=party.size,
        phone=party.phone,
        note=party.note,
        status=party.status,
        bucket=bucket_for_size(party.size),
        quoted_wait_minutes=party.quoted_wait_minutes,
        current_estimate_minutes=waitlist.live_estimate(db, party) if active else None,
        position_in_line=waitlist.position_in_line(db, party) if active else None,
        joined_at=party.joined_at,
        notified_at=party.notified_at,
        seated_at=party.seated_at,
        closed_at=party.closed_at,
    )


@router.post("", response_model=PartyResponse, status_code=status.HTTP_201_CREATED)
def create_party(payload: PartyCreate, db: Database = Depends(get_db)) -> PartyResponse:
    party = waitlist.add_party(
        db,
        name=payload.name,
        size=payload.size,
        phone=payload.phone,
        note=payload.note,
    )
    return to_response(db, party)


@router.get("", response_model=list[PartyResponse])
def list_parties(
    db: Database = Depends(get_db),
    status_filter: Literal["active", "all"] = Query("active", alias="status"),
) -> list[PartyResponse]:
    parties = waitlist.list_queue(db, active_only=status_filter == "active")
    return [to_response(db, party) for party in parties]


@router.get("/{party_id}", response_model=PartyResponse)
def get_party(party_id: int, db: Database = Depends(get_db)) -> PartyResponse:
    return to_response(db, waitlist.get_party(db, party_id))


@router.post("/{party_id}/notify", response_model=PartyResponse)
def notify_party(party_id: int, db: Database = Depends(get_db)) -> PartyResponse:
    return to_response(db, waitlist.notify(db, party_id))


@router.post("/{party_id}/seat", response_model=PartyResponse)
def seat_party(party_id: int, db: Database = Depends(get_db)) -> PartyResponse:
    return to_response(db, waitlist.seat(db, party_id))


@router.post("/{party_id}/no-show", response_model=PartyResponse)
def no_show_party(party_id: int, db: Database = Depends(get_db)) -> PartyResponse:
    return to_response(db, waitlist.no_show(db, party_id))


@router.post("/{party_id}/cancel", response_model=PartyResponse)
def cancel_party(party_id: int, db: Database = Depends(get_db)) -> PartyResponse:
    return to_response(db, waitlist.cancel(db, party_id))
