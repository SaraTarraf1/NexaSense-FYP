
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MonitoringSensorResponse(BaseModel):
    sensor_type: str
    unit: str | None = None
    value: float | None = None
    timestamp: datetime | None = None
    validation_status: str | None = None
    status: Literal["current", "stale", "missing"]
    freshness_threshold_seconds: int


class MonitoringAnomalyResponse(BaseModel):
    reading_id: int
    sensor_type: str
    value: float
    unit: str
    timestamp: datetime
    anomaly_type: Literal["above_threshold", "below_threshold"] | None
    message: str | None


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
    anomalies: list[MonitoringAnomalyResponse] = Field(default_factory=list)
    faults: list = []
    health_status: str = "not_evaluated"
