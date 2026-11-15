
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import EquipmentLayout from "../components/EquipmentLayout.jsx";

import {
  getInspectionById,
  getLatestSensorReadings,
  getInspectionReadings,
  completeInspection,
  cancelInspection,
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

  const [inspection, setInspection] = useState(null);
  const [latest, setLatest] = useState([]);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
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
  }, [inspectionId]);

  async function handleFinish(action) {
    const message =
      action === "complete"
        ? "Complete this inspection?"
        : "Cancel this inspection?";

    if (!window.confirm(message)) return;

    setProcessing(true);
    setError("");

    try {
      const updated =
        action === "complete"
          ? await completeInspection(inspectionId)
          : await cancelInspection(inspectionId);

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
            <p>Real-time equipment sensor monitoring</p>
          </div>

          {inspection && (
            <span className={`inspection-status ${inspection.status}`}>
              {inspection.status}
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
            <div>
              <span>Started</span>
              <strong>{formatDate(inspection.started_at)}</strong>
            </div>
            <div>
              <span>Ended</span>
              <strong>{formatDate(inspection.ended_at)}</strong>
            </div>
          </section>
        )}

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
      </div>
    </EquipmentLayout>
  );
}
