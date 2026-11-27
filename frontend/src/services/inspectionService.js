
const API_URL = "http://127.0.0.1:8000";

async function inspectionRequest(endpoint, { includeObservation = false, ...options } = {}) {
  const token = sessionStorage.getItem("nexasense_token");

  if (!token) {
    throw new Error(
      "Your session has expired. Please log in again."
    );
  }

  let response;

  try {
    response = await fetch(
      `${API_URL}/api/inspections${endpoint}`,
      {
        ...options,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          ...options.headers,
        },
      }
    );
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
    let message = "Inspection operation failed.";

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
      // Keep the default error message.
    }

    throw Object.assign(new Error(message), { status: response.status });
  }

  const data = await response.json();
  return includeObservation
    ? { readings: data, observed_at: response.headers.get("X-Observed-At") }
    : data;
}


// POST /api/inspections
export async function startInspection(equipmentId) {
  return inspectionRequest("", {
    method: "POST",
    body: JSON.stringify({
      equipment_id: equipmentId,
    }),
  });
}


export function scheduleInspection(equipmentId, scheduledAt, notes) {
  return inspectionRequest("/schedule", {
    method: "POST",
    body: JSON.stringify({ equipment_id: equipmentId, scheduled_at: scheduledAt, notes }),
  });
}

export function startScheduledInspection(inspectionId) {
  return inspectionRequest(`/${inspectionId}/start`, { method: "POST" });
}


// GET /api/inspections
export async function getAllInspections() {
  return inspectionRequest("", {
    method: "GET",
  });
}


// GET /api/inspections/{inspection_id}
export async function getInspectionById(inspectionId, { signal } = {}) {
  return inspectionRequest(`/${inspectionId}`, { signal, cache: "no-store" });
}


// POST /api/inspections/{inspection_id}/complete
export async function completeInspection(inspectionId) {
  return inspectionRequest(`/${inspectionId}/complete`, {
    method: "POST",
  });
}


// POST /api/inspections/{inspection_id}/cancel
export async function cancelInspection(inspectionId) {
  return inspectionRequest(`/${inspectionId}/cancel`, {
    method: "POST",
  });
}


export function cancelInspectionBooking(inspectionId) {
  return inspectionRequest(`/${inspectionId}/cancel-booking`, { method: "POST" });
}


export function failInspection(inspectionId, failureReason) {
  return inspectionRequest(`/${inspectionId}/fail`, {
    method: "POST",
    body: JSON.stringify({ failure_reason: failureReason }),
  });
}


// GET /api/inspections/{inspection_id}/readings
export async function getInspectionReadings(
  inspectionId,
  limit = 100,
  { signal } = {}
) {
  return inspectionRequest(
    `/${inspectionId}/readings?limit=${limit}`,
    { signal, cache: "no-store" }
  );
}


// GET /api/inspections/{inspection_id}/readings/latest
export async function getLatestSensorReadings(inspectionId, { signal, includeObservation = false } = {}) {
  return inspectionRequest(
    `/${inspectionId}/readings/latest?validated_only=true`,
    { signal, includeObservation, cache: "no-store" }
  );
}


export function getInspectionReminders(signal) {
  return inspectionRequest("/reminders", { signal });
}
