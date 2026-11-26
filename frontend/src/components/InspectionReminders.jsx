import { useEffect, useId, useRef, useState } from "react";
import { Link, Outlet, useOutletContext } from "react-router-dom";

import { getInspectionReminders } from "../services/inspectionService.js";
import "./InspectionReminders.css";

export function InspectionReminderOutlet() {
  const [reminders, setReminders] = useState([]);

  useEffect(() => {
    const controller = new AbortController();
    let refreshing = false;

    async function refresh() {
      if (refreshing) return;
      refreshing = true;
      try {
        const data = await getInspectionReminders(controller.signal);
        if (!controller.signal.aborted) setReminders(data);
      } catch {
        // Keep the current reminders during a connection interruption.
      } finally {
        refreshing = false;
      }
    }

    void refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, []);

  return <Outlet context={reminders} />;
}

export default function InspectionReminders() {
  const reminders = useOutletContext() ?? [];
  const [open, setOpen] = useState(false);
  const container = useRef(null);
  const trigger = useRef(null);
  const panelId = useId();
  const headingId = useId();
  const count = reminders.length;
  const readyLabel = count === 1 ? "1 inspection ready to start" : `${count} inspections ready to start`;

  useEffect(() => {
    if (!open) return;

    function closeOnOutsideClick(event) {
      if (!container.current?.contains(event.target)) setOpen(false);
    }

    function closeOnEscape(event) {
      if (event.key !== "Escape" || event.defaultPrevented) return;
      setOpen(false);
      trigger.current?.focus();
    }

    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div className="inspection-reminders" ref={container}>
      <button
        type="button"
        className="inspection-reminders-trigger"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={count ? `Inspection reminders, ${readyLabel}` : "Inspection reminders"}
        onClick={() => setOpen((value) => !value)}
        ref={trigger}
      >
        <span className="inspection-reminders-bell" aria-hidden="true" />
        <span className="inspection-reminders-label">Reminders</span>
        {count > 0 && <span className="inspection-reminders-count" aria-hidden="true">{count}</span>}
      </button>
      <span className="inspection-reminders-announcement" role="status">
        {count > 0 ? readyLabel : ""}
      </span>
      <section
        className="inspection-reminders-panel"
        id={panelId}
        aria-labelledby={headingId}
        hidden={!open}
      >
        <header className="inspection-reminders-heading">
          <h2 id={headingId}>Inspection reminders</h2>
          {count > 0 && <p>{readyLabel}</p>}
        </header>
        {count > 0 ? (
          <ul>
            {reminders.map((reminder) => (
              <li key={reminder.inspection_id}>
                <Link to={`/inspections/${reminder.inspection_id}`} onClick={() => setOpen(false)}>
                  <span className="inspection-reminders-item">
                    <strong>{reminder.equipment_name}</strong>
                    <span className="inspection-reminders-meta">
                      Inspection #{reminder.inspection_id} · <time dateTime={reminder.scheduled_at}>
                        {new Date(reminder.scheduled_at).toLocaleString(undefined, {
                          dateStyle: "medium",
                          timeStyle: "short",
                        })}
                      </time>
                    </span>
                  </span>
                  <span className="inspection-reminders-arrow" aria-hidden="true">→</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="inspection-reminders-empty">No inspections are ready to start.</p>
        )}
      </section>
    </div>
  );
}
