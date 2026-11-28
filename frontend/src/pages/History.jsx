import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import EquipmentLayout from "../components/EquipmentLayout";
import { HealthStatusBadge } from "../components/EquipmentHealthAssessment";
import { getAllEquipment, getEquipmentHistory } from "../services/equipmentService";
import { sensorLabel } from "../utils/sensorLabels";
import "./History.css";

const sections = {
  readings: "Sensor readings",
  anomalies: "Detected anomalies",
  faults: "Classified faults",
  health: "Health timeline",
  inspections: "Inspection history",
};
const pageSize = 25;
const formatDate = (value) => value ? new Date(value).toLocaleString() : "—";
const formatValue = (value) => Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 4 }) : "—";
const label = (value) => value?.replaceAll("_", " ") || "—";

function useResult(load, key) {
  const [state, setState] = useState(null);
  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    load(controller.signal).then(data => {
      if (!controller.signal.aborted) setState({ key, data });
    }).catch(error => {
      if (!controller.signal.aborted) setState({ key, error: [403, 404].includes(error.status) ? "Access denied or equipment unavailable." : error.message });
    });
    return () => controller.abort();
  }, [load, key]);
  return state?.key === key ? state : null;
}

function formatInputDate(value) {
  return [value.getFullYear(), String(value.getMonth() + 1).padStart(2, "0"), String(value.getDate()).padStart(2, "0")].join("-");
}

function defaults(equipment) {
  const today = new Date();
  const start = new Date(today);
  start.setDate(start.getDate() - 29);
  return { equipment, start: formatInputDate(start), end: formatInputDate(today) };
}

function Trend({ group }) {
  const { points, minimum, maximum, unit } = group;
  const start = Date.parse(points[0].timestamp);
  const end = Date.parse(points.at(-1).timestamp);
  const positions = points.map(({ timestamp, value }) => [
    start === end ? 230 : 12 + 436 * (Date.parse(timestamp) - start) / (end - start),
    minimum === maximum ? 73 : 132 - 118 * (value - minimum) / (maximum - minimum),
  ]);
  return <figure className="history-trend">
    <figcaption>{sensorLabel(group.sensor_type)} <span>({unit})</span></figcaption>
    <div className="history-trend-area">
      <div className="history-scale"><span>{formatValue(maximum)}</span><span>{formatValue(minimum)}</span></div>
      <svg viewBox="0 0 460 146" role="img" aria-label={`${sensorLabel(group.sensor_type)} over time in ${unit}`}>
        <path d="M12 14V132H448 M12 14H448 M12 73H448" className="history-gridlines" />
        <polyline points={positions.map(position => position.join(",")).join(" ")} />
        {positions.map(([x, y], index) => <circle key={index} cx={x} cy={y} r="3">
          <title>{formatDate(points[index].timestamp)} · {formatValue(points[index].value)} {unit}</title>
        </circle>)}
      </svg>
    </div>
    <div className="history-chart-times"><time>{formatDate(start)}</time><time>{formatDate(end)}</time></div>
  </figure>;
}

function Occurrences({ title, items }) {
  return <div><h3>{title}</h3>{items.length ? <ul>{items.map(item => <li key={item.type}>
    {label(item.type)} · {item.count} ({(100 * item.frequency).toFixed(1)}%){item.count > 1 && " · Recurring"}
  </li>)}</ul> : <p>None recorded.</p>}</div>;
}

export function SensorStatistics({ data }) {
  return <div className="history-scroll"><table><thead><tr>{["Sensor", "Unit", "Minimum", "Maximum", "Average", "Valid readings"].map(title => <th key={title} scope="col">{title}</th>)}</tr></thead>
    <tbody>{data.map(group => <tr key={JSON.stringify([group.sensor_type, group.unit])}>
      <th scope="row">{sensorLabel(group.sensor_type)}</th><td>{group.unit}</td>
      {[group.minimum, group.maximum, group.average, group.count].map((value, index) => <td key={index}>{formatValue(value)}</td>)}
    </tr>)}</tbody></table></div>;
}

function Summary({ data }) {
  const counts = [
    ["Inspections", data.inspections], ["Valid readings", data.valid_measurements],
    ["Anomalies", data.anomalies], ["Fault classifications", data.faults], ["Health assessments", data.health_assessments],
  ];
  return <>
    <dl className="history-metrics">{counts.map(([name, count]) => <div className="history-card" key={name}><dt>{name}</dt><dd>{count}</dd></div>)}</dl>
    <section className="history-card">
      <h2>Sensor statistics</h2>
      {data.sensors.length ? <>
        <SensorStatistics data={data.sensors} />
        <div className="history-charts">{data.sensors.filter(group => group.points.length > 0).map(group =>
          <Trend key={JSON.stringify([group.sensor_type, group.unit])} group={group} />
        )}</div>
      </> : <p>No valid measurements in this date range.</p>}
    </section>
    <section className="history-card history-occurrences">
      <Occurrences title="Anomaly occurrences" items={data.anomaly_types} />
      <Occurrences title="Fault occurrences" items={data.fault_types} />
    </section>
  </>;
}

function InspectionLink({ id }) {
  return <Link to={`/inspections/${id}`}>#{id}</Link>;
}

export function RecordTable({ items, section }) {
  if (section === "health") return <ol className="history-timeline">{items.map(item => <li key={item.id}>
    <time>{formatDate(item.assessed_at)}</time> <InspectionLink id={item.inspection_id} /> <HealthStatusBadge status={item.status} />
    <p>{item.message}</p>{item.missing_sensor_types.length > 0 && <p>Missing sensors: {item.missing_sensor_types.map(sensorLabel).join(", ")}</p>}
  </li>)}</ol>;
  let headings;
  let rows;
  if (section === "inspections") {
    headings = ["Inspection", "Scheduled", "Started", "Ended", "Status", "Health"];
    rows = items.map(item => [<InspectionLink id={item.id} />, formatDate(item.scheduled_at), formatDate(item.started_at),
      formatDate(item.ended_at), label(item.status), <HealthStatusBadge status={item.health_status} />]);
  } else if (section === "faults") {
    headings = ["Classified at", "Inspection", "Status", "Findings and evidence"];
    rows = items.map(item => [formatDate(item.classified_at), <InspectionLink id={item.source_reading.inspection_id} />,
      label(item.status), <>{item.message}{item.missing_sensor_types.length > 0 && <p>Missing sensors: {item.missing_sensor_types.map(sensorLabel).join(", ")}</p>}
      {item.matches.map(match => <details key={match.rule_id}>
        <summary>{label(match.fault_type)} · {match.rule_id}</summary>
        <ul>{match.evidence.map(reading => <li key={reading.id}>{sensorLabel(reading.sensor_type)} · {formatValue(reading.value)} {reading.unit} · {formatDate(reading.timestamp)}</li>)}</ul>
      </details>)}</>]);
  } else {
    headings = ["Timestamp", "Inspection", "Sensor", "Measurement", section === "anomalies" ? "Anomaly" : "Validation"];
    rows = items.map(item => [formatDate(item.timestamp), <InspectionLink id={item.inspection_id} />,
      sensorLabel(item.sensor_type), item.value == null ? "—" : `${formatValue(item.value)} ${item.unit}`,
      section === "anomalies" ? `${label(item.anomaly_type)} · ${item.detection_message ?? ""}` :
        [label(item.validation_status), item.validation_message].filter(Boolean).join(" · ")]);
  }
  return <div className="history-scroll"><table><thead><tr>{headings.map(title => <th key={title} scope="col">{title}</th>)}</tr></thead>
    <tbody>{rows.map((row, index) => <tr key={items[index].id ?? items[index].source_reading.id}>{row.map((cell, column) => <td key={column}>{cell}</td>)}</tr>)}</tbody>
  </table></div>;
}

function Records({ query, section, offset, setOffset }) {
  const [result, setResult] = useState(null);
  const { equipment, start, end } = query;
  useEffect(() => {
    const controller = new AbortController();
    getEquipmentHistory(equipment, section, { start, end, offset, limit: pageSize }, controller.signal)
      .then(data => { if (!controller.signal.aborted) setResult({ section, offset, data }); })
      .catch(error => { if (!controller.signal.aborted) setResult({ section, offset, error: error.message }); });
    return () => controller.abort();
  }, [equipment, start, end, section, offset]);
  const current = result?.section === section && result.offset === offset ? result : null;
  if (!current) return <p role="status">Loading records…</p>;
  if (current.error) return <p role="alert">{current.error}</p>;
  const { items, total } = current.data;
  if (!items.length) return <p>No records in this date range.</p>;
  return <>
    <RecordTable items={items} section={section} />
    <div className="history-pagination">
      <button disabled={offset === 0} onClick={() => setOffset(offset - pageSize)}>Previous</button>
      <span>{offset + 1}–{offset + items.length} of {total}</span>
      <button disabled={offset + pageSize >= total} onClick={() => setOffset(offset + pageSize)}>Next</button>
    </div>
  </>;
}

function Analysis({ query }) {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [section, setSection] = useState(query.section);
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    getEquipmentHistory(query.equipment, null, { start: query.start, end: query.end }, controller.signal)
      .then(data => { if (!controller.signal.aborted) setSummary(data); })
      .catch(error => {
        if (!controller.signal.aborted) setError([403, 404].includes(error.status) ? "Access denied or equipment unavailable." : error.message);
      });
    return () => controller.abort();
  }, [query]);
  if (error) return <p className="equipment-error" role="alert">{error}</p>;
  if (!summary) return <p role="status">Loading historical analysis…</p>;
  return <>
    <Summary data={summary} />
    <section className="history-card">
      <h2>Historical records</h2>
      <div className="history-sections" aria-label="Record type">{Object.entries(sections).map(([value, name]) =>
        <button key={value} aria-pressed={section === value} onClick={() => { setSection(value); setOffset(0); }}>{name}</button>
      )}</div>
      <Records query={query} section={section} offset={offset} setOffset={setOffset} />
    </section>
  </>;
}

export default function History() {
  const [params] = useSearchParams();
  const equipment = params.get("equipment") ?? "";
  const section = Object.hasOwn(sections, params.get("section")) ? params.get("section") : "readings";
  return <EquipmentLayout breadcrumb="History"><HistoryFilters key={`${equipment}/${section}`} equipment={equipment} section={section} /></EquipmentLayout>;
}

function HistoryFilters({ equipment, section }) {
  const [filters, setFilters] = useState(() => defaults(equipment));
  const [query, setQuery] = useState(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const choices = useResult(loadEquipment, "equipment");

  function apply(event) {
    event.preventDefault();
    if (!filters.equipment || !filters.start || !filters.end || filters.start > filters.end) {
      setError("Select equipment and a date range with the end on or after the start.");
      return;
    }
    const start = new Date(`${filters.start}T00:00:00`);
    const end = new Date(`${filters.end}T00:00:00`);
    end.setDate(end.getDate() + 1);
    if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime())) {
      setError("Enter valid start and end dates.");
      return;
    }
    setQuery({ equipment: filters.equipment, start: start.toISOString(), end: end.toISOString(), section });
    setError("");
    setRevision(value => value + 1);
  }

  function update(event) {
    setFilters({ ...filters, [event.target.name]: event.target.value });
    setQuery(null);
    setError("");
  }

  return <div className="history-page">
    <header><h1>Historical Data and Trend Analysis</h1><p>Review recorded measurements, diagnostics and equipment health across inspections.</p></header>
    <form className="history-card history-filters" onSubmit={apply} noValidate>
      <label>Equipment<select name="equipment" value={filters.equipment} onChange={update} required>
        <option value="">Select equipment</option>
        {filters.equipment && !choices?.data?.some(item => String(item.id) === filters.equipment) &&
          <option value={filters.equipment}>Equipment #{filters.equipment}</option>}
        {choices?.data?.map(item => <option key={item.id} value={item.id}>{item.name} · {item.identifier}</option>)}
      </select></label>
      <label>Start date<input name="start" type="date" value={filters.start} onChange={update} required /></label>
      <label>End date<input name="end" type="date" value={filters.end} onChange={update} required /></label>
      <button className="equipment-primary-button" type="submit">Analyze</button>
    </form>
    {!choices && <p role="status">Loading registered equipment…</p>}
    {choices?.error && <p role="alert">{choices.error}</p>}
    {choices?.data?.length === 0 && <p>Register equipment to begin analyzing inspection history. <Link to="/equipment/new">Register equipment</Link></p>}
    {error && <p role="alert" className="equipment-error">{error}</p>}
    {query && <Analysis key={revision} query={query} />}
  </div>;
}

function loadEquipment(signal) {
  return getAllEquipment({ signal });
}
