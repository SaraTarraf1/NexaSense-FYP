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
