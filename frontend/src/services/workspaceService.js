const API_URL = "http://127.0.0.1:8000";

export function getDashboard(_resourceId, signal) {
  return workspaceRequest("/dashboard", { signal });
}

export async function workspaceRequest(endpoint, { pdf = false, ...options } = {}) {
  const token = sessionStorage.getItem("nexasense_token");
  let response;
  try {
    response = await fetch(`${API_URL}/api${endpoint}`, {
      ...options,
      cache: "no-store",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new Error("Unable to connect to the server. Please try again.", { cause: error });
  }
  if (response.status === 401) {
    sessionStorage.removeItem("nexasense_token");
    window.location.replace("/login");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw Object.assign(new Error(typeof body?.detail === "string" ? body.detail : "The request could not be completed."), { status: response.status });
  }
  return pdf ? response.blob() : response.json();
}

export function getEligibleInspections(equipment, offset, signal) {
  return workspaceRequest(`/reports/eligible/${equipment}?offset=${offset}`, { signal });
}

export function getReports(equipment, offset, signal) {
  const params = new URLSearchParams({ offset });
  if (equipment) params.set("equipment_id", equipment);
  return workspaceRequest(`/reports?${params}`, { signal });
}

export function generateReport(equipment, inspection, signal) {
  return workspaceRequest("/reports", {
    method: "POST", signal,
    body: JSON.stringify({ equipment_id: Number(equipment), inspection_id: Number(inspection) }),
  });
}

export function getReport(id, signal) {
  return workspaceRequest(`/reports/${id}`, { signal });
}

export async function downloadReport(id, signal) {
  const blob = await workspaceRequest(`/reports/${id}/pdf`, { signal, pdf: true });
  if (signal?.aborted) return;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `nexasense-report-${id}.pdf`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
