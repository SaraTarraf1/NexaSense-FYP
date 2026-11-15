
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class MonitoringSensorResponse(BaseModel):
    sensor_type: str
    unit: str | None = None
    value: float | None = None
    timestamp: datetime | None = None
    validation_status: str | None = None
    status: Literal["current", "stale", "missing"]
    freshness_threshold_seconds: int


class EquipmentMonitoringResponse(BaseModel):
    equipment_id: int
    equipment_name: str
    equipment_type: str
    equipment_status: str
    inspection_id: int | None = None
    inspection_status: str | None = None
    monitoring_status: Literal["current", "stale", "missing"]
    is_live: bool
    sensors: list[MonitoringSensorResponse]
    last_valid_reading_at: datetime | None = None
    anomalies: list = []
    faults: list = []
    health_status: str = "not_evaluated"
