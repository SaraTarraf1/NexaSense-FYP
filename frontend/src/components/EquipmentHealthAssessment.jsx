import { HEALTH_LABELS } from "../utils/healthStatus";
import { sensorLabel } from "../utils/sensorLabels";
import "./EquipmentHealth.css";

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" });

function AssessmentTime({ value }) {
  return <time dateTime={value}>{dateFormat.format(new Date(value))}</time>;
}

export function HealthStatusBadge({ status = "not_evaluated" }) {
  return <span className="equipment-health-badge" data-health={status}>{HEALTH_LABELS[status]}</span>;
}

function AssessmentEvidence({ assessment }) {
  return (
    <>
      {assessment.missing_sensor_types.length > 0 && (
        <p>Readings needed from {assessment.missing_sensor_types.map(sensorLabel).join(", ")}.</p>
      )}
      {assessment.fault_rule_ids.length > 0 && (
        <p>Matched fault rules {assessment.fault_rule_ids.join(", ")}.</p>
      )}
      {assessment.evidence.length > 0 && (
        <>
          <h3>Supporting readings</h3>
          <ul className="equipment-health-evidence" role="list">
            {assessment.evidence.map((reading) => (
              <li key={reading.reading_id}>
                <span>{sensorLabel(reading.sensor_type)}</span>
                <strong>{reading.value} {reading.unit}</strong>
                <AssessmentTime value={reading.timestamp} />
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}

export default function EquipmentHealthAssessment({ monitoring }) {
  const {
    health_assessment: assessment,
    last_completed_health_assessment: lastCompleted,
    health_history: history = [],
  } = monitoring;
  const stale = assessment && monitoring.is_live
    && monitoring.monitoring_status !== "current" && assessment.status !== "insufficient_data";

  return (
    <section className="eq-detail-card equipment-health" aria-label="Equipment health assessment">
      <header className="equipment-health-heading">
        <h2>Equipment health</h2>
        <HealthStatusBadge status={monitoring.health_status} />
      </header>
      {assessment ? (
        <>
          <p>{assessment.message}</p>
          <p className="equipment-health-context">
            Inspection #{assessment.inspection_id} ·{" "}
            <AssessmentTime value={assessment.assessed_at} />
          </p>
          {stale && <p className="equipment-health-stale">Sensor readings are no longer current.</p>}
          <AssessmentEvidence assessment={assessment} />
        </>
      ) : (
        <p>{monitoring.inspection_id
          ? "This inspection has no saved assessment yet."
          : "Start an inspection to assess equipment health."}</p>
      )}
      {lastCompleted && (!assessment || assessment.status === "insufficient_data") && (
        <div className="equipment-health-previous">
          <span>Last completed assessment</span>
          <HealthStatusBadge status={lastCompleted.status} />
          <AssessmentTime value={lastCompleted.assessed_at} />
        </div>
      )}

      <h3>Assessment history</h3>
      {history.length === 0 ? (
        <p>No assessment records yet.</p>
      ) : (
        <div className="equipment-health-history">
          <table>
            <thead>
              <tr><th scope="col">Time</th><th scope="col">Inspection</th><th scope="col">Status</th></tr>
            </thead>
            <tbody>
              {history.map((entry) => (
                <tr key={entry.id}>
                  <td><AssessmentTime value={entry.assessed_at} /></td>
                  <td>#{entry.inspection_id}</td>
                  <td><HealthStatusBadge status={entry.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
