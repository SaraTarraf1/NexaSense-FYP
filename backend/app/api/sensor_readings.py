from datetime import datetime, timezone
from math import isfinite

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_db
from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.models.user import User
from app.schemas.sensor_reading import SensorReadingResponse

router = APIRouter(
    prefix="/api/inspections",
    tags=["Sensor Readings"],
)


def verify_inspection_access(
    db: Session,
    inspection_id: int,
    user_id: int,
) -> Inspection:
    inspection = db.scalar(
        select(Inspection).join(Equipment, Equipment.id == Inspection.equipment_id).where(
            Inspection.id == inspection_id,
            Inspection.user_id == user_id,
            Equipment.user_id == user_id,
        )
    )

    if inspection is None:
        raise HTTPException(
            status_code=404,
            detail="Inspection not found.",
        )

    return inspection


def serialize_reading(
    reading: SensorReading,
    sensor_type: str,
    freshness_threshold_seconds: int | None = None,
) -> SensorReadingResponse:
    nonfinite = reading.value is not None and not isfinite(reading.value)
    return SensorReadingResponse(
        id=reading.id,
        inspection_id=reading.inspection_id,
        equipment_id=reading.equipment_id,
        sensor_id=reading.sensor_id,
        sensor_type=sensor_type,
        value=None if nonfinite else reading.value,
        unit=reading.unit,
        timestamp=reading.timestamp,
        validation_status="invalid" if nonfinite and reading.validation_status == "valid" else reading.validation_status,
        validation_message=reading.validation_message or ("Non-finite measurement." if nonfinite else None),
        freshness_threshold_seconds=freshness_threshold_seconds,
    )


@router.get(
    "/{inspection_id}/readings",
    response_model=list[SensorReadingResponse],
)
def list_sensor_readings(
    inspection_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = verify_inspection_access(
        db,
        inspection_id,
        current_user.id,
    )

    rows = db.execute(
        select(SensorReading, Sensor.sensor_type)
        .join(Sensor, SensorReading.sensor_id == Sensor.id)
        .where(
            SensorReading.inspection_id == inspection_id,
            SensorReading.equipment_id == inspection.equipment_id,
        )
        .order_by(
            SensorReading.timestamp.desc(),
            SensorReading.id.desc(),
        )
        .limit(limit)
    ).all()

    return [
        serialize_reading(reading, sensor_type)
        for reading, sensor_type in rows
    ]

@router.get(
    "/{inspection_id}/readings/latest",
    response_model=list[SensorReadingResponse],
)
def latest_sensor_readings(
    inspection_id: int,
    response: Response,
    validated_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inspection = verify_inspection_access(
        db,
        inspection_id,
        current_user.id,
    )

    now = datetime.now(timezone.utc)
    response.headers["X-Observed-At"] = now.isoformat()
    response.headers["Cache-Control"] = "no-store"
    response.headers["Access-Control-Expose-Headers"] = "X-Observed-At"

    readings = select(
        SensorReading.id,
        func.row_number().over(
            partition_by=SensorReading.sensor_id,
            order_by=(
                SensorReading.timestamp.desc(),
                SensorReading.id.desc(),
            ),
        ).label("sensor_rank"),
    ).where(
        SensorReading.inspection_id == inspection_id,
        SensorReading.equipment_id == inspection.equipment_id,
    )

    if validated_only:
        readings = readings.where(
            SensorReading.validation_status == "valid",
            SensorReading.value.is_not(None),
            SensorReading.value > float("-inf"),
            SensorReading.value < float("inf"),
            SensorReading.timestamp <= now,
        )

    ranked = readings.subquery()

    rows = db.execute(
        select(SensorReading, Sensor)
        .join(
            ranked,
            ranked.c.id == SensorReading.id,
        )
        .join(
            Sensor,
            SensorReading.sensor_id == Sensor.id,
        )
        .where(ranked.c.sensor_rank == 1)
        .order_by(
            SensorReading.timestamp.desc(),
            SensorReading.id.desc(),
        )
    )

    return [
        serialize_reading(
            reading,
            sensor.sensor_type,
            sensor.collection_interval_seconds * 3,
        )
        for reading, sensor in rows
    ]
