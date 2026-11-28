import { useMonitoringClock, useMonitoringPoll } from "./useMonitoringPoll";
import { getEquipmentMonitoring } from "../services/equipmentService";

async function readEquipment(equipmentId, signal) {
  const data = await getEquipmentMonitoring(equipmentId, { signal });

  if (data.equipment_id !== equipmentId) {
    throw new Error(
      "The monitoring update did not match this equipment."
    );
  }

  if (!Number.isFinite(Date.parse(data.observed_at))) {
    throw new Error(
      "The monitoring update contains an invalid timestamp."
    );
  }

  return data;
}

export function ageMonitoringSnapshot(data, elapsed) {
  if (!data?.is_live) return data;
  const serverNow = Date.parse(data.observed_at) + Math.max(0, elapsed);
  const sensors = data.sensors.map((sensor) => {
    if (sensor.status !== "current") {
      return sensor;
    }

    const timestamp = Date.parse(sensor.timestamp);
    const age = serverNow - timestamp;

    const stale =
      !Number.isFinite(timestamp) ||
      age < 0 ||
      age > sensor.freshness_threshold_seconds * 1000;

    return {
      ...sensor,
      status: stale ? "stale" : "current",
    };
  });

  const statuses = new Set(
    sensors.map((sensor) => sensor.status)
  );

  const monitoringStatus =
    statuses.has("missing") || !statuses.size
      ? "missing"
      : statuses.has("stale")
        ? "stale"
        : "current";

  return { ...data, sensors, monitoring_status: monitoringStatus };
}

export function useEquipmentMonitoring(equipmentId) {
  const { data, receivedAt, ...status } = useMonitoringPoll(
    equipmentId,
    readEquipment
  );

  const now = useMonitoringClock(data?.is_live, receivedAt);

  const monitoring = ageMonitoringSnapshot(data, now - receivedAt);

  return {
    ...status,
    receivedAt,
    monitoring,
  };
}