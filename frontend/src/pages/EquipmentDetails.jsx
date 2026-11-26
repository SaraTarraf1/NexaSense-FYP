import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import EquipmentAlerts from "../components/EquipmentAlerts";
import EquipmentLayout from "../components/EquipmentLayout";
import { HealthStatusBadge } from "../components/EquipmentHealthAssessment";
import { useEquipmentMonitoring } from "../hooks/useEquipmentMonitoring";
import { getEquipmentById } from "../services/equipmentService";
import "./EquipmentDetails.css";
import { EquipmentMonitoringPanel } from "./EquipmentMonitoring";

const sensors = [
  { name: "Temperature", short: "Temp", unit: "°C", color: "temperature" },
  { name: "Humidity", short: "Humidity", unit: "%RH", color: "humidity" },
  { name: "Vibration", short: "Vibration", unit: "mm/s", color: "vibration" },
  { name: "Energy", short: "Energy", unit: "kWh", color: "energy" },
];
const tabs = [
  ["overview", "Overview"], ["inspections", "Inspections"],
  ["sensors", "Sensor history"], ["health", "Health & faults"],
  ["alerts", "Alerts"], ["profile", "Profile"],
];

function Icon({ name, ...props }) {
  const paths = {
    play: <path d="m8 5 10 7-10 7Z" />,
    calendar: <><rect x="4" y="5" width="16" height="16" rx="2" /><path d="M8 3v4m8-4v4M4 11h16" /></>,
    report: <><path d="M14 3H5v18h14V8ZM14 3v5h5M8 12h8m-8 4h6" /></>,
    clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    health: <><path d="m12 3 10 18H2Z" /><path d="M12 9v5m0 3v.1" /></>,
    tool: <path d="m14 6 4-4a6 6 0 0 1-7 8L4 18l3 3 8-8a6 6 0 0 0 7-7l-4 4Z" />,
  };
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.report}</svg>;
}

function formatDate(value, dateOnly = false) {
  if (!value) return "Not specified";
  return dateOnly ? new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { month: "short", year: "numeric" }) : new Date(value).toLocaleString();
}

function EmptyState({ title, children }) {
  return <div className="eq-detail-empty"><span className="eq-empty-icon"><Icon name="report" /></span><h3>{title}</h3><p>{children}</p></div>;
}

function SensorCards() {
  return <section aria-label="Latest sensor readings">
    <div className="equipment-section-heading"><h2>Latest readings</h2><span>Awaiting valid inspection readings</span></div>
    <div className="eq-reading-grid">{sensors.map(sensor => <article className={`eq-reading-card ${sensor.color}`} key={sensor.name}>
      <div className="eq-reading-heading"><h3>{sensor.name}</h3><span className="eq-status-tag">Missing</span></div>
      <p className="eq-reading-value">— <small>{sensor.unit}</small></p>
      <div className="eq-sparkline-empty" aria-label="No readings to chart"><span>No readings yet</span></div>
      <p className="eq-reading-note"><Icon name="clock" /> No valid value or timestamp</p>
    </article>)}</div>
  </section>;
}

export default function EquipmentDetails() {
  const { equipmentId } = useParams();
  const { state } = useLocation();
  const [record, setRecord] = useState(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [tab, setTab] = useState("overview");
  const [sensorIndex, setSensorIndex] = useState(0);
  useEffect(() => {
    let active = true;
    getEquipmentById(equipmentId).then(data => { if (active) { setRecord(data); setError(""); } })
      .catch(err => { if (active) setError(err.message); });
    return () => { active = false; };
  }, [equipmentId, attempt]);
  const equipment = record?.id === Number(equipmentId) ? record : null;
  const monitoringState = useEquipmentMonitoring(equipment?.id);
  const healthAssessment = monitoringState.monitoring?.health_assessment;
  const sensor = sensors[sensorIndex];

  function tabKeyDown(event, index) {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    else if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    else return;
    event.preventDefault();
    setTab(tabs[next][0]);
    document.getElementById(`eq-tab-${tabs[next][0]}`)?.focus();
  }

  const trend = <section className="eq-detail-card eq-trend-card">
    <div className="eq-card-heading"><div><h2>{sensor.name} trend</h2><p>Inspection history · no valid readings available</p></div></div>
    <div className="eq-sensor-picker" aria-label="Trend sensor">{sensors.map((item, index) => <button key={item.name} onClick={() => setSensorIndex(index)} aria-pressed={sensorIndex === index}><i className={item.color} />{item.short}</button>)}</div>
    <div className="eq-chart-empty"><div><span className={`eq-chart-unit ${sensor.color}`}>{sensor.unit}</span><strong>No {sensor.name.toLowerCase()} history yet</strong><p>Valid readings from inspections will appear here.</p></div></div>
    {tab !== "sensors" && <button className="eq-text-link" onClick={() => setTab("sensors")}>Open full sensor history <span aria-hidden="true">→</span></button>}
  </section>;
  return <EquipmentLayout breadcrumb={equipment?.identifier || "Equipment details"}>
    <div className="eq-details">
      <Link className="eq-back-button" to="/equipment"><span aria-hidden="true">←</span> Back to equipment</Link>
      {error && <div className="equipment-error" role="alert">{error} <button onClick={() => { setError(""); setAttempt(value => value + 1); }}>Try again</button> <Link to="/equipment">Back to equipment</Link></div>}
      {!equipment && !error && <p role="status">Loading equipment details...</p>}
      {equipment && !error && <>
        {state?.success && <p className="equipment-success" role="status">{state.success}</p>}
        <header className="eq-profile-header">
          <div className="eq-profile-main">
            <div className="eq-profile-code">{equipment.identifier}<span className="equipment-badge active">{equipment.status}</span></div>
            <h1>{equipment.name}</h1>
            <div className="equipment-meta">{[equipment.equipment_type, equipment.location, [equipment.manufacturer, equipment.model].filter(Boolean).join(" "), equipment.installation_date && `Installed ${formatDate(equipment.installation_date, true)}`].filter(Boolean).map((value, index) => <span key={index}>{value}</span>)}</div>
            <div className="eq-profile-actions">
              <button className="eq-primary-action" disabled title="Inspection execution is not connected yet"><Icon name="play" />Start inspection</button>
              <button disabled title="Inspection scheduling is not connected yet"><Icon name="calendar" />Schedule</button>
              <button disabled title="Report generation is not connected yet"><Icon name="report" />Generate report</button>
              <Link to={`/equipment/${equipment.id}/edit`}>Edit equipment</Link>
            </div>
            <p className="eq-controls-note">Inspection, scheduling and report controls are awaiting integration.</p>
          </div>
          <aside className="eq-health-summary">
            <p>Last recorded health</p>
            <strong><Icon name="health" /><HealthStatusBadge status={monitoringState.monitoring?.health_status} /></strong>
            <small>{healthAssessment
              ? formatDate(healthAssessment.assessed_at)
              : "Awaiting an assessment for this inspection"}</small>
          </aside>
        </header>
        <div className="eq-detail-tabs" role="tablist" aria-label="Equipment details">{tabs.map(([value, label], index) => <button key={value} id={`eq-tab-${value}`} role="tab" aria-selected={tab === value} aria-controls="eq-detail-panel" tabIndex={tab === value ? 0 : -1} onKeyDown={event => tabKeyDown(event, index)} onClick={() => setTab(value)}>{label}</button>)}</div>
        <div id="eq-detail-panel" role="tabpanel" aria-labelledby={`eq-tab-${tab}`} tabIndex={0}>
          {tab === "overview" && <EquipmentMonitoringPanel {...monitoringState} />}
          {tab === "sensors" && <><SensorCards /><div className="eq-history-full">{trend}</div></>}
          {tab === "health" && <EquipmentMonitoringPanel {...monitoringState} healthAndFaults />}
          {tab === "inspections" && <section className="eq-detail-card"><h2>Inspections</h2><EmptyState title="Inspection history is unavailable">Inspections for this equipment will appear when the inspection service is connected.</EmptyState></section>}
          {tab === "alerts" && <EquipmentAlerts key={equipment.id} equipmentId={equipment.id} />}
          {tab === "profile" && <section className="eq-detail-card"><div className="eq-card-heading"><h2>Equipment profile</h2><Link className="eq-text-link" to={`/equipment/${equipment.id}/edit`}>Edit profile →</Link></div><dl className="equipment-details-grid">{[["Identifier", equipment.identifier], ["Name", equipment.name], ["Type", equipment.equipment_type], ["Location", equipment.location], ["Manufacturer", equipment.manufacturer], ["Model", equipment.model], ["Serial number", equipment.serial_number], ["Status", equipment.status], ["Installation date", formatDate(equipment.installation_date, true)], ["Registered on", formatDate(equipment.created_at)], ["Last updated", formatDate(equipment.updated_at)]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value || "Not specified"}</dd></div>)}</dl><div className="equipment-details-description"><span>Notes</span><p>{equipment.description || "No notes provided."}</p></div></section>}
        </div>
      </>}
    </div>
  </EquipmentLayout>;
}
