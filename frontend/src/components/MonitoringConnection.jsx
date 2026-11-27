import "./MonitoringConnection.css";

export default function MonitoringConnection({ error, unavailable, receivedAt, loading }) {
  const state = unavailable ? "unavailable" : error ? "disconnected" : loading ? "connecting" : "connected";
  const label = {
    unavailable: "Monitoring unavailable",
    disconnected: "Connection lost",
    connecting: "Connecting",
    connected: "Connected",
  }[state];

  return (
    <div className={`monitoring-connection ${state}`}>
      <p role="status">
        <strong>{label}</strong>
        {unavailable && <span>{error}</span>}
        {state === "disconnected" && (
          <span>{receivedAt ? "Showing last received data. Reconnecting…" : "Reconnecting…"}</span>
        )}
      </p>
      {receivedAt && (
        <span className="monitoring-last-sync">
          Last sync <time dateTime={new Date(receivedAt).toISOString()}>{new Date(receivedAt).toLocaleTimeString()}</time>
        </span>
      )}
    </div>
  );
}
