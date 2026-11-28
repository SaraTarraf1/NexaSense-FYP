import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import EquipmentAlerts from "../components/EquipmentAlerts";
import EquipmentLayout from "../components/EquipmentLayout";
import MonitoringConnection from "../components/MonitoringConnection";
import { useEquipmentMonitoring } from "../hooks/useEquipmentMonitoring";
import { getAllEquipment } from "../services/equipmentService";
import { EquipmentMonitoringPanel } from "./EquipmentMonitoring";
import "./History.css";

const alertStatuses = new Set(["open", "closed"]);

function MonitoringSelection({ equipmentId }) {
  const navigate = useNavigate();
  const state = useEquipmentMonitoring(equipmentId);
  return <>
    <MonitoringConnection {...state} />
    {state.monitoring?.inspection_id && <p>
      <Link to={`/inspections/${state.monitoring.inspection_id}`}>Open {state.monitoring.is_live ? "active" : "recorded"} inspection</Link>
    </p>}
    <EquipmentMonitoringPanel {...state} onOpenAlerts={() => navigate(`/alerts?equipment=${equipmentId}`)} />
  </>;
}

export default function EquipmentWorkspace({ mode }) {
  const [params, setParams] = useSearchParams();
  const equipmentId = params.get("equipment") ?? "";
  const alertStatus = alertStatuses.has(params.get("status")) ? params.get("status") : "";
  const [registry, setRegistry] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    getAllEquipment({ signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setRegistry({ data }); })
      .catch(error => { if (!controller.signal.aborted) setRegistry({ error: error.message }); });
    return () => controller.abort();
  }, []);
  const selection = registry?.data?.find(item => String(item.id) === equipmentId);
  const isAlerts = mode === "alerts";
  const title = isAlerts ? "Alerts and notifications" : "Equipment monitoring";

  function update(key, value) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next);
  }

  return <EquipmentLayout breadcrumb={isAlerts ? "Alerts" : "Monitoring"}><div className="history-page">
    <header><h1>{title}</h1><p>{isAlerts ? "Review open alerts and previous notifications by equipment." : "Open live inspection readings or the most recent recorded measurements."}</p></header>
    <div className="history-card history-filters">
      <label>Equipment<select value={selection ? equipmentId : ""} onChange={event => update("equipment", event.target.value)}>
        <option value="">Select equipment</option>
        {registry?.data?.map(item => <option key={item.id} value={item.id}>{item.name} · {item.identifier}</option>)}
      </select></label>
      {isAlerts && <label>Alert status<select value={alertStatus} onChange={event => update("status", event.target.value)}>
        <option value="">All alerts</option><option value="open">Open</option><option value="closed">Closed</option>
      </select></label>}
    </div>
    {!registry && <p role="status">Loading equipment…</p>}
    {registry?.error && <p role="alert">{registry.error}</p>}
    {registry?.data?.length === 0 && <p>No equipment registered. <Link to="/equipment/new">Register equipment</Link></p>}
    {registry?.data && equipmentId && !selection && <p role="alert">Access denied or equipment unavailable.</p>}
    {selection && <section aria-label={selection.name}>
      <h2><Link to={`/equipment/${selection.id}`}>{selection.name}</Link></h2>
      {isAlerts ? <EquipmentAlerts key={`${equipmentId}/${alertStatus}`} equipmentId={selection.id} status={alertStatus} /> :
        <MonitoringSelection key={equipmentId} equipmentId={selection.id} />}
    </section>}
  </div></EquipmentLayout>;
}
