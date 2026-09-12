"""Request and response bodies. Every shape the API promises lives here."""
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models import PartyStatus, SizeBucket


class LoginRequest(BaseModel):
    password: str


class SessionResponse(BaseModel):
    signed_in: bool


class PartyCreate(BaseModel):
    """What the host types at the door."""

    name: str = Field(min_length=1, max_length=80)
    size: int = Field(ge=1, le=40)
    phone: str | None = Field(default=None, max_length=40)
    note: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def name_is_not_only_spaces(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A party needs a name.")
        return value


class PartyResponse(BaseModel):
    """Everything the host console needs, token included (spec 8.2)."""

    id: int
    token: str
    name: str
    size: int
    phone: str | None
    note: str | None
    status: PartyStatus
    bucket: SizeBucket
    quoted_wait_minutes: int
    current_estimate_minutes: int | None
    position_in_line: int | None
    joined_at: datetime
    notified_at: datetime | None
    seated_at: datetime | None
    closed_at: datetime | None


class WaitlistEntry(BaseModel):
    """The guest's own status (spec 8.3).

    Built by hand rather than serialised from a PartyRecord, so a field added
    to the record can never leak to a guest.
    """

    restaurant_name: str
    party_first_name: str
    size: int
    status: PartyStatus
    position_in_line: int
    estimated_wait_minutes: int
    joined_at: datetime


class BucketSettingsSchema(BaseModel):
    default_turn_minutes: int = Field(ge=1, le=600)
    table_count: int = Field(ge=1, le=200)


class ConfigSchema(BaseModel):
    """Operational settings, editable from the host console (spec 7)."""

    restaurant_name: str = Field(min_length=1, max_length=80)
    history_window: int = Field(ge=1, le=500)
    smoothing_constant: int = Field(ge=0, le=100)
    buckets: dict[SizeBucket, BucketSettingsSchema]


class StatsResponse(BaseModel):
    date: date
    parties_seated: int
    guests_seated: int
    average_wait_minutes: int | None
    median_wait_minutes: int | None
    no_show_count: int
    cancelled_count: int
    quote_accuracy_minutes: int | None
