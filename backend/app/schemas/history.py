from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from app.schemas.inspection import InspectionResponse
from app.schemas.sensor_reading import SensorReadingResponse


class HistoryReading(SensorReadingResponse):
    detection_status: str
    anomaly_type: str | None
    detection_message: str | None


class HistoryFaultMatch(BaseModel):
    rule_id: str
    fault_type: str
    evidence_reading_ids: list[int]
    evidence: list[HistoryReading]


class HistoryFault(BaseModel):
    source_reading: HistoryReading
    classified_at: datetime
    status: str
    message: str
    matches: list[HistoryFaultMatch]
    missing_sensor_types: list[str]


class HistoryHealth(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    inspection_id: int
    status: str
    assessed_at: datetime | None = None
    message: str | None = None
    evidence_reading_ids: list[int] = []
    fault_rule_ids: list[str] = []
    missing_sensor_types: list[str] = []


class HistoryInspection(InspectionResponse):
    health_status: str


class HistoryPoint(BaseModel):
    timestamp: datetime
    value: float


class SensorStatistics(BaseModel):
    sensor_type: str
    unit: str
    minimum: float
    maximum: float
    average: float
    count: int
    points: list[HistoryPoint] = []


class Occurrence(BaseModel):
    type: str
    count: int
    frequency: float


class HistorySummary(BaseModel):
    inspections: int
    valid_measurements: int
    anomalies: int
    faults: int
    health_assessments: int
    sensors: list[SensorStatistics]
    anomaly_types: list[Occurrence]
    fault_types: list[Occurrence]


T = TypeVar("T")


class HistoryPage(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int
