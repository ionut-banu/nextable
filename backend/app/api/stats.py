"""Today's figures, spec 8.2."""
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query

from app.auth import require_session
from app.db import Database, get_db
from app.schemas import StatsResponse
from app.services import stats as stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"], dependencies=[Depends(require_session)])


@router.get("", response_model=StatsResponse)
def get_stats(
    db: Database = Depends(get_db),
    day: date | None = Query(default=None, alias="date"),
) -> StatsResponse:
    summary = stats_service.summarise(db, day or datetime.now(UTC).date())
    return StatsResponse(**vars(summary))
