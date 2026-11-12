import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import EquipmentLayout from "../components/EquipmentLayout";
import AddEquipmentModal from "../components/AddEquipmentModal";
import { getAllEquipment } from "../services/equipmentService";

function EquipmentIcon({ type }) {
  const name = type.toLowerCase();
  const kind = /electrical|generator/.test(name) ? "power" : /pump|water/.test(name) ? "water" : /ventilation|fan/.test(name) ? "fan" : "cooling";
  return <span className={`equipment-machine-icon ${kind}`} aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    {kind === "power" ? <path d="m13 2-9 12h7l-1 8 10-13h-8z" /> : kind === "water" ? <path d="M12 3S6 10 6 14a6 6 0 0 0 12 0c0-4-6-11-6-11Z" /> : kind === "fan" ? <><circle cx="12" cy="12" r="2" /><path d="M10 10C3 9 7 1 11 5l1 5m2 0c1-7 9-3 5 1l-5 1m0 2c7 1 3 9-1 5l-1-5m-2 0c-1 7-9 3-5-1l5-1" /></> : <path d="M12 2v20M2 12h20M5 5l14 14M5 19 19 5" />}
  </svg></span>;
}

export default function Equipment({ defaultAddOpen = false }) {
  const { state } = useLocation();
  const navigate = useNavigate();
  const [equipment, setEquipment] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(state?.success || "");
  const [adding, setAdding] = useState(defaultAddOpen);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [location, setLocation] = useState("");
  const [health, setHealth] = useState("");
  const [status, setStatus] = useState("active");
  const [view, setView] = useState("table");
  const [ascending, setAscending] = useState(true);
  const [page, setPage] = useState(1);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    getAllEquipment().then(data => { if (active) setEquipment(data); })
      .catch(err => { if (active) setError(err.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);

  function closeModal() {
    setAdding(false);
    if (defaultAddOpen) navigate("/equipment", { replace: true });
  }
  function saved(item) {
    const message = "Equipment registered successfully and is now active.";
    setEquipment(previous => [item, ...previous]);
    setSuccess(message);
    setAdding(false);
    setPage(1);
    if (defaultAddOpen) navigate("/equipment", { replace: true, state: { success: message } });
  }
  function filter(setter, value) { setter(value); setPage(1); }
  const types = [...new Set(equipment.map(item => item.equipment_type))].sort();
  const locations = [...new Set(equipment.map(item => item.location))].sort();
  const filtered = equipment.filter(item =>
    [item.name, item.identifier].some(value => value?.toLowerCase().includes(query.trim().toLowerCase())) &&
    (!type || item.equipment_type === type) && (!location || item.location === location) &&
    (!health || health === "unknown") && (!status || item.status === status)
  ).sort((a, b) => ascending ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name));
  const pages = Math.max(1, Math.ceil(filtered.length / 8));
  const currentPage = Math.min(page, pages);
  const visible = filtered.slice((currentPage - 1) * 8, currentPage * 8);
  const hasFilters = query.trim() || type || location || health || status !== "active";

  return <EquipmentLayout>
    <div className="equipment-registry">
      <header className="equipment-header">
        <div><h1>Equipment</h1><p>Register, edit and track every machine NexaSense inspects.</p></div>
        <button className="equipment-add-btn" onClick={() => setAdding(true)}><span aria-hidden="true">+</span> Add equipment</button>
      </header>
      {success && <p className="equipment-success" role="status">{success}</p>}
      <div className="equipment-toolbar">
        <label className="equipment-search"><span className="equipment-sr-only">Search equipment by name or ID</span><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></svg><input type="search" placeholder="Name or ID" value={query} onChange={e => filter(setQuery, e.target.value)} /></label>
        <label className="equipment-filter"><span>Type:</span><select aria-label="Filter by type" value={type} onChange={e => filter(setType, e.target.value)}><option value="">All</option>{types.map(value => <option key={value}>{value}</option>)}</select></label>
        <label className="equipment-filter"><span>Location:</span><select aria-label="Filter by location" value={location} onChange={e => filter(setLocation, e.target.value)}><option value="">All</option>{locations.map(value => <option key={value}>{value}</option>)}</select></label>
        <label className="equipment-filter"><span>Health:</span><select aria-label="Filter by health" value={health} onChange={e => filter(setHealth, e.target.value)}><option value="">Any</option><option value="unknown">Unknown</option></select></label>
        <button className={`equipment-status-filter${status ? " selected" : ""}`} onClick={() => filter(setStatus, status ? "" : "active")} aria-pressed={Boolean(status)}>Status: {status ? "Active" : "All"}<span aria-hidden="true">{status ? "×" : "+"}</span></button>
      </div>
      <div className="equipment-view-row"><div className="equipment-view-toggle" aria-label="Equipment view">{["table", "cards"].map(mode => <button key={mode} aria-pressed={view === mode} onClick={() => setView(mode)}>{mode === "table" ? "Table" : "Cards"}</button>)}</div></div>
      {loading && <p role="status" className="equipment-empty">Loading equipment...</p>}
      {error && <div className="equipment-error" role="alert">{error} <button onClick={() => { setError(""); setLoading(true); setAttempt(value => value + 1); }}>Try again</button></div>}
      {!loading && !error && <>
        {visible.length === 0 ? <div className="equipment-empty"><h2>{hasFilters || equipment.length ? "No matching equipment" : "Your registry starts here"}</h2><p>{hasFilters || equipment.length ? "Try another name, identifier or filter." : "Add your first machine to keep its profile and inspection information in one place."}</p><button className="equipment-add-btn" onClick={() => setAdding(true)}>+ Add equipment</button></div> : view === "table" ?
          <div className="equipment-table-wrap"><table className="equipment-table"><thead><tr><th aria-sort={ascending ? "ascending" : "descending"}><button className="equipment-sort" onClick={() => setAscending(value => !value)}>Equipment <span aria-hidden="true">{ascending ? "↑" : "↓"}</span></button></th><th>Type</th><th>Location</th><th>Health</th><th>Last inspection</th><th>Status</th><th><span className="equipment-sr-only">Actions</span></th></tr></thead><tbody>{visible.map(item => <tr key={item.id}>
            <td><div className="equipment-table-name"><EquipmentIcon type={item.equipment_type} /><Link to={`/equipment/${item.id}`}><strong>{item.name}</strong><small>{item.identifier}</small></Link></div></td>
            <td>{item.equipment_type}</td><td>{item.location}</td><td><span className="equipment-badge equipment-health-badge">Unknown</span></td><td className="equipment-muted">Not available</td><td><span className="equipment-table-status">{item.status}</span></td><td><Link className="equipment-details-btn" to={`/equipment/${item.id}`} aria-label={`View details for ${item.name}`}>View details <span aria-hidden="true">→</span></Link></td>
          </tr>)}</tbody></table></div> :
          <div className="equipment-grid">{visible.map(item => <article className="equipment-card" key={item.id}><div className="equipment-card-top"><EquipmentIcon type={item.equipment_type} /><span className="equipment-badge active">{item.status}</span></div><h2><Link to={`/equipment/${item.id}`}>{item.name}</Link></h2><p className="equipment-muted">{item.identifier}</p><p>{item.equipment_type} · {item.location}</p><p>Health <span className="equipment-badge">Unknown</span></p><Link className="equipment-view-btn" to={`/equipment/${item.id}`}>View details →</Link></article>)}</div>}
        <footer className="equipment-pagination"><span>{filtered.length ? `Showing ${(currentPage - 1) * 8 + 1}–${Math.min(currentPage * 8, filtered.length)} of ${filtered.length}` : "0 equipment"}</span><div><button disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>Previous</button><button disabled={currentPage === pages} onClick={() => setPage(currentPage + 1)}>Next</button></div></footer>
      </>}
    </div>
    {adding && <AddEquipmentModal onClose={closeModal} onSaved={saved} />}
  </EquipmentLayout>;
}
