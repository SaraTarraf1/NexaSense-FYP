from datetime import datetime

from pydantic import BaseModel

from app.schemas.equipment_monitoring import EquipmentMonitoringResponse


class EquipmentCounts(BaseModel):
    total: int
    active: int
    inactive: int


class HealthCounts(BaseModel):
    normal: int = 0
    warning: int = 0
    critical: int = 0
    insufficient_data: int = 0
    not_evaluated: int = 0


class AlertCounts(BaseModel):
    total: int
    warning: int
    critical: int


class InspectionCounts(BaseModel):
    scheduled: int = 0
    active: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0


class AttentionItem(BaseModel):
    equipment_id: int
    equipment_name: str
    inspection_id: int | None
    health_status: str
    open_alerts: int
    reasons: list[str]


class RecentInspection(BaseModel):
    id: int
    equipment_id: int
    equipment_name: str
    status: str
    scheduled_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    activity_at: datetime


class DashboardOverview(BaseModel):
    observed_at: datetime
    equipment: EquipmentCounts
    health: HealthCounts
    alerts: AlertCounts
    inspections: InspectionCounts
    attention: list[AttentionItem]
    recent_inspections: list[RecentInspection]
    monitoring: list[EquipmentMonitoringResponse]
