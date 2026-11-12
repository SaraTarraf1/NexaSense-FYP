# Equipment reference and behavior

Equipment screens follow the supplied `04 · Equipment.pdf` and `05 · Equipment details.pdf` mockups and the Equipment Profile and Equipment Monitoring activity diagrams. The authentication and Multi-Sensor diagrams provide related access and monitoring context.

## Implemented

- Workspace navigation, teal registry controls, table/card views, name/ID search, type/location/health/status filters, sorting and pagination. Table rows provide a View details action.
- Required name, type, identifier and location; optional manufacturer, model, installation date, serial number and notes.
- Identifiers normalize to uppercase and accept letters, numbers, hyphens and underscores. They are unique per owner, enforced in the database and on create/update.
- The server assigns numeric IDs, authenticated ownership, active status and creation/update timestamps. Existing records receive `EQ-<id>` identifiers through migration `c12e73b54a90`.
- Save errors preserve the form, successful saves show confirmation, and owner checks protect every equipment operation.
- Add equipment opens a compact centered native dialog over the registry, including direct visits to `/equipment/new`. Escape, outside click, Cancel and the close button dismiss it; dismissal is disabled while saving. Successful registration updates the registry. Editing retains its dedicated route; details provide overview and profile views.

## Monitoring integration still required

The current equipment API exposes profile data only. Sensor readings, inspection runs, robot connectivity, health assessments, faults, scheduling and reports are not implemented by this change. The UI shows missing readings, unavailable timestamps and unknown health without copying the PDFs' example data.

When monitoring is connected, verify ownership before retrieving readings. Associate readings with equipment, sensor and inspection; validate readings and timestamps; label missing or outdated values; display available health, anomalies and faults. Do not treat absent data as normal health. Sensor collection and anomaly detection should follow the supplied Multi-Sensor activity diagram.
