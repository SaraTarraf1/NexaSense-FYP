# NexaSense FYP

**AI-Powered Autonomous Inspection Robot for Smart Home and Facility Maintenance**

NexaSense is a final-year engineering project for an indoor inspection system that will combine robotics, IoT sensing, AI-based anomaly detection, equipment monitoring, and web-based maintenance reporting. The **current repository is the development foundation**, not a completed autonomous robot. Sensor values are planned to be simulated during early development; real Raspberry Pi hardware and MQTT integration will follow.

**Repository:** https://github.com/SaraTarraf1/NexaSense-FYP  
**Local Windows project directory:** `C:\Users\Sara\Desktop\NexaSense-FYP` (a local folder outside OneDrive)  
**Primary branch:** `main`

## 1. Foundation completion status

| Foundation task | Status | Verification |
|---|---|---|
| GitHub repository and project structure | Complete | Repository connected to `origin/main`; clean working tree after push |
| Python and FastAPI backend | Complete | `/` and `/health` respond; Swagger UI available |
| React and Vite frontend | Complete | Development server and production build verified |
| PostgreSQL and Alembic | Complete | Connection as `nexasense_user`; revision `8b70b860f363 (head)` |
| Postman and pytest | Complete | Postman `GET /health` returns 200; 3 pytest tests passed |

This status describes the **environment and application skeleton**. Authentication, sensor ingestion, equipment management, AI detection, inspection scheduling, dashboards, robot navigation, and reports still require implementation.

## 2. Technology stack

| Layer | Technology | Version verified during setup |
|---|---|---|
| OS / IDE | Windows, Visual Studio Code, PowerShell | Local development |
| Version control | Git and GitHub | `main` branch |
| Backend language | Python | 3.12.7 |
| Backend framework | FastAPI | 0.162.4 |
| ASGI server | Uvicorn | 0.54.0 |
| Database | PostgreSQL | 18.6 |
| Database administration | pgAdmin 4 | Installed with PostgreSQL |
| ORM / migrations | SQLAlchemy, Alembic | Exact installed versions in `backend/requirements.txt` |
| PostgreSQL driver | psycopg 3 with binary extras | Exact version in requirements |
| Configuration | python-dotenv | Exact version in requirements |
| Frontend runtime | Node.js / npm | 24.22.1 / 11.19.1 |
| UI | React / React DOM | 19.3.1 |
| Frontend tooling | Vite | 8.3.7 |
| API manual testing | Postman | Desktop application |
| Automated API testing | pytest, HTTPX, FastAPI TestClient | Exact versions in requirements |

**Source of truth for package versions:** `backend/requirements.txt` and `frontend/package-lock.json`. Versions above reflect the successful foundation setup; future upgrades may change them.

## 3. Repository structure

```text
NexaSense-FYP/
├── .gitignore
├── README.md                         # This root guide
├── backend/
│   ├── .env.example                   # Safe template; commit this
│   ├── .env                           # Local secrets; NEVER commit
│   ├── .venv/                         # Local Python environment; ignored
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 49a6f97c0dfc_initial_database_schema.py
│   │       └── 8b70b860f363_initial_database_schema.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   │   └── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
│       ├── __init__.py
│       └── test_main.py
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── eslint.config.js
│   ├── index.html
│   ├── public/
│   └── src/
│       ├── App.jsx
│       ├── App.css
│       ├── main.jsx
│       ├── index.css
│       ├── assets/
│       ├── components/
│       ├── context/
│       ├── hooks/
│       ├── layouts/
│       ├── pages/
│       ├── services/
│       └── utils/
└── docs/
    └── postman/
        └── NexaSense_FYP_API.postman_collection.json
```

Empty folders are intentionally retained with `__init__.py` (Python packages) or `.gitkeep` (frontend placeholders). `frontend/node_modules/`, `frontend/dist/`, and `backend/.venv/` are generated locally and should not be committed. The two tracked initial migrations are part of the actual history; do not delete them merely because both have similar names.

## 4. Fresh installation on Windows

### 4.1 Install prerequisites

Install **Git**, **VS Code** (with Python extension), **Python 3.12**, **Node.js 24** (includes npm), **PostgreSQL 18** (with pgAdmin and command-line tools), and **Postman**. Official websites:

- Python: https://www.python.org/downloads/
- Node.js: https://nodejs.org/
- Git: https://git-scm.com/downloads
- VS Code: https://code.visualstudio.com/
- PostgreSQL: https://www.postgresql.org/download/windows/
- Postman: https://www.postman.com/downloads/

Confirm installation in PowerShell:

```powershell
py -3.12 --version
node --version
npm --version
git --version
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" --version
Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
```

During initial setup, PostgreSQL 18.6 was installed to `C:\Program Files\PostgreSQL\18`; its Windows service was `postgresql-x64-18`. Keep the PostgreSQL administrator (`postgres`) password private.

### 4.2 Clone the repository and open VS Code

```powershell
New-Item -ItemType Directory -Path "C:\Users\Sara\Desktop" -Force
cd "C:\Users\Sara\Desktop"
git clone https://github.com/SaraTarraf1/NexaSense-FYP.git
cd NexaSense-FYP
code .
```

**Note:** On this computer, `[Environment]::GetFolderPath("Desktop")` returned `C:\Users\Sara\OneDrive\Desktop`. The chosen project directory `C:\Users\Sara\Desktop\NexaSense-FYP` is therefore a **separate local folder**, not the Windows Desktop folder redirected by OneDrive. On another computer, choose any suitable local directory.

### 4.3 Restore the backend virtual environment

From the repository root:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

In VS Code select **Python: Select Interpreter** and choose `backend\.venv\Scripts\python.exe`. If the project is moved to a different path, **recreate `.venv`** because executable launchers can retain the previous absolute path. Do not commit `.venv`.

### 4.4 Restore the frontend

Open a separate VS Code terminal:

```powershell
cd "C:\Users\Sara\Desktop\NexaSense-FYP\frontend"
npm ci
npm run lint
npm run build
```

`npm ci` uses the committed `package-lock.json` for a reproducible installation. For ordinary local changes, `npm install` is also available.

## 5. PostgreSQL database configuration

### 5.1 Create the application role and database

In **pgAdmin 4**, connect to the local PostgreSQL 18 server as an administrator. Create a login role named `nexasense_user` with a **strong private password** and without superuser or database-creation privileges. Create a database named `nexasense_db`, with `nexasense_user` as owner. Default local PostgreSQL port is `5432` in this setup.

Equivalent SQL (execute as a PostgreSQL administrator; substitute a private password and **do not commit or share it**):

```sql
CREATE ROLE nexasense_user LOGIN PASSWORD 'REPLACE_WITH_PRIVATE_PASSWORD';
CREATE DATABASE nexasense_db OWNER nexasense_user;
```

Run `CREATE DATABASE` outside an explicit transaction block. If the role/database already exists, do not run these creation statements again.

### 5.2 Configure local environment variables

Inside `backend`, copy the committed template to a local `.env`:

```powershell
cd "C:\Users\Sara\Desktop\NexaSense-FYP\backend"
Copy-Item .env.example .env
```

Set values in `backend/.env`:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nexasense_db
DB_USER=nexasense_user
DB_PASSWORD=REPLACE_WITH_YOUR_PRIVATE_PASSWORD
```

**Never put the real password in README files, screenshots, Git commits, Postman exports, or messages.** If the password includes `#`, spaces, or other special characters, follow `.env` quoting rules; SQLAlchemy's `URL.create()` safely handles URL encoding when building the connection.

`backend/app/core/database.py` loads the `.env`, constructs a SQLAlchemy PostgreSQL URL using the `psycopg` driver, creates the engine and session factory, and defines the declarative `Base` for future models. The PostgreSQL server and database are **not stored inside the Git repository**: each developer needs their own PostgreSQL instance or approved shared development database.

### 5.3 Apply existing Alembic migrations

From the activated backend environment:

```powershell
python -m alembic upgrade head
python -m alembic current
```

The verified revision at foundation completion was:

```text
8b70b860f363 (head)
```

In pgAdmin, open Query Tool on `nexasense_db`:

```sql
SELECT * FROM alembic_version;
SELECT current_database(), current_user;
```

The version query should show the current Alembic revision. In pgAdmin, `current_user` may be `postgres` if the Query Tool is connected as the administrator; the Python application uses `nexasense_user`.

**Future schema changes:** Define SQLAlchemy models, ensure they are imported into Alembic's metadata context, then run:

```powershell
python -m alembic revision --autogenerate -m "Describe schema change"
# Review the generated migration carefully before applying it.
python -m alembic upgrade head
python -m alembic current
```

Do not blindly run autogeneration without importing the relevant model modules into Alembic's metadata. The foundation revisions establish migration tracking; they do **not** implement the complete FYP ERD.

## 6. Run the application locally

Use **two separate VS Code terminals**.

### Terminal A — FastAPI backend

```powershell
cd "C:\Users\Sara\Desktop\NexaSense-FYP\backend"
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

- Backend root: http://127.0.0.1:8000/
- Health endpoint: http://127.0.0.1:8000/health
- Interactive Swagger API docs: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

Expected responses:

```json
{"message":"Welcome to NexaSense API","status":"running"}
```

```json
{"status":"healthy","service":"NexaSense Backend"}
```

The `/health` endpoint currently reports the **application's health**, not an active database or sensor health check.

### Terminal B — React frontend

```powershell
cd "C:\Users\Sara\Desktop\NexaSense-FYP\frontend"
npm run dev
```

Open http://localhost:5173/ (or the local URL printed by Vite). The current frontend is a welcome/skeleton screen. It does not yet implement all dashboard features or necessarily communicate with the backend.

Stop either server using **Ctrl+C** in its terminal.

## 7. Testing

### 7.1 Postman manual testing

Import the committed collection:

`docs/postman/NexaSense_FYP_API.postman_collection.json`

In Postman choose **Import**, select the file, and open **NexaSense FYP API**. Start the backend first. The collection contains the foundation requests:

| Request | Method | URL | Expected |
|---|---|---|---|
| Root Endpoint | GET | `http://127.0.0.1:8000/` | HTTP 200 and welcome JSON |
| Health Check | GET | `http://127.0.0.1:8000/health` | HTTP 200 and healthy JSON |

Do not export authentication tokens or passwords into committed collections. Later, organize requests into Authentication, Equipment, Sensors, Inspections, Anomalies, and Alerts folders.

### 7.2 pytest automated tests

```powershell
cd "C:\Users\Sara\Desktop\NexaSense-FYP\backend"
.\.venv\Scripts\Activate.ps1
python -m pytest tests/ -v
```

`backend/tests/test_main.py` tests: (1) root response is HTTP 200 with expected JSON; (2) health response is HTTP 200 with expected JSON; (3) an unknown path returns HTTP 404. **Foundation result: 3 passed.** The run also displayed one Starlette/FastAPI deprecation warning about importing `TestClient`; this was a warning, not a test failure. The tests use FastAPI's `TestClient` and do not require Uvicorn to be running.

## 8. GitHub collaboration workflow

```powershell
cd "C:\Users\Sara\Desktop\NexaSense-FYP"
git status
git pull origin main
# Edit files, then review changes.
git add <specific-files>
git diff --cached --name-only
git commit -m "Describe the change"
git push origin main
```

Use feature branches and pull requests when collaborating, particularly for model and migration changes. **Never commit** `.env`, `.venv/`, `node_modules/`, credentials, or generated build output. `backend/.env.example` is intentionally committed; `backend/.env` is ignored. Confirm with:

```powershell
git check-ignore -v backend/.env
git check-ignore -v backend/.venv
git status
```

The final foundation Postman/pytest commit was `0b42b24` on `main` and the working tree was clean after pushing. Future README edits will create a new commit.

## 9. Issues encountered and resolutions

| Issue during setup | Cause / resolution |
|---|---|
| PowerShell refused to activate `.venv` / run npm scripts | Execution policy blocked PowerShell scripts. Applied `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`, then reopened the terminal. |
| Python dependency installation was slow or timed out | Initial pip resolver backtracking/network timeouts. Retried and installed backend packages successfully; saved working versions to `requirements.txt`. |
| `psql` command not found | PostgreSQL binaries were not on `PATH`; used `& "C:\Program Files\PostgreSQL\18\bin\psql.exe" --version`. |
| PostgreSQL authentication failed for `nexasense_user` | Reset role password in pgAdmin and updated private `backend/.env`; subsequent SQLAlchemy connection succeeded. |
| Alembic `current` initially showed no revision | No migrations had been applied. Created/applied baseline migrations and confirmed `8b70b860f363 (head)`. |
| Moving project out of OneDrive failed with "file is being used by another process" | Closed VS Code/terminals and other programs holding project files; moved the project to `C:\Users\Sara\Desktop\NexaSense-FYP`. |
| Python environment after moving directories | Recreated `backend/.venv` at the new path and reinstalled from `requirements.txt`; Python, pip, and Alembic checks passed. |
| pytest displayed one deprecation warning | Three tests passed; warning originated in testing dependencies. Revisit when upgrading FastAPI/Starlette. |
| Postman collection initially exported to repository root | Moved JSON to `docs/postman/` and committed it. |

## 10. Planned functional architecture (not yet implemented)

```text
[Indoor equipment / facilities]
           |
[Simulated readings initially; later real sensors on Raspberry Pi]
           |
[Future ingestion: HTTP API and/or MQTT bridge]
           |
[FastAPI services + validation + anomaly detection]
           |
[PostgreSQL: equipment, sensors, readings, inspections,
 anomalies, faults, alerts, maintenance history, users]
           |
[React web dashboard: monitoring, alerts, history, reports]
```

**Planned feature areas** (based on FYP scope): user registration/login and role-based access; equipment and sensor management; inspection records; simulated multi-sensor monitoring; AI anomaly detection and fault classification; real-time alerts; web dashboard; later autonomous navigation, mobile app, maintenance recommendations, and reporting. The detailed entities, permissions, workflows, and relationships should follow the approved ERD, use cases, and Azure DevOps user stories—not assumptions in this README.

### Raspberry Pi and MQTT migration plan

1. **Keep a stable reading format:** agree on `device_id`, `equipment_id`, `sensor_type`, `value`, `unit`, `timestamp`, and data-quality/status fields. Define Pydantic validation schemas and test them using simulated payloads first.
2. **Introduce a sensor ingestion service:** implement FastAPI endpoints or a background MQTT subscriber/worker that validates incoming messages before storing them. Avoid running a long-lived MQTT subscriber inside a per-request handler.
3. **Choose and configure a broker:** for development, use an approved local or managed MQTT broker. Define topics, QoS, authentication, TLS, reconnect behavior, and message deduplication. Do not put broker credentials in source code.
4. **Connect real Raspberry Pi sensors:** read physical sensor values on the Pi, attach timestamps/device identity, and publish messages using a Python MQTT client. Keep the Pi code separate from the web UI and database credentials.
5. **Preserve the backend contract:** both simulator and real hardware should produce the same validated payload shape so dashboards and anomaly-detection logic need minimal changes.
6. **Handle failures:** design for sensor disconnects, stale readings, duplicate MQTT messages, out-of-range values, and temporary database/network outages.
7. **Extend the schema with migrations:** add actual sensor, reading, inspection, anomaly, and alert models through reviewed Alembic migrations; evaluate time-series partitioning or TimescaleDB only if measurements justify it.
8. **Test in stages:** unit tests for parsing and thresholds; API integration tests; MQTT message flow tests; end-to-end dashboard tests; then physical hardware verification.

**MQTT and Raspberry Pi are future integration work, not currently installed or verified in this repository.** No Kubernetes, Kafka, RabbitMQ, or Docker stack is required for the five foundation tasks documented here.

## 11. Quick verification checklist

From the project root after a fresh installation:

```powershell
# Git
git status

# Backend dependencies and database migration
cd backend
.\.venv\Scripts\Activate.ps1
python --version
python -m pip check
python -m alembic current
python -m pytest tests/ -v

# Frontend checks (in another terminal)
cd ..\frontend
npm run lint
npm run build
```

For live manual checks, run `python -m uvicorn app.main:app --reload` from `backend`, then `npm run dev` from `frontend`, and test the two Postman requests. A clean environment should have its own local `.env` and PostgreSQL database configured before running Alembic.

## 12. Next development steps

After the five foundation tasks, proceed with the approved Azure DevOps feature stories in dependency order: authentication and roles, core equipment/sensor data model, simulated sensor ingestion, anomaly detection, alerts, and web dashboard. Add tests and migrations incrementally, and keep README instructions updated as actual features are implemented.

---

**Security reminder:** The committed README and `.env.example` contain no real database password. The local `.env` is required but intentionally excluded from GitHub.
