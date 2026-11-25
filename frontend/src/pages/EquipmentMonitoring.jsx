
import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router-dom";

import FaultClassifications from "../components/FaultClassifications";
import { getEquipmentMonitoring } from "../services/equipmentService";
import "./EquipmentMonitoring.css";

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "Not available";
}

export function EquipmentMonitoringPanel({ equipmentId, faultsOnly = false }) {


  const [monitoring, setMonitoring] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    let pending = false;

    async function loadMonitoring() {
      if (pending) return;
      pending = true;

      try {
        const data = await getEquipmentMonitoring(equipmentId);

        if (active) {
          setMonitoring(data);
          setError("");
        }
      } catch (err) {
        if (active) {
          setError(err.message);
        }
      } finally {
        pending = false;
        if (active) setLoading(false);
      }
    }

    loadMonitoring();

    const interval = setInterval(loadMonitoring, 5000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [equipmentId]);

  return (
    <section
      className="monitoring-page monitoring-embedded"
      aria-label={faultsOnly ? "Equipment faults" : "Equipment monitoring"}
    >
        {loading && <p role="status">Loading monitoring data...</p>}

        {error && (
          <div className="monitoring-error" role="alert">
            {error}
          </div>
        )}

        {monitoring && faultsOnly && <FaultClassifications monitoring={monitoring} />}

        {monitoring && !faultsOnly && (
          <>
            <header className="monitoring-header">
              <div>
                <h2>Equipment monitoring</h2>
                <p>
                  Monitoring · {monitoring.equipment_type}
                </p>
              </div>

              <span className={`monitoring-badge ${monitoring.monitoring_status}`}>
                {monitoring.monitoring_status.toUpperCase()}
              </span>
            </header>

            <section className="monitoring-overview">
              <article className="monitoring-info-card">
                <h2>Equipment Status</h2>
                <strong>{monitoring.equipment_status}</strong>
              </article>

              <article className="monitoring-info-card">
                <h2>Inspection Status</h2>
                <strong>
                  {monitoring.inspection_status || "No inspection"}
                </strong>
              </article>

              <article className="monitoring-info-card">
                <h2>Monitoring Mode</h2>
                <strong>
                  {monitoring.is_live ? "Live" : "Historical"}
                </strong>
              </article>
            </section>

            <section className="monitoring-section">
              <h2>Sensor Monitoring</h2>

              <div className="monitoring-sensor-grid">
                {monitoring.sensors.map((sensor) => (
                  <article
                    className="monitoring-sensor-card"
                    key={sensor.sensor_type}
                  >
                    <div className="monitoring-sensor-heading">
                      <h3>{sensor.sensor_type}</h3>

                      <span className={`monitoring-badge ${sensor.status}`}>
                        {sensor.status}
                      </span>
                    </div>

                    <div className="monitoring-sensor-value">
                      {sensor.value !== null
                        ? `${sensor.value} ${sensor.unit || ""}`
                        : "No data"}
                    </div>

                    <p>
                      Last valid reading:
                      <br />
                      {formatDate(sensor.timestamp)}
                    </p>

                    <p>
                      Freshness threshold:
                      {" "}{sensor.freshness_threshold_seconds}s
                    </p>
                  </article>
                ))}
              </div>

              {monitoring.sensors.length === 0 && (
                <p>No sensors are configured for this equipment.</p>
              )}
            </section>

            <section className="monitoring-section">
              <h2>Recent anomalies ({monitoring.anomalies.length})</h2>

              {monitoring.anomalies.length > 0 ? (
                <ul className="monitoring-anomaly-list" role="list">
                  {monitoring.anomalies.map((anomaly) => (
                    <li className="monitoring-anomaly" key={anomaly.reading_id}>
                      <div className="monitoring-anomaly-heading">
                        <div>
                          <h3>{anomaly.sensor_type}</h3>
                          <strong>{anomaly.value} {anomaly.unit}</strong>
                        </div>
                        <time dateTime={anomaly.timestamp}>
                          {formatDate(anomaly.timestamp)}
                        </time>
                      </div>
                      <p>{anomaly.message || "Reading outside the configured operating range."}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>
                  {monitoring.is_live
                    ? "No anomalies recorded for this inspection yet."
                    : "Start an inspection to see recent anomalies."}
                </p>
              )}
            </section>

            <FaultClassifications monitoring={monitoring} />

            <footer className="monitoring-footer">
              <p>
                Last valid sensor reading:
                {" "}{formatDate(monitoring.last_valid_reading_at)}
              </p>

              <p>Automatically refreshes every 5 seconds.</p>
            </footer>
          </>
        )}
      </section>
  );
}

export default function EquipmentMonitoring() {
  const { equipmentId } = useParams();
  return <Navigate to={`/equipment/${equipmentId}`} replace />;
}
