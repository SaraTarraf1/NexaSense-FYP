from dataclasses import dataclass

from app.core.equipment_identifiers import identifier_prefix


@dataclass(frozen=True)
class FaultRule:
    rule_id: str
    equipment_codes: tuple[str, ...]
    required_high_sensors: tuple[str, ...]
    fault_type: str


# Prototype rules use the existing above_threshold anomaly result for each sensor.
FAULT_RULES = (
    FaultRule(
        rule_id="DR-001",
        equipment_codes=("AC", "HP", "GEN"),
        required_high_sensors=("temperature", "thermal"),
        fault_type="overheating",
    ),
    FaultRule(
        rule_id="DR-002",
        equipment_codes=("AC", "HP", "GEN"),
        required_high_sensors=("vibration", "temperature"),
        fault_type="mechanical_stress",
    ),
    FaultRule(
        rule_id="DR-003",
        equipment_codes=("EP",),
        required_high_sensors=("temperature", "thermal"),
        fault_type="electrical_overheating",
    ),
    FaultRule(
        rule_id="DR-004",
        equipment_codes=("WP",),
        required_high_sensors=("vibration", "temperature"),
        fault_type="pump_mechanical_fault",
    ),
    FaultRule(
        rule_id="DR-005",
        equipment_codes=("VU",),
        required_high_sensors=("vibration", "temperature"),
        fault_type="ventilation_mechanical_fault",
    ),
    FaultRule(
        rule_id="DR-006",
        equipment_codes=("WH",),
        required_high_sensors=("temperature", "thermal"),
        fault_type="heating_system_overheating",
    ),
)


def get_fault_rules(equipment_type: str) -> tuple[FaultRule, ...]:
    equipment_code = identifier_prefix(equipment_type)
    return tuple(rule for rule in FAULT_RULES if equipment_code in rule.equipment_codes)
