
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.services.health_assessment_service import HealthStatus


class MonitoringSensorResponse(BaseModel):
    sensor_type: str
    unit: str | None = None
    value: float | None = None
    timestamp: datetime | None = None
    validation_status: str | None = None
    status: Literal["current", "stale", "missing"]
    freshness_threshold_seconds: int


class MonitoringReadingEvidence(BaseModel):
    reading_id: int
    sensor_type: str
    value: float
    unit: str
    timestamp: datetime


class MonitoringAnomalyResponse(MonitoringReadingEvidence):
    anomaly_type: Literal["above_threshold", "below_threshold"] | None
    message: str | None


class MonitoringFaultMatchResponse(BaseModel):
    rule_id: str
    fault_type: str
    evidence_reading_ids: list[int]
    evidence: list[MonitoringReadingEvidence]


class MonitoringFaultResponse(BaseModel):
    source_reading: MonitoringReadingEvidence
    status: Literal["identified", "unknown", "undetermined"]
    message: str
    matches: list[MonitoringFaultMatchResponse]
    missing_sensor_types: list[str]


class MonitoringHealthHistoryEntry(BaseModel):
    id: int
    inspection_id: int
    status: HealthStatus
    assessed_at: datetime


class MonitoringHealthAssessmentResponse(MonitoringHealthHistoryEntry):
    message: str
    evidence: list[MonitoringReadingEvidence]
    fault_rule_ids: list[str]
    missing_sensor_types: list[str]


class MonitoringAlertSummary(BaseModel):
    warning: int = 0
    critical: int = 0


class EquipmentMonitoringResponse(BaseModel):
    equipment_id: int
    observed_at: datetime
    alert_summary: MonitoringAlertSummary
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
    faults: list[MonitoringFaultResponse] = Field(default_factory=list)
    health_status: HealthStatus | Literal["not_evaluated"] = "not_evaluated"
    health_assessment: MonitoringHealthAssessmentResponse | None = None
    last_completed_health_assessment: MonitoringHealthHistoryEntry | None = None
    health_history: list[MonitoringHealthHistoryEntry] = Field(default_factory=list)
