# Architecture

This document describes the structure of the Skynet backend and the design decisions used to enforce aviation workflow correctness.

## 1. Backend Structure

The application uses a layered FastAPI architecture.

| Layer | Files | Responsibility |
| --- | --- | --- |
| Entry point | `app/main.py` | Builds the app, registers routers, configures error handlers, initializes the database, and seeds data |
| Routes | `app/api/routes/` | Receive HTTP requests, bind dependencies, and call service functions |
| Services | `app/services/` | Enforce business rules, state transitions, and audit logging |
| Core helpers | `app/core/` | Configuration, authentication, permissions, error helpers, and query helpers |
| Persistence | `app/db/` | SQLAlchemy models, session creation, and startup seed data |
| Schemas | `app/schemas/` | Pydantic contracts used by the API and OpenAPI |
| Tests | `tests/` | Workflow, RBAC, scoping, and audit verification |

The most important rule is that routes stay thin. Business logic lives in services where it can be tested directly.

### Request Flow

```text
Client -> FastAPI route -> dependency checks -> service function -> database transaction -> audit log -> response model
```

## 2. Database Design

The schema is relational and centered on aviation operations.

| Table | Purpose | Key Relationships |
| --- | --- | --- |
| `bases` | Training locations | One base has many users, aircraft, sorties, defects, and training records |
| `users` | People using the platform | Each user belongs to one base |
| `aircraft` | Fleet records and readiness state | Each aircraft belongs to one base and can have many sorties and defects |
| `sorties` | Training flight records | Each sortie links one cadet, one instructor, one aircraft, and one base |
| `training_progress` | Instructor evaluation and CFI approval | Each record is tied to one sortie |
| `defects` | Maintenance and safety issues | Each defect belongs to one aircraft and may optionally link to one sortie |
| `audit_logs` | Immutable operational history | Each log records one action against one entity |

### Database Integrity Rules

| Rule | Implementation |
| --- | --- |
| Unique sortie number | Database uniqueness constraint and service-level conflict check |
| Unique aircraft registration | Database uniqueness constraint and service-level conflict check |
| One training record per sortie | Service-level existence check before insertion |
| Overlapping sortie windows | Service-level conflict detection before aircraft assignment |
| Severe open defects block readiness | Maintenance service query before `READY` transition |

## 3. Role And Permission Design

Role checks are enforced in both the route layer and the service layer. Frontend visibility is not treated as security.

| Role | Permission Model |
| --- | --- |
| `ADMIN` | Bypasses base scoping and can perform all operations |
| `DISPATCHER` | Manages sorties and operational dispatch at the user base |
| `INSTRUCTOR` | Manages training progress for assigned sorties and can report defects |
| `CFI` | Reviews and decides training submissions |
| `CADET` | Views own sorties and approved progress only |
| `MAINTENANCE_OFFICER` | Manages defects and aircraft readiness |

The permission helpers in `app/core/permissions.py` centralize these checks so routes do not need to duplicate them.

## 4. State Transition Handling

The assessment is primarily about workflow correctness. The backend therefore treats sortie, aircraft, training, and defect records as state machines.

### Sortie State Machine

| Current State | Allowed Next State | Trigger |
| --- | --- | --- |
| `SCHEDULED` | `RELEASED` | Dispatcher releases the sortie |
| `RELEASED` | `AIRBORNE` | Dispatcher marks the sortie airborne |
| `AIRBORNE` | `LANDED` | Dispatcher marks the sortie landed |
| `LANDED` | `TRAINING_SUBMITTED` | Training progress is submitted |
| `TRAINING_SUBMITTED` | `TRAINING_APPROVED` | CFI approves the training |
| `TRAINING_APPROVED` | `CLOSED` | Dispatcher closes the sortie |
| `SCHEDULED`, `RELEASED`, `AIRBORNE`, `LANDED`, `TRAINING_SUBMITTED`, `TRAINING_APPROVED` | `CANCELLED` | Dispatcher cancels the sortie when appropriate |
| `AIRCRAFT_GROUNDED` | `RECOVERY_REQUIRED` | Defect recovery is cleared |
| `RECOVERY_REQUIRED` | `CLOSED` | Dispatcher closes after recovery and approval |

### Aircraft State Machine

| Current State | Allowed Next State | Trigger |
| --- | --- | --- |
| `READY` | `SCHEDULED` | Sortie creation or assignment |
| `SCHEDULED` | `AIRBORNE` | Sortie departs |
| `AIRBORNE` | `LANDED` | Sortie returns |
| Any state | `GROUNDED` | Maintenance grounds the aircraft |
| Any state | `READY` | Maintenance clears severe open defects |
| Any state | `MAINTENANCE` | Safety or maintenance hold |

### Training Progress State Machine

| Current State | Allowed Next State | Trigger |
| --- | --- | --- |
| `DRAFT` | `SUBMITTED` | Instructor submits evaluation |
| `REJECTED` | `SUBMITTED` | Instructor resubmits after rejection |
| `SUBMITTED` | `APPROVED` | CFI approves |
| `SUBMITTED` | `REJECTED` | CFI rejects |

### Defect State Machine

| Current State | Allowed Next State | Trigger |
| --- | --- | --- |
| `OPEN` | `RESOLVED` | Maintenance resolves the issue |
| `OPEN` | `DEFERRED` | Maintenance defers the issue |

### Transition Enforcement

The service layer rejects invalid transitions using structured `INVALID_STATE_TRANSITION` errors. The route layer does not allow direct database mutation, so workflow changes always pass through the service logic.

## 5. Audit Log Design

Audit logging is used to preserve traceability for operational actions.

| Design Element | Description |
| --- | --- |
| Actor | The authenticated user who performed the action |
| Action | A stable verb such as `SORTIE_RELEASED`, `TRAINING_APPROVED`, or `DEFECT_RESOLVED` |
| Entity | The affected business object and its identifier |
| Old value | Snapshot of the previous relevant state |
| New value | Snapshot of the resulting relevant state |
| Reason | Optional human explanation provided by the caller |
| Timestamp | Stored on every write and returned in the API |

Audit records are written in the same transaction as the business change, so the history matches the final committed state.

## 6. Error Handling Design

The application returns structured errors instead of raw Python exceptions.

| Error Code | Status | Meaning |
| --- | --- | --- |
| `UNAUTHORIZED` | 401 | Token missing or invalid |
| `FORBIDDEN` | 403 | Caller is authenticated but not allowed to perform the action |
| `NOT_FOUND` | 404 | Resource is missing or hidden by scope |
| `CONFLICT` | 409 | State conflict, duplicate, overlap, or readiness block |
| `INVALID_STATE_TRANSITION` | 409 | Transition is not valid from the current state |
| `VALIDATION_ERROR` | 422 | Schema or business validation failed |

The error handler in `app/main.py` normalizes these responses into a consistent JSON shape with `error`, `message`, and an optional `field`.

## 7. Seed Data

Seed data is loaded by `app/db/seed.py` during application startup if the `users` table is empty.

| Seed Group | Contents |
| --- | --- |
| Bases | Delhi Base and Mumbai Base |
| Users | Admin, dispatcher, instructor, CFI, cadet, maintenance officer |
| Aircraft | Ready, grounded, and cross-base aircraft records |
| Sorties | Multiple workflow states for testing and demonstration |
| Training progress | Approved and submitted examples |
| Defects | Open critical defect and resolved low-severity defect |
| Audit log | Initial seed marker |

This makes the repository runnable immediately after startup and ensures the assessment reviewer has sample data for route testing.

## 8. Backend Enforcement Versus Frontend Responsibility

| Responsibility | Backend | Frontend |
| --- | --- | --- |
| Authentication | Enforces token checks | Renders login and session state |
| Authorization | Enforces role and base access | Hides irrelevant buttons and pages |
| Workflow correctness | Enforces state transitions | Presents valid actions to the user |
| Data integrity | Enforces constraints and conflicts | Collects user input |
| Auditability | Writes audit logs | Displays history if needed |

The backend is the source of truth. Frontend visibility is only a convenience layer.

## 9. Known Trade-Offs

| Trade-Off | Reason |
| --- | --- |
| Mock login instead of a full identity provider | Keeps the assessment focused on backend workflow logic |
| SQLite default for local development | Makes the repository easy to run without extra services |
| List endpoints return arrays instead of a paging envelope | Keeps the contract simple while still supporting pagination filters |
| No request-id middleware | Not required by the assessment scope |
| No idempotency key support | Not required for the core workflow validation |
| No background job runner | All required state changes can be processed synchronously |

## 10. Operational Summary

The backend is designed to answer one question reliably: can the system prevent unsafe aviation operations?

The implementation does this by combining:

- explicit state machines
- role and base scoping
- relational data integrity
- auditability
- structured error handling
- automated tests

