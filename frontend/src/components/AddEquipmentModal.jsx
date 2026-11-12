import { useEffect, useRef, useState } from "react";
import EquipmentForm from "./EquipmentForm";

export default function AddEquipmentModal({ onClose, onSaved }) {
  const dialog = useRef(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const element = dialog.current;
    const previousOverflow = document.body.style.overflow;
    element.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      element.close();
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  return <dialog
    ref={dialog}
    className="equipment-modal"
    aria-labelledby="add-equipment-title"
    onCancel={event => { event.preventDefault(); if (!saving) onClose(); }}
    onClick={event => {
      if (event.target !== dialog.current || saving) return;
      const bounds = dialog.current.getBoundingClientRect();
      if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) onClose();
    }}
  >
    <button type="button" className="equipment-modal-close" aria-label="Close add equipment" disabled={saving} onClick={onClose}>×</button>
    <EquipmentForm embedded onCancel={onClose} onSaved={onSaved} onSavingChange={setSaving} />
  </dialog>;
}
