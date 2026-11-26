from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.equipment_monitoring import MonitoringReadingEvidence


class AlertNotificationResponse(BaseModel):
    channel: str
    status: Literal["pending", "delivered", "failed"]
    attempted_at: datetime | None
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class AlertResponse(BaseModel):
    id: int
    equipment_id: int
    inspection_id: int
    event_type: Literal["anomaly", "fault"]
    event_key: str
    severity: Literal["warning", "critical"]
    description: str
    status: str
    created_at: datetime
    notifications: list[AlertNotificationResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AlertDetailResponse(AlertResponse):
    source_reading_id: int
    evidence: list[MonitoringReadingEvidence]


class AlertPageResponse(BaseModel):
    items: list[AlertResponse]
    next_before_id: int | None
