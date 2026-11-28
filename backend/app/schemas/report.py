from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.alert import AlertResponse
from app.schemas.equipment import EquipmentResponse
from app.schemas.history import HistoryFault, HistoryHealth, HistoryReading, SensorStatistics
from app.schemas.inspection import InspectionResponse


class ReportCreate(BaseModel):
    equipment_id: int = Field(gt=0)
    inspection_id: int = Field(gt=0)


class ReportSnapshot(BaseModel):
    schema_version: int = 1
    equipment: EquipmentResponse
    inspection: InspectionResponse
    duration_seconds: float | None
    health_status: str
    readings: list[HistoryReading]
    statistics: list[SensorStatistics]
    anomalies: list[HistoryReading]
    faults: list[HistoryFault]
    health: list[HistoryHealth]
    alerts: list[AlertResponse] = Field(default_factory=list)
    recommendations: list[str]
    limitations: list[str]


class ReportSummary(BaseModel):
    id: int
    equipment_id: int
    equipment_name: str
    inspection_id: int
    inspection_date: datetime | None
    generated_at: datetime
    health_status: str


class ReportDetail(ReportSummary):
    snapshot: ReportSnapshot
