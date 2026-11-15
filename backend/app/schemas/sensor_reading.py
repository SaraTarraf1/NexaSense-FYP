
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SensorReadingResponse(BaseModel):
    id: int
    inspection_id: int
    equipment_id: int
    sensor_id: int
    sensor_type: str
    value: float | None
    unit: str
    timestamp: datetime
    validation_status: str
    validation_message: str | None

    model_config = ConfigDict(from_attributes=True)
