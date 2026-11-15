import { useEffect, useRef } from "react";

export default function DeleteEquipmentModal({ item, deleting, error, onClose, onConfirm }) {
  const dialog = useRef(null);

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

  return <dialog ref={dialog} className="equipment-modal equipment-delete-modal"
    aria-labelledby="delete-equipment-title" aria-describedby="delete-equipment-description"
    onCancel={event => { event.preventDefault(); if (!deleting) onClose(); }}>
    <button type="button" className="equipment-modal-close" aria-label="Close delete confirmation" disabled={deleting} onClick={onClose}>&times;</button>
    <div className="equipment-delete-symbol" aria-hidden="true">!</div>
    <h2 id="delete-equipment-title">Delete equipment?</h2>
    <p id="delete-equipment-description">Are you sure you want to delete <strong>{item.name} ({item.identifier})</strong>? This action cannot be undone.</p>
    {error && <p className="equipment-error" role="alert">{error}</p>}
    <div className="equipment-delete-modal-actions">
      <button type="button" className="equipment-cancel-delete" autoFocus disabled={deleting} onClick={onClose}>Cancel</button>
      <button type="button" className="equipment-confirm-delete" disabled={deleting} onClick={onConfirm}>{deleting ? "Deleting..." : "Delete equipment"}</button>
    </div>
  </dialog>;
}
