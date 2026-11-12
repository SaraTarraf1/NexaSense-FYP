import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getEquipmentById, registerEquipment, updateEquipment } from "../services/equipmentService";
import EquipmentLayout from "./EquipmentLayout";

const empty = { name: "", equipment_type: "", identifier: "", location: "", manufacturer: "", model: "", serial_number: "", installation_date: "", description: "" };
const types = ["Air conditioner", "Electrical panel", "Water pump", "Ventilation", "Water heater", "Heat pump", "Generator"];

export default function EquipmentForm({ equipmentId, embedded = false, onCancel, onSaved, onSavingChange }) {
  const navigate = useNavigate();
  const editing = Boolean(equipmentId);
  const [form, setForm] = useState(empty);
  const [loadedId, setLoadedId] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState(false);
  const back = editing ? `/equipment/${equipmentId}` : "/equipment";
  useEffect(() => {
    if (!equipmentId) return;
    let active = true;
    getEquipmentById(equipmentId).then(data => {
      if (active) { setForm(Object.fromEntries(Object.keys(empty).map(key => [key, data[key] ?? ""]))); setLoadedId(equipmentId); }
    }).catch(err => { if (active) { setError(err.message); setFailed(true); } });
    return () => { active = false; };
  }, [equipmentId]);
  function change(event) { setForm(previous => ({ ...previous, [event.target.name]: event.target.value })); }
  async function submit(event) {
    event.preventDefault();
    if (saving) return;
    setError("");
    if ((editing ? ["name", "equipment_type", "identifier", "location"] : ["name", "equipment_type", "location"]).some(key => !form[key].trim())) { setError("Complete all required fields."); return; }
    setSaving(true);
    onSavingChange?.(true);
    try {
      const payload = { ...form, installation_date: form.installation_date || null };
      if (!editing && !form.identifier.trim()) delete payload.identifier;
      const result = editing ? await updateEquipment(equipmentId, payload) : await registerEquipment(payload);
      if (onSaved) { onSaved(result); return; }
      navigate(back, { replace: true, state: { success: editing ? "Equipment updated successfully." : "Equipment registered successfully and is now active." } });
    } catch (err) { setError(err.message); } finally { setSaving(false); onSavingChange?.(false); }
  }
  const panel = <section className="equipment-editor-panel"><header><h2 id={embedded ? "add-equipment-title" : undefined}>{editing ? "Edit equipment" : "Add equipment"}</h2><p>Fields marked * are required</p></header>
        {error && <p className="equipment-error" role="alert">{error}</p>}
        {editing && loadedId !== equipmentId ? !failed && <p role="status">Loading equipment...</p> : <form className="equipment-form" onSubmit={submit}>
          <fieldset disabled={saving}><div className="equipment-form-grid">
            <label className="equipment-field-wide">Name *<input name="name" value={form.name} onChange={change} maxLength={150} required placeholder="e.g. Server Room AC" /></label>
            <label className="equipment-field-wide">Type *<input name="equipment_type" list="equipment-types" value={form.equipment_type} onChange={change} maxLength={100} required placeholder="Select or enter an equipment type" /><datalist id="equipment-types">{types.map(type => <option key={type} value={type} />)}</datalist></label>
            <label className="equipment-field-wide">Identifier {editing ? "*" : "(automatic)"}<input name="identifier" value={form.identifier} onChange={change} maxLength={100} pattern="[A-Za-z0-9][A-Za-z0-9_-]*" title="Use letters, numbers, hyphens or underscores" required={editing} placeholder={editing ? "e.g. AC1" : "Assigned automatically, e.g. AC1"} /><small>{editing ? "Unique in your registry. Saved in uppercase." : "Leave blank for a type-based ID: AC1, AC2, WP1… Or enter your own."}</small></label>
            <label className="equipment-field-wide">Location *<input name="location" value={form.location} onChange={change} maxLength={200} required placeholder="e.g. Server Room, Ground floor" /></label>
            <label>Manufacturer<input name="manufacturer" value={form.manufacturer} onChange={change} maxLength={150} placeholder="e.g. Carrier" /></label>
            <label>Model<input name="model" value={form.model} onChange={change} maxLength={150} placeholder="e.g. 42QHC" /></label>
            <label>Installation date<input type="date" name="installation_date" value={form.installation_date} onChange={change} /></label>
            <label>Serial number<input name="serial_number" value={form.serial_number} onChange={change} maxLength={150} placeholder="Manufacturer serial number" /></label>
            <label className="equipment-field-wide">Notes<textarea name="description" value={form.description} onChange={change} rows={4} placeholder="Anything the inspection team should know" /></label>
          </div><div className="equipment-form-actions"><button type="button" className="equipment-cancel-btn" onClick={() => onCancel ? onCancel() : navigate(back)}>Cancel</button><button className="equipment-add-btn" type="submit">{saving ? "Saving..." : "Save equipment"}</button></div></fieldset>
        </form>}
      </section>;
  if (embedded) return panel;
  return <EquipmentLayout breadcrumb={editing ? "Edit equipment" : "Add equipment"}>
    <Link className="equipment-back" to={back}>← Back to equipment{editing ? " details" : ""}</Link>
    <div className="equipment-editor-layout">
      <div className="equipment-editor-intro"><p className="equipment-eyebrow">Equipment profile</p><h1>{editing ? "Keep your equipment up to date." : "Every inspection starts with a profile."}</h1><p>Identify your machine and its location so inspection information stays linked to the right equipment.</p><div className="equipment-info-note">Identifiers must be unique in your registry. New equipment is assigned to your account and starts with an active status.</div></div>
      {panel}
    </div>
  </EquipmentLayout>;
}
