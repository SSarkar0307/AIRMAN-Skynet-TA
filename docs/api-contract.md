# API Contract

This document describes the HTTP contract for the Skynet backend. Responses are JSON. Authentication uses a bearer token in the `Authorization` header.

## Common Conventions

### Authentication

All protected endpoints require:

```http
Authorization: Bearer <access_token>
```

The token is issued by `POST /auth/login`.

### Response Models

| Model | Fields |
| --- | --- |
| `LoginResponse` | `access_token`, `token_type`, `user` |
| `AuthUserResponse` | `id`, `full_name`, `email`, `role`, `base_id` |
| `UserResponse` | `id`, `full_name`, `email`, `role`, `base_id` |
| `BaseResponse` | `id`, `name`, `code`, `location` |
| `AircraftResponse` | `id`, `registration`, `aircraft_type`, `base_id`, `status`, `tbo_remaining_hours` |
| `SortieResponse` | `id`, `sortie_number`, `cadet_id`, `instructor_id`, `aircraft_id`, `base_id`, `lesson_type`, `scheduled_start`, `scheduled_end`, `actual_start`, `actual_end`, `status`, `delay_minutes`, `cancel_reason`, `version` |
| `TrainingProgressResponse` | `id`, `sortie_id`, `cadet_id`, `instructor_id`, `base_id`, `lesson_type`, `maneuver_score`, `communication_score`, `situational_awareness_score`, `remarks`, `status`, `submitted_at`, `approved_by`, `approved_at`, `rejection_reason` |
| `DefectResponse` | `id`, `aircraft_id`, `sortie_id`, `reported_by`, `base_id`, `severity`, `description`, `status`, `resolved_by`, `resolved_at`, `resolution_note` |
| `AuditLogResponse` | `id`, `actor_id`, `actor_role`, `action`, `entity_type`, `entity_id`, `old_value`, `new_value`, `reason`, `timestamp` |

### Error Model

Errors use a consistent shape:

```json
{
  "error": "FORBIDDEN",
  "message": "You do not have permission to perform this action"
}
```

Validation errors may also include `field`.

### Common Error Codes

| Code | Meaning |
| --- | --- |
| `UNAUTHORIZED` | Missing or invalid bearer token |
| `FORBIDDEN` | Authenticated caller is not allowed to perform the action |
| `NOT_FOUND` | The requested record does not exist or is not visible |
| `CONFLICT` | The request conflicts with the current state or another record |
| `INVALID_STATE_TRANSITION` | The requested workflow step is not valid from the current state |
| `VALIDATION_ERROR` | Input failed schema or business-rule validation |

### Pagination And Filtering

List endpoints accept `page` and `page_size` query parameters. The implementation returns a JSON array of records rather than a pagination wrapper.

Route-specific filters include:

- `search`
- `role`
- `base_id`
- `status`
- `aircraft_id`
- `cadet_id`
- `instructor_id`
- `severity`
- `entity_type`
- `entity_id`
- `action`
- `actor_id`
- `created_from`
- `created_to`
- `start_from`
- `start_to`

## Endpoint Catalog

### Auth

| Route | Method | Auth / Role | Request Body | Response Body | Errors |
| --- | --- | --- | --- | --- | --- |
| `/auth/login` | `POST` | Public | `LoginRequest` with `email`, `role` | `LoginResponse` with token and user identity | `404 NOT_FOUND` if the email and role do not match a seeded or created user |
| `/auth/me` | `GET` | Any authenticated user | None | `AuthUserResponse` | `401 UNAUTHORIZED` if the token is missing or invalid |

### Users

| Route | Method | Auth / Role | Request Body | Response Body | Errors |
| --- | --- | --- | --- | --- | --- |
| `/users` | `GET` | Any authenticated user; non-admins are base-scoped | Query parameters: `page`, `page_size`, `search`, `role`, `base_id` | Array of `UserResponse` records | `401`, `403` for invalid scope conditions |
| `/users/{user_id}` | `GET` | Any authenticated user; admin can view all; non-admins can view own record or same-base records | Path parameter `user_id` | `UserResponse` | `404 NOT_FOUND`, `403 FORBIDDEN` |

### Bases

| Route | Method | Auth / Role | Request Body | Response Body | Errors |
| --- | --- | --- | --- | --- | --- |
| `/bases` | `GET` | Any authenticated user; non-admins are base-scoped | Query parameters: `page`, `page_size`, `search` | Array of `BaseResponse` records | `401`, `403` |
| `/bases/{base_id}` | `GET` | Any authenticated user; non-admins are base-scoped | Path parameter `base_id` | `BaseResponse` | `404 NOT_FOUND`, `403 FORBIDDEN` |

### Aircraft

| Route | Method | Auth / Role | Request Body | Response Body | Errors |
| --- | --- | --- | --- | --- | --- |
| `/aircraft` | `POST` | `ADMIN` only | `AircraftCreate` with `registration`, `aircraft_type`, `base_id`, `status`, `tbo_remaining_hours` | `AircraftResponse` | `403 FORBIDDEN`, `409 CONFLICT` if registration already exists |
| `/aircraft` | `GET` | Any authenticated user; non-admins are base-scoped | Query parameters: `page`, `page_size`, `search`, `status`, `base_id` | Array of `AircraftResponse` records | `401`, `403` |
| `/aircraft/{aircraft_id}` | `GET` | Any authenticated user; non-admins are base-scoped | Path parameter `aircraft_id` | `AircraftResponse` | `404 NOT_FOUND`, `403 FORBIDDEN` |
| `/aircraft/{aircraft_id}/ground` | `PATCH` | `ADMIN` or `MAINTENANCE_OFFICER` at the same base | None | `AircraftResponse` | `403 FORBIDDEN`, `404 NOT_FOUND`, `409 CONFLICT` |
| `/aircraft/{aircraft_id}/ready` | `PATCH` | `ADMIN` or `MAINTENANCE_OFFICER` at the same base | None | `AircraftResponse` | `403 FORBIDDEN`, `404 NOT_FOUND`, `409 CONFLICT` if severe open defects remain |

### Sorties

| Route | Method | Auth / Role | Request Body | Response Body | Errors |
| --- | --- | --- | --- | --- | --- |
| `/sorties` | `POST` | `DISPATCHER` only, same base as the sortie | `SortieCreate` with `sortie_number`, `cadet_id`, `instructor_id`, `aircraft_id`, `base_id`, `lesson_type`, `scheduled_start`, `scheduled_end` | `SortieResponse` | `403 FORBIDDEN`, `404 NOT_FOUND`, `409 CONFLICT`, `422 VALIDATION_ERROR` |
| `/sorties` | `GET` | Any authenticated user; scope depends on role | Query parameters: `page`, `page_size`, `search`, `status`, `base_id`, `aircraft_id`, `instructor_id`, `cadet_id`, `start_from`, `start_to` | Array of `SortieResponse` records | `401`, `403` |
| `/sorties/{sortie_id}` | `GET` | Any authenticated user who is allowed to view the sortie | Path parameter `sortie_id` | `SortieResponse` | `404 NOT_FOUND`, `403 FORBIDDEN` |
| `/sorties/{sortie_id}/release` | `PATCH` | `DISPATCHER` only, same base as the sortie | None | `SortieResponse` | `403 FORBIDDEN`, `409 CONFLICT`, `409 INVALID_STATE_TRANSITION`, `404 NOT_FOUND` |
| `/sorties/{sortie_id}/airborne` | `PATCH` | `DISPATCHER` only | None | `SortieResponse` | `403 FORBIDDEN`, `409 INVALID_STATE_TRANSITION`, `404 NOT_FOUND` |
| `/sorties/{sortie_id}/landed` | `PATCH` | `DISPATCHER` only | None | `SortieResponse` | `403 FORBIDDEN`, `409 INVALID_STATE_TRANSITION`, `404 NOT_FOUND` |
| `/sorties/{sortie_id}/cancel` | `PATCH` | `DISPATCHER` only | `SortieCancelRequest` with optional `cancel_reason` | `SortieResponse` | `403 FORBIDDEN`, `409 INVALID_STATE_TRANSITION`, `404 NOT_FOUND` |
| `/sorties/{sortie_id}/close` | `PATCH` | `DISPATCHER` only | None | `SortieResponse` | `403 FORBIDDEN`, `409 INVALID_STATE_TRANSITION`, `409 CONFLICT`, `404 NOT_FOUND` |

### Training Progress

| Route | Method | Auth / Role | Request Body | Response Body | Errors |
| --- | --- | --- | --- | --- | --- |
| `/training-progress` | `POST` | `INSTRUCTOR` only, or `ADMIN` | `TrainingProgressCreate` with `sortie_id`, optional draft scores, and remarks | `TrainingProgressResponse` | `403 FORBIDDEN`, `404 NOT_FOUND`, `409 CONFLICT` |
| `/training-progress/{sortie_id}` | `GET` | Any authenticated user allowed to view the progress | Path parameter `sortie_id` | `TrainingProgressResponse` | `404 NOT_FOUND`, `403 FORBIDDEN` |
| `/training-progress/{progress_id}/submit` | `PATCH` | `INSTRUCTOR` only for the assigned progress, or `ADMIN` | `TrainingSubmitRequest` with `maneuver_score`, `communication_score`, `situational_awareness_score`, `remarks` | `TrainingProgressResponse` | `403 FORBIDDEN`, `409 INVALID_STATE_TRANSITION`, `422 VALIDATION_ERROR` |
| `/training-progress/{progress_id}/approve` | `PATCH` | `CFI` only at the same base, or `ADMIN` | None | `TrainingProgressResponse` | `403 FORBIDDEN`, `409 INVALID_STATE_TRANSITION`, `404 NOT_FOUND` |
| `/training-progress/{progress_id}/reject` | `PATCH` | `CFI` only at the same base, or `ADMIN` | `TrainingRejectRequest` with `rejection_reason` | `TrainingProgressResponse` | `403 FORBIDDEN`, `409 INVALID_STATE_TRANSITION`, `404 NOT_FOUND` |

### Defects

| Route | Method | Auth / Role | Request Body | Response Body | Errors |
| --- | --- | --- | --- | --- | --- |
| `/defects` | `POST` | `DISPATCHER`, `INSTRUCTOR`, `MAINTENANCE_OFFICER`, or `ADMIN` | `DefectCreate` with `aircraft_id`, optional `sortie_id`, `severity`, `description` | `DefectResponse` | `403 FORBIDDEN`, `404 NOT_FOUND`, `409 CONFLICT` |
| `/defects` | `GET` | Any authenticated user; non-admins are base-scoped | Query parameters: `page`, `page_size`, `search`, `status`, `severity`, `base_id`, `aircraft_id` | Array of `DefectResponse` records | `401`, `403` |
| `/defects/{defect_id}` | `GET` | Any authenticated user; non-admins are base-scoped | Path parameter `defect_id` | `DefectResponse` | `404 NOT_FOUND`, `403 FORBIDDEN` |
| `/defects/{defect_id}/resolve` | `PATCH` | `MAINTENANCE_OFFICER` or `ADMIN` at the same base | `DefectResolveRequest` with optional `resolution_note` | `DefectResponse` | `403 FORBIDDEN`, `409 INVALID_STATE_TRANSITION`, `404 NOT_FOUND` |
| `/defects/{defect_id}/defer` | `PATCH` | `MAINTENANCE_OFFICER` or `ADMIN` at the same base | `DefectDeferRequest` with optional `resolution_note` | `DefectResponse` | `403 FORBIDDEN`, `409 INVALID_STATE_TRANSITION`, `404 NOT_FOUND` |

### Audit Logs

| Route | Method | Auth / Role | Request Body | Response Body | Errors |
| --- | --- | --- | --- | --- | --- |
| `/audit-logs` | `GET` | `ADMIN` can list all logs; non-admins must query a specific entity | Query parameters: `page`, `page_size`, `entity_type`, `entity_id`, `action`, `actor_id`, `created_from`, `created_to` | Array of `AuditLogResponse` records | `401`, `403` when a non-admin requests the unfiltered collection |

### Health

| Route | Method | Auth / Role | Request Body | Response Body | Errors |
| --- | --- | --- | --- | --- | --- |
| `/health` | `GET` | Public | None | `{ "status": "ok" }` | None |

## Important Endpoint Examples

### 1. Create A Sortie

Request:

```http
POST /sorties
Authorization: Bearer <dispatcher-token>
Content-Type: application/json
```

```json
{
  "sortie_number": "S2001",
  "cadet_id": 5,
  "instructor_id": 3,
  "aircraft_id": 1,
  "base_id": 1,
  "lesson_type": "Circuit Pattern",
  "scheduled_start": "2026-05-17T06:00:00Z",
  "scheduled_end": "2026-05-17T07:00:00Z"
}
```

Response:

```json
{
  "id": 42,
  "sortie_number": "S2001",
  "cadet_id": 5,
  "instructor_id": 3,
  "aircraft_id": 1,
  "base_id": 1,
  "lesson_type": "Circuit Pattern",
  "scheduled_start": "2026-05-17T06:00:00Z",
  "scheduled_end": "2026-05-17T07:00:00Z",
  "actual_start": null,
  "actual_end": null,
  "status": "SCHEDULED",
  "delay_minutes": null,
  "cancel_reason": null,
  "version": 0
}
```

### 2. Release A Sortie

Request:

```http
PATCH /sorties/42/release
Authorization: Bearer <dispatcher-token>
```

Response:

```json
{
  "id": 42,
  "sortie_number": "S2001",
  "status": "RELEASED"
}
```

### 3. Mark A Sortie Airborne

Request:

```http
PATCH /sorties/42/airborne
Authorization: Bearer <dispatcher-token>
```

Response:

```json
{
  "id": 42,
  "sortie_number": "S2001",
  "status": "AIRBORNE",
  "actual_start": "2026-05-17T06:05:00Z"
}
```

### 4. Create And Submit Training Progress

Request:

```http
POST /training-progress
Authorization: Bearer <instructor-token>
Content-Type: application/json
```

```json
{
  "sortie_id": 42,
  "maneuver_score": 4,
  "communication_score": 4,
  "situational_awareness_score": 4,
  "remarks": "Initial evaluation notes."
}
```

Response:

```json
{
  "id": 18,
  "sortie_id": 42,
  "cadet_id": 5,
  "instructor_id": 3,
  "base_id": 1,
  "lesson_type": "Circuit Pattern",
  "maneuver_score": 4,
  "communication_score": 4,
  "situational_awareness_score": 4,
  "remarks": "Initial evaluation notes.",
  "status": "DRAFT",
  "submitted_at": null,
  "approved_by": null,
  "approved_at": null,
  "rejection_reason": null
}
```

### 5. Approve Training Progress

Request:

```http
PATCH /training-progress/18/approve
Authorization: Bearer <cfi-token>
```

Response:

```json
{
  "id": 18,
  "sortie_id": 42,
  "status": "APPROVED",
  "approved_by": 4,
  "approved_at": "2026-05-17T08:00:00Z"
}
```

### 6. Create A Defect

Request:

```http
POST /defects
Authorization: Bearer <maintenance-token>
Content-Type: application/json
```

```json
{
  "aircraft_id": 1,
  "sortie_id": 42,
  "severity": "CRITICAL",
  "description": "Engine oil pressure dropped below minimum during landing roll."
}
```

Response:

```json
{
  "id": 9,
  "aircraft_id": 1,
  "sortie_id": 42,
  "reported_by": 6,
  "base_id": 1,
  "severity": "CRITICAL",
  "description": "Engine oil pressure dropped below minimum during landing roll.",
  "status": "OPEN",
  "resolved_by": null,
  "resolved_at": null,
  "resolution_note": null
}
```

### 7. Ground An Aircraft

Request:

```http
PATCH /aircraft/1/ground
Authorization: Bearer <maintenance-token>
```

Response:

```json
{
  "id": 1,
  "registration": "VT-ABC",
  "status": "GROUNDED"
}
```

### 8. List Audit Logs

Request:

```http
GET /audit-logs?entity_type=sortie&entity_id=42&page=1&page_size=10
Authorization: Bearer <admin-token>
```

Response:

```json
[
  {
    "id": 120,
    "actor_id": 2,
    "actor_role": "DISPATCHER",
    "action": "SORTIE_RELEASED",
    "entity_type": "sortie",
    "entity_id": 42,
    "old_value": {
      "status": "SCHEDULED"
    },
    "new_value": {
      "status": "RELEASED"
    },
    "reason": null,
    "timestamp": "2026-05-17T06:00:10Z"
  }
]
```

## Complete Operational Flow

The assessment workflow is implemented across the following routes in order:

1. `POST /auth/login`
2. `POST /sorties`
3. `PATCH /sorties/{id}/release`
4. `PATCH /sorties/{id}/airborne`
5. `PATCH /sorties/{id}/landed`
6. `POST /training-progress`
7. `PATCH /training-progress/{id}/submit`
8. `PATCH /training-progress/{id}/approve` or `PATCH /training-progress/{id}/reject`
9. `PATCH /sorties/{id}/close`
10. `POST /defects` when a safety issue is reported
11. `PATCH /aircraft/{id}/ground` when maintenance grounds the aircraft
12. `PATCH /defects/{id}/resolve` or `PATCH /defects/{id}/defer`
13. `PATCH /aircraft/{id}/ready` after severe open defects are cleared
14. `GET /audit-logs` to review the operational trail

This sequence mirrors the aviation workflow described in the assessment and is enforced in the service layer.
