from datetime import timedelta
from typing import Literal


AlertSeverity = Literal["warning", "critical"]

ALERT_DUPLICATE_WINDOW = timedelta(seconds=60)
IN_APP_NOTIFICATION_CHANNEL = "in_app"

IDENTIFIED_FAULT_SEVERITIES: dict[str, AlertSeverity] = {
    "overheating": "critical",
    "electrical_overheating": "critical",
    "heating_system_overheating": "critical",
    "mechanical_stress": "warning",
    "pump_mechanical_fault": "warning",
    "ventilation_mechanical_fault": "warning",
}
UNRESOLVED_FAULT_SEVERITIES: dict[str, AlertSeverity] = {
    "unknown": "warning",
    "undetermined": "warning",
}


def get_anomaly_alert_severity(
    validation_status: str, detection_status: str
) -> AlertSeverity | None:
    if validation_status == "valid" and detection_status == "anomaly":
        return "warning"
    return None


def get_fault_alert_severity(
    classification_status: str, fault_type: str | None = None
) -> AlertSeverity | None:
    if classification_status == "identified":
        return IDENTIFIED_FAULT_SEVERITIES.get(fault_type or "")
    return UNRESOLVED_FAULT_SEVERITIES.get(classification_status)
