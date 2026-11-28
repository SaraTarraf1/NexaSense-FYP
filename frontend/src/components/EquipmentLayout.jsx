
import { Link, NavLink } from "react-router-dom";
import InspectionReminders from "./InspectionReminders.jsx";
import "../pages/Equipment.css";

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
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              isActive ? "selected" : ""
            }
          >
            Dashboard
          </NavLink>

          <NavLink
            to="/equipment"
            className={({ isActive }) =>
              isActive ? "selected" : ""
            }
          >
            Equipment
          </NavLink>

          <NavLink
            to="/inspections"
            className={({ isActive }) =>
              isActive ? "selected" : ""
            }
          >
            Inspections
          </NavLink>
          <NavLink to="/history">History</NavLink>
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
          <span>
            <Link to="/dashboard">Home</Link>
            {" / "}

            {breadcrumb === "Equipment" ? (
              <span>Equipment</span>
            ) : (
              <>
                <Link to="/inspections">Inspections</Link>
                {" / "}
                {breadcrumb}
              </>
            )}
          </span>

          <InspectionReminders />
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
