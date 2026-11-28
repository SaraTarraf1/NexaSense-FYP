import { Link } from "react-router-dom";
import EquipmentLayout from "../components/EquipmentLayout";
import { HealthStatusBadge } from "../components/EquipmentHealthAssessment";
import MonitoringConnection from "../components/MonitoringConnection";
import { ageMonitoringSnapshot } from "../hooks/useEquipmentMonitoring";
import { useMonitoringClock, useMonitoringPoll } from "../hooks/useMonitoringPoll";
import { getDashboard } from "../services/workspaceService";
import { HEALTH_LABELS } from "../utils/healthStatus";
import { sensorLabel } from "../utils/sensorLabels";
import "./Dashboard.css";

const inspectionLabels = {
  scheduled: "Scheduled", active: "In progress", completed: "Completed", failed: "Failed", cancelled: "Cancelled",
};

const time = (timestamp) => timestamp ? <time dateTime={timestamp}>{new Date(timestamp).toLocaleString()}</time> : "—";
const monotonicNow = () => performance.now();

function InspectionStatus({ status }) {
  return <span className={`ops-status ${status}`}>{inspectionLabels[status] ?? status}</span>;
}

function Metrics({ overview }) {
  const { equipment, alerts, inspections } = overview;
  return <div className="ops-metrics">
    <article className="ops-card ops-metric">
      <Link to="/equipment">Registered equipment</Link><strong>{equipment.total}</strong>
      <p>{equipment.active} active · {equipment.inactive} inactive</p>
    </article>
    <article className="ops-card ops-metric">
      <Link to="/alerts">Open alerts</Link><strong>{alerts.total}</strong>
      <p><span className="ops-warning">{alerts.warning} warning</span> · <span className="ops-critical">{alerts.critical} critical</span></p>
    </article>
    <article className="ops-card ops-metric">
      <Link to="/inspections">Inspections in progress</Link><strong>{inspections.active}</strong>
      <p>{inspections.scheduled} scheduled · {inspections.completed} completed</p>
    </article>
  </div>;
}

function HealthDistribution({ counts, total }) {
  return <section className="ops-card">
    <h2>Equipment health</h2>
    <p>Latest recorded assessment per equipment.</p>
    {total > 0 && <div className="ops-health-bar" aria-hidden="true">
      {Object.keys(HEALTH_LABELS).map(status => counts[status] > 0 &&
        <span key={status} className={status} style={{ flexGrow: counts[status] }} />)}
    </div>}
    <ul className="ops-health-legend">{Object.keys(HEALTH_LABELS).map(status =>
      <li key={status}><HealthStatusBadge status={status} /><strong>{counts[status]}</strong></li>
    )}</ul>
  </section>;
}

function Attention({ items }) {
  return <section className="ops-card">
    <h2>Equipment requiring attention</h2>
    {items.length === 0 ? <p>No equipment currently requires attention.</p> :
      <ul className="ops-attention-list">{items.map(item => <li key={item.equipment_id}>
        <div><Link to={`/equipment/${item.equipment_id}`}>{item.equipment_name}</Link>
          <p>{item.reasons.join(" · ")}</p></div>
        <div><HealthStatusBadge status={item.health_status} />
          {item.open_alerts > 0 && <Link to={`/alerts?equipment=${item.equipment_id}&status=open`}>{item.open_alerts} open</Link>}
        </div>
      </li>)}</ul>}
  </section>;
}

function Monitoring({ snapshots, connection }) {
  const elapsedClock = useMonitoringClock(snapshots.some(item => item.is_live), connection.receivedMonotonicAt, monotonicNow);
  const age = elapsedClock - (connection.receivedMonotonicAt ?? elapsedClock);
  return <section className="ops-card">
    <div className="ops-section-header"><h2>Latest monitoring</h2><Link to="/monitoring">Open monitoring</Link></div>
    {!snapshots.some(item => item.is_live) && <p>No active inspection in this account.</p>}
    {snapshots.length === 0 && <p>Sensor measurements will appear after an inspection starts.</p>}
    <div className="ops-monitoring">{snapshots.map(snapshot => {
      const item = ageMonitoringSnapshot(snapshot, age);
      return <article className="ops-monitor" key={item.equipment_id}>
        <header>
          <Link to={`/equipment/${item.equipment_id}/monitoring`}>{item.equipment_name}</Link>
          <span className={`ops-mode ${item.is_live ? "live" : ""}`}>{item.is_live ? "Live inspection" : "Historical"}</span>
        </header>
        <div className="ops-monitor-status">
          <Link to={`/inspections/${item.inspection_id}`}>Inspection #{item.inspection_id}</Link>
          <InspectionStatus status={item.inspection_status} />
          <HealthStatusBadge status={item.health_status} />
        </div>
        {item.sensors.length ? <dl>{item.sensors.map(sensor => <div key={sensor.sensor_type}>
          <dt>{sensorLabel(sensor.sensor_type)}</dt>
          <dd>{sensor.value == null ? "No valid value" : `${sensor.value} ${sensor.unit}`}</dd>
          <p>{item.is_live ? { current: "Current", stale: "Outdated", missing: "Missing" }[sensor.status] : sensor.value == null ? "Missing" : "Recorded"} · {time(sensor.timestamp)}</p>
        </div>)}</dl> : <p>No sensors configured.</p>}
        {item.is_live && <p>{item.anomalies.length} recent anomalies · {item.faults.length} recent fault classifications</p>}
        {item.anomalies[0]?.message && <p>{item.anomalies[0].message}</p>}
        {item.faults[0]?.message && <p>{item.faults[0].message}</p>}
      </article>;
    })}</div>
  </section>;
}

function RecentInspections({ items, counts }) {
  return <section className="ops-card">
    <div className="ops-section-header"><h2>Recent inspection activity</h2><Link to="/inspections">All inspections</Link></div>
    <ul className="ops-inspection-totals">{Object.entries(inspectionLabels).map(([status, label]) =>
      <li key={status}><InspectionStatus status={status} /> <strong aria-label={`${counts[status]} ${label.toLowerCase()}`}>{counts[status]}</strong></li>
    )}</ul>
    {items.length > 0 ? <div className="ops-table-wrapper"><table>
      <thead><tr>{["Inspection", "Equipment", "Status", "Scheduled", "Started", "Last activity"].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
      <tbody>{items.map(item => <tr key={item.id}>
        <th scope="row"><Link to={`/inspections/${item.id}`}>#{item.id}</Link></th>
        <td><Link to={`/equipment/${item.equipment_id}`}>{item.equipment_name}</Link></td>
        <td><InspectionStatus status={item.status} /></td><td>{time(item.scheduled_at)}</td>
        <td>{time(item.started_at)}</td><td>{time(item.activity_at)}</td>
      </tr>)}</tbody>
    </table></div> : <p>No inspection activity recorded.</p>}
  </section>;
}

export default function Dashboard() {
  const { data, ...connection } = useMonitoringPoll("overview", getDashboard, { interval: 10000 });
  return <EquipmentLayout breadcrumb="Dashboard">
    <div className="ops-dashboard">
      <header className="ops-header">
        <div><h1>Inspection dashboard</h1><p>Equipment condition, inspection activity, and maintenance follow-up.</p></div>
        <div className="ops-actions">
          <Link className="ops-action-primary" to="/equipment/new">Register equipment</Link>
          <Link to="/inspections">Start or schedule inspection</Link>
          <Link to="/history">Analyze history</Link>
          <Link to="/reports">Generate report</Link>
        </div>
      </header>
      <MonitoringConnection {...connection} />
      {data && <>
        <Metrics overview={data} />
        <div className="ops-health-attention">
          <HealthDistribution counts={data.health} total={data.equipment.total} />
          <Attention items={data.attention} />
        </div>
        <Monitoring snapshots={data.monitoring} connection={connection} />
        <RecentInspections items={data.recent_inspections} counts={data.inspections} />
      </>}
    </div>
  </EquipmentLayout>;
}
