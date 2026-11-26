
import math
from dataclasses import dataclass
from typing import Literal

from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading


ValidationStatus = Literal["valid", "invalid", "missing"]


@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    message: str | None


def validate_sensor_reading(
    sensor: Sensor,
    value: float | None,
) -> ValidationResult:
    """
    Validate a sensor measurement against the
    configured physical measurement limits.

    This function does not detect equipment anomalies.
    """

    if value is None:
        return ValidationResult(
            status="missing",
            message="No measurement received from sensor.",
        )

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ValidationResult(
            status="invalid",
            message="Sensor measurement must be numeric.",
        )

    if not math.isfinite(value):
        return ValidationResult(
            status="invalid",
            message="Sensor measurement must be finite.",
        )

    if value < sensor.min_value or value > sensor.max_value:
        return ValidationResult(
            status="invalid",
            message=(
                f"Measurement {value} {sensor.unit} is outside "
                f"sensor limits [{sensor.min_value}, "
                f"{sensor.max_value}] {sensor.unit}."
            ),
        )

    return ValidationResult(
        status="valid",
        message=None,
    )


def is_evaluated_measurement(reading: SensorReading) -> bool:
    return (
        reading.validation_status == "valid"
        and reading.id is not None
        and reading.equipment_id is not None
        and reading.inspection_id is not None
        and reading.value is not None
        and math.isfinite(reading.value)
        and reading.timestamp is not None
        and (
            (reading.detection_status == "normal" and reading.anomaly_type is None)
            or (
                reading.detection_status == "anomaly"
                and reading.anomaly_type in ("above_threshold", "below_threshold")
            )
        )
    )
