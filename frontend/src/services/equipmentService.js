
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
    throw new Error("Your session has expired. Please log in again.");
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

    throw new Error(message);
  }

  return response.json();
}

// POST /api/equipment
export async function registerEquipment(equipmentData) {
  return equipmentRequest("", {
    method: "POST",
    body: JSON.stringify(equipmentData),
  });
}

// GET /api/equipment
export async function getAllEquipment() {
  return equipmentRequest("", {
    method: "GET",
  });
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
