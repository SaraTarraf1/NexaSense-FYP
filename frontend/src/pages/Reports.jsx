import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import EquipmentLayout from "../components/EquipmentLayout";
import { HealthStatusBadge } from "../components/EquipmentHealthAssessment";
import { getAllEquipment } from "../services/equipmentService";
import { getInspectionById } from "../services/inspectionService";
import { downloadReport, generateReport, getEligibleInspections, getReport, getReports } from "../services/workspaceService";
import { RecordTable, SensorStatistics } from "./History";

const date = (value) => value ? new Date(value).toLocaleString() : "Unavailable";

function PageControls({ page, setOffset }) {
  if (!page || page.total <= page.limit) return null;
  return <div className="history-pagination">
    <button disabled={!page.offset} onClick={() => setOffset(page.offset - page.limit)}>Previous</button>
    <span>{page.offset + 1}–{page.offset + page.items.length} of {page.total}</span>
    <button disabled={page.offset + page.limit >= page.total} onClick={() => setOffset(page.offset + page.limit)}>Next</button>
  </div>;
}

function DownloadButton({ id }) {
  const active = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => () => active.current?.abort(), []);
  async function download() {
    if (active.current) return;
    const controller = new AbortController();
    active.current = controller;
    setBusy(true);
    setError("");
    try {
      await downloadReport(id, controller.signal);
    } catch (error) {
      if (!controller.signal.aborted) setError(error.message);
    } finally {
      active.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return <div><button type="button" onClick={download} disabled={busy}>{busy ? "Downloading…" : "Download PDF"}</button>
    {error && <p role="alert">{error}</p>}</div>;
}

function ReportHistory({ equipment }) {
  const [offset, setOffset] = useState(0);
  const [result, setResult] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    getReports(equipment, offset, controller.signal)
      .then(data => { if (!controller.signal.aborted) setResult({ offset, data }); })
      .catch(error => { if (!controller.signal.aborted) setResult({ offset, error: error.message }); });
    return () => controller.abort();
  }, [equipment, offset]);
  const current = result?.offset === offset ? result : null;
  const page = current?.data;
  return <section className="history-card">
    <h2>Saved reports</h2>
    {!current && <p role="status">Loading reports…</p>}
    {current?.error && <p role="alert">{current.error}</p>}
    {page?.items.length === 0 && <p>No reports have been generated for this selection.</p>}
    {page?.items.length > 0 && <div className="history-scroll"><table>
      <thead><tr>{["Report", "Equipment", "Inspection", "Inspection date", "Generated", "Health", "PDF"].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
      <tbody>{page.items.map(report => <tr key={report.id}>
        <th scope="row"><Link to={`/reports/${report.id}`}>View report #{report.id}</Link></th>
        <td><Link to={`/equipment/${report.equipment_id}`}>{report.equipment_name}</Link></td>
        <td><Link to={`/inspections/${report.inspection_id}`}>#{report.inspection_id}</Link></td>
        <td>{date(report.inspection_date)}</td><td>{date(report.generated_at)}</td>
        <td><HealthStatusBadge status={report.health_status} /></td><td><DownloadButton id={report.id} /></td>
      </tr>)}</tbody>
    </table></div>}
    <PageControls page={page} setOffset={setOffset} />
  </section>;
}

function InspectionPicker({ equipment, preselected }) {
  const navigate = useNavigate();
  const generation = useRef(null);
  const [result, setResult] = useState(null);
  const [selection, setSelection] = useState(preselected);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => () => generation.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController();
    const selected = preselected
      ? getInspectionById(preselected, { signal: controller.signal }).catch(() => null)
      : Promise.resolve(null);
    Promise.all([getEligibleInspections(equipment, offset, controller.signal), selected])
      .then(([data, inspection]) => {
        if (controller.signal.aborted) return;
        const valid = inspection?.status === "completed" && String(inspection.equipment_id) === equipment;
        setResult({ offset, data, pinned: valid ? inspection : null });
      })
      .catch(error => { if (!controller.signal.aborted) setResult({ offset, error: error.message }); });
    return () => controller.abort();
  }, [equipment, offset, preselected]);
  const current = result?.offset === offset ? result : null;
  const choices = current?.data?.items ?? [];
  const pinned = current?.pinned;
  const options = pinned && !choices.some(item => item.id === pinned.id) ? [pinned, ...choices] : choices;
  const eligible = options.some(item => String(item.id) === selection);

  async function submit(event) {
    event.preventDefault();
    if (!eligible || generation.current) return;
    const controller = new AbortController();
    generation.current = controller;
    setBusy(true);
    setError("");
    try {
      const report = await generateReport(equipment, selection, controller.signal);
      if (!controller.signal.aborted) navigate(`/reports/${report.id}`);
    } catch (error) {
      if (!controller.signal.aborted) setError(error.message);
    } finally {
      generation.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return <>
    {!current && <p role="status">Loading completed inspections…</p>}
    {current?.error && <p role="alert">{current.error}</p>}
    {current?.data && options.length === 0 && <p>This equipment has no completed inspections.</p>}
    {options.length > 0 && <form className="history-filters" onSubmit={submit}>
      <label>Completed inspection<select value={eligible ? selection : ""} onChange={event => setSelection(event.target.value)} disabled={busy}>
        <option value="">Select inspection</option>
        {options.map(item => <option key={item.id} value={item.id}>#{item.id} · {date(item.started_at)} · Completed</option>)}
      </select></label>
      <button type="submit" disabled={!eligible || busy}>{busy ? "Generating report…" : "Generate report"}</button>
    </form>}
    {error && <p role="alert">{error}</p>}
    <PageControls page={current?.data} setOffset={setOffset} />
  </>;
}

function ReportsWorkspace({ initialEquipment, initialInspection }) {
  const [equipment, setEquipment] = useState(initialEquipment);
  const [choices, setChoices] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    getAllEquipment({ signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setChoices({ data }); })
      .catch(error => { if (!controller.signal.aborted) setChoices({ error: error.message }); });
    return () => controller.abort();
  }, []);
  return <div className="history-page">
    <header><h1>Inspection and Maintenance Reports</h1><p>Generate a saved report from a completed inspection and download it as a PDF.</p></header>
    <section className="history-card">
      <h2>Generate a report</h2>
      <div className="history-filters"><label>Equipment<select value={equipment} onChange={event => setEquipment(event.target.value)}>
        <option value="">Select equipment</option>
        {equipment && !choices?.data?.some(item => String(item.id) === equipment) && <option value={equipment}>Equipment #{equipment}</option>}
        {choices?.data?.map(item => <option key={item.id} value={item.id}>{item.name} · {item.identifier}</option>)}
      </select></label></div>
      {!choices && <p role="status">Loading equipment…</p>}
      {choices?.error && <p role="alert">{choices.error}</p>}
      {choices?.data?.length === 0 && <p>Register equipment to generate inspection reports.</p>}
      {equipment && <InspectionPicker key={equipment} equipment={equipment} preselected={equipment === initialEquipment ? initialInspection : ""} />}
    </section>
    <ReportHistory key={equipment} equipment={equipment} />
  </div>;
}

function DetailFields({ entries }) {
  return <dl className="equipment-details-grid">{entries.map(([label, value]) =>
    <div key={label}><dt>{label}</dt><dd>{value ?? "Unavailable"}</dd></div>
  )}</dl>;
}

function SavedReport({ id }) {
  const [result, setResult] = useState(null);
  useEffect(() => {
    const controller = new AbortController();
    getReport(id, controller.signal)
      .then(report => { if (!controller.signal.aborted) setResult({ report }); })
      .catch(error => { if (!controller.signal.aborted) setResult({ error: error.message }); });
    return () => controller.abort();
  }, [id]);
  if (!result) return <p role="status">Loading saved report…</p>;
  if (result.error) return <p role="alert">{result.error}</p>;
  const { report } = result;
  const { snapshot } = report;
  const { equipment, inspection } = snapshot;
  return <div className="history-page">
    <header>
      <Link to={`/reports?equipment=${report.equipment_id}`}>Back to reports</Link>
      <h1>Inspection and Maintenance Report #{report.id}</h1>
      <p>Generated {date(report.generated_at)}</p>
      <DownloadButton id={report.id} />
    </header>
    <section className="history-card"><h2>Equipment</h2><DetailFields entries={[
      ["Name", equipment.name], ["Identifier", equipment.identifier], ["Type", equipment.equipment_type],
      ["Location", equipment.location], ["Manufacturer", equipment.manufacturer], ["Model", equipment.model],
      ["Serial number", equipment.serial_number], ["Installed", equipment.installation_date],
      ["Status", equipment.status], ["Notes", equipment.description],
    ]} /></section>
    <section className="history-card"><h2>Inspection execution</h2><DetailFields entries={[
      ["Inspection", <Link to={`/inspections/${inspection.id}`}>#{inspection.id}</Link>],
      ["Status", "Completed"], ["Scheduled", date(inspection.scheduled_at)], ["Started", date(inspection.started_at)],
      ["Ended", date(inspection.ended_at)], ["Duration", snapshot.duration_seconds == null ? null : `${snapshot.duration_seconds.toLocaleString()} s`],
      ["Notes", inspection.notes],
    ]} /></section>
    <section className="history-card"><h2>Equipment health</h2><HealthStatusBadge status={snapshot.health_status} />
      {snapshot.health.length > 0 && <RecordTable items={snapshot.health} section="health" />}
    </section>
    {snapshot.alerts.length > 0 && <section className="history-card"><h2>Recorded alert severity</h2>
      <ul>{snapshot.alerts.map(alert => <li key={alert.id}>
        <HealthStatusBadge status={alert.severity} /> {alert.status} · {date(alert.created_at)} · {alert.description}
      </li>)}</ul>
    </section>}
    <section className="history-card"><h2>Suggested maintenance actions</h2><ul>{snapshot.recommendations.map(action => <li key={action}>{action}</li>)}</ul>
      {snapshot.limitations.length > 0 && <><h3>Analysis limitations</h3><ul>{snapshot.limitations.map(item => <li key={item}>{item}</li>)}</ul></>}
    </section>
    <section className="history-card"><h2>Sensor statistics</h2>
      {snapshot.statistics.length ? <SensorStatistics data={snapshot.statistics} /> : <p>No valid measurements.</p>}
    </section>
    {[["anomalies", "Detected anomalies"], ["faults", "Classified faults"], ["readings", "Stored measurements"]].map(([section, title]) =>
      <section className="history-card" key={section}><h2>{title} ({snapshot[section].length})</h2>
        {snapshot[section].length ? <RecordTable items={snapshot[section]} section={section} /> : <p>No records saved.</p>}
      </section>
    )}
  </div>;
}

export default function Reports() {
  const { reportId } = useParams();
  const [params] = useSearchParams();
  const equipment = params.get("equipment") ?? "";
  const inspection = params.get("inspection") ?? "";
  return <EquipmentLayout breadcrumb="Reports">
    {reportId ? <SavedReport key={reportId} id={reportId} /> :
      <ReportsWorkspace key={`${equipment}/${inspection}`} initialEquipment={equipment} initialInspection={inspection} />}
  </EquipmentLayout>;
}
