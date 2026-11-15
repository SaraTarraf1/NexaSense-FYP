
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InspectionCreate(BaseModel):
    equipment_id: int


class InspectionResponse(BaseModel):
    id: int
    equipment_id: int
    user_id: int
    status: str
    started_at: datetime
    ended_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
