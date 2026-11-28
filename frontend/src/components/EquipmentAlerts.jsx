import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { closeEquipmentAlert, getEquipmentAlert, getEquipmentAlerts } from "../services/equipmentService";
import { sensorLabel } from "../utils/sensorLabels";
import "./EquipmentAlerts.css";

const REFRESH_MS = 5000;
const ALERT_TYPES = {
  anomaly: "Sensor anomaly",
  fault: "Fault classification",
  health: "Health assessment",
};
const SEVERITY_LABELS = { warning: "Warning", critical: "Critical" };
const DELIVERY_LABELS = { pending: "Pending", delivered: "Delivered", failed: "Failed" };
const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" });

function AlertTime({ timestamp }) {
  return <time dateTime={timestamp}>{dateFormat.format(new Date(timestamp))}</time>;
}

function AlertEvidence({ equipmentId, alertId }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    getEquipmentAlert(equipmentId, alertId, { signal: controller.signal })
      .then((result) => {
        if (!controller.signal.aborted) setDetail(result);
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(err.message);
      });
    return () => controller.abort();
  }, [equipmentId, alertId, attempt]);

  function retry() {
    setError("");
    setAttempt((value) => value + 1);
  }

  return (
    <section className="equipment-alert-evidence">
      <h3>Supporting readings</h3>
      {error && (
        <div className="equipment-alert-error">
          <p role="alert">{error}</p>
          <button className="eq-text-link" onClick={retry} type="button">Retry readings</button>
        </div>
      )}
      {!detail && !error && <p role="status">Loading supporting readings…</p>}
      {detail?.evidence.length === 0 && <p>Supporting readings are unavailable.</p>}
      {detail?.evidence.length > 0 && (
        <ul className="equipment-alert-evidence-list" role="list">
          {detail.evidence.map((reading) => (
            <li key={reading.reading_id}>
              <div>
                <span>{sensorLabel(reading.sensor_type)}</span>
                {reading.reading_id === detail.source_reading_id && (
                  <small className="equipment-alert-trigger">Trigger reading</small>
                )}
                <AlertTime timestamp={reading.timestamp} />
              </div>
              <strong>{reading.value} {reading.unit}</strong>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function NotificationDelivery({ notifications }) {
  return (
    <section className="equipment-alert-delivery">
      <h3>Notification delivery</h3>
      {notifications.length === 0 ? (
        <p>No delivery record is available.</p>
      ) : (
        <ul className="equipment-alert-delivery-list" role="list">
          {notifications.map((notification) => (
            <li key={notification.channel}>
              <span>{notification.channel === "in_app" ? "In-app" : notification.channel}</span>
              <strong data-delivery={notification.status}>{DELIVERY_LABELS[notification.status]}</strong>
              {notification.attempted_at && <AlertTime timestamp={notification.attempted_at} />}
              {notification.error_message && <p>{notification.error_message}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function EquipmentAlertItem({ equipmentId, alert, onClosed }) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const notificationStatus = ["failed", "pending", "delivered"].find((status) =>
    alert.notifications.some((notification) => notification.status === status)
  );

  async function close() {
    setBusy(true);
    setError("");
    try {
      await closeEquipmentAlert(equipmentId, alert.id);
      onClosed(alert.id);
    } catch (error) {
      setError(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className={`equipment-alert equipment-alert-${alert.severity}`}>
      <details onToggle={(event) => setExpanded(event.currentTarget.open)}>
        <summary className="equipment-alert-summary">
          <span className="equipment-alert-content">
            <span className="equipment-alert-labels">
              <span className="equipment-alert-severity">{SEVERITY_LABELS[alert.severity]}</span>
              <span>{ALERT_TYPES[alert.event_type]}</span>
              <span>{alert.status === "open" ? "Open" : "Closed"}</span>
              {notificationStatus && (
                <span data-delivery={notificationStatus}>Notification {notificationStatus}</span>
              )}
            </span>
            <strong>{alert.description}</strong>
          </span>
          <span className="equipment-alert-summary-end">
            <AlertTime timestamp={alert.created_at} />
            <span className="equipment-alert-chevron" aria-hidden="true" />
          </span>
        </summary>
        {expanded && (
          <div className="equipment-alert-details">
            <dl className="equipment-alert-meta">
              <div><dt>Inspection</dt><dd><Link to={`/inspections/${alert.inspection_id}`}>#{alert.inspection_id}</Link></dd></div>
              <div><dt>Alert status</dt><dd>{alert.status}</dd></div>
              {alert.health_assessment_id !== null && alert.health_assessment_id !== undefined && (
                <div><dt>Health assessment</dt><dd>#{alert.health_assessment_id}</dd></div>
              )}
            </dl>
            {alert.status === "open" && <button type="button" className="eq-text-link" onClick={close} disabled={busy}>
              {busy ? "Closing alert…" : "Close alert"}
            </button>}
            {error && <p role="alert">{error}</p>}
            <div className="equipment-alert-detail-grid">
              <AlertEvidence equipmentId={equipmentId} alertId={alert.id} />
              <NotificationDelivery notifications={alert.notifications} />
            </div>
          </div>
        )}
      </details>
    </li>
  );
}

export default function EquipmentAlerts({ equipmentId, status }) {
  const [beforeId, setBeforeId] = useState(null);
  const [page, setPage] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    let timer;

    async function loadAlerts() {
      try {
        const result = await getEquipmentAlerts(equipmentId, {
          beforeId,
          status,
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setPage(result);
          setError("");
        }
      } catch (err) {
        if (!controller.signal.aborted) setError(err.message);
      } finally {
        if (beforeId === null && !controller.signal.aborted) {
          timer = setTimeout(loadAlerts, REFRESH_MS);
        }
      }
    }

    loadAlerts();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [equipmentId, beforeId, attempt, status]);

  function showPage(cursor) {
    setPage(null);
    setError("");
    setBeforeId(cursor);
  }

  function onClosed(id) {
    setPage(previous => previous ? {
      ...previous,
      items: status === "open"
        ? previous.items.filter(item => item.id !== id)
        : previous.items.map(item => item.id === id ? { ...item, status: "closed" } : item),
    } : previous);
    setAttempt(value => value + 1);
  }

  return (
    <section className="eq-detail-card equipment-alerts" aria-labelledby="equipment-alerts-heading">
      <header className="eq-card-heading">
        <h2 id="equipment-alerts-heading">Equipment alerts</h2>
      </header>
      {!page && !error && <p role="status">Loading alerts…</p>}
      {error && (
        <div className="equipment-alert-error">
          <p role="alert">{error}</p>
          <button className="eq-text-link" type="button" onClick={() => {
            setError("");
            setAttempt((value) => value + 1);
          }}>
            Retry alerts
          </button>
        </div>
      )}
      {page?.items.length === 0 && (
        <div className="eq-detail-empty">
          <h3>{beforeId === null ? "No alerts recorded" : "No older alerts"}</h3>
          {beforeId === null && <p>Alerts appear here when an inspection detects an anomaly or a potential fault.</p>}
        </div>
      )}
      {page?.items.length > 0 && (
        <ul className="equipment-alert-list" role="list">
          {page.items.map((alert) => (
            <EquipmentAlertItem key={alert.id} equipmentId={equipmentId} alert={alert} onClosed={onClosed} />
          ))}
        </ul>
      )}
      {(beforeId !== null || page?.next_before_id) && (
        <nav className="equipment-alert-pages" aria-label="Alert pages">
          {beforeId !== null && (
            <button className="eq-text-link" type="button" onClick={() => showPage(null)}>Back to latest</button>
          )}
          {page?.next_before_id && (
            <button className="eq-text-link" type="button" onClick={() => showPage(page.next_before_id)}>
              Older alerts
            </button>
          )}
        </nav>
      )}
    </section>
  );
}
