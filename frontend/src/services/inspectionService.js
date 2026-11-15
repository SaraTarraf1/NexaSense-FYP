
const API_URL = "http://127.0.0.1:8000";

async function inspectionRequest(endpoint, options = {}) {
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

    throw new Error(
      "Your session has expired. Please log in again."
    );
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

    throw new Error(message);
  }

  return response.json();
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


// GET /api/inspections
export async function getAllInspections() {
  return inspectionRequest("", {
    method: "GET",
  });
}


// GET /api/inspections/{inspection_id}
export async function getInspectionById(inspectionId) {
  return inspectionRequest(`/${inspectionId}`, {
    method: "GET",
  });
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


// GET /api/inspections/{inspection_id}/readings
export async function getInspectionReadings(
  inspectionId,
  limit = 100
) {
  return inspectionRequest(
    `/${inspectionId}/readings?limit=${limit}`,
    {
      method: "GET",
    }
  );
}


// GET /api/inspections/{inspection_id}/readings/latest
export async function getLatestSensorReadings(inspectionId) {
  return inspectionRequest(
    `/${inspectionId}/readings/latest`,
    {
      method: "GET",
    }
  );
}
