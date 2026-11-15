
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_db
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
        select(Inspection).where(
            Inspection.id == inspection_id,
            Inspection.user_id == user_id,
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
) -> SensorReadingResponse:
    return SensorReadingResponse(
        id=reading.id,
        inspection_id=reading.inspection_id,
        equipment_id=reading.equipment_id,
        sensor_id=reading.sensor_id,
        sensor_type=sensor_type,
        value=reading.value,
        unit=reading.unit,
        timestamp=reading.timestamp,
        validation_status=reading.validation_status,
        validation_message=reading.validation_message,
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
    verify_inspection_access(
        db,
        inspection_id,
        current_user.id,
    )

    rows = db.execute(
        select(SensorReading, Sensor.sensor_type)
        .join(Sensor, SensorReading.sensor_id == Sensor.id)
        .where(SensorReading.inspection_id == inspection_id)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_inspection_access(
        db,
        inspection_id,
        current_user.id,
    )

    rows = db.execute(
        select(SensorReading, Sensor.sensor_type)
        .join(Sensor, SensorReading.sensor_id == Sensor.id)
        .where(SensorReading.inspection_id == inspection_id)
        .order_by(
            SensorReading.timestamp.desc(),
            SensorReading.id.desc(),
        )
    ).all()

    latest_by_sensor = {}

    for reading, sensor_type in rows:
        if sensor_type not in latest_by_sensor:
            latest_by_sensor[sensor_type] = serialize_reading(
                reading,
                sensor_type,
            )

    return list(latest_by_sensor.values())
