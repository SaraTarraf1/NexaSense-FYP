import { Link } from "react-router-dom";
import "../pages/Equipment.css";

export default function EquipmentLayout({ children, breadcrumb = "Equipment" }) {
  return <div className="equipment-workspace">
    <aside className="equipment-sidebar">
      <Link to="/dashboard" className="equipment-brand"><span className="equipment-logo">N</span><span><strong>NexaSense</strong><small>Inspection & Monitoring</small></span></Link>
      <p className="equipment-eyebrow">Workspace</p>
      <nav aria-label="Workspace"><Link to="/dashboard">Dashboard</Link><Link to="/equipment" className="selected" aria-current="page">Equipment</Link></nav>
      <div className="equipment-robot"><strong>Robot connection</strong><span className="equipment-muted">Status unavailable</span><p>Sensor readiness will appear when a robot is connected.</p></div>
    </aside>
    <div className="equipment-workspace-body">
      <div className="equipment-topbar"><span><Link to="/dashboard">Home</Link> / <Link to="/equipment">Equipment</Link>{breadcrumb !== "Equipment" && <> / {breadcrumb}</>}</span><span className="equipment-workspace-label">Inspection workspace</span></div>
      <main className="equipment-page"><div className="equipment-container">{children}</div></main>
    </div>
  </div>;
}
