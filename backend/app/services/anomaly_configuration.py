from typing import TypedDict

from app.core.equipment_identifiers import identifier_prefix
from app.services.sensor_configuration import EQUIPMENT_SENSOR_MAPPING


class AnomalyRule(TypedDict):
    min_normal: float
    max_normal: float


# Prototype operating thresholds calibrated to the simulator's normal ranges.
DEFAULT_ANOMALY_RULES: dict[str, AnomalyRule] = {
    "temperature": {"min_normal": 20.0, "max_normal": 45.0},
    "vibration": {"min_normal": 0.5, "max_normal": 4.0},
    "thermal": {"min_normal": 25.0, "max_normal": 60.0},
}

EQUIPMENT_ANOMALY_RULES = {
    equipment_code: {
        sensor_type: DEFAULT_ANOMALY_RULES[sensor_type].copy()
        for sensor_type in sensor_types
    }
    for equipment_code, sensor_types in EQUIPMENT_SENSOR_MAPPING.items()
}


def get_anomaly_rule(equipment_type: str, sensor_type: str) -> AnomalyRule | None:
    equipment_code = identifier_prefix(equipment_type)
    return EQUIPMENT_ANOMALY_RULES.get(equipment_code, {}).get(sensor_type)
