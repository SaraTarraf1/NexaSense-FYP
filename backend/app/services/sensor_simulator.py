
import random
from dataclasses import dataclass
from typing import Literal


SimulationMode = Literal["normal", "abnormal", "invalid", "missing"]


@dataclass(frozen=True)
class SimulatedMeasurement:
    value: float | None
    mode: SimulationMode


# Developer-controlled simulation settings.
# Normal mode is the default.
SIMULATION_MODE: SimulationMode = "normal"


NORMAL_RANGES = {
    "temperature": (20.0, 45.0),
    "vibration": (0.5, 4.0),
    "thermal": (25.0, 60.0),
}


ABNORMAL_RANGES = {
    "temperature": (80.0, 110.0),
    "vibration": (15.0, 30.0),
    "thermal": (120.0, 200.0),
}


def simulate_sensor_reading(
    sensor_type: str,
    mode: SimulationMode | None = None,
) -> SimulatedMeasurement:
    """
    Generate a simulated sensor measurement.

    Simulation modes:
    - normal: realistic operating values
    - abnormal: unusual but physically measurable values
    - invalid: deliberately out-of-range measurement
    - missing: no measurement received

    Abnormal measurements are not automatically invalid.
    Fault detection is handled by later features.
    """

    selected_mode = mode or SIMULATION_MODE

    if sensor_type not in NORMAL_RANGES:
        raise ValueError(f"Unsupported sensor type: {sensor_type}")

    if selected_mode == "missing":
        return SimulatedMeasurement(value=None, mode="missing")

    if selected_mode == "invalid":
        invalid_values = {
            "temperature": 999.0,
            "vibration": -50.0,
            "thermal": 999.0,
        }

        return SimulatedMeasurement(
            value=invalid_values[sensor_type],
            mode="invalid",
        )

    if selected_mode == "normal":
        minimum, maximum = NORMAL_RANGES[sensor_type]

    elif selected_mode == "abnormal":
        minimum, maximum = ABNORMAL_RANGES[sensor_type]

    else:
        raise ValueError(f"Unsupported simulation mode: {selected_mode}")

    value = round(random.uniform(minimum, maximum), 2)

    return SimulatedMeasurement(
        value=value,
        mode=selected_mode,
    )
