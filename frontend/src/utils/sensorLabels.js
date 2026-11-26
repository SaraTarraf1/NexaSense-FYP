const SENSOR_LABELS = {
  temperature: "Temperature",
  thermal: "Thermal temperature",
  vibration: "Vibration",
};

export function sensorLabel(sensorType) {
  return SENSOR_LABELS[sensorType] || sensorType;
}
