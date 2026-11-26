
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class InspectionCreate(BaseModel):
    equipment_id: int


class InspectionSchedule(InspectionCreate):
    scheduled_at: AwareDatetime
    notes: str | None = Field(default=None, max_length=1000)


class InspectionFailure(BaseModel):
    failure_reason: str | None = Field(default=None, max_length=1000)


class InspectionResponse(BaseModel):
    id: int
    equipment_id: int
    user_id: int
    status: str
    scheduled_at: datetime | None = None
    start_blocker: str | None = None
    notes: str | None = None
    failure_reason: str | None = None
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class InspectionReminder(BaseModel):
    inspection_id: int
    equipment_name: str
    scheduled_at: datetime
    reminded_at: datetime
