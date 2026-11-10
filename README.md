# NexaSense — AI-Powered Autonomous Inspection Robot

## 1. Project Overview

NexaSense is an AI-Powered Autonomous Inspection Robot for Smart Home and Facility Maintenance.

The project aims to develop an intelligent system that monitors equipment conditions, detects abnormal sensor measurements, identifies potential faults, evaluates equipment health, and provides alerts and inspection reports through a web-based dashboard.

The system will integrate robotics, IoT sensors, backend services, database management, and web technologies.

### Development Approach

**Current Semester — Software Implementation**

- Develop the frontend and backend applications.
- Implement user authentication and equipment management.
- Develop inspection management and monitoring features.
- Use simulated sensor values for equipment monitoring.
- Implement rule-based anomaly detection and fault classification.
- Develop alerts, historical monitoring, and reporting features.
- Test each functional feature.

**Next Semester — Physical Robot Integration**

- Integrate the Raspberry Pi robot and physical sensors.
- Implement MQTT communication between the robot and backend.
- Replace simulated measurements with real sensor readings.
- Integrate real-time monitoring with physical equipment.
- Perform complete hardware–software integration testing.

The same GitHub repository, frontend, backend, and database will be maintained throughout both semesters.

---

## 2. Technology Stack

| Component | Technology |
|---|---|
| Development Environment | Visual Studio Code |
| Frontend | React, JavaScript, HTML, CSS, Vite |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| Database Integration | SQLAlchemy |
| Database Migrations | Alembic |
| API Development and Testing | Postman |
| Backend Testing | pytest |
| Version Control | Git and GitHub |
| Current Sensor Data | Simulated sensor values |
| Future Hardware | Raspberry Pi and physical sensors |
| Future Communication | MQTT |
| Real-Time Monitoring | WebSockets when required |

Docker is not required for the initial development environment.

---

## 3. Development Environment and Installed Versions

The initial development environment was configured on Windows.

| Software | Verified Version |
|---|---|
| Visual Studio Code | 1.144.1 (x64) |
| Git | 2.56.0.windows.2 |
| Python selected for backend | 3.12.7 |
| Node.js | 24.22.1 |
| npm | 11.19.1 |
| PostgreSQL | Pending installation |

### Verify Installed Software

Open the PowerShell terminal in Visual Studio Code.

```powershell
git --version
code --version
py -3.12 --version
node --version
npm.cmd --version
```

Python 3.12.7 was selected for backend development because of its broad compatibility with FastAPI and related libraries.

---

## 4. GitHub Repository Setup

### Repository Information

- Repository name: `NexaSense-FYP`
- Repository URL: https://github.com/SaraTarraf1/NexaSense-FYP
- Main branch: `main`
- Repository visibility: Public
- Version control: Git

### Clone the Repository

To set up the project on a new computer:

```powershell
git clone https://github.com/SaraTarraf1/NexaSense-FYP.git
cd NexaSense-FYP
code .
```

The repository can be cloned into any preferred local directory.

### Verify GitHub Connection

```powershell
git status
git remote -v
```

The `git status` command displays the current branch and local changes.

The `git remote -v` command verifies the remote GitHub repository.

### Basic Git Workflow

After making changes:

```powershell
git status
git add .
git commit -m "Describe the changes"
git push origin main
```

For collaborative feature development, use separate branches and pull requests rather than pushing all changes directly to `main`.

### Collaboration

The repository will be shared between project team members.

Team members should:

- Pull the latest changes before starting development.
- Use descriptive commit messages.
- Work on separate feature branches when appropriate.
- Review changes before merging into `main`.
- Never commit passwords, API keys, or private configuration files.

---

## 5. Project Directory Structure

The initial project structure is:

```text
NexaSense-FYP/
│
├── backend/
│   └── .gitkeep
│
├── frontend/
│   └── .gitkeep
│
├── docs/
│   └── .gitkeep
│
├── .gitignore
└── README.md
```

### Directory Descriptions

**backend/**

Contains the Python FastAPI application, API endpoints, database models, business logic, and backend tests.

**frontend/**

Contains the React web application, pages, reusable components, and frontend services.

**docs/**

Contains project documentation, architecture diagrams, and supporting design materials.

**README.md**

Contains the project overview, selected technologies, installation procedures, development commands, configuration instructions, and troubleshooting notes.

**.gitignore**

Excludes unnecessary local files, dependencies, virtual environments, and sensitive configuration files from version control.

---

## 6. Backend Environment Setup

Status: Not started.

Planned technologies:

- Python 3.12
- FastAPI
- Uvicorn
- SQLAlchemy
- Alembic
- PostgreSQL driver
- pytest

The installation commands, virtual environment configuration, backend structure, and execution instructions will be added during Backend Environment Setup.

---

## 7. Frontend Environment Setup

Status: Not started.

Planned technologies:

- React
- JavaScript
- Vite
- HTML and CSS

The frontend initialization commands, dependencies, project structure, and development server instructions will be added during Frontend Environment Setup.

---

## 8. PostgreSQL Database Setup

Status: Not started.

PostgreSQL will be used as the primary database for NexaSense.

The database will store application information such as:

- Users and authentication records
- Equipment and robots
- Inspections
- Sensor readings
- Anomaly detection results
- Fault classifications
- Equipment health assessments
- Alerts and notifications
- Inspection reports

SQLAlchemy will manage database models and interactions, while Alembic will manage schema migrations.

Installation and configuration instructions will be added during PostgreSQL Database Setup.

---

## 9. Development and Testing Tools

Status: Not started.

Postman will be used to develop and manually verify backend API requests.

pytest will be used for automated backend testing.

Feature-specific test cases will be created and executed as the corresponding features are implemented.

---

## 10. Environment Variables and Security

Sensitive configuration information must not be committed to GitHub.

Examples include:

- Database passwords
- API keys
- Authentication secrets
- Private configuration values

Local environment variables will be stored in `.env` files, which are excluded by `.gitignore`.

A `.env.example` file will document required environment variable names using placeholder values.

---

## 11. Troubleshooting and Setup Notes

### Issue 1 — Python Command Not Working

**Problem:**

Running:

```powershell
python --version
```

produced an executable path error.

**Investigation:**

```powershell
py --version
py -0p
where.exe python
Get-Command python -All
```

The Python launcher detected multiple Python installations.

**Solution:**

Use the Python launcher to select Python 3.12 explicitly:

```powershell
py -3.12 --version
```

Verified result: Python 3.12.7.

A dedicated virtual environment will be created for the backend during its setup task.

### Issue 2 — npm Blocked by PowerShell

**Problem:**

Running:

```powershell
npm --version
```

failed because PowerShell blocked the `npm.ps1` script.

**Solution:**

Use:

```powershell
npm.cmd --version
```

Verified npm version: 11.19.1.

This avoids changing the system-wide PowerShell execution policy.

### Note — OneDrive Desktop Location

The project was placed on the Windows Desktop, which is synchronized with OneDrive.

Local development path at initial setup:

```text
C:\Users\Sara\OneDrive\Desktop\NexaSense-FYP
```

This path is specific to the initial development computer and is not required on other computers.

If OneDrive synchronization causes file-locking or development issues, the repository can be moved to a non-synchronized directory without losing its GitHub connection.

---

## 12. Development Progress

| Task | Status |
|---|---|
| GitHub Repository and Project Structure Setup | In progress |
| Backend Environment Setup | Not started |
| Frontend Environment Setup | Not started |
| PostgreSQL Database Setup and Configuration | Not started |
| Development Tools Configuration | Not started |

This section will be updated as development progresses.

---

## 13. Continuing Development Next Semester

To continue development on the same computer or another computer:

1. Open the existing repository or clone it from GitHub.
2. Review this README for software prerequisites and required versions.
3. Install backend and frontend dependencies.
4. Configure local environment variables.
5. Start PostgreSQL.
6. Apply database migrations.
7. Start the FastAPI backend.
8. Start the React frontend.
9. Continue development using the existing codebase.

Detailed commands will be added as each development environment task is completed.

The final robot implementation will extend the existing application rather than replace it.