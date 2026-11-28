
const API_URL = "http://127.0.0.1:8000";

async function equipmentRequest(endpoint, options = {}) {
  const token = sessionStorage.getItem("nexasense_token");

  if (!token) {
    throw new Error("Your session has expired. Please log in again.");
  }

  let response;

  try {
    response = await fetch(`${API_URL}/api/equipment${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...options.headers,
      },
    });
  } catch {
    throw new Error(
      "Unable to connect to the server. Please try again."
    );
  }

  if (response.status === 401) {
    sessionStorage.removeItem("nexasense_token");
    window.location.replace("/login");

    throw Object.assign(new Error("Your session has expired. Please log in again."), {
      status: 401,
    });
  }

  if (!response.ok) {
    let message = "Equipment operation failed. Please try again.";

    try {
      const errorData = await response.json();

      if (typeof errorData.detail === "string") {
        message = errorData.detail;
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail
          .map((error) => error.msg)
          .join(", ");
      }
    } catch {
      // Use the default error message.
    }

    throw Object.assign(new Error(message), { status: response.status });
  }

  return response.status === 204 ? null : response.json();
}

// POST /api/equipment
export async function registerEquipment(equipmentData) {
  return equipmentRequest("", {
    method: "POST",
    body: JSON.stringify(equipmentData),
  });
}

// GET /api/equipment
export async function getAllEquipment({ signal } = {}) {
  return equipmentRequest("", {
    method: "GET",
    signal,
  });
}

export function getEquipmentHistory(equipmentId, section, params, signal) {
  const path = section ? `/${section}` : "";
  return equipmentRequest(`/${equipmentId}/history${path}?${new URLSearchParams(params)}`, { signal });
}

// GET /api/equipment/{equipment_id}
export async function getEquipmentById(equipmentId) {
  return equipmentRequest(`/${equipmentId}`, {
    method: "GET",
  });
}

// PUT /api/equipment/{equipment_id}
export async function updateEquipment(equipmentId, equipmentData) {
  return equipmentRequest(`/${equipmentId}`, {
    method: "PUT",
    body: JSON.stringify(equipmentData),
  });
}

export async function deleteEquipment(equipmentId) {
  return equipmentRequest(`/${equipmentId}`, { method: "DELETE" });
}


// GET /api/equipment/{equipment_id}/monitoring
export function getEquipmentMonitoring(equipmentId, { signal } = {}) {
  return equipmentRequest(`/${equipmentId}/monitoring`, { signal, cache: "no-store" });
}

export function getEquipmentAlerts(equipmentId, { beforeId = null, status, signal } = {}) {
  const query = new URLSearchParams({ limit: "20" });
  if (beforeId !== null) query.set("before_id", String(beforeId));
  if (status) query.set("status", status);
  return equipmentRequest(`/${equipmentId}/alerts?${query}`, { signal });
}

export function getEquipmentAlert(equipmentId, alertId, { signal } = {}) {
  return equipmentRequest(`/${equipmentId}/alerts/${alertId}`, { signal });
}

export function closeEquipmentAlert(equipmentId, alertId) {
  return equipmentRequest(`/${equipmentId}/alerts/${alertId}/close`, { method: "POST" });
}
