
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import EquipmentLayout from "../components/EquipmentLayout.jsx";
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

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "—";
}

export default function InspectionMonitoring() {
  const { inspectionId } = useParams();
  return <InspectionDetails key={inspectionId} inspectionId={inspectionId} />;
}

function InspectionDetails({ inspectionId }) {
  const [inspection, setInspection] = useState(null);
  const [latest, setLatest] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const [actionError, setActionError] = useState("");
  const [now, setNow] = useState(Date.now);
  const isScheduled = inspection?.status === "scheduled";
  const cancelledBooking = inspection?.status === "cancelled" && !inspection.started_at;

  useEffect(() => {
    if (!isScheduled) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [isScheduled]);

  async function handleBookingAction(action) {
    if (processing) return;
    if (action === "cancel" && !window.confirm("Cancel this inspection booking?")) return;

    setProcessing(action);
    setActionError("");
    const request = action === "start" ? startScheduledInspection : cancelInspectionBooking;
    try {
      setInspection(await request(inspectionId));
    } catch (err) {
      setActionError(err.message);
    } finally {
      setProcessing(false);
    }
  }

  useEffect(() => {
    if (processing) return;
    let cancelled = false;

    async function refresh() {
      try {
        const [inspectionData, latestData, historyData] =
          await Promise.all([
            getInspectionById(inspectionId),
            getLatestSensorReadings(inspectionId),
            getInspectionReadings(inspectionId, 30),
          ]);

        if (cancelled) return;

        setInspection(inspectionData);
        setLatest(latestData);
        setHistory(historyData);
        setError("");
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    refresh();

    const interval = window.setInterval(refresh, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [inspectionId, processing]);

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
    setError("");

    try {
      const updated = await request(inspectionId, failureReason);

      setInspection(updated);

      const [latestData, historyData] = await Promise.all([
        getLatestSensorReadings(inspectionId),
        getInspectionReadings(inspectionId, 30),
      ]);

      setLatest(latestData);
      setHistory(historyData);
    } catch (err) {
      setError(err.message);
    } finally {
      setProcessing(false);
    }
  }

  if (loading) {
    return (
      <EquipmentLayout breadcrumb="Live Monitoring">
        <p>Loading inspection...</p>
      </EquipmentLayout>
    );
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

        {error && (
          <div className="inspections-error" role="alert">
            {error}
          </div>
        )}

        {inspection && (
          <section className="monitoring-details">
            <div>
              <span>Equipment ID</span>
              <strong>#{inspection.equipment_id}</strong>
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
            {actionError && <p className="inspections-error" role="alert">{actionError}</p>}
          </section>
        )}

        {inspection && !isScheduled && !cancelledBooking && (
          <>
            <div className="monitoring-section-title">
              <h2>Sensor Measurements</h2>
              <span>
                {inspection?.status === "active"
                  ? "Refreshing every 5 seconds"
                  : "Final recorded measurements"}
              </span>
            </div>

            <section className="monitoring-sensors">
              {SENSOR_TYPES.map((sensor) => {
                const reading = latest.find(
                  (item) => item.sensor_type === sensor.type
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
                        reading?.validation_status || "missing"
                      }`}
                    >
                      {reading?.validation_status || "No data"}
                    </span>

                    <p>
                      Last updated: {formatDate(reading?.timestamp)}
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
