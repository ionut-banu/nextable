"""Operational settings, spec 7 and 8.2."""
from fastapi import APIRouter, Depends

from app.auth import require_session
from app.db import Database, get_db
from app.models import BucketSettings, ConfigRecord
from app.schemas import BucketSettingsSchema, ConfigSchema

router = APIRouter(prefix="/api/config", tags=["config"], dependencies=[Depends(require_session)])


def to_schema(record: ConfigRecord) -> ConfigSchema:
    return ConfigSchema(
        restaurant_name=record.restaurant_name,
        history_window=record.history_window,
        smoothing_constant=record.smoothing_constant,
        buckets={
            bucket: BucketSettingsSchema(
                default_turn_minutes=settings.default_turn_minutes,
                table_count=settings.table_count,
            )
            for bucket, settings in record.buckets.items()
        },
    )


@router.get("", response_model=ConfigSchema)
def get_config(db: Database = Depends(get_db)) -> ConfigSchema:
    return to_schema(db.config)


@router.put("", response_model=ConfigSchema)
def update_config(payload: ConfigSchema, db: Database = Depends(get_db)) -> ConfigSchema:
    db.config = ConfigRecord(
        restaurant_name=payload.restaurant_name,
        history_window=payload.history_window,
        smoothing_constant=payload.smoothing_constant,
        buckets={
            bucket: BucketSettings(
                default_turn_minutes=settings.default_turn_minutes,
                table_count=settings.table_count,
            )
            for bucket, settings in payload.buckets.items()
        },
    )
    return to_schema(db.config)
