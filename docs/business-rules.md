# Business Rules

This document captures the operational rules enforced by the backend.

## Core Workflow

### Sortie Flow

1. Sortie is scheduled.
2. Dispatcher releases the sortie.
3. Aircraft becomes airborne.
4. Aircraft lands.
5. Instructor creates training progress.
6. Instructor submits the evaluation.
7. CFI approves or rejects the evaluation.
8. Dispatcher closes the sortie after approval and safety checks.

### Safety Flow

1. Defect is reported.
2. High or critical defects ground the aircraft.
3. Maintenance resolves or defers the defect.
4. Aircraft returns to ready state only when severe open defects are cleared.

## Sortie Rules

| Rule | Result |
| --- | --- |
| `SCHEDULED -> RELEASED` only | Other transitions are rejected |
| `RELEASED -> AIRBORNE` only | Aircraft must be available and not grounded |
| `AIRBORNE -> LANDED` only | Landing must follow airborne status |
| `LANDED -> TRAINING_SUBMITTED` only | Training progress must exist |
| `TRAINING_SUBMITTED -> TRAINING_APPROVED` only | CFI approval required |
| `TRAINING_APPROVED -> CLOSED` only | Training must be approved and the aircraft must be clear of blocking defects |
| `CANCELLED` is terminal | Closed and cancelled sorties cannot be reopened |

## Aircraft Rules

| Rule | Result |
| --- | --- |
| One aircraft cannot fly overlapping sorties | Overlapping assignments raise `CONFLICT` |
| Grounded aircraft cannot be dispatched | Release and assignment are blocked |
| Severe open defects block readiness | `READY` is denied until the defect is resolved or deferred |
| Maintenance officers and admins control readiness | Other roles cannot ground or ready aircraft |

## Training Progress Rules

| Rule | Result |
| --- | --- |
| Only the assigned instructor can create or submit progress | Other callers receive `FORBIDDEN` |
| CFI approval is required for closure | Sorties cannot close before training approval |
| Scores must be between 1 and 5 | Validation error is returned otherwise |
| Remarks are required on submission | Empty remarks are rejected |
| Approved progress is visible to cadets | Rejected or draft progress remains restricted |

## Defect Rules

| Rule | Result |
| --- | --- |
| Defects are base-scoped | Non-admin users can only act on their own base |
| Critical and high defects ground the aircraft | The aircraft cannot be readied until the defect is cleared |
| Defect resolution is maintenance-controlled | Only maintenance officers and admins can resolve or defer |
| Defect audit history is mandatory | Every create/resolve/defer action is logged |

## Access Control Rules

| Role | Key Limits |
| --- | --- |
| `ADMIN` | Full access across the system |
| `DISPATCHER` | Cannot approve training progress |
| `INSTRUCTOR` | Cannot approve or reject training progress |
| `CFI` | Cannot manage aircraft readiness unless acting as admin |
| `CADET` | Read-only participation in own records |
| `MAINTENANCE_OFFICER` | Cannot approve training progress |

## Audit Trail Rules

| Rule | Result |
| --- | --- |
| Every critical operational action is audited | Dispatch, training, defect, and readiness actions create audit rows |
| Audit rows record actor and reason | The history can be traced to a person and a cause |
| Old and new values are stored | Operational changes remain explainable after the fact |

## Invalid Actions That Must Be Rejected

| Invalid Action | Expected Result |
| --- | --- |
| Cadet tries to approve training | `FORBIDDEN` |
| Dispatcher tries to approve training | `FORBIDDEN` |
| Sortie jumps from `SCHEDULED` to `AIRBORNE` | `INVALID_STATE_TRANSITION` |
| Aircraft with open critical defect is marked ready | `CONFLICT` |
| Aircraft is assigned to overlapping sorties | `CONFLICT` |
| Draft training is approved directly | `INVALID_STATE_TRANSITION` |
| Closed sortie is cancelled again | `INVALID_STATE_TRANSITION` |

