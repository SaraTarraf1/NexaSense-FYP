import { useEffect, useState } from "react";

import { getEquipmentMonitoring } from "../services/equipmentService";

export function useEquipmentMonitoring(equipmentId) {
  const [snapshot, setSnapshot] = useState(null);

  useEffect(() => {
    if (equipmentId == null) return;

    const controller = new AbortController();
    let timer;

    async function loadMonitoring() {
      try {
        const monitoring = await getEquipmentMonitoring(equipmentId, { signal: controller.signal });
        if (!controller.signal.aborted) setSnapshot({ equipmentId, monitoring, error: "" });
      } catch (err) {
        if (!controller.signal.aborted) {
          setSnapshot((previous) => ({
            equipmentId,
            monitoring: previous?.equipmentId === equipmentId ? previous.monitoring : null,
            error: err.message,
          }));
        }
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(loadMonitoring, 5000);
      }
    }

    loadMonitoring();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [equipmentId]);

  const current = snapshot?.equipmentId === equipmentId ? snapshot : null;
  return {
    monitoring: current?.monitoring ?? null,
    error: current?.error ?? "",
    loading: equipmentId != null && current === null,
  };
}
