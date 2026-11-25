
"""
SQLAlchemy models for the NexaSense application.

Import models here so that Alembic can discover them
when generating database migrations.
"""

from app.models.user import User
from app.models.revoked_token import RevokedToken
from app.models.equipment import Equipment
from app.models.inspection import Inspection
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.models.fault_classification import FaultClassification

__all__ = [
    "User",
    "RevokedToken",
    "Equipment",
    "Inspection",
    "Sensor",
    "SensorReading",
    "FaultClassification",
]
