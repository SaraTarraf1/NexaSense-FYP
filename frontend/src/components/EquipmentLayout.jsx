
import { useState } from "react";
import { Link, NavLink, useNavigate, useOutletContext } from "react-router-dom";
import InspectionReminders from "./InspectionReminders.jsx";
import { logoutUser } from "../services/authService.js";
import "../pages/Equipment.css";

const links = [
  ["/dashboard", "Dashboard"], ["/equipment", "Equipment"], ["/inspections", "Inspections"],
  ["/monitoring", "Monitoring"], ["/alerts", "Alerts"], ["/history", "History"], ["/reports", "Reports"],
];

function AccountMenu() {
  const { user } = useOutletContext() ?? {};
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  if (!user) return null;

  async function logout() {
    setBusy(true);
    try {
      await logoutUser();
    } finally {
      navigate("/login", { replace: true });
    }
  }

  return <details className="equipment-account">
    <summary>{user.full_name}</summary>
    <div className="equipment-account-panel">
      <strong>{user.email}</strong>
      <span>{user.role}</span>
      <button type="button" onClick={logout} disabled={busy}>{busy ? "Logging out…" : "Log out"}</button>
    </div>
  </details>;
}

export default function EquipmentLayout({
  children,
  breadcrumb = "Equipment",
}) {
  return (
    <div className="equipment-workspace">
      {/* Sidebar */}
      <aside className="equipment-sidebar">
        <Link to="/dashboard" className="equipment-brand">
          <span className="equipment-logo">N</span>

          <span>
            <strong>NexaSense</strong>
            <small>Inspection & Monitoring</small>
          </span>
        </Link>

        <p className="equipment-eyebrow">Workspace</p>

        {/* Navigation */}
        <nav aria-label="Workspace">
          {links.map(([path, name]) => <NavLink to={path} key={path} className={({ isActive }) => isActive ? "selected" : ""}>
            {name}
          </NavLink>)}
        </nav>

        {/* Robot Connection */}
        <div className="equipment-robot">
          <strong>Robot connection</strong>

          <span className="equipment-muted">
            Status unavailable
          </span>

          <p>
            Sensor readiness will appear when a robot is
            connected.
          </p>
        </div>
      </aside>

      {/* Main Workspace */}
      <div className="equipment-workspace-body">
        {/* Top Navigation */}
        <div className="equipment-topbar">
          <span><Link to="/dashboard">Home</Link> / <span>{breadcrumb}</span></span>
          <div className="equipment-topbar-actions"><InspectionReminders /><AccountMenu /></div>
        </div>

        {/* Page Content */}
        <main className="equipment-page">
          <div className="equipment-container">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
