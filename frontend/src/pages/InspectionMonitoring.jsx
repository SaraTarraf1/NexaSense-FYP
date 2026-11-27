
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import EquipmentLayout from "../components/EquipmentLayout.jsx";
import MonitoringConnection from "../components/MonitoringConnection.jsx";
import { useMonitoringClock, useMonitoringPoll } from "../hooks/useMonitoringPoll.js";
import ScheduledInspectionAction from "../components/ScheduledInspectionAction.jsx";

import {
  getInspectionById,
  getLatestSensorReadings,
  getInspectionReadings,
  completeInspection,
  cancelInspection,
  cancelInspectionBooking,
  failInspection,
  startScheduledInspection,
} from "../services/inspectionService.js";

import "./InspectionMonitoring.css";

const SENSOR_TYPES = [
  { type: "temperature", label: "Temperature", icon: "🌡️" },
  { type: "vibration", label: "Vibration", icon: "〰️" },
  { type: "thermal", label: "Thermal", icon: "🔥" },
];

const monotonicNow = () => performance.now();

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "—";
}

async function readInspection(inspectionId, signal) {
  const inspection = await getInspectionById(inspectionId, { signal });
  if (inspection.id !== inspectionId) {
    throw new Error("The monitoring update did not match this inspection.");
  }
  if (!inspection.started_at) return { inspection, latest: [], history: [] };

  const [latest, history] = await Promise.all([
    getLatestSensorReadings(inspectionId, { signal, includeObservation: true }),
    getInspectionReadings(inspectionId, 30, { signal }),
  ]);
  if (!Number.isFinite(Date.parse(latest.observed_at))) {
    throw new Error("The monitoring update contains an invalid timestamp.");
  }

  function matchingReadings(readings) {
    const matching = readings.filter((item) =>
      item.equipment_id === inspection.equipment_id && item.inspection_id === inspection.id
    );
    return Array.from(new Map(matching.map((item) => [item.id, item])).values());
  }
  return {
    inspection,
    latest: matchingReadings(latest.readings),
    history: matchingReadings(history),
    observed_at: latest.observed_at,
  };
}

function hasInspectionUpdates({ inspection }) {
  return inspection.status === "active" || inspection.status === "scheduled";
}

export default function InspectionMonitoring() {
  const { inspectionId } = useParams();
  return <InspectionDetails key={inspectionId} inspectionId={Number(inspectionId)} />;
}

function InspectionDetails({ inspectionId }) {
  const [processing, setProcessing] = useState(false);
  const [actionError, setActionError] = useState("");
  const { data, updateData, receivedMonotonicAt, ...connection } = useMonitoringPoll(inspectionId, readInspection, {
    enabled: !processing,
    shouldContinue: hasInspectionUpdates,
  });
  const { inspection, latest = [], history = [] } = data ?? {};
  const isScheduled = inspection?.status === "scheduled";
  const isActive = inspection?.status === "active";
  const cancelledBooking = inspection?.status === "cancelled" && !inspection.started_at;
  const now = useMonitoringClock(isScheduled, connection.receivedAt);
  const elapsedClock = useMonitoringClock(isActive, receivedMonotonicAt, monotonicNow);
  const observedAt = Date.parse(data?.observed_at);
  const serverNow = receivedMonotonicAt != null
    ? observedAt + (elapsedClock - receivedMonotonicAt)
    : NaN;

  async function handleBookingAction(action) {
    if (processing) return;
    if (action === "cancel" && !window.confirm("Cancel this inspection booking?")) return;

    setProcessing(action);
    setActionError("");
    const request = action === "start" ? startScheduledInspection : cancelInspectionBooking;
    try {
      const inspection = await request(inspectionId);
      updateData((data) => ({ ...data, inspection }));
    } catch (err) {
      setActionError(err.message);
    } finally {
      setProcessing(false);
    }
  }

  async function handleFinish(action) {
    const outcomes = {
      complete: { prompt: "Complete this inspection?", request: completeInspection },
      cancel: { prompt: "Cancel this inspection?", request: cancelInspection },
      fail: { request: failInspection },
    };
    const { prompt, request } = outcomes[action];
    let failureReason;
    if (action === "fail") {
      failureReason = window.prompt("Mark inspection as failed? Add an optional reason.");
      if (failureReason === null) return;
    } else if (!window.confirm(prompt)) {
      return;
    }

    setProcessing(true);
    setActionError("");

    try {
      const inspection = await request(inspectionId, failureReason);
      updateData((data) => ({ ...data, inspection }));
    } catch (err) {
      setActionError(err.message);
    } finally {
      setProcessing(false);
    }
  }

  return (
    <EquipmentLayout breadcrumb="Live Monitoring">
      <div className="monitoring-page">
        <div className="monitoring-header">
          <div>
            <Link to="/inspections">← All inspections</Link>
            <h1>Inspection #{inspectionId}</h1>
            <p>{isScheduled || cancelledBooking ? "Equipment inspection booking" : "Equipment sensor measurements"}</p>
          </div>

          {inspection && (
            <span className={`inspection-status ${inspection.status}`}>
              {inspection.status === "active" ? "In progress" : inspection.status}
            </span>
          )}
        </div>

        {(isActive || isScheduled || !data || connection.error) && <MonitoringConnection {...connection} />}
        {actionError && <p className="inspections-error" role="alert">{actionError}</p>}

        {inspection && (
          <section className="monitoring-details">
            <div>
              <span>Equipment ID</span>
              <Link to={`/equipment/${inspection.equipment_id}`}>#{inspection.equipment_id} · Equipment monitoring</Link>
            </div>
            {inspection.scheduled_at && (
              <div>
                <span>Scheduled for</span>
                <strong>{formatDate(inspection.scheduled_at)}</strong>
              </div>
            )}
            <div>
              <span>Started at</span>
              <strong>{formatDate(inspection.started_at)}</strong>
            </div>
            <div>
              <span>{cancelledBooking ? "Cancelled at" : inspection.status === "completed" ? "Completed at" : "Ended at"}</span>
              <strong>{formatDate(inspection.ended_at)}</strong>
            </div>
          </section>
        )}
        {inspection?.notes && (
          <section className="inspections-card">
            <h2>Inspection notes</h2>
            <p className="inspection-notes">{inspection.notes}</p>
          </section>
        )}
        {inspection?.failure_reason && (
          <section className="inspections-card">
            <h2>Failure reason</h2>
            <p className="inspection-notes">{inspection.failure_reason}</p>
          </section>
        )}

        {isScheduled && (
          <section className="inspections-card">
            <h2>Start inspection</h2>
            <ScheduledInspectionAction
              inspection={inspection}
              now={now}
              busy={Boolean(processing)}
              starting={processing === "start"}
              cancelling={processing === "cancel"}
              onStart={() => handleBookingAction("start")}
              onCancel={() => handleBookingAction("cancel")}
            />
          </section>
        )}

        {inspection && !isScheduled && !cancelledBooking && (
          <>
            <div className="monitoring-section-title">
              <h2>Sensor Measurements</h2>
              <span>{isActive ? "Latest validated readings" : "Final validated readings"}</span>
            </div>

            <section className="monitoring-sensors">
              {SENSOR_TYPES.map((sensor) => {
                const reading = latest.find(
                  (item) => item.sensor_type === sensor.type
                );

                const age = serverNow - Date.parse(reading?.timestamp);
                const threshold = reading?.freshness_threshold_seconds * 1000;
                const stale = isActive && reading && (
                  !Number.isFinite(age) || age < 0
                  || !Number.isFinite(threshold) || threshold <= 0 || age > threshold
                );

                return (
                  <article
                    className="monitoring-sensor-card"
                    key={sensor.type}
                  >
                    <div className="monitoring-sensor-heading">
                      <span>{sensor.icon}</span>
                      <h3>{sensor.label}</h3>
                    </div>

                    <div className="monitoring-sensor-value">
                      {reading?.value ?? "—"}
                      {reading?.value != null && (
                        <small> {reading.unit}</small>
                      )}
                    </div>

                    <span
                      className={`monitoring-validation ${
                        stale ? "stale" : reading ? "valid" : "missing"
                      }`}
                    >
                      {stale ? "Stale" : reading ? "Valid" : "No data"}
                    </span>

                    <p>
                      Last valid reading: {formatDate(reading?.timestamp)}
                    </p>
                  </article>
                );
              })}
            </section>

            {inspection?.status === "active" && (
              <section className="monitoring-actions">
                <button
                  className="monitoring-complete"
                  disabled={processing}
                  onClick={() => handleFinish("complete")}
                >
                  {processing ? "Processing..." : "Complete Inspection"}
                </button>

                <button
                  className="monitoring-cancel"
                  disabled={processing}
                  onClick={() => handleFinish("cancel")}
                >
                  Cancel Inspection
                </button>
                <button
                  type="button"
                  className="monitoring-fail"
                  disabled={processing}
                  onClick={() => handleFinish("fail")}
                >
                  Mark failed
                </button>
              </section>
            )}

            <section className="inspections-card">
              <h2>Recent Sensor Readings</h2>
              <p>Latest 30 measurements recorded in PostgreSQL.</p>

              <div className="inspections-table-wrapper">
                <table className="inspections-table">
                  <thead>
                    <tr>
                      <th>Sensor</th>
                      <th>Value</th>
                      <th>Status</th>
                      <th>Timestamp</th>
                    </tr>
                  </thead>

                  <tbody>
                    {history.map((reading) => (
                      <tr key={reading.id}>
                        <td>{reading.sensor_type}</td>
                        <td>
                          {reading.value ?? "—"} {reading.unit}
                        </td>
                        <td>{reading.validation_status}</td>
                        <td>{formatDate(reading.timestamp)}</td>
                      </tr>
                    ))}

                    {history.length === 0 && (
                      <tr>
                        <td colSpan="4">
                          No readings available yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </EquipmentLayout>
  );
}
