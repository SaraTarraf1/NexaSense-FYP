
from app.core.equipment_identifiers import identifier_prefix


# Sensor types required for each equipment category.
# These configurations are controlled by developers.
EQUIPMENT_SENSOR_MAPPING = {
    "AC": ["temperature", "vibration", "thermal"],
    "EP": ["temperature", "thermal"],
    "WP": ["vibration", "temperature"],
    "VU": ["vibration", "temperature"],
    "WH": ["temperature", "thermal"],
    "HP": ["temperature", "vibration", "thermal"],
    "GEN": ["temperature", "vibration", "thermal"],
}


# Prototype sensor specifications.
# Limits represent physically acceptable measurement values,
# not thresholds for determining equipment health.
SENSOR_DEFINITIONS = {
    "temperature": {
        "name": "Temperature Sensor",
        "unit": "°C",
        "min_value": -40.0,
        "max_value": 125.0,
        "collection_interval_seconds": 5,
    },
    "vibration": {
        "name": "Vibration Sensor",
        "unit": "mm/s",
        "min_value": 0.0,
        "max_value": 100.0,
        "collection_interval_seconds": 5,
    },
    "thermal": {
        "name": "Thermal Temperature Sensor",
        "unit": "°C",
        "min_value": -20.0,
        "max_value": 300.0,
        "collection_interval_seconds": 5,
    },
}


def get_required_sensor_types(equipment_type: str) -> list[str]:
    """
    Automatically determine the required sensor types
    based on the equipment category.
    """

    prefix = identifier_prefix(equipment_type)

    return EQUIPMENT_SENSOR_MAPPING.get(prefix, [])
