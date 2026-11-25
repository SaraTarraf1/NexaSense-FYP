const SENSOR_LABELS = {
  temperature: "Temperature",
  thermal: "Thermal temperature",
  vibration: "Vibration",
};

const FAULT_STATUS = {
  identified: { label: "Rule matched" },
  unknown: { label: "Unknown", title: "No matching rule" },
  undetermined: { label: "Undetermined", title: "More evidence needed" },
};

function sensorLabel(sensorType) {
  return SENSOR_LABELS[sensorType] || sensorType;
}

function getFaultEntries(faults) {
  const displayedMatches = new Set();

  return faults.flatMap((fault) => {
    if (fault.status !== "identified") {
      return [{ key: `reading-${fault.source_reading.reading_id}`, fault }];
    }

    return fault.matches.flatMap((match) => {
      const key = `${match.rule_id}:${match.evidence_reading_ids.join(",")}`;
      if (displayedMatches.has(key)) return [];
      displayedMatches.add(key);
      return [{ key, fault, match }];
    });
  });
}

function FaultEntry({ fault, match }) {
  const { source_reading: source, status, missing_sensor_types: missingSensors } = fault;
  const { label, title: unmatchedTitle } = FAULT_STATUS[status];
  const title = match ? `Potential ${match.fault_type.replaceAll("_", " ")}` : unmatchedTitle;

  return (
    <li className="monitoring-fault">
      <div className="monitoring-fault-heading">
        <h3>{title}</h3>
        <span className={`monitoring-badge fault-${status}`}>{label}</span>
      </div>
      <p className="monitoring-fault-meta">
        {match
          ? `Rule ${match.rule_id}`
          : `${sensorLabel(source.sensor_type)} · ${source.value} ${source.unit}`}
        {" · "}
        <time dateTime={source.timestamp}>{new Date(source.timestamp).toLocaleString()}</time>
      </p>
      {match ? (
        match.evidence.length > 0 && (
          <ul className="monitoring-fault-evidence" aria-label="Supporting readings" role="list">
            {match.evidence.map((reading) => (
              <li key={reading.reading_id}>
                <span>{sensorLabel(reading.sensor_type)}</span>
                <strong>{reading.value} {reading.unit}</strong>
              </li>
            ))}
          </ul>
        )
      ) : (
        <>
          <p>{fault.message}</p>
          {missingSensors.length > 0 && (
            <p>Needed: {missingSensors.map(sensorLabel).join(", ")}</p>
          )}
        </>
      )}
    </li>
  );
}

export default function FaultClassifications({ monitoring }) {
  const entries = getFaultEntries(monitoring.faults);
  const visibleEntries = entries.slice(0, 5);
  const olderEntries = entries.slice(5);

  return (
    <section className="monitoring-section monitoring-fault-section" aria-label="Recent fault classifications">
      <h2>Recent fault classifications</h2>
      {monitoring.inspection_id && (
        <p className="monitoring-fault-context">
          {monitoring.is_live ? "Live inspection" : "Latest inspection"}
        </p>
      )}
      {entries.length === 0 ? (
        <p>
          {monitoring.inspection_id
            ? "No fault classifications recorded for this inspection."
            : "Fault classifications appear here after an inspection records a sensor anomaly."}
        </p>
      ) : (
        <>
          <ul className="monitoring-fault-list" role="list">
            {visibleEntries.map(({ key, ...entry }) => <FaultEntry key={key} {...entry} />)}
          </ul>
          {olderEntries.length > 0 && (
            <details className="monitoring-fault-more">
              <summary>Show older classifications ({olderEntries.length})</summary>
              <ul className="monitoring-fault-list" role="list">
                {olderEntries.map(({ key, ...entry }) => <FaultEntry key={key} {...entry} />)}
              </ul>
            </details>
          )}
        </>
      )}
    </section>
  );
}
