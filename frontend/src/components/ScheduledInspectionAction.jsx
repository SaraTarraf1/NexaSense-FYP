export default function ScheduledInspectionAction({ inspection, now, busy, starting, cancelling, onStart, onCancel }) {
  const due = Date.parse(inspection.scheduled_at) <= now;
  const reason = due
    ? inspection.start_blocker
    : `Available at ${new Date(inspection.scheduled_at).toLocaleString()}`;

  return (
    <div className="inspection-schedule-action">
      {due && !reason && <span className="inspection-status ready">Ready to start</span>}
      <button
        type="button"
        className="inspection-start-scheduled"
        disabled={busy || Boolean(reason)}
        onClick={onStart}
      >
        {starting ? "Starting…" : "Start"}
      </button>
      <button
        type="button"
        className="inspection-cancel-booking"
        disabled={busy}
        onClick={onCancel}
      >
        {cancelling ? "Cancelling…" : "Cancel booking"}
      </button>
      {reason && <small>{reason}</small>}
    </div>
  );
}
