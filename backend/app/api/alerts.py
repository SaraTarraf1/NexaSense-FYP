from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, get_db
from app.models.alert import Alert
from app.models.alert_notification import AlertNotification
from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.models.user import User
from app.schemas.alert import (
    AlertDetailResponse,
    AlertNotificationResponse,
    AlertPageResponse,
    AlertResponse,
)
from app.schemas.equipment_monitoring import MonitoringReadingEvidence


router = APIRouter(prefix="/api/equipment", tags=["Alerts"])


def _get_owned_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Equipment:
    equipment = db.scalar(
        select(Equipment).where(
            Equipment.id == equipment_id,
            Equipment.user_id == current_user.id,
        )
    )
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found.")
    return equipment


def _alert_responses(
    db: Session, alerts: list[Alert], recipient_id: int
) -> list[AlertResponse]:
    if not alerts:
        return []

    notifications = db.scalars(
        select(AlertNotification)
        .where(
            AlertNotification.alert_id.in_([alert.id for alert in alerts]),
            AlertNotification.recipient_user_id == recipient_id,
        )
        .order_by(AlertNotification.id)
    )
    by_alert: dict[int, list[AlertNotificationResponse]] = defaultdict(list)
    for notification in notifications:
        by_alert[notification.alert_id].append(
            AlertNotificationResponse.model_validate(notification)
        )

    responses = []
    for alert in alerts:
        response = AlertResponse.model_validate(alert)
        response.notifications = by_alert.get(alert.id, [])
        responses.append(response)
    return responses


def owned_alerts(equipment: Equipment):
    return select(Alert).join(
        Inspection, (Inspection.id == Alert.inspection_id) & (Inspection.equipment_id == Alert.equipment_id)
    ).where(Alert.equipment_id == equipment.id, Inspection.user_id == equipment.user_id)


@router.get("/{equipment_id}/alerts", response_model=AlertPageResponse)
def list_equipment_alerts(
    limit: int = Query(default=50, ge=1, le=100),
    before_id: int | None = Query(default=None, ge=1),
    status: Literal["open", "closed"] | None = None,
    equipment: Equipment = Depends(_get_owned_equipment),
    db: Session = Depends(get_db),
):
    """List saved alerts for the equipment, most recent first."""
    query = owned_alerts(equipment)
    if status:
        query = query.where(Alert.status == status)
    if before_id is not None:
        cursor_time = db.scalar(
            owned_alerts(equipment).with_only_columns(Alert.created_at).where(Alert.id == before_id)
        )
        if cursor_time is None:
            raise HTTPException(status_code=404, detail="Alert cursor not found.")
        query = query.where(
            or_(
                Alert.created_at < cursor_time,
                and_(Alert.created_at == cursor_time, Alert.id < before_id),
            )
        )

    alerts = list(
        db.scalars(query.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit + 1))
    )
    return AlertPageResponse(
        items=_alert_responses(db, alerts[:limit], equipment.user_id),
        next_before_id=alerts[limit - 1].id if len(alerts) > limit else None,
    )


@router.get("/{equipment_id}/alerts/{alert_id}", response_model=AlertDetailResponse)
def get_equipment_alert(
    alert_id: int,
    equipment: Equipment = Depends(_get_owned_equipment),
    db: Session = Depends(get_db),
):
    """Read a saved alert and its supporting measurements."""
    alert = db.scalar(owned_alerts(equipment).where(Alert.id == alert_id))
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found.")

    evidence_rows = db.execute(
        select(SensorReading, Sensor.sensor_type)
        .join(Sensor, Sensor.id == SensorReading.sensor_id)
        .where(
            SensorReading.id.in_(alert.evidence_reading_ids),
            SensorReading.equipment_id == equipment.id,
            SensorReading.inspection_id == alert.inspection_id,
            SensorReading.validation_status == "valid",
            SensorReading.value > float("-inf"),
            SensorReading.value < float("inf"),
        )
    )
    by_reading = {
        reading.id: MonitoringReadingEvidence(
            reading_id=reading.id,
            sensor_type=sensor_type,
            value=reading.value,
            unit=reading.unit,
            timestamp=reading.timestamp,
        )
        for reading, sensor_type in evidence_rows
    }
    summary = _alert_responses(db, [alert], equipment.user_id)[0]
    return AlertDetailResponse(
        **summary.model_dump(),
        source_reading_id=alert.source_reading_id,
        evidence=[
            by_reading[reading_id]
            for reading_id in alert.evidence_reading_ids
            if reading_id in by_reading
        ],
    )


@router.post("/{equipment_id}/alerts/{alert_id}/close", status_code=204)
def close_equipment_alert(
    alert_id: int,
    equipment: Equipment = Depends(_get_owned_equipment),
    db: Session = Depends(get_db),
):
    alert = db.scalar(owned_alerts(equipment).where(Alert.id == alert_id).with_for_update(of=Alert))
    if alert is None:
        raise HTTPException(404, "Alert not found.")
    if alert.status == "open":
        alert.status = "closed"
    db.commit()
    return Response(status_code=204)
