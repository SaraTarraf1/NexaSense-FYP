import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import EquipmentLayout from "../components/EquipmentLayout.jsx";
import ScheduledInspectionAction from "../components/ScheduledInspectionAction.jsx";
import { getAllEquipment } from "../services/equipmentService.js";
import {
  cancelInspectionBooking,
  getAllInspections,
  scheduleInspection,
  startInspection,
  startScheduledInspection,
} from "../services/inspectionService.js";

import "./Inspections.css";

const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

function localDateTime(date) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

function InspectionTime({ timestamp }) {
  if (!timestamp) return "—";
  return <time dateTime={timestamp}>{new Date(timestamp).toLocaleString()}</time>;
}

function EquipmentSelect({ id, items, value, onChange }) {
  return (
    <>
      <label htmlFor={id}>Equipment</label>
      <select
        id={id}
        value={items.some((item) => String(item.id) === value) ? value : ""}
        onChange={(event) => onChange(event.target.value)}
        required
      >
        <option value="">Select equipment</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name} — {item.equipment_type}
          </option>
        ))}
      </select>
    </>
  );
}

export default function Inspections() {
  const navigate = useNavigate();
  const { search } = useLocation();
  const entry = new URLSearchParams(search);
  const preset = entry.get("equipment") ?? "";
  const [equipment, setEquipment] = useState([]);
  const [inspections, setInspections] = useState([]);
  const [immediateEquipment, setImmediateEquipment] = useState(entry.get("mode") === "start" ? preset : "");
  const [scheduledEquipment, setScheduledEquipment] = useState(entry.get("mode") === "schedule" ? preset : "");
  const [scheduledTime, setScheduledTime] = useState("");
  const [notes, setNotes] = useState("");
  const [now, setNow] = useState(Date.now);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [scheduleError, setScheduleError] = useState("");
  const [rowError, setRowError] = useState(null);

  const hasScheduledInspections = inspections.some((inspection) => inspection.status === "scheduled");

  useEffect(() => {
    let active = true;
    Promise.all([getAllEquipment(), getAllInspections()])
      .then(([equipmentData, inspectionData]) => {
        if (!active) return;
        setEquipment(equipmentData);
        setInspections(inspectionData);
        setNow(Date.now());
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!hasScheduledInspections) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [hasScheduledInspections]);

  useEffect(() => {
    if (!hasScheduledInspections || pending !== null) return;

    let active = true;
    let refreshing = false;
    async function refreshInspections() {
      if (refreshing) return;
      refreshing = true;
      try {
        const data = await getAllInspections();
        if (active) setInspections(data);
      } catch {
        // Keep the last visible schedule while the connection recovers.
      } finally {
        refreshing = false;
      }
    }

    const timer = setInterval(refreshInspections, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [hasScheduledInspections, pending]);

  function beginAction(action) {
    setPending(action);
    setError("");
    setNotice("");
  }

  async function start(action, request) {
    if (pending !== null) return;
    beginAction(action);
    setRowError(null);
    try {
      const inspection = await request();
      navigate(`/inspections/${inspection.id}`);
    } catch (err) {
      if (typeof action === "number") {
        setRowError({ id: action, message: err.message });
      } else {
        setError(err.message);
      }
    } finally {
      setPending(null);
    }
  }

  async function handleCancelBooking(inspectionId) {
    if (pending !== null || !window.confirm("Cancel this inspection booking?")) return;
    beginAction(`cancel-${inspectionId}`);
    setRowError(null);

    try {
      const updated = await cancelInspectionBooking(inspectionId);
      setInspections((previous) => previous.map((item) => item.id === updated.id ? updated : item));
      setNotice("Booking cancelled.");
    } catch (err) {
      setRowError({ id: inspectionId, message: err.message });
    } finally {
      setPending(null);
    }
  }

  async function handleSchedule(event) {
    event.preventDefault();
    if (pending !== null) return;
    setScheduleError("");
    setNotice("");
    const date = new Date(scheduledTime);
    if (!Number.isFinite(date.getTime()) || localDateTime(date) !== scheduledTime) {
      setScheduleError("Choose a valid date and time in your local time zone.");
      return;
    }
    if (date.getTime() <= Date.now()) {
      setScheduleError("Choose a date and time in the future.");
      return;
    }

    beginAction("schedule");
    try {
      const inspection = await scheduleInspection(Number(scheduledEquipment), date.toISOString(), notes.trim());
      setInspections((previous) => [inspection, ...previous]);
      setNow(Date.now());
      setScheduledTime("");
      setNotes("");
      setNotice("Inspection scheduled. It will be available to start manually at the planned time.");
    } catch (err) {
      setScheduleError(err.message);
    } finally {
      setPending(null);
    }
  }

  const activeEquipment = equipment.filter((item) => item.status === "active");
  const nameById = new Map(equipment.map((item) => [item.id, item.name]));
  const equipmentName = (id) => nameById.get(id) ?? `Equipment #${id}`;
  const scheduled = inspections
    .filter((inspection) => inspection.status === "scheduled")
    .sort((a, b) => Date.parse(a.scheduled_at) - Date.parse(b.scheduled_at) || a.id - b.id);
  const history = inspections.filter((inspection) => inspection.status !== "scheduled");

  return (
    <EquipmentLayout breadcrumb="Inspections">
      <div className="inspections-page">
        <header className="inspections-header">
          <h1>Equipment inspections</h1>
        </header>

        {error && <p className="inspections-error" role="alert">{error}</p>}
        {notice && <p className="inspections-success" role="status">{notice}</p>}
        {loading && <p role="status">Loading equipment and inspections…</p>}
        {!loading && activeEquipment.length === 0 && (
          <p>No active equipment available. <Link to="/equipment">View equipment</Link></p>
        )}

        <div className="inspections-form-grid">
          <section className="inspections-card">
            <h2>Start new inspection</h2>
            <form onSubmit={(event) => {
              event.preventDefault();
              void start("immediate", () => startInspection(Number(immediateEquipment)));
            }}>
              <EquipmentSelect
                id="inspection-equipment"
                items={activeEquipment}
                value={immediateEquipment}
                onChange={setImmediateEquipment}
              />
              <button type="submit" disabled={loading || pending !== null || activeEquipment.length === 0}>
                {pending === "immediate" ? "Starting…" : "Start Inspection"}
              </button>
            </form>
          </section>
          <section className="inspections-card">
            <h2>Schedule inspection</h2>
            <form onSubmit={handleSchedule}>
              <EquipmentSelect
                id="schedule-equipment"
                items={activeEquipment}
                value={scheduledEquipment}
                onChange={setScheduledEquipment}
              />
              <label htmlFor="schedule-time">Scheduled date and time</label>
              <input
                id="schedule-time"
                type="datetime-local"
                value={scheduledTime}
                min={localDateTime(new Date(now))}
                onChange={(event) => setScheduledTime(event.target.value)}
                aria-describedby="schedule-time-zone"
                required
              />
              <small id="schedule-time-zone">Time zone {timeZone}</small>
              {scheduleError && <p className="inspections-error" role="alert">{scheduleError}</p>}
              <label htmlFor="schedule-notes">Notes (optional)</label>
              <textarea
                id="schedule-notes"
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                maxLength={1000}
                rows={3}
              />
              <button type="submit" disabled={loading || pending !== null || activeEquipment.length === 0}>
                {pending === "schedule" ? "Saving…" : "Save scheduled inspection"}
              </button>
            </form>
          </section>
        </div>

        {!loading && (
          <>
            <section className="inspections-card">
              <h2>Scheduled inspections</h2>
              {scheduled.length === 0 ? <p>No scheduled inspections.</p> : (
                <div className="inspections-table-wrapper">
                  <table className="inspections-table" aria-label="Scheduled inspections">
                    <thead>
                      <tr><th>Inspection</th><th>Equipment</th><th>Scheduled for</th><th>Status</th><th>Notes</th><th>Action</th></tr>
                    </thead>
                    <tbody>
                      {scheduled.map((inspection) => (
                        <tr key={inspection.id}>
                          <td><Link to={`/inspections/${inspection.id}`}>#{inspection.id}</Link></td>
                          <td>{equipmentName(inspection.equipment_id)}</td>
                          <td><InspectionTime timestamp={inspection.scheduled_at} /></td>
                          <td><span className="inspection-status scheduled">Scheduled</span></td>
                          <td className="inspection-notes">{inspection.notes || "—"}</td>
                          <td>
                            <ScheduledInspectionAction
                              inspection={inspection}
                              now={now}
                              busy={pending !== null}
                              starting={pending === inspection.id}
                              cancelling={pending === `cancel-${inspection.id}`}
                              onCancel={() => handleCancelBooking(inspection.id)}
                              onStart={() => start(inspection.id, () => startScheduledInspection(inspection.id))}
                            />
                            {rowError?.id === inspection.id && (
                              <p className="inspections-error" role="alert">{rowError.message}</p>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="inspections-card">
              <h2>Inspection history</h2>
              {history.length === 0 ? <p>No inspection history yet.</p> : (
                <div className="inspections-table-wrapper">
                  <table className="inspections-table" aria-label="Inspection history">
                    <thead>
                      <tr><th>Inspection</th><th>Equipment</th><th>Status</th><th>Scheduled for</th><th>Started at</th><th>Completed at / ended</th><th>Action</th></tr>
                    </thead>
                    <tbody>
                      {history.map((inspection) => (
                        <tr key={inspection.id}>
                          <td>#{inspection.id}</td>
                          <td>{equipmentName(inspection.equipment_id)}</td>
                          <td>
                            <span className={`inspection-status ${inspection.status}`}>
                              {inspection.status === "active" ? "In progress" : inspection.status}
                            </span>
                          </td>
                          <td><InspectionTime timestamp={inspection.scheduled_at} /></td>
                          <td><InspectionTime timestamp={inspection.started_at} /></td>
                          <td><InspectionTime timestamp={inspection.ended_at} /></td>
                          <td>
                            <Link to={`/inspections/${inspection.id}`}>
                              {inspection.status === "completed" ? "View results" : "View inspection"}
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </EquipmentLayout>
  );
}
