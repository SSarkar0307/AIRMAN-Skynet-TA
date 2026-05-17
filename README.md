# Skynet Flight Operations Backend

Skynet is a backend-only aviation operations platform for flight schools and aviation academies. The repository models a real operational workflow rather than a generic CRUD service. The backend enforces sortie lifecycle transitions, aircraft readiness, training approval, defect handling, role-based access control, base scoping, and audit logging.

The project is structured as a small enterprise backend with the following core technologies:

- FastAPI for the HTTP layer
- SQLAlchemy for relational persistence
- Pydantic for request and response validation
- Alembic for schema migrations
- Pytest for workflow verification
- Docker Compose for a PostgreSQL-backed runtime

## Project Overview

The system simulates the operations backbone of an aviation academy SaaS. It manages aircraft, instructors, cadets, sorties, defects, and training approval records. The backend is responsible for rejecting unsafe or invalid actions, preserving traceability, and enforcing permissions in the API itself.

Core examples of enforced behavior:

- a cadet cannot approve training
- a sortie cannot move from `SCHEDULED` directly to `AIRBORNE`
- a grounded aircraft cannot be released for flight
- aircraft at one base cannot be controlled by users from another base unless the caller is `ADMIN`
- open high or critical defects block aircraft readiness

## Repository Layout

```text
.
|-- app/
|   |-- api/
|   |   `-- routes/
|   |-- core/
|   |-- db/
|   |-- schemas/
|   |-- services/
|   `-- main.py
|-- docs/
|-- migrations/
|   |-- env.py
|   |-- script.py.mako
|   `-- versions/
|-- tests/
|-- Dockerfile
|-- docker-compose.yml
|-- alembic.ini
|-- pyproject.toml
`-- README.md
```

## Architecture At A Glance

| Layer | Responsibility |
| --- | --- |
| `app/main.py` | App bootstrap, router registration, error handlers, startup database initialization |
| `app/api/routes/` | Thin HTTP route handlers and dependency wiring |
| `app/services/` | Business rules, state transitions, workflow enforcement, audit writes |
| `app/core/` | Settings, authentication, permissions, errors, query helpers |
| `app/db/` | SQLAlchemy models, session setup, startup seeding |
| `app/schemas/` | Request and response models used by FastAPI and OpenAPI |
| `migrations/` | Alembic migration environment and schema history |
| `tests/` | Automated verification for workflow, RBAC, scoping, and audit behavior |

The main architectural rule is simple: business logic lives in services, not in routes.

## Domain Model

| Entity | Purpose |
| --- | --- |
| Users | Aviation staff and trainees who authenticate into the platform |
| Bases | Physical training locations such as Delhi or Mumbai |
| Aircraft | Fleet records, readiness, and maintenance state |
| Sorties | Training flights and dispatch lifecycle records |
| Training Progress | Instructor evaluation and CFI approval history |
| Defects | Maintenance and safety issues affecting aircraft |
| Audit Logs | Immutable operational history for traceability |

## Roles And Permissions

| Role | Allowed Actions |
| --- | --- |
| `ADMIN` | Full access across all routes and all bases |
| `DISPATCHER` | Create sorties, release sorties, mark airborne, mark landed, cancel, close, and view operational records at the same base |
| `INSTRUCTOR` | View assigned sorties, create and submit training progress for assigned sorties, report defects at the same base |
| `CFI` | Approve or reject training progress at the same base |
| `CADET` | View own sorties and approved training progress |
| `MAINTENANCE_OFFICER` | Report defects, resolve or defer defects, ground aircraft, and mark aircraft ready |

## Workflow Summary

### Sortie Lifecycle

1. Sortie is scheduled.
2. Dispatcher releases the sortie.
3. Aircraft becomes airborne.
4. Aircraft lands.
5. Instructor creates and submits training progress.
6. CFI approves or rejects training progress.
7. Sortie closes after approval and safety checks.

### Aircraft And Defect Safety Workflow

1. A defect is reported.
2. High or critical defects ground the aircraft.
3. Maintenance resolves or defers the defect.
4. The aircraft can be marked ready only after severe open defects are cleared.

### Training Workflow

1. Instructor creates draft progress for an assigned sortie.
2. Instructor submits the evaluation with scores and remarks.
3. CFI reviews the submission and approves or rejects it.
4. Approved progress is visible to the cadet.

## Technology Stack

| Tool | Purpose |
| --- | --- |
| FastAPI | HTTP API framework and OpenAPI generation |
| Pydantic v2 | Request and response validation |
| SQLAlchemy 2.x | ORM and relational data access |
| Alembic | Database migration versioning |
| Pytest | Automated workflow verification |
| Uvicorn | ASGI application server |
| PostgreSQL | Containerized database backend |
| SQLite | Default local development database |

## Setup Instructions

### Prerequisites

- Python 3.12
- pip
- Git
- Docker Desktop if the container stack will be used

### Install Dependencies

```bash
pip install -e .
```

### Environment Variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | Database connection string | `sqlite+pysqlite:///./airman.db` |
| `JWT_SECRET_KEY` | Signing key for mock JWT tokens | `dev-secret-change-me` |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes | `120` |
| `APP_VERSION` | Application version shown in metadata | `1.0.0` |
| `API_VERSION` | API version tag used by the app | `v1` |
| `DATABASE_CONNECT_RETRIES` | Startup retry count for database initialization | `5` |
| `DATABASE_CONNECT_RETRY_DELAY_SECONDS` | Delay between startup retries | `2` |

## Run The Backend

### Local SQLite Mode

```powershell
$env:DATABASE_URL = "sqlite+pysqlite:///./airman.db"
$env:JWT_SECRET_KEY = "dev-secret-change-me"
uvicorn app.main:app --reload
```

The application serves the API at `http://127.0.0.1:8000`.

### Docker Compose Mode

```bash
docker compose up --build
```

Docker Compose starts PostgreSQL, runs Alembic migrations, seeds the database, and then launches the API server.

### API Documentation

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Run Migrations And Create Tables

The backend creates tables on startup, and Alembic is included for explicit schema management.

```bash
alembic upgrade head
```

To create a new migration after changing models:

```bash
alembic revision -m "describe your change"
```

To revert one migration:

```bash
alembic downgrade -1
```

Migration files are located in `migrations/versions/`.

## Seed Data

The application seeds demo data automatically when the database is empty.

The default dataset includes:

- two bases
- six users across the supported roles
- three aircraft
- five sorties with different workflow states
- training progress records
- open and resolved defects

To reseed a local SQLite database:

1. Stop the application.
2. Delete `airman.db`.
3. Start the application again.

To reseed the Docker Compose database:

1. Stop the stack.
2. Run `docker compose down -v`.
3. Start the stack again.

## Testing

Run the full automated suite with:

```bash
pytest
```

The tests verify:

- sortie state transitions
- aircraft grounding and readiness rules
- training progress permissions and approvals
- base scoping
- RBAC enforcement
- audit log creation
- validation failures for invalid scores and empty remarks

To run a single test file:

```bash
pytest tests/test_sorties.py
```

## API Summary

| Area | Route | Method | Purpose |
| --- | --- | --- | --- |
| Auth | `/auth/login` | `POST` | Mock login using email and role |
| Auth | `/auth/me` | `GET` | Return the current authenticated user |
| Users | `/users` | `GET` | List users with search, role, and base filtering |
| Users | `/users/{user_id}` | `GET` | Fetch a single user record |
| Bases | `/bases` | `GET` | List training bases |
| Bases | `/bases/{base_id}` | `GET` | Fetch a single base record |
| Aircraft | `/aircraft` | `POST` | Create an aircraft record |
| Aircraft | `/aircraft` | `GET` | List aircraft with filters |
| Aircraft | `/aircraft/{aircraft_id}` | `GET` | Fetch a single aircraft record |
| Aircraft | `/aircraft/{aircraft_id}/ground` | `PATCH` | Ground an aircraft |
| Aircraft | `/aircraft/{aircraft_id}/ready` | `PATCH` | Mark an aircraft ready |
| Sorties | `/sorties` | `POST` | Create a sortie |
| Sorties | `/sorties` | `GET` | List sorties with filters |
| Sorties | `/sorties/{sortie_id}` | `GET` | Fetch a single sortie |
| Sorties | `/sorties/{sortie_id}/release` | `PATCH` | Release a scheduled sortie |
| Sorties | `/sorties/{sortie_id}/airborne` | `PATCH` | Mark the sortie airborne |
| Sorties | `/sorties/{sortie_id}/landed` | `PATCH` | Mark the sortie landed |
| Sorties | `/sorties/{sortie_id}/cancel` | `PATCH` | Cancel a sortie |
| Sorties | `/sorties/{sortie_id}/close` | `PATCH` | Close a sortie after approval |
| Training | `/training-progress` | `POST` | Create draft training progress |
| Training | `/training-progress/{sortie_id}` | `GET` | Fetch training progress for a sortie |
| Training | `/training-progress/{progress_id}/submit` | `PATCH` | Submit draft or rejected progress |
| Training | `/training-progress/{progress_id}/approve` | `PATCH` | Approve submitted progress |
| Training | `/training-progress/{progress_id}/reject` | `PATCH` | Reject submitted progress |
| Defects | `/defects` | `POST` | Create a defect record |
| Defects | `/defects` | `GET` | List defects with filters |
| Defects | `/defects/{defect_id}` | `GET` | Fetch a single defect |
| Defects | `/defects/{defect_id}/resolve` | `PATCH` | Resolve an open defect |
| Defects | `/defects/{defect_id}/defer` | `PATCH` | Defer an open defect |
| Audit | `/audit-logs` | `GET` | List audit records |
| Health | `/health` | `GET` | Service health check |

## Business Rules Implemented

| Rule | Enforcement |
| --- | --- |
| Sortie state transitions are ordered | Invalid transitions raise `INVALID_STATE_TRANSITION` |
| Aircraft readiness is safety-gated | High or critical open defects block readiness |
| Base isolation is enforced | Non-admin users are limited to their own base |
| Training approval is restricted | Only `CFI` or `ADMIN` can approve or reject |
| Cadets are read-only participants | Cadets cannot create or modify operational records |
| Aircraft assignment must not overlap | Overlapping sortie windows are rejected |
| Critical actions are audited | Dispatch, training, defect, and readiness actions create audit entries |

## Known Limitations

| Limitation | Notes |
| --- | --- |
| Mock authentication | Login uses email and role rather than a production identity provider |
| No refresh tokens | Access tokens are short-lived but not paired with refresh tokens |
| No rate limiting | Public route throttling is not implemented |
| No idempotency keys | Critical mutation retries are not deduplicated |
| No request tracing middleware | Request IDs and structured trace logs are not included |

## What Would Be Improved With More Time

| Improvement | Reason |
| --- | --- |
| Real authentication provider | Replace mock login with password-based or SSO authentication |
| Request tracing and structured logs | Improve operational debugging and auditability |
| Idempotency keys | Protect critical actions from duplicate submissions |
| Rate limiting | Reduce abuse risk on public endpoints |
| Concurrency control hardening | Add broader safeguards for multi-actor updates |
| Soft delete or archival flows | Preserve historical records with more operational flexibility |
| PostgreSQL deployment tuning | Add production-specific connection and runtime settings |

## AI Usage Disclosure Summary

AI assistance was used heavily during the coding phase after the problem was simplified into smaller backend modules. The architecture, database design, route structure, and business rules were designed by the author, and AI implemented the coding work under that guidance. The final repository was reviewed against the assessment requirements before submission.

The full disclosure document is available at [docs/ai-usage-disclosure.md](docs/ai-usage-disclosure.md).

## Reference Documentation

- [docs/api-contract.md](docs/api-contract.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/business-rules.md](docs/business-rules.md)
- [docs/known-limitations.md](docs/known-limitations.md)

This README is the operational reference for the project.
