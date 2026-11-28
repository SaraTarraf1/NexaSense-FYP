# NexaSense prototype workflows

Start PostgreSQL, activate the backend environment, and run `python -m alembic upgrade head` and `python -m scripts.seed_sensors` for a fresh development database. Start the API with `python -m uvicorn app.main:app --reload` from `backend` and the frontend with `npm run dev` from `frontend`. API contracts are also available at `http://127.0.0.1:8000/docs`.

## Historical data and trend analysis

The authenticated routes below use the existing bearer token. Equipment outside the user's account returns 404. Pass ISO 8601 timestamps with an explicit offset in `start` and `end`. The API normalizes both to UTC and includes the start while excluding the end. The browser translates the selected local calendar days into a range that includes the entire end day.

| Method | Route | Response |
| --- | --- | --- |
| GET | `/api/equipment/{id}/history` | Counts, full-period sensor statistics, chart samples, and diagnostic frequencies |
| GET | `/api/equipment/{id}/history/{section}` | Ordered page with `items`, `total`, `offset`, and `limit` |

Record sections are `readings`, `anomalies`, `faults`, `health`, and `inspections`. The default page has 25 rows, with a maximum of 100. Readings and embedded anomalies use measurement time, faults use classification time, and health uses assessment time. Inspection history uses actual start when available, then scheduled time, then creation time. Equal timestamps are ordered by record identifier. Inspection history shows the most recent assessment in the selected period for each inspection and uses **Not evaluated** when no assessment exists in that period.

Statistics group readings by sensor type and recorded unit. SQL computes the minimum, maximum, average, and count using valid finite values across the full period. The table preserves invalid and missing records and their validation messages. Charts select up to 200 points per group by taking evenly spaced positions in chronological order and retaining the first and last points. Sampling can omit short-lived extrema while the full-period statistical table retains them.

Anomaly frequencies are the share of saved anomalies with that type. Fault frequencies are the share of saved classification records with the type or, when no type matched, the recorded classification status. A classification with multiple distinct matches contributes once to each matching type. The service reads saved records and evidence without re-evaluating inspections. History needs no new migration or dependencies.

### History QA

1. Complete a simulated inspection and open **Equipment → Sensor history → Analyze this equipment's sensor history**.
2. Confirm the equipment is selected. Analyze dates spanning the inspection and compare counts against the paginated reading, anomaly, fault, and health views.
3. Confirm charts label temperature, thermal temperature, and vibration using the recorded units when those sensors have results. Open a fault match to view its evidence.
4. Try a reversed date range, an empty range, and a URL referencing equipment owned by a second account. Check that switching equipment clears previous results immediately.
5. Capture the summary with sensor charts, the paginated reading table, and the health timeline for project evidence.

## Inspection and maintenance reports

Choose equipment and a completed inspection in **Reports**. Equipment Details opens Reports with equipment selected, and completed inspection details open it with both selections populated. Generation collects the stored inspection, equipment profile, readings, anomalies, fault matches and evidence, health assessments, and recorded alert severity for that inspection. Repeated generation returns the first saved report.

Migration `fce4763b892a` adds `inspection_reports` with an owner, equipment and inspection foreign keys, a timezone-aware generation time, a unique inspection reference, and a versioned JSON snapshot. PostgreSQL locks the inspection row during report generation to serialize concurrent requests for the same inspection. Deleting a parent record under the existing data deletion policy removes its dependent reports. ReportLab 5.1.2 renders the saved snapshot with repeating table headings and numbered pages.

| Method | Route | Response |
| --- | --- | --- |
| GET | `/api/reports/eligible/{equipment_id}` | Paginated completed inspections for owned equipment |
| POST | `/api/reports` | Saved report detail for JSON fields `equipment_id` and `inspection_id` |
| GET | `/api/reports` | Paginated saved report history with an optional `equipment_id` filter |
| GET | `/api/reports/{report_id}` | Metadata and saved snapshot |
| GET | `/api/reports/{report_id}/pdf` | Authenticated PDF attachment |

Report listing and eligibility accept `offset` and `limit`. An inaccessible resource returns 404. An owned inspection with a status other than completed returns 409 on generation.

| Stored result | Suggested action |
| --- | --- |
| DR-001 overheating | Inspect ventilation, cooling and operating conditions |
| DR-002 mechanical stress | Inspect components, mounting and alignment |
| DR-003 electrical overheating | Arrange a qualified electrical inspection |
| DR-004 pump mechanical fault | Inspect pump mounting, coupling, bearings and operating conditions |
| DR-005 ventilation mechanical fault | Inspect the fan, drive, mounting and airflow |
| DR-006 heating system overheating | Inspect controls, heat transfer and ventilation |
| Unknown or undetermined fault | Arrange technical inspection or collect missing measurements, respectively |
| Insufficient data or not evaluated | Complete required measurements and review the next health assessment |
| Normal, warning or critical | Continue routine maintenance, schedule a review, or prioritize a qualified review, respectively |

These recommendations are predefined maintenance suggestions. Long inspections increase snapshot size and PDF creation time because all stored measurements are included. Built-in PDF fonts cover the standard Latin character set.

### Reports QA

1. Open a completed inspection and follow **Generate or view report**. Generate twice and check that both requests return the same report ID.
2. Compare the saved inspection, statistics, evidence, and health with the originating inspection. Generate a report for a completed inspection with missing data and check the limitations.
3. Download the PDF. Inspect the branding, generation date, page numbers, and final reading on a multi-page report. Try the PDF route without a token and with another account.
4. Capture the report list, saved details, and a multi-page PDF preview for project evidence.

## Inspection dashboard

`GET /api/dashboard` returns an authenticated overview with equipment totals, latest health counts, open alert totals, inspection counts by status, attention items, recent inspection activity, and monitoring snapshots. The response includes the server's observation timestamp. Each count and preview is scoped to the signed-in account. Health counts use the most recently saved assessment per equipment. Equipment with no assessment counts as **Not evaluated**.

Equipment appears in the attention preview when it has open alerts, warning or critical health from its latest executed inspection, or a valid anomaly or identified fault recorded within the last 60 seconds of its active inspection. Closing an alert retains the original event, evidence, and notifications. An unresolved alert remains actionable until closed. Older faults alone do not keep equipment in the attention preview.

The overview returns up to 12 attention items, 10 recent inspections with active runs prioritized, and monitoring for up to six equipment items, with active runs first. The Monitoring and Alerts workspaces offer the full equipment selector. Monitoring reuses the existing inspection-scoped sensor service and labels live, outdated, missing, and historical values. The dashboard refreshes every 10 seconds after the last request completes. It retains the last successful response across transient errors, shows its synchronization time, and cancels pending work when the route is left.

Use `GET /api/equipment/{equipment_id}/alerts?status=open` or `status=closed` to filter the existing alert history. `POST /api/equipment/{equipment_id}/alerts/{alert_id}/close` closes an owned alert and returns 204. Repeating the request leaves its closed status intact. `PUT /api/equipment/{equipment_id}` accepts `status` set to `active` or `inactive`. Neither integration requires a new migration.

### End-to-end demonstration and manual QA

1. Log in with a demonstration account. Check the empty dashboard for a new account and confirm the workspace links are visible.
2. Register equipment with a supported sensor configuration, such as an Air conditioner. Edit its profile and verify the registry filters by name, type, location, and status. Deactivate and reactivate the equipment.
3. Schedule a future inspection and manually start an inspection. Open the active inspection and check that saved readings display within the polling interval. Check freshness and timestamps. An abnormal simulator run in an isolated environment exercises validation, anomalies, faults, health assessment and alerts. Restore normal simulator behavior afterward.
4. Open Alerts, select the equipment, and close an alert. Filter for closed alerts and follow the related inspection link.
5. Complete the inspection. Refresh or reconnect after completion and confirm that the inspection polling loop stays stopped.
6. Open History for the equipment, choose the inspection date, and compare the readings, statistics, diagnostics and health against the source inspection.
7. From the completed inspection, generate a report, reopen it from Reports, and download its PDF.
8. Return to the dashboard and verify the completed and scheduled counts, updated alert totals, and historical monitoring label. Simulate a temporary connection failure and check that the last successful overview stays visible until refresh recovers.
9. Inspect the dashboard, History, and Reports layouts at desktop and phone widths. Log out and confirm that opening a protected deep link redirects to Login.

Capture a dashboard with an active inspection and attention items, a completed inspection with historical monitoring, and the mobile dashboard for project evidence.

## Verification and staging

From `backend`, run `python -m pytest tests/ -q`, `python -m alembic current`, `python -m alembic heads`, and `python -m alembic check`. From `frontend`, run `npm run lint` and `npm run build`. From the repository root, run `git diff --check` and `git status --short`.

- Monitoring correction, `fix: exclude non-finite values from live readings`. Stage `backend/app/api/sensor_readings.py`, `backend/app/services/equipment_monitoring_service.py`, and `backend/tests/test_equipment_monitoring.py`.
- US12, `feat: add historical analysis and sensor trends`. Stage `backend/app/api/history.py`, `backend/app/schemas/history.py`, `backend/app/services/history_service.py`, `backend/tests/test_history.py`, `frontend/src/pages/History.jsx`, `frontend/src/pages/History.css`, and `frontend/src/services/equipmentService.js`, plus the history hunks in `backend/app/main.py`, `frontend/src/App.jsx`, `frontend/src/components/EquipmentLayout.jsx`, `frontend/src/pages/EquipmentDetails.jsx`, `README.md`, and this guide.
- US13, `feat: save inspection reports and export PDFs`. Stage `backend/alembic/versions/fce4763b892a_create_inspection_reports.py`, `backend/app/api/reports.py`, `backend/app/models/inspection_report.py`, `backend/app/models/__init__.py`, `backend/app/schemas/report.py`, `backend/app/services/report_service.py`, `backend/app/services/report_pdf.py`, `backend/requirements.txt`, `backend/tests/test_reports.py`, `frontend/src/pages/Reports.jsx`, `frontend/src/pages/InspectionMonitoring.jsx`, and `frontend/src/services/workspaceService.js`, plus `README.md` and the report hunks in `backend/app/main.py`, `frontend/src/App.jsx`, `frontend/src/components/EquipmentLayout.jsx`, `frontend/src/pages/EquipmentDetails.jsx`, `frontend/src/pages/History.jsx`, and this guide.
- US14, `feat: integrate the inspection dashboard and workspaces`. Stage `backend/app/api/dashboard.py`, `backend/app/api/alerts.py`, `backend/app/api/equipment.py`, `backend/app/api/inspections.py`, `backend/app/schemas/dashboard.py`, `backend/app/schemas/equipment.py`, `backend/app/services/dashboard_service.py`, `backend/app/services/inspection_service.py`, `backend/tests/test_dashboard.py`, `frontend/src/components/EquipmentAlerts.jsx`, `frontend/src/components/InspectionReminders.jsx`, `frontend/src/components/ProtectedRoute.jsx`, `frontend/src/hooks/useEquipmentMonitoring.js`, `frontend/src/hooks/useMonitoringPoll.js`, `frontend/src/pages/Dashboard.jsx`, `frontend/src/pages/Dashboard.css`, `frontend/src/pages/Equipment.css`, `frontend/src/pages/Equipment.jsx`, `frontend/src/pages/EquipmentWorkspace.jsx`, `frontend/src/services/authService.js`, plus `README.md` and the dashboard hunks in `backend/app/main.py`, `backend/app/services/equipment_monitoring_service.py`, `frontend/src/App.jsx`, `frontend/src/components/EquipmentLayout.jsx`, `frontend/src/pages/EquipmentDetails.jsx`, `frontend/src/services/equipmentService.js`, `frontend/src/services/workspaceService.js`, and this guide.

The feature branches are stacked. Review `feature/historical-data-trend-analysis` against `main`, then `feature/inspection-maintenance-reports` against the history branch, and `feature/web-based-dashboard` against the reports branch. The history branch includes the separately committed monitoring correction and starts at the merge of Real-Time Monitoring.
