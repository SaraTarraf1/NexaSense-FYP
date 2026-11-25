from dataclasses import dataclass
from typing import Literal

from app.services.anomaly_configuration import get_anomaly_rule


DetectionStatus = Literal["normal", "anomaly", "not_evaluated"]
AnomalyType = Literal["below_threshold", "above_threshold"]


@dataclass(frozen=True)
class AnomalyDetectionResult:
    status: DetectionStatus
    anomaly_type: AnomalyType | None = None
    message: str | None = None
    min_threshold: float | None = None
    max_threshold: float | None = None


def detect_anomaly(
    equipment_type: str,
    sensor_type: str,
    value: float | None,
    validation_status: str,
) -> AnomalyDetectionResult:
    """Evaluate a validated sensor reading against prototype operating thresholds."""
    if validation_status != "valid" or value is None:
        return AnomalyDetectionResult(
            status="not_evaluated",
            message="Reading is invalid or missing.",
        )

    rule = get_anomaly_rule(equipment_type, sensor_type)
    if rule is None:
        return AnomalyDetectionResult(
            status="not_evaluated",
            message="No anomaly rule configured.",
        )

    minimum = rule["min_normal"]
    maximum = rule["max_normal"]

    if value < minimum:
        return AnomalyDetectionResult(
            status="anomaly",
            anomaly_type="below_threshold",
            message=f"{sensor_type} reading {value} is below threshold {minimum}.",
            min_threshold=minimum,
            max_threshold=maximum,
        )

    if value > maximum:
        return AnomalyDetectionResult(
            status="anomaly",
            anomaly_type="above_threshold",
            message=f"{sensor_type} reading {value} exceeds threshold {maximum}.",
            min_threshold=minimum,
            max_threshold=maximum,
        )

    return AnomalyDetectionResult(
        status="normal",
        message="Reading is within normal operating range.",
        min_threshold=minimum,
        max_threshold=maximum,
    )
